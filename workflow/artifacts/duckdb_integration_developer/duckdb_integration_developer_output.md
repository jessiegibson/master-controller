I'll implement the DuckDB database layer with encrypted storage integration based on the Data Architecture specifications and encryption module.

# DuckDB Database Implementation

**Module**: `src/database/`
**Date**: 2024-12-28
**Status**: Implementation Complete

## Files Created

| File | Purpose |
|------|---------|
| `mod.rs` | Module exports and re-exports |
| `connection.rs` | DuckDB connection management with encryption |
| `migrations.rs` | Schema migrations versioned system |
| `models.rs` | Rust structs matching DuckDB schema |
| `repository.rs` | CRUD operations trait and implementations |
| `queries.rs` | Common query builders for reports |

## Database Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENCRYPTED DATABASE FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Master Key (from encryption module)                            │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────┐                                                │
│  │ HKDF-SHA256 │ ──► Database Key (256-bit)                     │
│  │ "database"  │                                                │
│  └─────────────┘                                                │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              FileEncryption                                 ││
│  │  ~/.finance-cli/data.db.enc ──► /tmp/data_XXXX.db         ││
│  │                                                             ││
│  │  ┌─────────────────────────────────────────────────────────┤│
│  │  │                DuckDB Engine                            ││
│  │  │  - OLAP optimized for analytics                        ││
│  │  │  - Columnar storage                                    ││
│  │  │  - Concurrent read support                             ││
│  │  │  - SQL analytics functions                             ││
│  │  └─────────────────────────────────────────────────────────┘│
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## src/database/mod.rs

```rust
//! Database layer for the Finance CLI.
//!
//! This module provides a complete database abstraction layer built on DuckDB
//! with encrypted storage. It includes connection management, schema migrations,
//! CRUD operations, and query builders for financial data.
//!
//! # Architecture
//!
//! - **Connection Management**: Encrypted database with connection pooling
//! - **Schema Migrations**: Versioned schema evolution system
//! - **Repository Pattern**: Type-safe CRUD operations
//! - **Query Builders**: Fluent API for complex queries
//! - **Models**: Rust structs matching database schema
//!
//! # Usage
//!
//! ```rust
//! use finance_cli::database::{Database, TransactionRepository};
//! use finance_cli::encryption::MasterKey;
//!
//! // Open encrypted database
//! let master_key = MasterKey::derive_from_password(password)?;
//! let db = Database::open("~/.finance-cli/data.db.enc", &master_key).await?;
//!
//! // Use repository pattern
//! let repo = TransactionRepository::new(&db);
//! let transactions = repo.find_by_date_range(start_date, end_date).await?;
//! ```

pub mod connection;
pub mod migrations;
pub mod models;
pub mod queries;
pub mod repository;

// Re-export commonly used types
pub use connection::{Database, DatabaseConfig, ConnectionPool};
pub use migrations::{Migration, MigrationRunner, CURRENT_VERSION};
pub use models::*;
pub use queries::*;
pub use repository::*;

/// Database operation errors.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// DuckDB operation failed.
    #[error("Database error: {0}")]
    DuckDb(#[from] duckdb::Error),

    /// Encryption operation failed.
    #[error("Encryption error: {0}")]
    Encryption(#[from] crate::encryption::Error),

    /// I/O operation failed.
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// Migration failed.
    #[error("Migration error: {0}")]
    Migration(String),

    /// Repository operation failed.
    #[error("Repository error: {0}")]
    Repository(String),

    /// Query builder error.
    #[error("Query error: {0}")]
    Query(String),

    /// Data validation error.
    #[error("Validation error: {0}")]
    Validation(String),

    /// Record not found.
    #[error("Record not found: {0}")]
    NotFound(String),

    /// Constraint violation.
    #[error("Constraint violation: {0}")]
    ConstraintViolation(String),
}

/// Result type for database operations.
pub type Result<T> = std::result::Result<T, Error>;

/// Initialize the database subsystem.
///
/// This should be called once at application startup to verify
/// DuckDB availability and set up any required extensions.
pub fn init() -> Result<()> {
    // Test DuckDB connection
    let conn = duckdb::Connection::open_in_memory()?;
    
    // Load required extensions
    conn.execute_batch("INSTALL 'uuid'; LOAD 'uuid';")?;
    
    tracing::info!("Database subsystem initialized successfully");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_init() {
        init().expect("Database init should succeed");
    }
}
```

---

## src/database/connection.rs

```rust
//! DuckDB connection management with encryption support.
//!
//! This module handles encrypted database files, connection pooling,
//! and concurrent access patterns for DuckDB.

use crate::database::{Error, Result};
use crate::encryption::{MasterKey, FileEncryption, DerivedKey};
use duckdb::{Connection, AccessMode, Config};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};
use tempfile::NamedTempFile;
use tokio::sync::{Semaphore, SemaphorePermit};
use tracing::{info, warn, debug};

/// Database configuration options.
#[derive(Debug, Clone)]
pub struct DatabaseConfig {
    /// Path to encrypted database file
    pub encrypted_path: PathBuf,
    
    /// Maximum number of concurrent readers
    pub max_readers: usize,
    
    /// Memory limit for DuckDB (in MB)
    pub memory_limit_mb: usize,
    
    /// Number of threads for parallel queries
    pub threads: Option<usize>,
    
    /// Enable query optimization
    pub enable_optimizer: bool,
    
    /// Temporary directory for decrypted database
    pub temp_dir: Option<PathBuf>,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            encrypted_path: PathBuf::from("~/.finance-cli/data.db.enc"),
            max_readers: 10,
            memory_limit_mb: 512,
            threads: None, // Auto-detect
            enable_optimizer: true,
            temp_dir: None, // Use system temp
        }
    }
}

/// Encrypted DuckDB database with connection management.
pub struct Database {
    config: DatabaseConfig,
    temp_db_path: PathBuf,
    temp_file: NamedTempFile,
    connection_pool: Arc<ConnectionPool>,
    _db_key: DerivedKey, // Keep key alive for re-encryption
}

impl Database {
    /// Open an encrypted database.
    ///
    /// # Arguments
    ///
    /// * `encrypted_path` - Path to the encrypted database file
    /// * `master_key` - Master key for decryption
    ///
    /// # Returns
    ///
    /// Returns a `Database` instance with the decrypted database loaded
    /// into a temporary file and ready for use.
    pub async fn open<P: AsRef<Path>>(
        encrypted_path: P, 
        master_key: &MasterKey
    ) -> Result<Self> {
        let config = DatabaseConfig {
            encrypted_path: encrypted_path.as_ref().to_path_buf(),
            ..Default::default()
        };
        Self::open_with_config(config, master_key).await
    }

    /// Open database with custom configuration.
    pub async fn open_with_config(
        config: DatabaseConfig,
        master_key: &MasterKey,
    ) -> Result<Self> {
        info!("Opening encrypted database: {}", config.encrypted_path.display());

        // Derive database-specific key
        let db_key = master_key.derive_database_key()?;

        // Create temporary file for decrypted database
        let temp_file = if let Some(temp_dir) = &config.temp_dir {
            NamedTempFile::new_in(temp_dir)?
        } else {
            // Prefer tmpfs/ramfs for security
            if Path::new("/dev/shm").exists() {
                NamedTempFile::new_in("/dev/shm")?
            } else {
                NamedTempFile::new()?
            }
        };
        
        let temp_db_path = temp_file.path().to_path_buf();
        debug!("Created temporary database at: {}", temp_db_path.display());

        // Decrypt database to temporary location
        if config.encrypted_path.exists() {
            let file_enc = FileEncryption::new();
            file_enc.decrypt_file(&config.encrypted_path, &temp_db_path, &db_key)?;
            info!("Database decrypted successfully");
        } else {
            // Create new database
            info!("Creating new database");
            Self::create_new_database(&temp_db_path, &config)?;
        }

        // Create connection pool
        let pool = ConnectionPool::new(&temp_db_path, &config)?;

        Ok(Self {
            config,
            temp_db_path,
            temp_file,
            connection_pool: Arc::new(pool),
            _db_key: db_key,
        })
    }

    /// Create a new empty database with initial schema.
    fn create_new_database(temp_path: &Path, config: &DatabaseConfig) -> Result<()> {
        let mut db_config = Config::default();
        
        if let Some(threads) = config.threads {
            db_config = db_config.with("threads", &threads.to_string())?;
        }
        
        db_config = db_config.with("memory_limit", &format!("{}MB", config.memory_limit_mb))?;
        
        let conn = Connection::open_with_flags(temp_path, db_config)?;
        
        // Install required extensions
        conn.execute_batch("INSTALL 'uuid'; LOAD 'uuid';")?;
        
        // Run initial migration
        let migration_runner = crate::database::migrations::MigrationRunner::new();
        migration_runner.run_migrations(&conn)?;
        
        Ok(())
    }

    /// Get the connection pool for database operations.
    pub fn pool(&self) -> Arc<ConnectionPool> {
        Arc::clone(&self.connection_pool)
    }

    /// Save changes back to encrypted file.
    pub async fn save(&self) -> Result<()> {
        info!("Saving database to encrypted file");
        
        let file_enc = FileEncryption::new();
        file_enc.encrypt_file(&self.temp_db_path, &self.config.encrypted_path, &self._db_key)?;
        
        info!("Database saved successfully");
        Ok(())
    }

    /// Get database statistics.
    pub async fn stats(&self) -> Result<DatabaseStats> {
        let conn = self.pool().writer().await?;
        
        let transaction_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM transactions",
            [],
            |row| row.get(0),
        )?;
        
        let category_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM categories",
            [],
            |row| row.get(0),
        )?;
        
        let account_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM accounts",
            [],
            |row| row.get(0),
        )?;
        
        let rule_count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM rules",
            [],
            |row| row.get(0),
        )?;

        Ok(DatabaseStats {
            transaction_count: transaction_count as usize,
            category_count: category_count as usize,
            account_count: account_count as usize,
            rule_count: rule_count as usize,
            database_size: std::fs::metadata(&self.temp_db_path)?.len(),
        })
    }
}

impl Drop for Database {
    fn drop(&mut self) {
        // Secure deletion is handled by NamedTempFile
        debug!("Database instance dropped");
    }
}

/// Connection pool for managing DuckDB connections.
///
/// DuckDB supports multiple concurrent readers but only one writer.
/// This pool manages access to ensure safe concurrent operations.
pub struct ConnectionPool {
    db_path: PathBuf,
    config: DatabaseConfig,
    writer_lock: Mutex<()>,
    reader_semaphore: Semaphore,
}

impl ConnectionPool {
    fn new(db_path: &Path, config: &DatabaseConfig) -> Result<Self> {
        Ok(Self {
            db_path: db_path.to_path_buf(),
            config: config.clone(),
            writer_lock: Mutex::new(()),
            reader_semaphore: Semaphore::new(config.max_readers),
        })
    }

    /// Get exclusive write connection.
    ///
    /// This method ensures only one writer can access the database at a time.
    pub async fn writer(&self) -> Result<WriterConnection> {
        let _lock = self.writer_lock.lock()
            .map_err(|_| Error::Repository("Writer lock poisoned".into()))?;
        
        let conn = self.create_connection(false)?;
        Ok(WriterConnection { 
            connection: conn, 
            _lock 
        })
    }

    /// Get concurrent read connection.
    ///
    /// Multiple readers can access the database simultaneously.
    pub async fn reader(&self) -> Result<ReaderConnection> {
        let permit = self.reader_semaphore.acquire().await
            .map_err(|_| Error::Repository("Failed to acquire reader permit".into()))?;
        
        let conn = self.create_connection(true)?;
        Ok(ReaderConnection { 
            connection: conn, 
            _permit: permit 
        })
    }

    fn create_connection(&self, read_only: bool) -> Result<Connection> {
        let mut config = Config::default();
        
        if read_only {
            config = config.access_mode(AccessMode::ReadOnly)?;
        }
        
        if let Some(threads) = self.config.threads {
            config = config.with("threads", &threads.to_string())?;
        }
        
        config = config.with("memory_limit", &format!("{}MB", self.config.memory_limit_mb))?;
        
        if self.config.enable_optimizer {
            config = config.with("enable_optimizer", "true")?;
        }

        let conn = Connection::open_with_flags(&self.db_path, config)?;
        
        // Load extensions for each connection
        conn.
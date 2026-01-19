//! Database connection and initialization

use rusqlite::{Connection, Result as SqlResult};
use std::path::Path;

use super::schema::{DEFAULT_AGENTS_SQL, SCHEMA_SQL};

/// Database wrapper for SQLite connection
pub struct Database {
    conn: Connection,
}

impl Database {
    /// Open or create a database at the specified path
    pub fn open<P: AsRef<Path>>(path: P) -> SqlResult<Self> {
        let conn = Connection::open(path)?;
        let db = Self { conn };
        db.initialize()?;
        Ok(db)
    }

    /// Create an in-memory database (for testing)
    pub fn in_memory() -> SqlResult<Self> {
        let conn = Connection::open_in_memory()?;
        let db = Self { conn };
        db.initialize()?;
        Ok(db)
    }

    /// Initialize the database schema
    fn initialize(&self) -> SqlResult<()> {
        self.conn.execute_batch(SCHEMA_SQL)?;
        self.conn.execute_batch(DEFAULT_AGENTS_SQL)?;
        Ok(())
    }

    /// Get a reference to the underlying connection
    pub fn conn(&self) -> &Connection {
        &self.conn
    }

    /// Get a mutable reference to the underlying connection
    pub fn conn_mut(&mut self) -> &mut Connection {
        &mut self.conn
    }

    /// Begin a transaction
    pub fn transaction(&mut self) -> SqlResult<rusqlite::Transaction<'_>> {
        self.conn.transaction()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_in_memory_database() {
        let db = Database::in_memory().expect("Failed to create in-memory database");

        // Verify tables exist
        let count: i64 = db
            .conn()
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='tasks'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(count, 1);
    }

    #[test]
    fn test_default_agents_inserted() {
        let db = Database::in_memory().expect("Failed to create in-memory database");

        let count: i64 = db
            .conn()
            .query_row("SELECT COUNT(*) FROM agents", [], |row| row.get(0))
            .unwrap();
        assert!(count >= 20, "Expected at least 20 default agents");
    }
}

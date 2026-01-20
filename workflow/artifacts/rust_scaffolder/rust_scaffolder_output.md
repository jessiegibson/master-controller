# Scaffolding Report

**Project**: Privacy-First Personal Finance CLI
**Date**: 2024-12-28
**Status**: Complete

## Created Structure

```
finance-cli/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── docs/
│   ├── requirements/
│   ├── architecture/
│   └── design/
├── src/
│   ├── main.rs
│   ├── lib.rs
│   ├── cli/
│   │   ├── mod.rs
│   │   ├── commands/
│   │   │   ├── mod.rs
│   │   │   ├── transaction.rs
│   │   │   ├── report.rs
│   │   │   ├── category.rs
│   │   │   └── config.rs
│   │   └── output.rs
│   ├── parsers/
│   │   ├── mod.rs
│   │   ├── csv.rs
│   │   ├── qfx.rs
│   │   └── detect.rs
│   ├── categorization/
│   │   ├── mod.rs
│   │   ├── engine.rs
│   │   ├── rules.rs
│   │   └── ml.rs
│   ├── calculator/
│   │   ├── mod.rs
│   │   ├── pnl.rs
│   │   ├── cashflow.rs
│   │   └── metrics.rs
│   ├── reports/
│   │   ├── mod.rs
│   │   ├── generator.rs
│   │   ├── formatters.rs
│   │   └── exports.rs
│   ├── tax/
│   │   ├── mod.rs
│   │   ├── schedule_c.rs
│   │   └── mappings.rs
│   ├── database/
│   │   ├── mod.rs
│   │   ├── connection.rs
│   │   ├── queries.rs
│   │   ├── migrations.rs
│   │   └── models.rs
│   ├── encryption/
│   │   ├── mod.rs
│   │   ├── cipher.rs
│   │   ├── key.rs
│   │   └── secure_memory.rs
│   ├── config/
│   │   ├── mod.rs
│   │   └── settings.rs
│   ├── logging/
│   │   ├── mod.rs
│   │   ├── logger.rs
│   │   └── formatters.rs
│   ├── error/
│   │   ├── mod.rs
│   │   └── types.rs
│   └── models/
│       ├── mod.rs
│       ├── transaction.rs
│       ├── category.rs
│       ├── account.rs
│       └── rule.rs
├── tests/
│   ├── integration/
│   │   ├── mod.rs
│   │   ├── parser_tests.rs
│   │   ├── categorization_tests.rs
│   │   └── report_tests.rs
│   └── fixtures/
│       ├── chase_sample.csv
│       ├── bofa_sample.csv
│       └── test_db.sql
├── benches/
│   ├── parser_bench.rs
│   └── categorization_bench.rs
├── Cargo.toml
├── Cargo.lock
├── rustfmt.toml
├── .gitignore
├── README.md
├── CHANGELOG.md
└── LICENSE
```

---

## Cargo.toml

```toml
[package]
name = "finance-cli"
version = "0.1.0"
edition = "2021"
authors = ["Finance CLI Team"]
description = "Privacy-first personal finance management CLI"
license = "MIT"
repository = "https://github.com/user/finance-cli"
readme = "README.md"
keywords = ["finance", "cli", "privacy", "budgeting"]
categories = ["command-line-utilities", "finance"]

[dependencies]
# CLI and argument parsing
clap = { version = "4.4", features = ["derive", "color", "help", "usage", "error-context"] }
clap_complete = "4.4"

# Database
duckdb = { version = "0.10", features = ["bundled"] }

# Encryption and security
aes-gcm = "0.10"
pbkdf2 = { version = "0.12", features = ["simple"] }
rand = "0.8"
zeroize = { version = "1.7", features = ["zeroize_derive"] }
secrecy = "0.8"

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
toml = "0.8"

# Date and time handling
chrono = { version = "0.4", features = ["serde"] }

# File parsing
csv = "1.3"
quick-xml = { version = "0.31", features = ["serialize"] }

# Error handling
thiserror = "1.0"
anyhow = "1.0"

# Async runtime (for potential future use)
tokio = { version = "1.35", features = ["rt", "rt-multi-thread", "macros", "fs", "io-util"], optional = true }

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-appender = "0.2"

# Terminal UI
console = "0.15"
indicatif = "0.17"
dialoguer = "0.11"
colored = "2.1"

# Utilities
uuid = { version = "1.6", features = ["v4", "serde"] }
regex = "1.10"
walkdir = "2.4"
tempfile = "3.8"

[dev-dependencies]
rstest = "0.18"
tempfile = "3.8"
criterion = { version = "0.5", features = ["html_reports"] }
proptest = "1.4"
serial_test = "3.0"

[features]
default = []
async = ["tokio"]

[[bench]]
name = "parser_bench"
harness = false

[[bench]]
name = "categorization_bench"
harness = false

[profile.release]
lto = true
codegen-units = 1
panic = "abort"
strip = true

[profile.dev]
debug = true

[lints.rust]
unsafe_code = "forbid"
unused_imports = "warn"
unused_variables = "warn"
dead_code = "warn"

[lints.clippy]
unwrap_used = "warn"
expect_used = "warn"
panic = "warn"
todo = "warn"
unimplemented = "warn"
dbg_macro = "warn"
print_stdout = "warn"
print_stderr = "warn"
missing_docs_in_private_items = "warn"
```

---

## src/main.rs

```rust
//! Finance CLI - Privacy-first personal finance management
//!
//! This is the main entry point for the CLI application.
//!
//! The application provides comprehensive financial management capabilities:
//! - Import transactions from 8 major banks (CSV/QFX formats)
//! - Rule-based automatic categorization
//! - Financial reports (P&L, Cash Flow, Schedule C)
//! - Local encrypted storage with no cloud dependencies
//! - Privacy-first design with AES-256-GCM encryption

use finance_cli::run;
use std::process::ExitCode;

/// Main entry point for the Finance CLI application.
///
/// Sets up logging, handles global error cases, and delegates to the main
/// application logic in the library crate.
///
/// # Exit Codes
/// - 0: Success
/// - 1: General application error
/// - 2: Configuration error
/// - 3: Permission/security error
fn main() -> ExitCode {
    // Initialize logging early to catch any startup issues
    if let Err(e) = finance_cli::logging::init() {
        eprintln!("Failed to initialize logging: {e}");
        return ExitCode::FAILURE;
    }

    // Run the main application logic
    match run() {
        Ok(()) => {
            tracing::info!("Application completed successfully");
            ExitCode::SUCCESS
        }
        Err(e) => {
            tracing::error!("Application error: {e}");
            eprintln!("Error: {e}");
            
            // Provide context-specific exit codes for better error handling
            match e.downcast_ref::<finance_cli::error::Error>() {
                Some(finance_cli::error::Error::Config(_)) => ExitCode::from(2),
                Some(finance_cli::error::Error::Encryption(_)) => ExitCode::from(3),
                Some(finance_cli::error::Error::Io { .. }) => ExitCode::from(3),
                _ => ExitCode::FAILURE,
            }
        }
    }
}
```

---

## src/lib.rs

```rust
//! Finance CLI Library
//!
//! This crate provides the core functionality for the Privacy-First Personal Finance CLI application.
//!
//! # Architecture
//!
//! The application follows a layered architecture:
//!
//! - **Interface Layer**: [`cli`] - Command-line interface and user interaction
//! - **Business Logic Layer**: [`categorization`], [`calculator`], [`reports`], [`tax`] - Core business logic
//! - **Data Layer**: [`parsers`], [`database`], [`config`] - Data access and management
//! - **Infrastructure Layer**: [`encryption`], [`logging`], [`error`] - Cross-cutting concerns
//!
//! # Security
//!
//! All sensitive data is encrypted at rest using AES-256-GCM with keys derived from user passwords
//! via PBKDF2. The application operates completely offline with no external network connections.
//!
//! # Privacy
//!
//! - No telemetry or analytics
//! - No cloud storage or external APIs
//! - All data remains on local filesystem
//! - Encrypted storage prevents unauthorized access
//!
//! # Example Usage
//!
//! ```ignore
//! use finance_cli::run;
//!
//! // Run the CLI application
//! run()?;
//! ```

// Interface Layer
pub mod cli;

// Business Logic Layer
pub mod calculator;
pub mod categorization;
pub mod reports;
pub mod tax;

// Data Layer
pub mod config;
pub mod database;
pub mod parsers;

// Infrastructure Layer
pub mod encryption;
pub mod error;
pub mod logging;

// Shared Models
pub mod models;

// Re-export commonly used types
pub use error::{Error, Result};

/// Run the Finance CLI application.
///
/// This is the main entry point called from `main.rs`. It handles:
/// 1. Command-line argument parsing
/// 2. Configuration loading
/// 3. Database initialization
/// 4. Command execution
/// 5. Graceful error handling
///
/// # Errors
///
/// Returns an error if:
/// - Command-line arguments are invalid
/// - Configuration cannot be loaded
/// - Database cannot be initialized
/// - Command execution fails
/// - Encryption/decryption fails
///
/// # Example
///
/// ```ignore
/// use finance_cli::run;
///
/// match run() {
///     Ok(()) => println!("Success!"),
///     Err(e) => eprintln!("Error: {e}"),
/// }
/// ```
pub fn run() -> Result<()> {
    tracing::info!("Starting Finance CLI application");

    // Parse command line arguments
    let cli_args = cli::parse_args()?;
    tracing::debug!("Parsed CLI arguments: {:?}", cli_args);

    // Load or initialize configuration
    let config = config::load_or_create()?;
    tracing::debug!("Loaded configuration");

    // Initialize database connection
    let db = database::initialize(&config)?;
    tracing::debug!("Database initialized");

    // Execute the requested command
    cli::execute_command(cli_args, config, db)?;

    tracing::info!("Application completed successfully");
    Ok(())
}

/// Initialize the application for testing.
///
/// Sets up a temporary database and configuration for integration tests.
/// This is used by the test suite to create isolated test environments.
///
/// # Errors
///
/// Returns an error if test setup fails.
#[cfg(test)]
pub fn init_for_testing() -> Result<(config::Config, database::Connection)> {
    use tempfile::TempDir;
    
    let temp_dir = TempDir::new().map_err(|e| Error::Io {
        path: std::env::temp_dir(),
        source: e,
    })?;
    
    let config = config::Config::for_testing(temp_dir.path())?;
    let db = database::initialize(&config)?;
    
    Ok((config, db))
}
```

---

## Module Structure

### src/cli/mod.rs

```rust
//! Command-line interface module.
//!
//! This module handles all user interaction through the command line:
//! - Argument parsing with clap
//! - Command dispatch to appropriate handlers
//! - Output formatting and display
//! - Interactive prompts and confirmations
//! - Progress indication for long operations
//!
//! # Commands
//!
//! The CLI supports the following top-level commands:
//! - `transaction`: Import, list, categorize, and manage transactions
//! - `report`: Generate financial reports (P&L, Cash Flow, Schedule C)
//! - `category`: Manage expense categories and rules
//! - `config`: Application configuration management
//! - `backup`: Database backup and restore operations
//!
//! # Example Usage
//!
//! ```bash
//! # Import transactions from a CSV file
//! finance transaction import ~/Downloads/statement.csv
//!
//! # Generate a P&L report for 2024
//! finance report pnl --year 2024 --format csv
//!
//! # Interactively categorize uncategorized transactions
//! finance transaction categorize
//! ```

use crate::{config::Config, database::Connection, error::Result};
use clap::{Parser, Subcommand};

pub mod commands;
pub mod output;

/// Main CLI application structure.
///
/// This defines the top-level command structure and global options.
#[derive(Parser, Debug)]
#[command(
    name = "finance",
    about = "Privacy-first personal finance management CLI",
    long_about = "A privacy-first personal finance management tool for freelancers and small business owners. 
Import transactions from bank exports, categorize them automatically, and generate tax-ready financial reports. 
All data is encrypted and stored locally with no cloud dependencies.",
    version
)]
pub struct Cli {
    /// Global options available to all commands
    #[command(flatten)]
    pub global: GlobalOptions,

    /// The command to execute
    #[command(subcommand)]
    pub command: Commands,
}

/// Global options available to all commands.
#[derive(Parser, Debug)]
pub struct GlobalOptions {
    /// Enable verbose logging
    #[arg(short, long, global = true)]
    pub verbose: bool,

    /// Suppress all output except errors
    #[arg(short, long, global = true, conflicts_with = "verbose")]
    pub quiet: bool,

    /// Configuration file path (defaults to ~/.finance-cli/config.toml)
    #[arg(short, long, global = true)]
    pub config: Option<std::path::PathBuf>,

    /// Database file path (defaults to ~/.finance-cli/finance.db)
    #[arg(short, long, global = true)]
    pub database: Option<std::path::PathBuf>,
}

/// Available CLI commands.
#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Transaction management (import, list, categorize)
    #[command(alias = "tx")]
    Transaction(commands::TransactionCommand),

    /// Generate financial reports
    Report(commands::ReportCommand),

    /// Manage categories and categorization rules
    Category(commands::CategoryCommand),

    /// Application configuration
    Config(commands::ConfigComman
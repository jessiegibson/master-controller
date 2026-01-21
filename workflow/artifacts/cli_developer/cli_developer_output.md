# Sprint S1-17: CLI Implementation

I'll implement the command-line interface using clap for the Finance CLI application, following the specifications and integrating with all other modules.

## File Structure

```
src/cli/
├── mod.rs              # CLI module exports
├── app.rs              # Main clap application
├── commands/
│   ├── mod.rs          # Command registry
│   ├── import.rs       # Import command
│   ├── list.rs         # List command
│   ├── categorize.rs   # Categorize command
│   ├── report.rs       # Report commands
│   ├── category.rs     # Category management
│   ├── account.rs      # Account management
│   ├── config.rs       # Configuration
│   └── interactive.rs  # Interactive mode
├── output/
│   ├── mod.rs          # Output formatting
│   ├── table.rs        # Table rendering
│   ├── json.rs         # JSON output
│   └── progress.rs     # Progress indicators
├── input/
│   ├── mod.rs          # Input utilities
│   ├── prompt.rs       # User prompts
│   └── secure.rs       # Secure input
└── error.rs            # CLI error handling
```

## Core Implementation

### CLI Module Root (`src/cli/mod.rs`)

```rust
//! Command-line interface module for Finance CLI.

pub mod app;
pub mod commands;
pub mod output;
pub mod input;
pub mod error;

pub use app::{Cli, run_cli};
pub use error::{CliError, CliResult, CliExitCode};

use crate::{
    config::AppConfig,
    database::EncryptedDatabase,
    error::Result,
};
use std::path::PathBuf;

/// Context available to all command handlers.
pub struct CommandContext {
    /// Database connection
    pub db: EncryptedDatabase,
    
    /// Configuration
    pub config: AppConfig,
    
    /// Output format
    pub output_format: OutputFormat,
    
    /// Color enabled
    pub color_enabled: bool,
    
    /// Verbosity level
    pub verbosity: u8,
    
    /// Quiet mode
    pub quiet: bool,
}

impl CommandContext {
    /// Create context from CLI args.
    pub async fn from_cli(cli: &Cli) -> Result<Self> {
        let config = AppConfig::load(cli.config.as_deref())?;
        
        // Prompt for passphrase
        let passphrase = crate::cli::input::secure::prompt_passphrase("Enter passphrase: ")?;
        
        let db = EncryptedDatabase::open(&config.database_path, passphrase)?;
        
        let color_enabled = !cli.no_color && atty::is(atty::Stream::Stdout);
        
        Ok(Self {
            db,
            config,
            output_format: cli.format,
            color_enabled,
            verbosity: cli.verbose,
            quiet: cli.quiet,
        })
    }
}

/// Output format options.
#[derive(Copy, Clone, PartialEq, Eq, clap::ValueEnum)]
pub enum OutputFormat {
    /// Pretty table format
    Table,
    /// JSON format
    Json,
    /// CSV format
    Csv,
    /// Plain text
    Plain,
}

/// Result of a command execution.
pub enum CommandResult {
    /// Success with optional message
    Success(Option<String>),
    
    /// Success with data to display
    Data(Box<dyn crate::cli::output::Displayable>),
    
    /// Partial success with warnings
    Partial {
        message: String,
        warnings: Vec<String>,
    },
}
```

### Main Application (`src/cli/app.rs`)

```rust
//! Main clap application definition.

use clap::{Parser, Subcommand, Args};
use std::path::PathBuf;
use std::process::ExitCode;

use super::{
    CommandContext, CommandResult, OutputFormat,
    commands::*,
    error::{CliError, CliExitCode, format_error},
    output::output_result,
};

/// Finance CLI - Privacy-first personal finance management.
#[derive(Parser)]
#[command(name = "finance")]
#[command(author = "Finance CLI Team")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(about = "Privacy-first personal finance management")]
#[command(long_about = "A command-line tool for managing personal finances with strong privacy guarantees.")]
#[command(propagate_version = true)]
pub struct Cli {
    /// Path to configuration file
    #[arg(short, long, global = true)]
    pub config: Option<PathBuf>,
    
    /// Output format
    #[arg(short, long, global = true, default_value = "table")]
    pub format: OutputFormat,
    
    /// Disable colored output
    #[arg(long, global = true)]
    pub no_color: bool,
    
    /// Verbose output
    #[arg(short, long, global = true, action = clap::ArgAction::Count)]
    pub verbose: u8,
    
    /// Quiet mode (minimal output)
    #[arg(short, long, global = true)]
    pub quiet: bool,
    
    #[command(subcommand)]
    pub command: Commands,
}

/// Top-level commands.
#[derive(Subcommand)]
pub enum Commands {
    /// Import transactions from files
    Import(ImportArgs),
    
    /// List transactions with filtering
    List(ListArgs),
    
    /// Categorize transactions
    Categorize(CategorizeArgs),
    
    /// Generate financial reports
    Report(ReportArgs),
    
    /// Manage categories
    Category(CategoryArgs),
    
    /// Manage accounts
    Account(AccountArgs),
    
    /// Manage configuration
    Config(ConfigArgs),
    
    /// Start interactive mode
    Interactive,
    
    /// Initialize new database
    Init(InitArgs),
    
    /// Show application status
    Status,
}

/// Import command arguments.
#[derive(Args)]
pub struct ImportArgs {
    /// File(s) to import
    #[arg(required = true)]
    pub files: Vec<PathBuf>,
    
    /// Account to import into
    #[arg(short, long)]
    pub account: Option<String>,
    
    /// File format (auto-detected if not specified)
    #[arg(long)]
    pub format: Option<String>,
    
    /// Skip duplicate detection
    #[arg(long)]
    pub allow_duplicates: bool,
    
    /// Dry run (don't actually import)
    #[arg(long)]
    pub dry_run: bool,
}

/// List command arguments.
#[derive(Args)]
pub struct ListArgs {
    /// Filter by account
    #[arg(short, long)]
    pub account: Option<String>,
    
    /// Filter by category
    #[arg(short = 'C', long)]
    pub category: Option<String>,
    
    /// Start date (YYYY-MM-DD)
    #[arg(long)]
    pub from: Option<String>,
    
    /// End date (YYYY-MM-DD)
    #[arg(long)]
    pub to: Option<String>,
    
    /// Show only uncategorized
    #[arg(short, long)]
    pub uncategorized: bool,
    
    /// Search description
    #[arg(short, long)]
    pub search: Option<String>,
    
    /// Maximum results
    #[arg(short, long, default_value = "50")]
    pub limit: usize,
    
    /// Sort order
    #[arg(long, default_value = "date-desc")]
    pub sort: String,
}

/// Categorize command arguments.
#[derive(Args)]
pub struct CategorizeArgs {
    /// Apply rules automatically
    #[arg(long)]
    pub apply_rules: bool,
    
    /// Interactive categorization
    #[arg(long)]
    pub interactive: bool,
    
    /// Minimum confidence for auto-categorization
    #[arg(long, default_value = "0.85")]
    pub threshold: f32,
    
    /// Maximum transactions to categorize
    #[arg(short, long)]
    pub limit: Option<usize>,
}

/// Report command arguments.
#[derive(Args)]
pub struct ReportArgs {
    #[command(subcommand)]
    pub command: ReportCommands,
}

#[derive(Subcommand)]
pub enum ReportCommands {
    /// Profit & Loss report
    Pnl(PnlArgs),
    
    /// Cash Flow report
    Cashflow(CashflowArgs),
    
    /// Schedule C tax report
    ScheduleC(ScheduleCArgs),
    
    /// Summary report
    Summary(SummaryArgs),
}

#[derive(Args)]
pub struct PnlArgs {
    /// Year for report
    #[arg(short, long)]
    pub year: Option<i32>,
    
    /// Quarter (1-4)
    #[arg(short, long)]
    pub quarter: Option<u32>,
    
    /// Month (1-12)
    #[arg(short, long)]
    pub month: Option<u32>,
    
    /// Compare to previous period
    #[arg(long)]
    pub compare: bool,
}

#[derive(Args)]
pub struct CashflowArgs {
    /// Year for report
    #[arg(short, long)]
    pub year: Option<i32>,
    
    /// Month (1-12)
    #[arg(short, long)]
    pub month: Option<u32>,
    
    /// Include projections
    #[arg(long)]
    pub projections: bool,
}

#[derive(Args)]
pub struct ScheduleCArgs {
    /// Tax year
    #[arg(short, long)]
    pub year: i32,
    
    /// Include transaction details
    #[arg(long)]
    pub details: bool,
    
    /// Export to file
    #[arg(short, long)]
    pub output: Option<PathBuf>,
}

#[derive(Args)]
pub struct SummaryArgs {
    /// Year for summary
    #[arg(short, long)]
    pub year: Option<i32>,
    
    /// Show monthly breakdown
    #[arg(long)]
    pub monthly: bool,
}

#[derive(Args)]
pub struct CategoryArgs {
    #[command(subcommand)]
    pub command: CategoryCommands,
}

#[derive(Subcommand)]
pub enum CategoryCommands {
    /// List all categories
    List,
    
    /// Add a new category
    Add {
        /// Category name
        name: String,
        
        /// Category type (income/expense)
        #[arg(short, long)]
        category_type: String,
        
        /// Parent category
        #[arg(short, long)]
        parent: Option<String>,
        
        /// Schedule C line mapping
        #[arg(long)]
        schedule_c: Option<String>,
    },
    
    /// Edit a category
    Edit {
        /// Category name or ID
        category: String,
    },
    
    /// Delete a category
    Delete {
        /// Category name or ID
        category: String,
        
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },
}

#[derive(Args)]
pub struct AccountArgs {
    #[command(subcommand)]
    pub command: AccountCommands,
}

#[derive(Subcommand)]
pub enum AccountCommands {
    /// List all accounts
    List,
    
    /// Add a new account
    Add {
        /// Account name
        name: String,
        
        /// Account type
        #[arg(short, long)]
        account_type: String,
    },
    
    /// Delete an account
    Delete {
        /// Account name or ID
        account: String,
        
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },
}

#[derive(Args)]
pub struct ConfigArgs {
    #[command(subcommand)]
    pub command: ConfigCommands,
}

#[derive(Subcommand)]
pub enum ConfigCommands {
    /// Show current configuration
    Show,
    
    /// Set a configuration value
    Set {
        /// Configuration key
        key: String,
        
        /// Configuration value
        value: String,
    },
    
    /// Reset configuration to defaults
    Reset {
        /// Skip confirmation
        #[arg(short, long)]
        force: bool,
    },
}

#[derive(Args)]
pub struct InitArgs {
    /// Database path
    #[arg(short, long)]
    pub path: Option<PathBuf>,
    
    /// Skip confirmation prompts
    #[arg(short, long)]
    pub force: bool,
}

/// Main CLI entry point.
pub fn run_cli() -> ExitCode {
    let cli = Cli::parse();
    
    // Set up logging based on verbosity
    let log_level = match cli.verbose {
        0 => log::LevelFilter::Warn,
        1 => log::LevelFilter::Info,
        2 => log::LevelFilter::Debug,
        _ => log::LevelFilter::Trace,
    };
    
    env_logger::Builder::from_default_env()
        .filter_level(log_level)
        .format_timestamp(None)
        .format_target(false)
        .init();
    
    // Run async runtime
    let runtime = tokio::runtime::Runtime::new().unwrap();
    
    match runtime.block_on(run_command(&cli)) {
        Ok(result) => {
            output_result(&cli, result);
            CliExitCode::Success.into()
        }
        Err(e) => {
            let color = !cli.no_color && atty::is(atty::Stream::Stderr);
            eprintln!("{}", format_error(&e, color));
            error_to_exit_code(&e).into()
        }
    }
}

async fn run_command(cli: &Cli) -> crate::error::Result<CommandResult> {
    match &cli.command {
        Commands::Init(args) => init::handle_init(args).await,
        Commands::Status => status::handle_status(cli).await,
        Commands::Interactive => interactive::handle_interactive(cli).await,
        _ => {
            // Commands that need database context
            let ctx = CommandContext::from_cli(cli).await?;
            
            match &cli.command {
                Commands::Import(args) => import::handle_import(&ctx, args).await,
                Commands::List(args) => list::handle_list(&ctx, args).await,
                Commands::Categorize(args) => categorize::handle_categorize(&ctx, args).await,
                Commands::Report(args) => report::handle_report(&ctx, args).await,
                Commands::Category(args) => category::handle_category(&ctx, args).await,
                Commands::Account(args) => account::handle_account(&ctx, args).await,
                Commands::Config(args) => config::handle_config(&ctx, args).await,
                _ => unreachable!(),
            }
        }
    }
}

fn error_to_exit_code(error: &crate::error::Error) -> CliExitCode {
    use crate::error::Error;
    
    match error {
        Error::NotFound(_) => CliExitCode::InputError,
        Error::InvalidInput(_) => CliExitCode::InputError,
        Error::Io(_) => CliExitCode::FileError,
        Error::Parse { .. } => CliExitCode::FormatError,
        Error::Database(_) => CliExitCode::DataError,
        Error::Encryption(_) => CliExitCode::AuthError,
        _ => CliExitCode::InternalError,
    }
}
```

### Import Command (`src/cli/commands/import.rs`)

```rust
//! Import command implementation.

use std::path::PathBuf;
use uuid::Uuid;

use crate::{
    cli::{CommandContext, CommandResult},
    cli::app::ImportArgs,
    cli::output::progress
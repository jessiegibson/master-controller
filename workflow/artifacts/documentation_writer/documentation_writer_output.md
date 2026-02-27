# Documentation Writer Output

**Date**: 2026-02-20
**Version**: 0.1.0
**Status**: Complete
**Agent**: Documentation Writer

---

## 1. User-Facing Documentation Plan

### Document Inventory

| Document | Priority | Purpose | Target Audience |
|----------|----------|---------|-----------------|
| `README.md` | P0 | Project overview, quick start, feature summary | All users |
| `docs/INSTALL.md` | P0 | Installation from source, Cargo, Homebrew | New users |
| `docs/QUICKSTART.md` | P0 | 5-minute getting started guide | New users |
| `docs/CLI_REFERENCE.md` | P0 | Complete command reference with examples | All users |
| `docs/SECURITY.md` | P1 | Encryption model, threat model, data privacy | Security-conscious users |
| `docs/USER_GUIDE.md` | P1 | Full workflow guide with all features | Regular users |
| `docs/tutorials/first-import.md` | P1 | Step-by-step first import walkthrough | Beginners |
| `docs/tutorials/categorization.md` | P1 | Rule setup and ML categorization | Intermediate |
| `docs/tutorials/reports.md` | P2 | Report generation workflows | Intermediate |
| `docs/tutorials/tax-preparation.md` | P2 | Schedule C workflow for freelancers | Tax preparation |

### CLI Usage Guide Outline

The CLI uses a subcommand structure rooted at `finance`:

```
finance <COMMAND> [OPTIONS]

Commands:
  init            Initialize a new database
  status          Show application status and statistics
  transaction     Transaction management (import, list, categorize) [alias: tx]
  report          Generate financial reports (pnl, cashflow, schedule-c)
  category        Manage categories and categorization rules
  config          Application configuration

Global Options:
  -v, --verbose   Enable verbose logging
  -q, --quiet     Suppress all output except errors
  -c, --config    Configuration file path
  -h, --help      Show help
  -V, --version   Show version
```

---

## 2. Developer Documentation Plan

### Document Inventory

| Document | Priority | Purpose |
|----------|----------|---------|
| `docs/ARCHITECTURE.md` | P0 | Layered architecture overview, module map, data flow |
| `docs/CONTRIBUTING.md` | P0 | Dev setup, coding standards, PR process |
| `docs/api/overview.md` | P1 | Internal module API overview |
| `docs/api/parsers.md` | P1 | Parser module: formats, bank detection, extensibility |
| `docs/api/database.md` | P1 | DuckDB integration, repositories, migrations |
| `docs/api/categorization.md` | P1 | Rule engine, ML categorization, confidence scoring |
| `docs/api/encryption.md` | P1 | AES-256-GCM, Argon2id key derivation |
| `docs/api/calculator.md` | P2 | P&L, cash flow, Schedule C calculations |
| `docs/CHANGELOG.md` | P2 | Version history |

### Architecture Overview (Summary for ARCHITECTURE.md)

The application follows a four-layer architecture:

```
Interface Layer       cli/           clap-based CLI, output formatting
Business Logic Layer  categorization/, calculator/   Rules, ML, financial calculations
Data Layer            parsers/, database/, config/    File parsing, DuckDB, settings
Infrastructure Layer  encryption/, logging/, error/   AES-GCM, tracing, error types
Shared                models/        Transaction, Category, Account, Rule, Money
```

**Key data flows**:
1. Import: File -> Parser (detect format/bank) -> Database (store transactions)
2. Categorize: Database (uncategorized) -> Rule Engine -> ML fallback -> Database (update)
3. Report: Database (query by date range) -> Calculator (aggregate) -> Output formatter

### Module Documentation Summary

| Module | Key Types | Source Files |
|--------|-----------|-------------|
| `models` | `Transaction`, `Category`, `Account`, `Rule`, `Money`, `DateRange` | `src/models/*.rs` |
| `parsers` | `ParseResult`, `FileFormat`, CSV/QFX parsers | `src/parsers/*.rs` |
| `database` | `Connection`, `TransactionRepository`, `CategoryRepository` | `src/database/*.rs` |
| `categorization` | Rule engine, ML categorizer, `CategorizedBy` | `src/categorization/*.rs` |
| `calculator` | P&L, Cash Flow, metrics | `src/calculator/*.rs` |
| `encryption` | Key derivation, AES-256-GCM cipher, secure memory | `src/encryption/*.rs` |
| `cli` | `Cli` struct, `Commands` enum, subcommand handlers | `src/cli/*.rs` |
| `config` | `Config`, `Settings`, directory management | `src/config/*.rs` |
| `logging` | Tracing subscriber init, formatters | `src/logging/*.rs` |
| `error` | `Error` enum, `Result` type alias, domain error types | `src/error/*.rs` |

### Contribution Guide Outline

1. **Prerequisites**: Rust 1.70+, DuckDB bundled via Cargo
2. **Setup**: `git clone`, `cargo build`, `cargo test`
3. **Branch workflow**: `feature/`, `fix/`, `refactor/`, `docs/` prefixes
4. **Commit style**: Imperative mood, include `Co-Authored-By` for AI-assisted commits
5. **Code standards**: `unsafe_code = "forbid"`, all clippy warnings addressed, `cargo fmt`
6. **Testing**: Unit tests per module, integration tests in `tests/`, property tests with proptest
7. **PR process**: Feature branch -> push to `github` remote -> PR -> merge to `main`

---

## 3. Draft README.md for finance-cli

```markdown
# Finance CLI

Privacy-first personal finance management for freelancers and small business owners.

All data stays on your machine. Encrypted. Offline. No subscriptions.

## Features

- **Transaction import** from CSV and QFX/OFX files (Chase, BofA, Amex, Ally, Capital One, Citi, Discover, Wealthfront)
- **Smart categorization** with user-defined rules and ML-assisted suggestions
- **Financial reports**: Profit & Loss, Cash Flow, IRS Schedule C
- **Local encryption**: AES-256-GCM with Argon2id key derivation
- **Offline-first**: No internet connection required, ever

## Quick Start

```bash
# Build from source
git clone https://github.com/jessiegibson/master-controller.git
cd finance-cli
cargo build --release

# Initialize database
./target/release/finance init

# Import bank transactions
finance transaction import ~/Downloads/chase-statement.csv

# Categorize transactions
finance transaction categorize

# Generate a P&L report
finance report pnl --year 2025
```

## Command Overview

| Command | Description |
|---------|-------------|
| `finance init` | Initialize a new encrypted database |
| `finance status` | Show database statistics |
| `finance transaction import <file>` | Import CSV/QFX transactions |
| `finance transaction list` | List transactions with filters |
| `finance transaction categorize` | Categorize uncategorized transactions |
| `finance report pnl` | Generate Profit & Loss report |
| `finance report cashflow` | Generate Cash Flow report |
| `finance report schedule-c --year <YEAR>` | Generate IRS Schedule C report |
| `finance category list` | List all categories |
| `finance category add <name>` | Add a custom category |
| `finance config show` | Show current configuration |

Use `finance <command> --help` for detailed options on any command.

## Supported Banks

| Institution | CSV | QFX/OFX |
|-------------|-----|---------|
| Chase | Yes | Yes |
| Bank of America | Yes | Yes |
| American Express | Yes | Yes |
| Ally | Yes | Yes |
| Capital One | Yes | Yes |
| Citi | Yes | Yes |
| Discover | Yes | Yes |
| Wealthfront | Yes | Yes |

File format and institution are auto-detected during import.

## Security Model

| Property | Detail |
|----------|--------|
| Encryption | AES-256-GCM |
| Key Derivation | Argon2id (64 MB memory, 3 iterations) |
| Data Storage | Local DuckDB database only |
| Network Access | None - fully offline |
| Passphrase Storage | Never stored on disk; zeroized from memory after use |

Your passphrase encrypts all financial data. There is no password recovery mechanism. Store your passphrase securely.

## System Requirements

| Requirement | Value |
|-------------|-------|
| Rust | 1.70+ (build from source) |
| OS | macOS 12+, Ubuntu 20.04+, Windows 10+ |
| Disk Space | ~50 MB |

## Project Structure

```
finance-cli/
  src/
    main.rs              Entry point
    lib.rs               Library root (layered architecture)
    cli/                 Command-line interface (clap)
    models/              Core data types (Transaction, Category, etc.)
    parsers/             CSV/QFX file parsing with bank detection
    database/            DuckDB connection, repositories, migrations
    categorization/      Rule engine and ML categorization
    calculator/          P&L, Cash Flow, Schedule C calculations
    encryption/          AES-256-GCM, Argon2id key derivation
    config/              Application settings
    logging/             Tracing-based structured logging
    error/               Error types with user-friendly messages
```

## Development

```bash
# Run tests
cargo test

# Run with verbose logging
cargo run -- -v transaction list

# Check for linting issues
cargo clippy

# Format code
cargo fmt
```

## License

MIT License
```

---

## 4. API / CLI Reference Outline

### CLI Reference Structure

```
CLI_REFERENCE.md
  Global Options (--verbose, --quiet, --config, --help, --version)

  finance init
    Options: --path, --force
    Example: finance init

  finance status
    No options
    Example output with transaction counts, categorization percentage

  finance transaction import <FILES>
    Options: --account, --format, --allow-duplicates, --dry-run
    Supported formats: CSV, QFX/OFX
    Auto-detection: format and institution
    Example: finance transaction import statement.csv --dry-run

  finance transaction list
    Options: --account, --category, --from, --to, --uncategorized, --search, --limit, --sort
    Alias: finance tx list
    Example: finance tx list --uncategorized --from 2025-01-01

  finance transaction categorize
    Options: --apply-rules, --interactive, --threshold, --limit
    Interactive mode: select category, skip, create rule
    Example: finance transaction categorize --apply-rules

  finance report pnl
    Options: --year, --quarter, --month, --compare
    Example: finance report pnl --year 2025 --month 3

  finance report cashflow
    Options: --year, --month, --projections
    Example: finance report cashflow --year 2025

  finance report schedule-c
    Options: --year (required), --details, --output
    IRS line item mapping: Lines 1, 8, 9, 17, 18, 22, 24a, 24b, 25, 27a
    Example: finance report schedule-c --year 2025 --details

  finance category list
    No options

  finance category add <NAME>
    Options: --category-type (income|expense), --parent, --schedule-c
    Example: finance category add "SaaS Tools" --category-type expense --schedule-c 27a

  finance config show
    No options

  finance config set <KEY> <VALUE>
    Example: finance config set default_format json

  Exit Codes
    0=Success, 1=General error, 2=Config error, 3=Encryption error, 4=I/O error, 5=Database error
```

### Internal API Documentation Outline

Each module document covers: purpose, public types, key functions, usage examples, error handling.

**parsers module** (`docs/api/parsers.md`):
- `parse_file(path, account) -> ParseResult` - Main entry point
- `detect_format(path) -> FileFormat` - Auto-detect CSV vs QFX/OFX
- `detect_institution(content) -> Option<String>` - Identify bank from headers
- `ParseResult` struct: transactions, duplicates, errors, format, institution
- `FileFormat` enum: Csv, Qfx, Ofx, Unknown
- Adding new bank parsers: implement CSV column mapping

**database module** (`docs/api/database.md`):
- `Connection` - DuckDB connection wrapper
- `TransactionRepository` - CRUD for transactions, count/count_uncategorized
- `CategoryRepository` - CRUD for categories, insert_defaults, count
- Migration system: version-controlled schema changes
- Query patterns for report generation

**categorization module** (`docs/api/categorization.md`):
- `Rule` struct with `RuleCondition`, `RuleOperator`, `ConditionField`
- `RuleBuilder` - Fluent API for constructing rules
- Rule matching: priority-ordered, supports contains/equals/starts_with/regex
- ML categorization: confidence scoring, threshold-based auto-apply
- `CategorizedBy` enum: Manual, Rule, MachineLearning

**encryption module** (`docs/api/encryption.md`):
- Key derivation: Argon2id with configurable parameters
- Cipher operations: encrypt/decrypt with AES-256-GCM
- Secure memory: `Zeroizing<T>` wrappers, no plaintext on disk
- Nonce management: 12-byte random per operation

**calculator module** (`docs/api/calculator.md`):
- P&L calculation: income/expense aggregation by category and period
- Cash flow: net flow by period with optional daily breakdown
- Metrics: summary statistics
- `Money` type: Decimal-based, formatted display, arithmetic ops
- `DateRange`: year/month/custom range construction

**models module** (`docs/api/overview.md`):
- `Transaction`: id, date, amount, description, category, account, status, hash
- `Category`: id, name, type (income/expense), schedule_c_line, parent
- `Account`: id, name, institution, account_type
- `Rule`: id, priority, conditions, target_category
- `Money`: Decimal wrapper with currency formatting
- `DateRange`: start/end date with helper constructors
- `Entity` trait: id(), is_new()
- `EntityMetadata`: created_at, updated_at timestamps

---

## Documentation Package Summary

| Document | Status | Notes |
|----------|--------|-------|
| README.md (draft) | Complete | Full draft included above |
| User doc plan | Complete | 10 documents prioritized P0-P2 |
| Developer doc plan | Complete | 9 documents with architecture summary |
| CLI reference outline | Complete | All commands, options, examples, exit codes |
| API doc outlines | Complete | 6 modules with types and function signatures |

### Style Compliance

- [x] Consistent heading hierarchy
- [x] Code examples for all commands
- [x] Tables for options and parameters
- [x] Cross-references between documents
- [x] Aligned with actual implemented code (src/ structure verified)
- [x] Exit codes match main.rs implementation
- [x] Command structure matches cli/mod.rs Cli and Commands enums

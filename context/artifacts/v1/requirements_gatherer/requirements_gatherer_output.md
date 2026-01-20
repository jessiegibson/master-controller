# Requirements Document: Privacy-First Personal Finance CLI

Version: 1
Date: 2024-12-28
Status: Draft

## Executive Summary

A privacy-first personal finance CLI application built in Rust for freelancers and small business owners. The application imports bank transactions from multiple financial institutions, categorizes them using rule-based logic, and generates tax-ready financial reports including P&L, Cash Flow, and IRS Schedule C mapping. All data is encrypted and stored locally with no cloud dependencies.

## Functional Requirements

### FR-001: Multi-Bank Transaction Import

**Priority**: must-have
**Size**: large

**Description**:
Import bank transactions from CSV and QFX files for supported financial institutions: Chase, Wealthfront, Bank of America, Ally, AMEX, Discover, Citi Bank, and Capital One.

**Acceptance Criteria**:
- Parse CSV files from all 8 supported banks with institution-specific field mapping
- Parse QFX files with standard OFX format support
- Handle malformed files gracefully with clear error messages
- Import transactions with date, amount, description, account, and raw category
- Detect and skip duplicate transactions based on date + amount + description hash
- Support batch import of multiple files

**Dependencies**: None

**Notes**: Each bank uses different CSV column layouts. Parser must handle institution-specific formats.

---

### FR-002: Local Data Storage

**Priority**: must-have
**Size**: medium

**Description**:
Store all financial data in encrypted local DuckDB database with no external dependencies.

**Acceptance Criteria**:
- Create and manage DuckDB database file locally
- Store transactions, categories, rules, and user preferences
- Support database backup and restore operations
- Handle database schema migrations for future versions
- Ensure database file is encrypted at rest

**Dependencies**: NFR-001 (Encryption)

**Notes**: DuckDB chosen for SQL capabilities without server overhead.

---

### FR-003: Rule-Based Transaction Categorization

**Priority**: must-have
**Size**: medium

**Description**:
Categorize imported transactions using user-defined rules based on transaction descriptions, amounts, and merchants.

**Acceptance Criteria**:
- Create rules with conditions: contains text, exact match, amount range, merchant name
- Apply rules in priority order (user-configurable)
- Support multiple conditions per rule (AND/OR logic)
- Allow manual override of rule-based categorizations
- Provide rule testing interface before applying to transactions
- Track rule effectiveness (how many transactions matched)

**Dependencies**: FR-002

**Notes**: Rule engine must be fast enough to process thousands of transactions quickly.

---

### FR-004: Recurring Transaction Detection

**Priority**: should-have
**Size**: medium

**Description**:
Auto-detect recurring transactions and prompt user for confirmation and automatic categorization.

**Acceptance Criteria**:
- Identify potential recurring transactions by similar amounts and descriptions
- Detect monthly, bi-weekly, weekly, and quarterly patterns
- Present detected patterns to user for confirmation
- Auto-categorize confirmed recurring transactions in future imports
- Allow user to modify or delete recurring transaction rules
- Handle amount variations (e.g., utility bills that vary slightly)

**Dependencies**: FR-002, FR-003

**Notes**: Detection algorithm should account for ±10% amount variation for utilities/services.

---

### FR-005: Transaction CRUD Operations

**Priority**: must-have
**Size**: small

**Description**:
Provide full Create, Read, Update, Delete operations for transactions through CLI interface.

**Acceptance Criteria**:
- View transactions with filtering by date range, category, amount, description
- Edit transaction details: date, amount, description, category
- Delete individual transactions with confirmation prompt
- Add manual transactions not from bank imports
- Bulk edit operations (e.g., recategorize multiple transactions)
- Undo last operation capability

**Dependencies**: FR-002

**Notes**: CLI interface should be intuitive with clear prompts and confirmations.

---

### FR-006: Profit & Loss Report Generation

**Priority**: must-have
**Size**: medium

**Description**:
Generate detailed Profit & Loss statements for specified date ranges with business income and expense categorization.

**Acceptance Criteria**:
- Calculate total business income from categorized transactions
- Calculate total business expenses by category
- Show net profit/loss for the period
- Support custom date ranges (monthly, quarterly, yearly, custom)
- Export reports to CSV and formatted text
- Include transaction counts and averages per category
- Handle multiple business account aggregation

**Dependencies**: FR-002, FR-003

**Notes**: Report format should be suitable for tax preparation and business analysis.

---

### FR-007: Cash Flow Report Generation

**Priority**: must-have
**Size**: medium

**Description**:
Generate cash flow statements showing money movement in and out of business accounts over time.

**Acceptance Criteria**:
- Show cash inflows by category and source
- Show cash outflows by category and destination
- Calculate net cash flow by period (monthly breakdown)
- Support date range selection
- Include beginning and ending cash positions
- Export to CSV and formatted text
- Handle multiple account aggregation

**Dependencies**: FR-002, FR-003

**Notes**: Cash flow should reconcile with bank account balances for accuracy verification.

---

### FR-008: IRS Schedule C Line Item Mapping

**Priority**: must-have
**Size**: large

**Description**:
Map business expense categories to specific IRS Schedule C line items for tax preparation.

**Acceptance Criteria**:
- Provide mapping interface for expense categories to Schedule C lines
- Support standard Schedule C line items (advertising, office expenses, travel, etc.)
- Calculate totals for each Schedule C line item
- Generate Schedule C summary report with line-by-line totals
- Allow custom mapping modifications
- Validate mappings against current tax year Schedule C form
- Export Schedule C data in tax software compatible format

**Dependencies**: FR-002, FR-003, FR-006

**Notes**: Schedule C mappings may need annual updates for tax law changes.

---

### FR-009: CLI Interface

**Priority**: must-have
**Size**: medium

**Description**:
Provide intuitive command-line interface using clap for all application functions.

**Acceptance Criteria**:
- Subcommands for import, categorize, report, edit, backup operations
- Interactive prompts for complex operations
- Progress indicators for long-running operations (imports, reports)
- Clear help text and usage examples
- Tab completion support where possible
- Colored output for better readability
- Consistent error messaging and logging

**Dependencies**: All other functional requirements

**Notes**: CLI should follow Unix conventions and be scriptable for automation.

---

### FR-010: Data Backup and Restore

**Priority**: should-have
**Size**: small

**Description**:
Provide backup and restore capabilities for the encrypted database and configuration.

**Acceptance Criteria**:
- Create encrypted backup files with timestamp
- Restore from backup files with integrity verification
- Support automatic periodic backups (configurable)
- Backup includes database, rules, categories, and user preferences
- Verify backup integrity before confirming completion
- List available backups with creation dates and sizes

**Dependencies**: FR-002, NFR-001

**Notes**: Backups should be portable across different systems.

---

## Non-Functional Requirements

### NFR-001: Local Data Encryption

**Priority**: must-have
**Category**: Security

**Description**:
All sensitive financial data must be encrypted at rest using AES-256-GCM with master password and recovery code system.

**Acceptance Criteria**:
- Encrypt database file with AES-256-GCM
- Derive encryption key from user master password using PBKDF2 (100,000+ iterations)
- Generate secure recovery code for password reset
- Recovery code allows database decryption and password reset
- No plaintext financial data stored on disk
- Secure memory handling (clear sensitive data after use)

**Dependencies**: None

---

### NFR-002: Performance

**Priority**: should-have
**Category**: Performance

**Description**:
Application must handle typical small business transaction volumes efficiently.

**Acceptance Criteria**:
- Import 10,000 transactions in under 30 seconds
- Generate reports for 1 year of data in under 5 seconds
- Database queries respond in under 1 second for typical operations
- Memory usage stays under 100MB during normal operations
- Startup time under 2 seconds

**Dependencies**: FR-002

---

### NFR-003: Reliability

**Priority**: must-have
**Category**: Reliability

**Description**:
Application must handle errors gracefully and protect data integrity.

**Acceptance Criteria**:
- Graceful handling of corrupted import files
- Database transaction rollback on operation failures
- Automatic data integrity checks on startup
- Clear error messages with suggested remediation
- No data loss during unexpected shutdowns
- Backup verification before destructive operations

**Dependencies**: FR-002

---

### NFR-004: Usability

**Priority**: should-have
**Category**: Usability

**Description**:
CLI interface must be intuitive for non-technical small business owners.

**Acceptance Criteria**:
- Clear command structure with logical grouping
- Interactive prompts for complex operations
- Progress indicators for long operations
- Helpful error messages with next steps
- Built-in help and examples for all commands
- Confirmation prompts for destructive operations

**Dependencies**: FR-009

---

### NFR-005: Privacy

**Priority**: must-have
**Category**: Security

**Description**:
Application must operate completely offline with no external data transmission.

**Acceptance Criteria**:
- No network connections initiated by application
- No telemetry or usage data collection
- No cloud storage dependencies
- All processing occurs locally
- No external API calls for any functionality
- User data never leaves local system

**Dependencies**: None

---

## Constraints

### CON-001: Technology Stack

**Type**: Technology

**Description**:
Application must be built using Rust programming language with specified dependencies: DuckDB for storage and clap for CLI parsing.

**Impact**:
Limits database options and requires Rust expertise. Benefits include memory safety, performance, and single binary distribution.

---

### CON-002: Single Business Scope

**Type**: Resource

**Description**:
MVP supports single business/sole proprietorship only. Multi-business support deferred to future phases.

**Impact**:
Simplifies data model and user interface. Reduces development complexity for initial release.

---

### CON-003: US Tax Jurisdiction

**Type**: Regulatory

**Description**:
Application targets US tax requirements only. IRS Schedule C line items and tax categories are US-specific.

**Impact**:
Limits international market but allows focus on US small business needs and tax compliance.

---

### CON-004: Local-Only Operation

**Type**: Technology

**Description**:
No cloud services, external APIs, or internet connectivity allowed. Complete offline operation required.

**Impact**:
Eliminates cloud storage options, real-time data feeds, and automatic bank connections. Increases user trust and privacy.

---

## Out of Scope

| ID | Item | Reason | Target Phase |
|----|------|--------|--------------|
| OOS-001 | PDF transaction import | Complex parsing, OCR requirements | Phase 2 |
| OOS-002 | Machine learning categorization | Rule-based sufficient for MVP | Phase 2 |
| OOS-003 | Multi-business support | Single business complexity sufficient | Phase 2 |
| OOS-004 | Mobile applications | CLI focus for MVP | Future |
| OOS-005 | Real-time bank connections | Privacy-first, local-only requirement | Never |
| OOS-006 | Cloud backup/sync | Privacy-first, local-only requirement | Never |
| OOS-007 | Multi-user/collaboration | Single user focus | Future |
| OOS-008 | Investment tracking | Business expense focus for MVP | Phase 2 |

---

## Assumptions

| ID | Assumption | Risk Level | Impact if Wrong | Flagged |
|----|------------|------------|-----------------|---------|
| A-001 | Users comfortable with CLI interface | Medium | Would need GUI development | No |
| A-002 | 8 supported banks cover 80%+ of target users | Low | Additional parser development | No |
| A-003 | Rule-based categorization sufficient accuracy | Medium | May need ML sooner than planned | No |
| A-004 | Single business model fits target market | Low | Data model changes needed | No |
| A-005 | Users will manage their own backups | Medium | Need automated cloud backup (conflicts with privacy) | No |
| A-006 | DuckDB performance adequate for target data volumes | Low | Database technology change | No |
| A-007 | Recovery code system acceptable UX | Medium | May need additional recovery options | No |

---

## Open Questions

### Critical (Blocking)

*All critical questions have been resolved.*

### Important (Should Resolve)

*All important questions have been resolved.*

---

## Resolved Questions

| Question | Answered By | Answer | Date |
|----------|-------------|--------|------|
| Which financial institutions to support? | Human Proxy | Chase, Wealthfront, BofA, Ally, AMEX, Discover, Citi, Capital One | 2024-12-28 |
| Single or multiple business support? | Human Proxy | Single business for MVP | 2024-12-28 |
| Encryption approach? | Human Proxy | Master password + recovery code | 2024-12-28 |
| PDF parsing in MVP? | Human Proxy | Defer to Phase 2 | 2024-12-28 |
| ML categorization in MVP? | Human Proxy | Rule-based for MVP | 2024-12-28 |
| Recurring transaction handling? | Human Proxy | Auto-detect with user confirmation | 2024-12-28 |
| Transaction editing capabilities? | Human Proxy | Full CRUD supported | 2024-12-28 |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2024-12-28 | Initial draft based on resolved clarifying questions |

---

# YAML Output

```yaml
metadata:
  project_name: "Privacy-First Personal Finance CLI"
  version: 1
  date: "2024-12-28"
  status: "draft"

summary: |
  A privacy-first personal finance CLI application built in Rust for freelancers and small business owners. 
  The application imports bank transactions from multiple financial institutions, categorizes them using 
  rule-based logic, and generates tax-ready financial reports including P&L, Cash Flow, and IRS Schedule C 
  mapping. All data is encrypted and stored locally with no cloud dependencies.

functional_requirements:
  - id: "FR-001"
    title: "Multi-Bank Transaction Import"
    description: |
      Import bank transactions from CSV and QFX files for supported financial institutions: Chase, 
      Wealthfront, Bank of America, Ally, AMEX, Discover, Citi Bank, and Capital One.
    priority: "must-have"
    size: "large"
    acceptance_criteria:
      - "Parse CSV files from all 8 supported banks with institution-specific field mapping"
      - "Parse QFX files with standard OFX format support"
      - "Handle malformed files gracefully with clear error messages"
      - "Import transactions with date, amount, description, account, and raw category"
      - "Detect and skip duplicate transactions based on date + amount + description hash"
      - "Support batch import of multiple files"
    dependencies: []
    notes: "Each bank uses different CSV column layouts. Parser must handle institution-specific formats."

  - id: "FR-002"
    title: "Local Data Storage"
    description: |
      Store all financial data in encrypted local DuckDB database with no external dependencies.
    priority: "must-have"
    size: "medium"
    acceptance_criteria:
      - "Create and manage DuckDB database file locally"
      - "Store transactions, categories, rules, and user preferences"
      - "Support database backup and restore operations"
      - "Handle database schema migrations for future versions"
      - "Ensure database file is encrypted at rest"
    dependencies: ["NFR-001"]
    notes: "DuckDB chosen for SQL capabilities without server overhead."

  - id: "FR-003"
    title: "Rule-Based Transaction Categorization"
    description: |
      Categorize imported transactions using user-defined rules based on transaction descriptions, 
      amounts, and merchants.
    priority: "must-have"
    size: "medium"
    acceptance_criteria:
      - "Create rules with conditions: contains text, exact match, amount range, merchant name"
      - "Apply rules in priority order (user-configurable)"
      - "Support multiple conditions per rule (AND/OR logic)"
      - "Allow manual override of rule-based categorizations"
      - "Provide rule testing interface before applying to transactions"
      - "Track rule effectiveness (how many transactions matched)"
    dependencies: ["FR-002"]
    notes: "Rule engine must be fast enough to process thousands of transactions quickly."

  - id: "FR-004"
    title: "Recurring Transaction Detection"
    description: |
      Auto-detect recurring transactions and prompt user for confirmation and automatic categorization.
    priority: "should-have"
    size: "medium
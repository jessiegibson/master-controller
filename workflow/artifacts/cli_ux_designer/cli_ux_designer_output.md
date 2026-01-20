# CLI Design: Privacy-First Personal Finance CLI

Version: 1
Date: 2024-12-28
Status: Draft

## Executive Summary

This document defines the complete command-line interface design for the Privacy-First Personal Finance CLI application. The CLI follows modern Unix conventions with a focus on discoverability, consistency, and user delight. It supports both interactive exploration and scripted automation while maintaining the application's core privacy-first principles.

## Design Philosophy

### Core Principles

1. **Discoverability First**: Users should be able to explore without documentation
2. **Consistent Patterns**: Same conventions throughout all commands
3. **Progressive Disclosure**: Simple by default, powerful when needed
4. **Forgiveness**: Help users recover from mistakes
5. **Privacy-First**: No data ever leaves the local system

### Modern CLI Patterns

Following successful CLI tools like `git`, `cargo`, `gh`, and `ripgrep`:
- Resource-based command structure: `finance <resource> <action>`
- Consistent flag naming and behavior
- Rich help system with examples
- Colored output with accessibility support
- JSON output for scripting

## Command Structure Overview

```
finance
├── init                    # Initial setup and password creation
├── import <files>          # Import bank transactions
├── transaction             # Transaction management
│   ├── list
│   ├── show <id>
│   ├── edit <id>
│   ├── delete <id>
│   └── add
├── categorize              # Interactive categorization
├── rule                    # Categorization rule management
│   ├── list
│   ├── add
│   ├── edit <id>
│   ├── delete <id>
│   └── test <pattern>
├── report                  # Financial reports
│   ├── pnl
│   ├── cashflow
│   └── schedule-c
├── backup                  # Data backup operations
│   ├── create
│   ├── restore <file>
│   └── list
├── config                  # Configuration management
│   ├── show
│   ├── set <key> <value>
│   └── reset
└── interactive             # Interactive mode
```

## Global Options

| Option | Short | Type | Description | Default |
|--------|-------|------|-------------|---------|
| `--help` | `-h` | flag | Show help information | |
| `--version` | `-V` | flag | Show version | |
| `--verbose` | `-v` | count | Increase verbosity (repeat for more) | 0 |
| `--quiet` | `-q` | flag | Suppress non-essential output | false |
| `--format` | `-f` | enum | Output format: table, json, csv | table |
| `--no-color` | | flag | Disable colored output | auto-detect |
| `--config` | `-c` | path | Path to config file | ~/.finance-cli/config.toml |

## Command Specifications

### `finance init`

Initialize the application with database creation and password setup.

**Synopsis:**
```bash
finance init [OPTIONS]
```

**Options:**
| Option | Short | Type | Description | Default |
|--------|-------|------|-------------|---------|
| `--data-dir` | `-d` | path | Data directory location | ~/.finance-cli |
| `--force` | | flag | Reinitialize existing setup | false |

**Interactive Flow:**
```
Welcome to Finance CLI!

This will create your encrypted financial database.

Choose a master password:
  • Minimum 12 characters
  • Mix of letters, numbers, symbols
  • You cannot recover data if you forget this

Master password: ••••••••••••••••••••
Confirm password: ••••••••••••••••••••

✓ Password accepted

Generating recovery code...

  IMPORTANT: Save this recovery code in a safe place
  
  Recovery Code: APPLE-BRAVE-CLOUD-DANCE-EAGLE-FLAME
  
  This code can restore access if you forget your password.
  Write it down and store it securely.

Continue? [y/N]: y

✓ Database created at ~/.finance-cli/data.db
✓ Configuration saved to ~/.finance-cli/config.toml

Next steps:
  1. Import your first transactions: finance import statement.csv
  2. Set up categorization rules: finance rule add
  3. Generate your first report: finance report pnl

Run 'finance --help' for all available commands.
```

**Exit Codes:**
- 0: Success
- 1: Invalid options
- 2: Directory creation failed
- 5: Password validation failed
- 20: User cancelled

---

### `finance import`

Import transactions from bank export files.

**Synopsis:**
```bash
finance import [OPTIONS] <FILE>...
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `FILE` | path | Yes | One or more files to import (CSV, QFX) |

**Options:**
| Option | Short | Type | Description | Default |
|--------|-------|------|-------------|---------|
| `--account` | `-a` | string | Account name to import into | auto-detect |
| `--bank` | `-b` | enum | Bank format: chase, wealthfront, bofa, ally, amex, discover, citi, capital-one | auto-detect |
| `--dry-run` | `-n` | flag | Show what would be imported | false |
| `--skip-duplicates` | | flag | Skip duplicate transactions | true |
| `--force` | | flag | Import even if duplicates found | false |

**Examples:**
```bash
# Import a single file
finance import statement.csv

# Import multiple files
finance import march.csv april.csv may.csv

# Preview import without saving
finance import --dry-run statement.csv

# Force specific bank format
finance import --bank chase statement.csv

# Import with explicit account name
finance import --account "Chase Checking" statement.csv
```

**Output:**
```
Importing transactions from statement.csv...

  ◐ Analyzing file format...
  ◓ Detected bank: Chase
  ◑ Detected account: Chase Sapphire (****1234)
  ◒ Parsing transactions...

  Found 47 transactions (Mar 1 - Mar 31, 2024)
  ├── 42 new transactions
  ├── 5 duplicates (skipped)
  └── 0 errors

  Auto-categorization:
  ├── 38 categorized by rules
  └── 4 need manual review

✓ Import complete (2.3s)

Next steps:
  • Review uncategorized: finance transaction list --uncategorized
  • Add categorization rules: finance rule add
  • Generate report: finance report pnl
```

**Dry Run Output:**
```
Preview: statement.csv (would import 42 transactions)

  SAMPLE TRANSACTIONS:
  
  DATE       │ DESCRIPTION              │ AMOUNT    │ CATEGORY
─────────────┼──────────────────────────┼───────────┼─────────────────
  2024-03-15 │ AMAZON.COM*1A2B3C4D      │   -$49.99 │ Office Supplies
  2024-03-14 │ UBER TRIP                 │   -$23.45 │ Transportation
  2024-03-14 │ STRIPE PAYMENT            │ +$1,500.00│ Income
  ... (showing 3 of 42)

  CATEGORIZATION PREVIEW:
  ├── 38 would be auto-categorized
  └── 4 would need manual review

Run without --dry-run to import these transactions.
```

**Error Handling:**
```bash
# File not found
$ finance import missing.csv
Error: File not found

  Could not find: missing.csv
  
  Available CSV files in current directory:
  • statement-march.csv
  • statement-april.csv
  
  Try: finance import statement-march.csv

# Unsupported format
$ finance import document.pdf
Error: Unsupported file format

  File: document.pdf
  Supported formats: CSV, QFX
  
  PDF parsing is planned for a future release.
  Export your transactions as CSV from your bank's website.

# All duplicates
$ finance import statement.csv
Warning: All transactions already imported

  Found 47 transactions in statement.csv
  All 47 were previously imported
  
  To force re-import: finance import --force statement.csv
  To see existing: finance transaction list --from 2024-03-01
```

---

### `finance transaction`

Manage individual transactions with full CRUD operations.

#### `finance transaction list`

List transactions with filtering and sorting options.

**Synopsis:**
```bash
finance transaction list [OPTIONS]
```

**Options:**
| Option | Short | Type | Description | Default |
|--------|-------|------|-------------|---------|
| `--account` | `-a` | string | Filter by account | all |
| `--category` | `-c` | string | Filter by category | all |
| `--from` | | date | Start date (YYYY-MM-DD) | 30 days ago |
| `--to` | | date | End date (YYYY-MM-DD) | today |
| `--uncategorized` | `-u` | flag | Show only uncategorized | false |
| `--min-amount` | | decimal | Minimum amount | |
| `--max-amount` | | decimal | Maximum amount | |
| `--search` | `-s` | string | Search description | |
| `--limit` | `-l` | integer | Max transactions to show | 50 |
| `--sort` | | enum | Sort by: date, amount, category, description | date |
| `--reverse` | `-r` | flag | Reverse sort order | false |

**Examples:**
```bash
# List recent transactions
finance transaction list

# Show uncategorized transactions
finance transaction list --uncategorized

# Search for Amazon purchases
finance transaction list --search amazon

# Large expenses in Q1
finance transaction list --from 2024-01-01 --to 2024-03-31 --max-amount -100

# Export as JSON
finance transaction list --format json > transactions.json
```

**Output (Table):**
```
Transactions (Dec 1 - Dec 28, 2024)

  DATE       │ DESCRIPTION                      │ AMOUNT     │ CATEGORY        │ ACCOUNT
─────────────┼──────────────────────────────────┼────────────┼─────────────────┼─────────────────
  2024-12-28 │ AMAZON.COM*1A2B3C4D             │    -$49.99 │ Office Supplies │ Chase Sapphire
  2024-12-27 │ UBER TRIP                        │    -$23.45 │ Transportation  │ Chase Sapphire
  2024-12-27 │ STRIPE PAYMENT                   │ +$1,500.00 │ Income          │ Chase Checking
  2024-12-26 │ WHOLE FOODS                      │    -$87.32 │ Groceries       │ Chase Sapphire
  2024-12-26 │ STARBUCKS                        │    -$5.47  │ Meals           │ Chase Sapphire

Showing 5 of 127 transactions. Use --limit to show more.
Total: +$1,333.77 (Income: +$1,500.00, Expenses: -$166.23)
```

**Output (JSON):**
```json
{
  "transactions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "date": "2024-12-28",
      "description": "AMAZON.COM*1A2B3C4D",
      "amount": -49.99,
      "category": "Office Supplies",
      "account": "Chase Sapphire",
      "imported_at": "2024-12-28T10:30:00Z"
    }
  ],
  "summary": {
    "total_count": 127,
    "shown_count": 5,
    "total_amount": 1333.77,
    "income": 1500.00,
    "expenses": -166.23
  },
  "filters": {
    "from": "2024-12-01",
    "to": "2024-12-28",
    "limit": 50
  }
}
```

#### `finance transaction show`

Show detailed information for a specific transaction.

**Synopsis:**
```bash
finance transaction show <ID>
```

**Arguments:**
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ID` | uuid | Yes | Transaction ID |

**Output:**
```
Transaction Details

  ID:          550e8400-e29b-41d4-a716-446655440000
  Date:        2024-12-28
  Description: AMAZON.COM*1A2B3C4D Seattle WA
  Amount:      -$49.99
  Category:    Office Supplies
  Account:     Chase Sapphire (****1234)
  
  Import Details:
  ├── Imported:    2024-12-28 10:30:00 PST
  ├── Source File: statement-dec-2024.csv
  ├── Line Number: 15
  └── Bank Format: Chase CSV
  
  Categorization:
  ├── Method:      Rule-based
  ├── Rule:        "AMAZON" → Office Supplies
  ├── Confidence:  95%
  └── Last Modified: Auto (import)
  
  Related Transactions:
  └── Similar: 3 other Amazon purchases this month

Actions:
  • Edit: finance transaction edit 550e8400-e29b-41d4-a716-446655440000
  • Delete: finance transaction delete 550e8400-e29b-41d4-a716-446655440000
```

#### `finance transaction edit`

Edit transaction details interactively.

**Synopsis:**
```bash
finance transaction edit <ID>
```

**Interactive Flow:**
```
Editing Transaction: 550e8400-e29b-41d4-a716-446655440000

Current Details:
  Date:        2024-12-28
  Description: AMAZON.COM*1A2B3C4D
  Amount:      -$49.99
  Category:    Office Supplies
  Account:     Chase Sapphire

What would you like to edit?
  [1] Date
  [2] Description
  [3] Amount
  [4] Category
  [5] Account
  [6] Save changes
  [7] Cancel

Choice: 4

Current category: Office Supplies

Available categories:
  [1] Office Supplies (current)
  [2] Software Subscriptions
  [3] Advertising
  [4] Travel
  [5] Meals
  [6] Professional Services
  [7] Other
  [8] Create new category

Choice: 2

✓ Category changed to "Software Subscriptions"

Create rule for similar transactions? [Y/n]: y

Rule: "AMAZON" → Software Subscriptions
This will affect 3 other transactions. Continue? [y/N]: n

✓ Transaction updated (category only)

What would you like to edit?
  [1] Date
  [2] Description  
  [3] Amount
  [4] Category (Software Subscriptions)
  [5] Account
  [6] Save changes ✓
  [7] Cancel

Choice: 6

✓ Changes saved
```

#### `finance transaction delete`

Delete a transaction with confirmation.

**Synopsis:**
```bash
finance transaction delete <ID> [OPTIONS]
```

**Options:**
| Option | Short | Type | Description | Default |
|--------|-------|------|-------------|---------|
| `--force` | `-f` | flag | Skip confirmation prompt | false |

**Interactive Flow:**
```
Delete Transaction

  Date:        2024-12-28
  Description: AMAZON.COM*1A2B3C4D
  Amount:      -$49.99
  Category:    Office Supplies
  Account:     Chase Sapphire

⚠ This action cannot be undone.

Are you sure you want to delete this transaction? [y/N]: y

✓ Transaction deleted

This will affect your reports. Consider regenerating:
  • finance report pnl
  • finance report cashflow
```

#### `finance transaction add`

Add a manual transaction.

**Synopsis:**
```bash
finance transaction add [OPTIONS]
```

**Options:**
| Option | Short | Type
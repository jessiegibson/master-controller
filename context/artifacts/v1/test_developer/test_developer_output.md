# Sprint S1-14: Testing Framework Setup

## Overview

I'll implement a comprehensive testing framework for the Finance CLI with proper test organization, fixtures, utilities, and CI/CD integration.

## Implementation

### 1. Test Directory Structure

```
finance-cli/
├── tests/
│   ├── common/
│   │   ├── mod.rs
│   │   ├── fixtures.rs
│   │   ├── assertions.rs
│   │   ├── mocks.rs
│   │   └── generators.rs
│   ├── integration/
│   │   ├── mod.rs
│   │   ├── parser_tests.rs
│   │   ├── db_tests.rs
│   │   └── report_tests.rs
│   └── e2e/
│       ├── mod.rs
│       ├── import_workflow.rs
│       └── report_workflow.rs
├── fixtures/
│   ├── csv/
│   ├── qfx/
│   ├── expected/
│   └── rules/
├── benches/
│   ├── parser_bench.rs
│   └── report_bench.rs
└── .github/
    └── workflows/
        └── ci.yml
```

### 2. Core Test Infrastructure

**tests/common/mod.rs**
```rust
//! Common test utilities and infrastructure.

pub mod fixtures;
pub mod assertions;
pub mod mocks;
pub mod generators;

use std::path::{Path, PathBuf};
use tempfile::TempDir;
use uuid::Uuid;
use chrono::NaiveDate;
use rust_decimal::Decimal;
use finance_cli::{
    db::{Database, EncryptedDatabase},
    models::{Transaction, Category, CategoryType, Account},
    encryption::Zeroizing,
};

/// Test context with temporary database and utilities.
pub struct TestContext {
    pub db: EncryptedDatabase,
    pub temp_dir: TempDir,
    pub db_path: PathBuf,
}

impl TestContext {
    /// Create new test context with empty database.
    pub fn new() -> Self {
        let temp_dir = TempDir::new().expect("Failed to create temp dir");
        let db_path = temp_dir.path().join("test.db");
        
        let passphrase = Zeroizing::new("test_passphrase".to_string());
        let db = EncryptedDatabase::create(&db_path, passphrase)
            .expect("Failed to create test database");
        
        Self { db, temp_dir, db_path }
    }
    
    /// Create context with seeded data.
    pub fn with_seed_data() -> Self {
        let ctx = Self::new();
        ctx.seed_default_data();
        ctx
    }
    
    /// Seed default test data.
    pub fn seed_default_data(&self) {
        let conn = self.db.connection().unwrap();
        
        // Insert test accounts
        conn.execute(
            "INSERT INTO accounts (id, name, institution, account_type, account_number, routing_number) VALUES 
             (?1, 'Test Checking', 'Chase', 'checking', '****1234', '021000021'),
             (?2, 'Test Credit', 'Amex', 'credit', '****5678', NULL),
             (?3, 'Test Savings', 'Bank of America', 'savings', '****9012', '026009593')",
            rusqlite::params![
                Uuid::new_v4().to_string(),
                Uuid::new_v4().to_string(),
                Uuid::new_v4().to_string(),
            ],
        ).unwrap();
        
        // Insert test categories
        let categories = [
            ("Income", "income", Some("1")),
            ("Office Supplies", "expense", Some("22")),
            ("Travel", "expense", Some("24a")),
            ("Meals", "expense", Some("24b")),
            ("Software", "expense", Some("27a")),
            ("Utilities", "expense", Some("25")),
            ("Professional Services", "expense", Some("17")),
            ("Advertising", "expense", Some("8")),
        ];
        
        for (name, cat_type, schedule_c) in categories {
            conn.execute(
                "INSERT INTO categories (id, name, category_type, schedule_c_line) VALUES (?1, ?2, ?3, ?4)",
                rusqlite::params![
                    Uuid::new_v4().to_string(),
                    name,
                    cat_type,
                    schedule_c,
                ],
            ).unwrap();
        }
    }
    
    /// Insert test transactions.
    pub fn insert_transactions(&self, transactions: &[TestTransaction]) {
        let conn = self.db.connection().unwrap();
        for tx in transactions {
            conn.execute(
                "INSERT INTO transactions (id, date, description, amount, category_id, account_id, import_id, created_at, updated_at)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
                rusqlite::params![
                    tx.id,
                    tx.date,
                    tx.description,
                    tx.amount.to_string(),
                    tx.category_id,
                    tx.account_id,
                    tx.import_id,
                    tx.created_at,
                    tx.updated_at,
                ],
            ).unwrap();
        }
    }
    
    /// Get path to fixture file.
    pub fn fixture_path(name: &str) -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("fixtures")
            .join(name)
    }
    
    /// Get account ID by name.
    pub fn get_account_id(&self, name: &str) -> String {
        let conn = self.db.connection().unwrap();
        conn.query_row(
            "SELECT id FROM accounts WHERE name = ?1",
            [name],
            |row| row.get::<_, String>(0),
        ).unwrap()
    }
    
    /// Get category ID by name.
    pub fn get_category_id(&self, name: &str) -> String {
        let conn = self.db.connection().unwrap();
        conn.query_row(
            "SELECT id FROM categories WHERE name = ?1",
            [name],
            |row| row.get::<_, String>(0),
        ).unwrap()
    }
}

/// Simple test transaction builder.
#[derive(Debug, Clone)]
pub struct TestTransaction {
    pub id: String,
    pub date: String,
    pub description: String,
    pub amount: Decimal,
    pub category_id: Option<String>,
    pub account_id: String,
    pub import_id: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

impl TestTransaction {
    /// Create expense transaction.
    pub fn expense(date: &str, description: &str, amount: f64) -> Self {
        let now = chrono::Utc::now().format("%Y-%m-%d %H:%M:%S").to_string();
        Self {
            id: Uuid::new_v4().to_string(),
            date: date.to_string(),
            description: description.to_string(),
            amount: Decimal::from_f64_retain(-amount.abs()).unwrap(),
            category_id: None,
            account_id: Uuid::new_v4().to_string(),
            import_id: None,
            created_at: now.clone(),
            updated_at: now,
        }
    }
    
    /// Create income transaction.
    pub fn income(date: &str, description: &str, amount: f64) -> Self {
        let now = chrono::Utc::now().format("%Y-%m-%d %H:%M:%S").to_string();
        Self {
            id: Uuid::new_v4().to_string(),
            date: date.to_string(),
            description: description.to_string(),
            amount: Decimal::from_f64_retain(amount.abs()).unwrap(),
            category_id: None,
            account_id: Uuid::new_v4().to_string(),
            import_id: None,
            created_at: now.clone(),
            updated_at: now,
        }
    }
    
    /// Set category.
    pub fn with_category(mut self, category_id: &str) -> Self {
        self.category_id = Some(category_id.to_string());
        self
    }
    
    /// Set account.
    pub fn with_account(mut self, account_id: &str) -> Self {
        self.account_id = account_id.to_string();
        self
    }
    
    /// Set import ID.
    pub fn with_import_id(mut self, import_id: &str) -> Self {
        self.import_id = Some(import_id.to_string());
        self
    }
}

/// Test result helper.
pub struct TestResult<T> {
    pub value: T,
    pub elapsed: std::time::Duration,
}

impl<T> TestResult<T> {
    pub fn timed<F>(f: F) -> Self 
    where 
        F: FnOnce() -> T,
    {
        let start = std::time::Instant::now();
        let value = f();
        let elapsed = start.elapsed();
        Self { value, elapsed }
    }
}
```

### 3. Custom Assertions

**tests/common/assertions.rs**
```rust
//! Custom test assertions for financial data.

use rust_decimal::Decimal;
use finance_cli::reports::Money;

/// Assert two Money values are equal within tolerance.
#[macro_export]
macro_rules! assert_money_eq {
    ($left:expr, $right:expr) => {
        assert_money_eq!($left, $right, Decimal::new(1, 2))  // 0.01 default tolerance
    };
    ($left:expr, $right:expr, $tolerance:expr) => {
        let left_amount = $left.amount();
        let right_amount = $right.amount();
        let diff = (left_amount - right_amount).abs();
        assert!(
            diff <= $tolerance,
            "Money values not equal: left={}, right={}, diff={}",
            Money::new(left_amount).format(),
            Money::new(right_amount).format(),
            diff,
        );
    };
}

/// Assert transaction counts match expected.
#[macro_export]
macro_rules! assert_transaction_count {
    ($ctx:expr, $expected:expr) => {
        let count: i64 = $ctx.db.connection().unwrap()
            .query_row("SELECT COUNT(*) FROM transactions", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, $expected, "Transaction count mismatch");
    };
}

/// Assert parse result has expected number of transactions.
#[macro_export]
macro_rules! assert_parsed_count {
    ($result:expr, $expected:expr) => {
        assert_eq!(
            $result.transactions.len(),
            $expected,
            "Expected {} transactions, got {}",
            $expected,
            $result.transactions.len(),
        );
    };
}

/// Assert no parse errors.
#[macro_export]
macro_rules! assert_no_parse_errors {
    ($result:expr) => {
        assert!(
            $result.errors.is_empty(),
            "Expected no parse errors, got: {:?}",
            $result.errors,
        );
    };
}

/// Assert parse has specific number of errors.
#[macro_export]
macro_rules! assert_parse_errors {
    ($result:expr, $expected:expr) => {
        assert_eq!(
            $result.errors.len(),
            $expected,
            "Expected {} parse errors, got {}",
            $expected,
            $result.errors.len(),
        );
    };
}

/// Assert decimal values are equal within precision.
#[macro_export]
macro_rules! assert_decimal_eq {
    ($left:expr, $right:expr) => {
        assert_decimal_eq!($left, $right, 2)  // 2 decimal places default
    };
    ($left:expr, $right:expr, $precision:expr) => {
        let left_rounded = $left.round_dp($precision);
        let right_rounded = $right.round_dp($precision);
        assert_eq!(
            left_rounded,
            right_rounded,
            "Decimal values not equal: left={}, right={}",
            left_rounded,
            right_rounded,
        );
    };
}

/// Assert report totals match expected values.
pub fn assert_pnl_totals(
    report: &finance_cli::reports::ProfitLossReport,
    expected_income: Decimal,
    expected_expenses: Decimal,
) {
    assert_money_eq!(report.total_income, Money::new(expected_income));
    assert_money_eq!(report.total_expenses, Money::new(expected_expenses));
    
    let expected_profit = expected_income - expected_expenses;
    assert_money_eq!(report.net_profit, Money::new(expected_profit));
}

/// Assert Schedule C line amounts.
pub fn assert_schedule_c_line(
    report: &finance_cli::reports::ScheduleCReport,
    line: &str,
    expected_amount: Decimal,
) {
    let line_item = report.expenses.iter()
        .find(|item| item.line.to_string() == line)
        .unwrap_or_else(|| panic!("Schedule C line {} not found", line));
    
    assert_money_eq!(line_item.amount, Money::new(expected_amount));
}

/// Assert categorization confidence is within range.
pub fn assert_confidence_range(
    confidence: f32,
    min: f32,
    max: f32,
) {
    assert!(
        confidence >= min && confidence <= max,
        "Confidence {} not in range [{}, {}]",
        confidence, min, max
    );
}
```

### 4. Mock Objects

**tests/common/mocks.rs**
```rust
//! Mock implementations for testing.

use async_trait::async_trait;
use std::collections::HashMap;
use uuid::Uuid;
use finance_cli::{
    categorization::{MlPredictor, MlPrediction, ModelInfo},
    models::Transaction,
    encryption::Zeroizing,
    db::Database,
};

/// Mock ML predictor with configurable responses.
pub struct MockPredictor {
    predictions: HashMap<String, (Uuid, f32)>,
    default_confidence: f32,
    delay_ms: u64,
}

impl MockPredictor {
    pub fn new() -> Self {
        Self {
            predictions: HashMap::new(),
            default_confidence: 0.0,
            delay_ms: 0,
        }
    }
    
    /// Add prediction for description pattern.
    pub fn with_prediction(mut self, pattern: &str, category_id: Uuid, confidence: f32) -> Self {
        self.predictions.insert(pattern.to_lowercase(), (category_id, confidence));
        self
    }
    
    /// Set default confidence for unknown patterns.
    pub fn with_default_confidence(mut self, confidence: f32) -> Self {
        self.default_confidence = confidence;
        self
    }
    
    /// Add artificial delay to simulate network calls.
    pub fn with_delay(mut self, delay_ms: u64) -> Self {
        self.delay_ms = delay_ms;
        self
    }
}

#[async_trait]
impl MlPredictor for MockPredictor {
    async fn predict(&self, transaction: &Transaction) -> Result<MlPrediction, Box<dyn std::error::Error + Send + Sync>> {
        if self.delay_ms > 0 {
            tokio::time::sleep(std::time::Duration::from_millis(self.delay_ms)).await;
        }
        
        let desc_lower = transaction.description.to_lowercase();
        
        for
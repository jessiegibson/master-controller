# Financial Reports Implementation

**Module**: `src/reports/`
**Date**: 2024-12-19
**Status**: Implementation Complete

## Files Created

| File | Purpose |
|------|---------|
| `mod.rs` | Module exports |
| `types.rs` | Core Money and Period types |
| `calculator.rs` | Core calculation engine |
| `pnl.rs` | Profit & Loss calculations |
| `cashflow.rs` | Cash Flow calculations |
| `aggregation.rs` | Data aggregation utilities |
| `export.rs` | Report export formats |
| `comparison.rs` | Period comparison utilities |

## Implementation

### Module Structure

```rust
// src/reports/mod.rs
//! Financial reporting module.

pub mod types;
pub mod calculator;
pub mod pnl;
pub mod cashflow;
pub mod aggregation;
pub mod export;
pub mod comparison;

pub use types::{Money, Period, ReportFilter};
pub use calculator::ReportCalculator;
pub use pnl::{ProfitLossReport, ProfitLossCalculator};
pub use cashflow::{CashFlowReport, CashFlowCalculator};
pub use export::{ReportExporter, ExportFormat};
pub use comparison::PeriodComparison;
```

### Core Types

```rust
// src/reports/types.rs
//! Core types for financial reporting.

use chrono::{NaiveDate, Datelike};
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Money amount with currency (USD assumed for MVP).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Money(Decimal);

impl Money {
    pub const ZERO: Money = Money(dec!(0));
    
    /// Create from decimal.
    pub fn new(amount: Decimal) -> Self {
        Self(amount)
    }
    
    /// Create from string (e.g., "123.45").
    pub fn from_str(s: &str) -> Result<Self, crate::Error> {
        let amount: Decimal = s.parse()
            .map_err(|_| crate::Error::InvalidAmount(s.to_string()))?;
        Ok(Self(amount))
    }
    
    /// Get the decimal value.
    pub fn amount(&self) -> Decimal {
        self.0
    }
    
    /// Check if negative (expense).
    pub fn is_negative(&self) -> bool {
        self.0 < Decimal::ZERO
    }
    
    /// Check if positive (income).
    pub fn is_positive(&self) -> bool {
        self.0 > Decimal::ZERO
    }
    
    /// Absolute value.
    pub fn abs(&self) -> Self {
        Self(self.0.abs())
    }
    
    /// Round to cents.
    pub fn round_cents(&self) -> Self {
        Self(self.0.round_dp(2))
    }
    
    /// Format as currency string.
    pub fn format(&self) -> String {
        let abs = self.0.abs();
        let sign = if self.0 < Decimal::ZERO { "-" } else { "" };
        format!("{}${:.2}", sign, abs)
    }
    
    /// Format with sign for display.
    pub fn format_signed(&self) -> String {
        if self.0 >= Decimal::ZERO {
            format!("+${:.2}", self.0)
        } else {
            format!("-${:.2}", self.0.abs())
        }
    }
}

impl std::ops::Add for Money {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        Self(self.0 + rhs.0)
    }
}

impl std::ops::Sub for Money {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        Self(self.0 - rhs.0)
    }
}

impl std::ops::Mul<Decimal> for Money {
    type Output = Self;
    fn mul(self, rhs: Decimal) -> Self {
        Self(self.0 * rhs)
    }
}

impl std::iter::Sum for Money {
    fn sum<I: Iterator<Item = Self>>(iter: I) -> Self {
        iter.fold(Money::ZERO, |acc, x| acc + x)
    }
}

impl std::fmt::Display for Money {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.format())
    }
}

/// A time period for aggregation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Period {
    /// Single day.
    Day(NaiveDate),
    
    /// Week (represented by start date).
    Week { year: i32, week: u32 },
    
    /// Calendar month.
    Month { year: i32, month: u32 },
    
    /// Calendar quarter.
    Quarter { year: i32, quarter: u32 },
    
    /// Calendar year.
    Year(i32),
    
    /// Custom date range.
    Custom { start: NaiveDate, end: NaiveDate },
}

impl Period {
    /// Create month period from date.
    pub fn month_of(date: NaiveDate) -> Self {
        Period::Month {
            year: date.year(),
            month: date.month(),
        }
    }
    
    /// Create quarter period from date.
    pub fn quarter_of(date: NaiveDate) -> Self {
        let quarter = (date.month() - 1) / 3 + 1;
        Period::Quarter {
            year: date.year(),
            quarter,
        }
    }
    
    /// Create year period from date.
    pub fn year_of(date: NaiveDate) -> Self {
        Period::Year(date.year())
    }
    
    /// Get start date of period.
    pub fn start_date(&self) -> NaiveDate {
        match self {
            Period::Day(d) => *d,
            Period::Week { year, week } => {
                NaiveDate::from_isoywd_opt(*year, *week, chrono::Weekday::Mon).unwrap()
            }
            Period::Month { year, month } => {
                NaiveDate::from_ymd_opt(*year, *month, 1).unwrap()
            }
            Period::Quarter { year, quarter } => {
                let month = (quarter - 1) * 3 + 1;
                NaiveDate::from_ymd_opt(*year, month, 1).unwrap()
            }
            Period::Year(year) => {
                NaiveDate::from_ymd_opt(*year, 1, 1).unwrap()
            }
            Period::Custom { start, .. } => *start,
        }
    }
    
    /// Get end date of period (inclusive).
    pub fn end_date(&self) -> NaiveDate {
        match self {
            Period::Day(d) => *d,
            Period::Week { year, week } => {
                NaiveDate::from_isoywd_opt(*year, *week, chrono::Weekday::Sun).unwrap()
            }
            Period::Month { year, month } => {
                let next_month = if *month == 12 {
                    NaiveDate::from_ymd_opt(*year + 1, 1, 1)
                } else {
                    NaiveDate::from_ymd_opt(*year, *month + 1, 1)
                };
                next_month.unwrap().pred_opt().unwrap()
            }
            Period::Quarter { year, quarter } => {
                let end_month = quarter * 3;
                let next = if end_month == 12 {
                    NaiveDate::from_ymd_opt(*year + 1, 1, 1)
                } else {
                    NaiveDate::from_ymd_opt(*year, end_month + 1, 1)
                };
                next.unwrap().pred_opt().unwrap()
            }
            Period::Year(year) => {
                NaiveDate::from_ymd_opt(*year, 12, 31).unwrap()
            }
            Period::Custom { end, .. } => *end,
        }
    }
    
    /// Check if date falls within period.
    pub fn contains(&self, date: NaiveDate) -> bool {
        date >= self.start_date() && date <= self.end_date()
    }
    
    /// Format period for display.
    pub fn format(&self) -> String {
        match self {
            Period::Day(d) => d.format("%Y-%m-%d").to_string(),
            Period::Week { year, week } => format!("{}-W{:02}", year, week),
            Period::Month { year, month } => format!("{}-{:02}", year, month),
            Period::Quarter { year, quarter } => format!("{} Q{}", year, quarter),
            Period::Year(year) => year.to_string(),
            Period::Custom { start, end } => {
                format!("{} to {}", start.format("%Y-%m-%d"), end.format("%Y-%m-%d"))
            }
        }
    }
    
    /// Get previous period of same type.
    pub fn previous(&self) -> Self {
        match self {
            Period::Day(d) => Period::Day(d.pred_opt().unwrap()),
            Period::Week { year, week } => {
                if *week > 1 {
                    Period::Week { year: *year, week: week - 1 }
                } else {
                    Period::Week { year: year - 1, week: 52 }
                }
            }
            Period::Month { year, month } => {
                if *month > 1 {
                    Period::Month { year: *year, month: month - 1 }
                } else {
                    Period::Month { year: year - 1, month: 12 }
                }
            }
            Period::Quarter { year, quarter } => {
                if *quarter > 1 {
                    Period::Quarter { year: *year, quarter: quarter - 1 }
                } else {
                    Period::Quarter { year: year - 1, quarter: 4 }
                }
            }
            Period::Year(year) => Period::Year(year - 1),
            Period::Custom { start, end } => {
                let duration = *end - *start;
                let new_end = *start - chrono::Duration::days(1);
                let new_start = new_end - duration;
                Period::Custom { start: new_start, end: new_end }
            }
        }
    }
}

/// Report filtering options.
#[derive(Debug, Clone)]
pub struct ReportFilter {
    /// Date range.
    pub period: Period,
    
    /// Filter by specific categories.
    pub category_ids: Option<Vec<Uuid>>,
    
    /// Filter by specific accounts.
    pub account_ids: Option<Vec<Uuid>>,
    
    /// Minimum transaction amount.
    pub min_amount: Option<Money>,
    
    /// Maximum transaction amount.
    pub max_amount: Option<Money>,
    
    /// Include uncategorized transactions.
    pub include_uncategorized: bool,
}

impl ReportFilter {
    /// Create filter for a period.
    pub fn new(period: Period) -> Self {
        Self {
            period,
            category_ids: None,
            account_ids: None,
            min_amount: None,
            max_amount: None,
            include_uncategorized: true,
        }
    }
    
    /// Filter by categories.
    pub fn categories(mut self, ids: Vec<Uuid>) -> Self {
        self.category_ids = Some(ids);
        self
    }
    
    /// Filter by accounts.
    pub fn accounts(mut self, ids: Vec<Uuid>) -> Self {
        self.account_ids = Some(ids);
        self
    }
    
    /// Filter by amount range.
    pub fn amount_range(mut self, min: Option<Money>, max: Option<Money>) -> Self {
        self.min_amount = min;
        self.max_amount = max;
        self
    }
    
    /// Exclude uncategorized.
    pub fn exclude_uncategorized(mut self) -> Self {
        self.include_uncategorized = false;
        self
    }
}

/// Amount for a category.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CategoryAmount {
    pub category_id: Option<Uuid>,
    pub category_name: String,
    pub amount: Money,
    pub transaction_count: usize,
    pub percentage_of_total: Decimal,
}

/// Transaction counts.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionCounts {
    pub total: usize,
    pub income: usize,
    pub expense: usize,
    pub uncategorized: usize,
}
```

### Profit & Loss Report

```rust
// src/reports/pnl.rs
//! Profit & Loss report calculations.

use super::types::{Money, Period, ReportFilter, CategoryAmount, TransactionCounts};
use crate::models::{Transaction, Category};
use rust_decimal::Decimal;
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// P&L report for a period.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfitLossReport {
    /// Report period.
    pub period: Period,
    
    /// Total income.
    pub total_income: Money,
    
    /// Income breakdown by category.
    pub income_by_category: Vec<CategoryAmount>,
    
    /// Total expenses.
    pub total_expenses: Money,
    
    /// Expense breakdown by category.
    pub expenses_by_category: Vec<CategoryAmount>,
    
    /// Net profit (income - expenses).
    pub net_profit: Money,
    
    /// Profit margin percentage.
    pub profit_margin: Option<Decimal>,
    
    /// Transaction counts.
    pub transaction_count: TransactionCounts,
    
    /// Report generation timestamp.
    pub generated_at: chrono::DateTime<chrono::Utc>,
}

impl ProfitLossReport {
    /// Get top income categories.
    pub fn top_income_categories(&self, limit: usize) -> &[CategoryAmount] {
        &self.income_by_category[..limit.min(self.income_by_category.len())]
    }
    
    /// Get top expense categories.
    pub fn top_expense_categories(&self, limit: usize) -> &[CategoryAmount] {
        &self.expenses_by_category[..limit.min(self.expenses_by_category.len())]
    }
    
    /// Check if profitable.
    pub fn is_profitable(&self) -> bool {
        self.net_profit.is_positive()
    }
    
    /// Get expense ratio (expenses / income).
    pub fn expense_ratio(&self) -> Option<Decimal> {
        if self.total_income.amount() > Decimal::ZERO {
            Some(self.total_expenses.amount() / self.total_income.amount())
        } else {
            None
        }
    }
}

/// P&L calculator.
pub struct ProfitLossCalculator;

impl ProfitLossCalculator {
    /// Calculate P&L for a filter.
    pub fn calculate(
        transactions: &[Transaction],
        categories: &[Category],
        filter: &ReportFilter,
    ) -> crate::Result<ProfitLossReport> {
        // Filter transactions
        let filtered_transactions = Self::filter_transactions(transactions, filter);
        
        // Separate income and expenses
        let (income_txs, expense_txs): (Vec<_>, Vec<_>) = filtered_transactions
            .iter()
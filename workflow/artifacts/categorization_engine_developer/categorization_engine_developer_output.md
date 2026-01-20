I'll implement the categorization engine based on the requirements and data architecture. Let me create the complete implementation:

## src/categorization/mod.rs

```rust
//! Categorization engine for automatic transaction classification.
//!
//! This module provides rule-based categorization with user-defined rules,
//! priority-based evaluation, and comprehensive testing capabilities.

pub mod conditions;
pub mod engine;
pub mod rule;
pub mod testing;

pub use engine::{CategorizationEngine, CategorizationResult, EngineConfig};
pub use rule::{Rule, RuleBuilder};
pub use conditions::{Condition, ConditionField, ConditionOperator, ConditionValue};
pub use testing::{RuleTestResult, RuleTester};

use uuid::Uuid;
use serde::{Deserialize, Serialize};

/// Result type for categorization operations.
pub type Result<T> = std::result::Result<T, CategorizationError>;

/// Categorization engine errors.
#[derive(Debug, thiserror::Error)]
pub enum CategorizationError {
    #[error("Invalid rule condition: {0}")]
    InvalidCondition(String),
    
    #[error("Rule not found: {0}")]
    RuleNotFound(Uuid),
    
    #[error("Category not found: {0}")]
    CategoryNotFound(Uuid),
    
    #[error("Regex error: {0}")]
    RegexError(#[from] regex::Error),
    
    #[error("JSON serialization error: {0}")]
    JsonError(#[from] serde_json::Error),
    
    #[error("Database error: {0}")]
    DatabaseError(String),
}

/// How a transaction was categorized.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CategorizationMethod {
    /// Automatically categorized by rule.
    Rule,
    /// Manually categorized by user.
    Manual,
    /// Not categorized.
    None,
}

/// Confidence level for categorization.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConfidenceLevel {
    /// Rule-based categorization (100% confidence).
    High,
    /// Manual categorization (100% confidence).
    Manual,
    /// Not categorized (0% confidence).
    None,
}

impl ConfidenceLevel {
    pub fn as_score(&self) -> f32 {
        match self {
            ConfidenceLevel::High => 1.0,
            ConfidenceLevel::Manual => 1.0,
            ConfidenceLevel::None => 0.0,
        }
    }
}
```

## src/categorization/conditions.rs

```rust
//! Condition types and matching logic for categorization rules.

use crate::models::Transaction;
use regex::Regex;
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::str::FromStr;

/// A single condition within a rule.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Condition {
    /// Field to evaluate.
    pub field: ConditionField,
    /// Operator for comparison.
    pub operator: ConditionOperator,
    /// Value to compare against.
    pub value: ConditionValue,
    /// Whether comparison is case-sensitive (for text operations).
    pub case_sensitive: bool,
}

/// Fields that can be used in conditions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConditionField {
    #[serde(rename = "description")]
    Description,
    #[serde(rename = "merchant_name")]
    MerchantName,
    #[serde(rename = "amount")]
    Amount,
    #[serde(rename = "account_id")]
    AccountId,
}

/// Operators for condition evaluation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConditionOperator {
    #[serde(rename = "contains")]
    Contains,
    #[serde(rename = "equals")]
    Equals,
    #[serde(rename = "starts_with")]
    StartsWith,
    #[serde(rename = "ends_with")]
    EndsWith,
    #[serde(rename = "regex")]
    Regex,
    #[serde(rename = "greater_than")]
    GreaterThan,
    #[serde(rename = "less_than")]
    LessThan,
    #[serde(rename = "between")]
    Between,
}

/// Values that can be compared in conditions.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ConditionValue {
    Text(String),
    Number(Decimal),
    Range(Decimal, Decimal),
    Uuid(uuid::Uuid),
}

/// Logical operator for combining conditions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LogicalOperator {
    #[serde(rename = "AND")]
    And,
    #[serde(rename = "OR")]
    Or,
}

/// A group of conditions with a logical operator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConditionGroup {
    pub operator: LogicalOperator,
    pub conditions: Vec<Condition>,
}

impl Condition {
    /// Create a new condition.
    pub fn new(
        field: ConditionField,
        operator: ConditionOperator,
        value: ConditionValue,
        case_sensitive: bool,
    ) -> Self {
        Self {
            field,
            operator,
            value,
            case_sensitive,
        }
    }
    
    /// Evaluate this condition against a transaction.
    pub fn evaluate(&self, transaction: &Transaction) -> crate::Result<bool> {
        let field_value = self.extract_field_value(transaction);
        
        match (&self.operator, &self.value) {
            // Text operations
            (ConditionOperator::Contains, ConditionValue::Text(text)) => {
                Ok(self.text_contains(&field_value, text))
            }
            (ConditionOperator::Equals, ConditionValue::Text(text)) => {
                Ok(self.text_equals(&field_value, text))
            }
            (ConditionOperator::StartsWith, ConditionValue::Text(text)) => {
                Ok(self.text_starts_with(&field_value, text))
            }
            (ConditionOperator::EndsWith, ConditionValue::Text(text)) => {
                Ok(self.text_ends_with(&field_value, text))
            }
            (ConditionOperator::Regex, ConditionValue::Text(pattern)) => {
                self.regex_matches(&field_value, pattern)
            }
            
            // Numeric operations
            (ConditionOperator::GreaterThan, ConditionValue::Number(value)) => {
                Ok(self.extract_numeric_value(transaction)? > *value)
            }
            (ConditionOperator::LessThan, ConditionValue::Number(value)) => {
                Ok(self.extract_numeric_value(transaction)? < *value)
            }
            (ConditionOperator::Between, ConditionValue::Range(min, max)) => {
                let amount = self.extract_numeric_value(transaction)?;
                Ok(amount >= *min && amount <= *max)
            }
            (ConditionOperator::Equals, ConditionValue::Number(value)) => {
                Ok(self.extract_numeric_value(transaction)? == *value)
            }
            
            // UUID operations
            (ConditionOperator::Equals, ConditionValue::Uuid(uuid)) => {
                match self.field {
                    ConditionField::AccountId => Ok(transaction.account_id == *uuid),
                    _ => Err(crate::CategorizationError::InvalidCondition(
                        "UUID comparison only supported for account_id field".to_string()
                    )),
                }
            }
            
            _ => Err(crate::CategorizationError::InvalidCondition(
                format!("Invalid operator {:?} for value type", self.operator)
            )),
        }
    }
    
    /// Extract the field value as a string.
    fn extract_field_value(&self, transaction: &Transaction) -> String {
        match self.field {
            ConditionField::Description => transaction.description.clone(),
            ConditionField::MerchantName => {
                transaction.merchant_name.clone().unwrap_or_default()
            }
            ConditionField::Amount => transaction.amount.to_string(),
            ConditionField::AccountId => transaction.account_id.to_string(),
        }
    }
    
    /// Extract numeric value for amount comparisons.
    fn extract_numeric_value(&self, transaction: &Transaction) -> crate::Result<Decimal> {
        match self.field {
            ConditionField::Amount => Ok(transaction.amount),
            _ => Err(crate::CategorizationError::InvalidCondition(
                "Numeric operations only supported for amount field".to_string()
            )),
        }
    }
    
    /// Check if text contains substring.
    fn text_contains(&self, text: &str, substring: &str) -> bool {
        if self.case_sensitive {
            text.contains(substring)
        } else {
            text.to_lowercase().contains(&substring.to_lowercase())
        }
    }
    
    /// Check if text equals value.
    fn text_equals(&self, text: &str, value: &str) -> bool {
        if self.case_sensitive {
            text == value
        } else {
            text.to_lowercase() == value.to_lowercase()
        }
    }
    
    /// Check if text starts with prefix.
    fn text_starts_with(&self, text: &str, prefix: &str) -> bool {
        if self.case_sensitive {
            text.starts_with(prefix)
        } else {
            text.to_lowercase().starts_with(&prefix.to_lowercase())
        }
    }
    
    /// Check if text ends with suffix.
    fn text_ends_with(&self, text: &str, suffix: &str) -> bool {
        if self.case_sensitive {
            text.ends_with(suffix)
        } else {
            text.to_lowercase().ends_with(&suffix.to_lowercase())
        }
    }
    
    /// Check if text matches regex pattern.
    fn regex_matches(&self, text: &str, pattern: &str) -> crate::Result<bool> {
        let regex = if self.case_sensitive {
            Regex::new(pattern)?
        } else {
            Regex::new(&format!("(?i){}", pattern))?
        };
        Ok(regex.is_match(text))
    }
}

impl ConditionGroup {
    /// Create a new condition group.
    pub fn new(operator: LogicalOperator, conditions: Vec<Condition>) -> Self {
        Self { operator, conditions }
    }
    
    /// Evaluate all conditions in this group.
    pub fn evaluate(&self, transaction: &Transaction) -> crate::Result<bool> {
        match self.operator {
            LogicalOperator::And => {
                for condition in &self.conditions {
                    if !condition.evaluate(transaction)? {
                        return Ok(false);
                    }
                }
                Ok(true)
            }
            LogicalOperator::Or => {
                for condition in &self.conditions {
                    if condition.evaluate(transaction)? {
                        return Ok(true);
                    }
                }
                Ok(false)
            }
        }
    }
}

impl FromStr for ConditionField {
    type Err = crate::CategorizationError;
    
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "description" => Ok(ConditionField::Description),
            "merchant_name" => Ok(ConditionField::MerchantName),
            "amount" => Ok(ConditionField::Amount),
            "account_id" => Ok(ConditionField::AccountId),
            _ => Err(crate::CategorizationError::InvalidCondition(
                format!("Unknown field: {}", s)
            )),
        }
    }
}

impl FromStr for ConditionOperator {
    type Err = crate::CategorizationError;
    
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "contains" => Ok(ConditionOperator::Contains),
            "equals" => Ok(ConditionOperator::Equals),
            "starts_with" => Ok(ConditionOperator::StartsWith),
            "ends_with" => Ok(ConditionOperator::EndsWith),
            "regex" => Ok(ConditionOperator::Regex),
            "greater_than" => Ok(ConditionOperator::GreaterThan),
            "less_than" => Ok(ConditionOperator::LessThan),
            "between" => Ok(ConditionOperator::Between),
            _ => Err(crate::CategorizationError::InvalidCondition(
                format!("Unknown operator: {}", s)
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::Transaction;
    use chrono::NaiveDate;
    use rust_decimal_macros::dec;
    use uuid::Uuid;
    
    fn create_test_transaction() -> Transaction {
        Transaction {
            id: Uuid::new_v4(),
            account_id: Uuid::new_v4(),
            category_id: None,
            import_batch_id: None,
            transaction_date: NaiveDate::from_ymd_opt(2024, 3, 15).unwrap(),
            amount: dec!(-49.99),
            description: "AMAZON.COM*1A2B3C4D AMZN.COM/BILL WA".to_string(),
            raw_category: Some("Shopping".to_string()),
            merchant_name: Some("Amazon.com".to_string()),
            location: None,
            reference_number: None,
            transaction_hash: "test_hash".to_string(),
            schedule_c_line: None,
            is_business_expense: false,
            is_tax_deductible: false,
            is_recurring: false,
            expense_type: None,
            metadata: None,
            imported_at: None,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
            categorized_by: None,
            confidence_score: None,
        }
    }
    
    #[test]
    fn test_contains_condition() {
        let condition = Condition::new(
            ConditionField::Description,
            ConditionOperator::Contains,
            ConditionValue::Text("AMAZON".to_string()),
            false,
        );
        
        let transaction = create_test_transaction();
        assert!(condition.evaluate(&transaction).unwrap());
    }
    
    #[test]
    fn test_amount_condition() {
        let condition = Condition::new(
            ConditionField::Amount,
            ConditionOperator::LessThan,
            ConditionValue::Number(dec!(0)),
            false,
        );
        
        let transaction = create_test_transaction();
        assert!(condition.evaluate(&transaction).unwrap());
    }
    
    #[test]
    fn test_condition_group_and() {
        let conditions = vec![
            Condition::new(
                ConditionField::Description,
                ConditionOperator::Contains,
                ConditionValue::Text("AMAZON".to_string()),
                false,
            ),
            Condition::new(
                ConditionField::Amount,
                
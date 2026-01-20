I'll implement the bank-specific CSV parsers for the 8 supported banks. Let me create the comprehensive implementation:

# Bank-Specific CSV Parser Implementation

**Module**: `src/parsers/banks/`
**Date**: 2024-12-28
**Status**: Implementation Complete

## Files Created

| File | Purpose |
|------|---------|
| `mod.rs` | Bank registry and auto-detection |
| `chase.rs` | Chase CSV format |
| `wealthfront.rs` | Wealthfront CSV format |
| `bofa.rs` | Bank of America CSV format |
| `ally.rs` | Ally CSV format |
| `amex.rs` | American Express CSV format |
| `discover.rs` | Discover CSV format |
| `citi.rs` | Citi Bank CSV format |
| `capital_one.rs` | Capital One CSV format |

---

## src/parsers/banks/mod.rs

```rust
//! Bank-specific CSV parser configurations.
//!
//! This module contains configurations for parsing CSV files from various
//! financial institutions. Each bank has its own unique CSV format with
//! different column layouts, date formats, and data conventions.
//!
//! # Supported Banks
//!
//! - Chase: Credit cards and checking accounts
//! - Wealthfront: Cash and investment accounts
//! - Bank of America: Credit cards and checking
//! - Ally: Online savings and checking
//! - American Express: Credit cards
//! - Discover: Credit cards and banking
//! - Citi Bank: Credit cards and checking
//! - Capital One: Credit cards and checking
//!
//! # Auto-Detection
//!
//! Bank formats are auto-detected using header patterns and file content
//! analysis. The detection process:
//!
//! 1. Analyze CSV headers for bank-specific patterns
//! 2. Check for known column names and ordering
//! 3. Validate data format consistency
//! 4. Fall back to generic CSV parsing if no match

pub mod ally;
pub mod amex;
pub mod bofa;
pub mod capital_one;
pub mod chase;
pub mod citi;
pub mod discover;
pub mod wealthfront;

use crate::parsers::{Error, FieldMapping, FieldRef, ParseConfig, ParseResult, RawTransaction, Result};
use csv::{Reader, StringRecord};
use std::collections::HashMap;
use std::io::Read;

/// Bank-specific CSV configuration.
#[derive(Debug, Clone)]
pub struct BankConfig {
    /// Bank name for identification
    pub name: String,
    
    /// Header patterns that identify this bank's CSV format
    pub header_patterns: Vec<String>,
    
    /// Field mapping configuration
    pub field_mapping: FieldMapping,
    
    /// Date format used by this bank
    pub date_format: String,
    
    /// Alternative date formats to try
    pub date_formats: Vec<String>,
    
    /// Whether amounts are signed (negative for debits)
    pub signed_amounts: bool,
    
    /// Number of header rows to skip
    pub skip_rows: usize,
    
    /// CSV delimiter (usually comma)
    pub delimiter: u8,
    
    /// Custom parsing logic if needed
    pub custom_parser: Option<fn(&StringRecord, &FieldMapping, usize) -> Result<RawTransaction>>,
}

/// Registry of all supported bank configurations.
pub struct BankRegistry {
    configs: Vec<BankConfig>,
}

impl BankRegistry {
    /// Create new registry with all supported banks.
    pub fn new() -> Self {
        Self {
            configs: vec![
                chase::config(),
                wealthfront::config(),
                bofa::config(),
                ally::config(),
                amex::config(),
                discover::config(),
                citi::config(),
                capital_one::config(),
            ],
        }
    }
    
    /// Detect bank from CSV headers and sample data.
    pub fn detect_bank(&self, headers: &StringRecord, sample_rows: &[StringRecord]) -> Option<&BankConfig> {
        let header_string = headers.iter().collect::<Vec<_>>().join(",").to_lowercase();
        
        for config in &self.configs {
            if self.matches_bank(config, &header_string, headers, sample_rows) {
                return Some(config);
            }
        }
        
        None
    }
    
    /// Get bank config by name.
    pub fn get_bank(&self, name: &str) -> Option<&BankConfig> {
        self.configs.iter().find(|c| c.name.eq_ignore_ascii_case(name))
    }
    
    /// List all supported banks.
    pub fn list_banks(&self) -> Vec<&str> {
        self.configs.iter().map(|c| c.name.as_str()).collect()
    }
    
    /// Check if a config matches the given CSV data.
    fn matches_bank(
        &self,
        config: &BankConfig,
        header_string: &str,
        headers: &StringRecord,
        sample_rows: &[StringRecord],
    ) -> bool {
        // Check header patterns
        for pattern in &config.header_patterns {
            if header_string.contains(&pattern.to_lowercase()) {
                // Additional validation with sample data
                if self.validate_with_samples(config, headers, sample_rows) {
                    return true;
                }
            }
        }
        
        false
    }
    
    /// Validate bank config against sample rows.
    fn validate_with_samples(
        &self,
        config: &BankConfig,
        headers: &StringRecord,
        sample_rows: &[StringRecord],
    ) -> bool {
        if sample_rows.is_empty() {
            return true; // Can't validate without samples
        }
        
        // Try to parse first sample row
        match parse_row_with_config(&sample_rows[0], headers, &config.field_mapping, 2) {
            Ok(_) => true,
            Err(_) => false,
        }
    }
}

impl Default for BankRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Parse a CSV using bank-specific configuration.
pub fn parse_with_bank_config<R: Read>(
    reader: R,
    config: &BankConfig,
    parse_config: &ParseConfig,
) -> Result<ParseResult> {
    let mut csv_reader = csv::ReaderBuilder::new()
        .delimiter(config.delimiter)
        .flexible(true)
        .trim(csv::Trim::All)
        .from_reader(reader);
    
    // Skip configured number of rows
    for _ in 0..config.skip_rows {
        if csv_reader.records().next().is_none() {
            break;
        }
    }
    
    // Read headers
    let headers = csv_reader.headers()?.clone();
    
    let mut transactions = Vec::new();
    let mut errors = Vec::new();
    let mut line_number = config.skip_rows + 2; // Account for skipped rows and header
    
    for result in csv_reader.records() {
        match result {
            Ok(record) => {
                match parse_row_with_config(&record, &headers, &config.field_mapping, line_number) {
                    Ok(mut transaction) => {
                        // Apply any custom parsing logic
                        if let Some(custom_parser) = config.custom_parser {
                            match custom_parser(&record, &config.field_mapping, line_number) {
                                Ok(custom_tx) => transaction = custom_tx,
                                Err(e) => {
                                    if parse_config.strict_mode {
                                        return Err(e);
                                    } else {
                                        errors.push(crate::parsers::ParseError {
                                            line_number,
                                            message: e.to_string(),
                                            raw_content: Some(record.iter().collect::<Vec<_>>().join(",")),
                                        });
                                        line_number += 1;
                                        continue;
                                    }
                                }
                            }
                        }
                        
                        transactions.push(transaction);
                    }
                    Err(e) => {
                        if parse_config.strict_mode {
                            return Err(e);
                        } else {
                            errors.push(crate::parsers::ParseError {
                                line_number,
                                message: e.to_string(),
                                raw_content: Some(record.iter().collect::<Vec<_>>().join(",")),
                            });
                        }
                    }
                }
            }
            Err(e) => {
                if parse_config.strict_mode {
                    return Err(Error::CsvParse {
                        filename: "unknown".to_string(),
                        line: line_number,
                        message: e.to_string(),
                    });
                } else {
                    errors.push(crate::parsers::ParseError {
                        line_number,
                        message: e.to_string(),
                        raw_content: None,
                    });
                }
            }
        }
        
        line_number += 1;
    }
    
    Ok(ParseResult {
        transactions,
        errors,
        format: crate::parsers::FileFormat::Csv,
        institution: Some(config.name.clone()),
        rows_processed: line_number - config.skip_rows - 2,
    })
}

/// Parse a single CSV row using field mapping.
pub fn parse_row_with_config(
    record: &StringRecord,
    headers: &StringRecord,
    mapping: &FieldMapping,
    line_number: usize,
) -> Result<RawTransaction> {
    // Extract date
    let date_str = get_field_value(record, headers, &mapping.date)?;
    let date = parse_date(&date_str, line_number)?;
    
    // Extract amount (handle signed vs separate debit/credit columns)
    let amount = if let Some(amount_field) = &mapping.amount {
        parse_amount(&get_field_value(record, headers, amount_field)?, line_number)?
    } else if let (Some(debit_field), Some(credit_field)) = (&mapping.debit, &mapping.credit) {
        let debit_str = get_field_value(record, headers, debit_field).unwrap_or_default();
        let credit_str = get_field_value(record, headers, credit_field).unwrap_or_default();
        
        let debit = if debit_str.is_empty() { 
            rust_decimal::Decimal::ZERO 
        } else { 
            -parse_amount(&debit_str, line_number)?.abs() 
        };
        
        let credit = if credit_str.is_empty() { 
            rust_decimal::Decimal::ZERO 
        } else { 
            parse_amount(&credit_str, line_number)?.abs() 
        };
        
        debit + credit
    } else {
        return Err(Error::FieldMapping {
            filename: "unknown".to_string(),
            message: "No amount field specified in mapping".to_string(),
        });
    };
    
    // Extract description
    let description = get_field_value(record, headers, &mapping.description)?;
    
    // Extract optional fields
    let raw_category = mapping.category
        .as_ref()
        .and_then(|field| get_field_value(record, headers, field).ok());
    
    let reference_number = mapping.reference
        .as_ref()
        .and_then(|field| get_field_value(record, headers, field).ok());
    
    // Extract metadata fields
    let mut metadata = HashMap::new();
    for field in &mapping.metadata_fields {
        if let Ok(value) = get_field_value(record, headers, field) {
            if !value.is_empty() {
                let field_name = match field {
                    FieldRef::Name(name) => name.clone(),
                    FieldRef::Index(idx) => format!("field_{}", idx),
                    FieldRef::AnyOf(names) => names.first().unwrap_or(&"unknown".to_string()).clone(),
                };
                metadata.insert(field_name, value);
            }
        }
    }
    
    Ok(RawTransaction {
        date,
        amount,
        description,
        raw_category,
        reference_number,
        metadata,
        source: crate::parsers::TransactionSource {
            filename: String::new(), // Will be set by caller
            line_number,
            raw_content: Some(record.iter().collect::<Vec<_>>().join(",")),
        },
    })
}

/// Get field value using field reference.
fn get_field_value(record: &StringRecord, headers: &StringRecord, field: &FieldRef) -> Result<String> {
    match field {
        FieldRef::Name(name) => {
            let index = headers.iter()
                .position(|h| h.eq_ignore_ascii_case(name))
                .ok_or_else(|| Error::MissingField {
                    field: name.clone(),
                    filename: "unknown".to_string(),
                })?;
            
            Ok(record.get(index).unwrap_or("").trim().to_string())
        }
        
        FieldRef::Index(index) => {
            Ok(record.get(*index).unwrap_or("").trim().to_string())
        }
        
        FieldRef::AnyOf(names) => {
            for name in names {
                if let Some(index) = headers.iter().position(|h| h.eq_ignore_ascii_case(name)) {
                    return Ok(record.get(index).unwrap_or("").trim().to_string());
                }
            }
            
            Err(Error::MissingField {
                field: format!("any of {:?}", names),
                filename: "unknown".to_string(),
            })
        }
    }
}

/// Parse date string with multiple format attempts.
fn parse_date(date_str: &str, line_number: usize) -> Result<chrono::NaiveDate> {
    let formats = [
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
    ];
    
    for format in &formats {
        if let Ok(date) = chrono::NaiveDate::parse_from_str(date_str, format) {
            return Ok(date);
        }
    }
    
    Err(Error::DateParse {
        date_str: date_str.to_string(),
        line: line_number,
    })
}

/// Parse amount string, handling various formats.
fn parse_amount(amount_str: &str, line_number: usize) -> Result<rust_decimal::Decimal> {
    let cleaned = amount_str
        .trim()
        .replace(['$', ',', ' '], "")
        .replace("(", "-")
        .replace(")", "");
    
    if cleaned.is_empty() {
        return Ok(rust_decimal::Decimal::ZERO);
    }
    
    cleaned.parse().map_err(|_| Error::AmountParse {
        amount_str: amount_str.to_string(),
        line: line_number,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_bank_registry() {
        let registry = BankRegistry::new();
        let banks = registry.list_banks();
        
        assert_eq!(banks.len(), 8);
        assert!(banks.contains(&"Chase"));
        assert!(banks.contains(&"Wealthfront"));
        assert!(banks.contains(&"Bank of America"));
    }
    
    #[test]
    fn test_date_parsing() {
        assert!(parse_date("03/15/2024", 1).is_ok());
        assert!(parse_date("2024-03-15", 1).is_ok());
        assert!(parse_date("15/03/2024",
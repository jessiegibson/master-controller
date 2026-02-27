//! File format and institution detection.

use crate::error::Result;
use std::path::Path;

/// Supported file formats.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FileFormat {
    Csv,
    Qfx,
    Ofx,
    Unknown,
}

impl FileFormat {
    pub fn as_str(&self) -> &'static str {
        match self {
            FileFormat::Csv => "csv",
            FileFormat::Qfx => "qfx",
            FileFormat::Ofx => "ofx",
            FileFormat::Unknown => "unknown",
        }
    }
}

/// Detect the file format based on extension and content.
pub fn detect_format(path: &Path) -> Result<FileFormat> {
    // First check extension
    if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
        match ext.to_lowercase().as_str() {
            "csv" => return Ok(FileFormat::Csv),
            "qfx" => return Ok(FileFormat::Qfx),
            "ofx" => return Ok(FileFormat::Ofx),
            _ => {}
        }
    }

    // Try to detect from content
    let content = std::fs::read_to_string(path).map_err(|e| crate::error::Error::Io {
        path: path.to_path_buf(),
        source: e,
    })?;

    detect_format_from_content(&content)
}

/// Detect format from file content.
pub fn detect_format_from_content(content: &str) -> Result<FileFormat> {
    let trimmed = content.trim();

    // QFX/OFX files typically start with OFXHEADER or <?xml
    if trimmed.starts_with("OFXHEADER") || trimmed.contains("<OFX>") {
        return Ok(FileFormat::Qfx);
    }

    // Check for CSV-like content (comma-separated values with headers)
    if let Some(first_line) = trimmed.lines().next() {
        if first_line.contains(',') && !first_line.contains('<') {
            return Ok(FileFormat::Csv);
        }
    }

    Ok(FileFormat::Unknown)
}

/// Known institution identifiers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Institution {
    Chase,
    BankOfAmerica,
    Wealthfront,
    Ally,
    AmericanExpress,
    Discover,
    Citi,
    CapitalOne,
    Unknown,
}

impl Institution {
    pub fn as_str(&self) -> &'static str {
        match self {
            Institution::Chase => "chase",
            Institution::BankOfAmerica => "bank_of_america",
            Institution::Wealthfront => "wealthfront",
            Institution::Ally => "ally",
            Institution::AmericanExpress => "american_express",
            Institution::Discover => "discover",
            Institution::Citi => "citi",
            Institution::CapitalOne => "capital_one",
            Institution::Unknown => "unknown",
        }
    }

    pub fn display_name(&self) -> &'static str {
        match self {
            Institution::Chase => "Chase",
            Institution::BankOfAmerica => "Bank of America",
            Institution::Wealthfront => "Wealthfront",
            Institution::Ally => "Ally",
            Institution::AmericanExpress => "American Express",
            Institution::Discover => "Discover",
            Institution::Citi => "Citi",
            Institution::CapitalOne => "Capital One",
            Institution::Unknown => "Unknown",
        }
    }
}

/// Check if `text` contains `word` as a whole word (not as a substring of another word).
fn contains_word(text: &str, word: &str) -> bool {
    for (i, _) in text.match_indices(word) {
        let before_ok = i == 0 || !text.as_bytes()[i - 1].is_ascii_alphanumeric();
        let after_idx = i + word.len();
        let after_ok = after_idx >= text.len() || !text.as_bytes()[after_idx].is_ascii_alphanumeric();
        if before_ok && after_ok {
            return true;
        }
    }
    false
}

/// Detect institution from CSV headers or content.
pub fn detect_institution(content: &str) -> Institution {
    let lower = content.to_lowercase();

    // Check institution-specific header patterns first (most reliable)
    // Chase: Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
    if lower.contains("details,posting date,description,amount") {
        return Institution::Chase;
    }

    // Bank of America: Date,Description,Amount,Running Bal.
    if lower.contains("date,description,amount,running bal") {
        return Institution::BankOfAmerica;
    }

    // Wealthfront: Date,Amount,Description,Balance
    if lower.contains("date,amount,description,balance") && contains_word(&lower, "wealthfront") {
        return Institution::Wealthfront;
    }

    // American Express: Date,Description,Amount (or Date,Reference,Amount)
    if lower.contains("american express") || lower.contains("amex") {
        return Institution::AmericanExpress;
    }

    // Ally: Date,Time,Amount,Type,Description
    if lower.contains("date,time,amount,type,description") {
        return Institution::Ally;
    }

    // Discover: Trans. Date,Post Date,Description,Amount,Category
    if lower.contains("trans. date,post date,description,amount") {
        return Institution::Discover;
    }

    // Citi: Status,Date,Description,Debit,Credit
    if lower.contains("status,date,description,debit,credit") {
        return Institution::Citi;
    }

    // Capital One: Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit
    if lower.contains("transaction date,posted date,card no") {
        return Institution::CapitalOne;
    }

    // Fall back to whole-word keyword matching to avoid false positives
    // (e.g. "chase" inside "purchase", "ally" inside "finally").
    if contains_word(&lower, "chase") {
        Institution::Chase
    } else if contains_word(&lower, "bofa") {
        Institution::BankOfAmerica
    } else if contains_word(&lower, "wealthfront") {
        Institution::Wealthfront
    } else if contains_word(&lower, "ally") {
        Institution::Ally
    } else if contains_word(&lower, "discover") {
        Institution::Discover
    } else if contains_word(&lower, "citibank") || contains_word(&lower, "citi") {
        Institution::Citi
    } else if lower.contains("capital one") {
        Institution::CapitalOne
    } else {
        Institution::Unknown
    }
}

/// Institution-specific CSV column mappings.
pub struct CsvMapping {
    pub date_column: usize,
    pub amount_column: usize,
    pub description_column: usize,
    pub category_column: Option<usize>,
    pub date_format: &'static str,
    pub has_header: bool,
    pub negate_amounts: bool,
}

impl Institution {
    /// Get the CSV column mapping for this institution.
    pub fn csv_mapping(&self) -> CsvMapping {
        match self {
            Institution::Chase => CsvMapping {
                date_column: 1,        // Posting Date
                amount_column: 3,      // Amount
                description_column: 2, // Description
                category_column: Some(4),
                date_format: "%m/%d/%Y",
                has_header: true,
                negate_amounts: false,
            },
            Institution::BankOfAmerica => CsvMapping {
                date_column: 0,
                amount_column: 2,
                description_column: 1,
                category_column: None,
                date_format: "%m/%d/%Y",
                has_header: true,
                negate_amounts: false,
            },
            Institution::Wealthfront => CsvMapping {
                date_column: 0,
                amount_column: 1,
                description_column: 2,
                category_column: None,
                date_format: "%Y-%m-%d",
                has_header: true,
                negate_amounts: false,
            },
            Institution::AmericanExpress => CsvMapping {
                date_column: 0,
                amount_column: 2,
                description_column: 1,
                category_column: None,
                date_format: "%m/%d/%Y",
                has_header: true,
                negate_amounts: true, // AMEX shows expenses as positive
            },
            Institution::Ally => CsvMapping {
                // Ally: Date, Time, Amount, Type, Description
                date_column: 0,
                amount_column: 2,
                description_column: 4,
                category_column: Some(3), // Type column
                date_format: "%Y-%m-%d",
                has_header: true,
                negate_amounts: false,
            },
            Institution::Discover => CsvMapping {
                // Discover: Trans. Date, Post Date, Description, Amount, Category
                date_column: 0,
                amount_column: 3,
                description_column: 2,
                category_column: Some(4),
                date_format: "%m/%d/%Y",
                has_header: true,
                negate_amounts: true, // Discover shows expenses as positive
            },
            Institution::Citi => CsvMapping {
                // Citi: Status, Date, Description, Debit, Credit
                // Using Date for date, Description for description
                // Amount column is Debit (index 3), but Citi uses separate debit/credit
                date_column: 1,
                amount_column: 3, // Debit column (negative amounts)
                description_column: 2,
                category_column: None,
                date_format: "%m/%d/%Y",
                has_header: true,
                negate_amounts: true,
            },
            Institution::CapitalOne => CsvMapping {
                // Capital One: Transaction Date, Posted Date, Card No., Description, Category, Debit, Credit
                date_column: 0,
                amount_column: 5, // Debit column
                description_column: 3,
                category_column: Some(4),
                date_format: "%Y-%m-%d",
                has_header: true,
                negate_amounts: true,
            },
            Institution::Unknown => CsvMapping {
                // Generic fallback
                date_column: 0,
                amount_column: 1,
                description_column: 2,
                category_column: None,
                date_format: "%Y-%m-%d",
                has_header: true,
                negate_amounts: false,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_format_csv() {
        let content = "Date,Amount,Description\n2024-01-15,-50.00,Test";
        assert_eq!(detect_format_from_content(content).unwrap(), FileFormat::Csv);
    }

    #[test]
    fn test_detect_format_qfx() {
        let content = "OFXHEADER:100\nDATA:OFXSGML";
        assert_eq!(detect_format_from_content(content).unwrap(), FileFormat::Qfx);
    }

    #[test]
    fn test_detect_institution_chase() {
        let content = "Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\nDEBIT,01/15/2024,AMAZON,-50.00,ACH,1000.00,";
        assert_eq!(detect_institution(content), Institution::Chase);
    }

    #[test]
    fn test_detect_institution_bofa() {
        let content = "Date,Description,Amount,Running Bal.\n01/15/2024,PURCHASE AT STORE,-25.00,500.00";
        assert_eq!(detect_institution(content), Institution::BankOfAmerica);
    }

    #[test]
    fn test_detect_institution_ally() {
        let content = "Date,Time,Amount,Type,Description\n2024-01-15,10:30:00,-50.00,Withdrawal,ATM Withdrawal";
        assert_eq!(detect_institution(content), Institution::Ally);
    }

    #[test]
    fn test_detect_institution_discover() {
        let content = "Trans. Date,Post Date,Description,Amount,Category\n01/15/2024,01/16/2024,AMAZON,50.00,Shopping";
        assert_eq!(detect_institution(content), Institution::Discover);
    }

    #[test]
    fn test_detect_institution_citi() {
        let content = "Status,Date,Description,Debit,Credit\nCleared,01/15/2024,PURCHASE,50.00,";
        assert_eq!(detect_institution(content), Institution::Citi);
    }

    #[test]
    fn test_detect_institution_capital_one() {
        let content = "Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit\n2024-01-15,2024-01-16,1234,STORE PURCHASE,Shopping,50.00,";
        assert_eq!(detect_institution(content), Institution::CapitalOne);
    }

    #[test]
    fn test_detect_institution_amex() {
        let content = "Date,Description,Amount\nAmerican Express Statement\n01/15/2024,STORE PURCHASE,50.00";
        assert_eq!(detect_institution(content), Institution::AmericanExpress);
    }

    #[test]
    fn test_csv_mapping_chase() {
        let mapping = Institution::Chase.csv_mapping();
        assert_eq!(mapping.date_column, 1);
        assert_eq!(mapping.amount_column, 3);
        assert_eq!(mapping.description_column, 2);
        assert_eq!(mapping.date_format, "%m/%d/%Y");
        assert!(!mapping.negate_amounts);
    }

    #[test]
    fn test_csv_mapping_ally() {
        let mapping = Institution::Ally.csv_mapping();
        assert_eq!(mapping.date_column, 0);
        assert_eq!(mapping.amount_column, 2);
        assert_eq!(mapping.description_column, 4);
        assert_eq!(mapping.date_format, "%Y-%m-%d");
    }

    #[test]
    fn test_csv_mapping_discover() {
        let mapping = Institution::Discover.csv_mapping();
        assert_eq!(mapping.date_column, 0);
        assert_eq!(mapping.amount_column, 3);
        assert_eq!(mapping.description_column, 2);
        assert!(mapping.negate_amounts);
    }

    #[test]
    fn test_csv_mapping_citi() {
        let mapping = Institution::Citi.csv_mapping();
        assert_eq!(mapping.date_column, 1);
        assert_eq!(mapping.amount_column, 3);
        assert_eq!(mapping.description_column, 2);
        assert!(mapping.negate_amounts);
    }

    #[test]
    fn test_csv_mapping_capital_one() {
        let mapping = Institution::CapitalOne.csv_mapping();
        assert_eq!(mapping.date_column, 0);
        assert_eq!(mapping.amount_column, 5);
        assert_eq!(mapping.description_column, 3);
        assert!(mapping.negate_amounts);
    }

    #[test]
    fn test_contains_word() {
        assert!(contains_word("hello world", "hello"));
        assert!(contains_word("hello world", "world"));
        assert!(!contains_word("hello world", "ello"));
        assert!(!contains_word("purchase", "chase"));
        assert!(!contains_word("finally", "ally"));
    }
}

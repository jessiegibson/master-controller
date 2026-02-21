# IRS Schedule C Line Item Mapping for Privacy-First Personal Finance CLI

**Date**: 2024-12-28  
**Version**: 1.0  
**Tax Year**: 2024  
**Target Users**: Freelancers and Sole Proprietors

---

## 1. Complete Schedule C Line Item Reference

### Part I - Income
| Line | Description | Purpose |
|------|-------------|---------|
| 1 | Gross receipts or sales | Total business income before returns |
| 2 | Returns and allowances | Refunds, discounts given to customers |
| 3 | Subtract line 2 from line 1 | Net sales |
| 4 | Cost of goods sold (from Part III) | Direct costs of products sold |
| 5 | Gross profit (line 3 minus line 4) | Profit after direct costs |
| 6 | Other income | Miscellaneous business income |
| 7 | Gross income (add lines 5 and 6) | Total business income |

### Part II - Expenses
| Line | Description | Deductible | Notes |
|------|-------------|------------|-------|
| 8 | Advertising | 100% | Marketing, ads, promotions |
| 9 | Car and truck expenses | 100% | Vehicle costs or mileage |
| 10 | Commissions and fees | 100% | Sales commissions, platform fees |
| 11 | Contract labor | 100% | Independent contractors (1099) |
| 12 | Depletion | 100% | Natural resource depletion (rare) |
| 13 | Depreciation and section 179 | 100% | Equipment, software depreciation |
| 14 | Employee benefit programs | 100% | Health insurance, retirement for employees |
| 15 | Insurance (other than health) | 100% | Business liability, property insurance |
| 16a | Interest - Mortgage (paid to banks, etc.) | 100% | Business property mortgage interest |
| 16b | Interest - Other | 100% | Business loan, credit card interest |
| 17 | Legal and professional services | 100% | Attorneys, accountants, consultants |
| 18 | Office expense | 100% | Supplies, postage, small equipment |
| 19 | Pension and profit-sharing plans | 100% | Employee retirement contributions |
| 20a | Rent or lease - Vehicles, machinery, equipment | 100% | Equipment rentals |
| 20b | Rent or lease - Other business property | 100% | Office rent, coworking spaces |
| 21 | Repairs and maintenance | 100% | Fixing equipment, property maintenance |
| 22 | Supplies | 100% | Materials, inventory for business use |
| 23 | Taxes and licenses | 100% | Business licenses, state/local taxes |
| 24a | Travel | 100% | Flights, hotels, transportation |
| 24b | Deductible meals | 50% | Business meals (2024: 50% deductible) |
| 25 | Utilities | 100% | Phone, internet, electricity |
| 26 | Wages | 100% | Employee salaries |
| 27a | Other expenses | Various | Miscellaneous business expenses |

### Part III - Cost of Goods Sold (if applicable)
| Line | Description |
|------|-------------|
| 33 | Method(s) used to value closing inventory |
| 34 | Was there any change in determining quantities, costs, or valuations between opening and closing inventory? |
| 35 | Inventory at beginning of year |
| 36 | Purchases less cost of items withdrawn for personal use |
| 37 | Cost of labor |
| 38 | Materials and supplies |
| 39 | Other costs |
| 40 | Add lines 35 through 39 |
| 41 | Inventory at end of year |
| 42 | Cost of goods sold (subtract line 41 from line 40) |

---

## 2. Recommended Default Expense Categories

### Database Schema Addition
```sql
-- Add Schedule C mapping to categories table
ALTER TABLE categories ADD COLUMN schedule_c_line VARCHAR(10);
ALTER TABLE categories ADD COLUMN deduction_percentage DECIMAL(5,2) DEFAULT 100.00;
ALTER TABLE categories ADD COLUMN is_cogs BOOLEAN DEFAULT FALSE;
```

### Default Categories with Schedule C Mapping
```yaml
default_categories:
  income:
    - name: "Business Income"
      schedule_c_line: "L1"
      is_income: true
      deduction_percentage: 0
      
    - name: "Consulting Revenue"
      schedule_c_line: "L1"
      is_income: true
      deduction_percentage: 0
      
    - name: "Freelance Income"
      schedule_c_line: "L1"
      is_income: true
      deduction_percentage: 0
      
    - name: "Other Business Income"
      schedule_c_line: "L6"
      is_income: true
      deduction_percentage: 0

  expenses:
    # Line 8 - Advertising
    - name: "Advertising & Marketing"
      schedule_c_line: "L8"
      deduction_percentage: 100
      examples: ["Google Ads", "Facebook Ads", "Business cards", "Website ads"]
      
    - name: "Social Media Marketing"
      schedule_c_line: "L8"
      deduction_percentage: 100
      
    # Line 9 - Car and truck expenses
    - name: "Vehicle Expenses"
      schedule_c_line: "L9"
      deduction_percentage: 100
      examples: ["Gas", "Car insurance", "Repairs", "Registration"]
      note: "Use actual expenses OR standard mileage rate"
      
    - name: "Mileage"
      schedule_c_line: "L9"
      deduction_percentage: 100
      note: "2024 rate: $0.67/mile for business use"
      
    # Line 10 - Commissions and fees
    - name: "Platform Fees"
      schedule_c_line: "L10"
      deduction_percentage: 100
      examples: ["Upwork fees", "Fiverr fees", "Etsy fees", "PayPal fees"]
      
    - name: "Payment Processing Fees"
      schedule_c_line: "L10"
      deduction_percentage: 100
      examples: ["Stripe fees", "Square fees", "Credit card processing"]
      
    # Line 11 - Contract labor
    - name: "Contractor Payments"
      schedule_c_line: "L11"
      deduction_percentage: 100
      note: "Must issue 1099-NEC if over $600/year"
      
    - name: "Freelancer Payments"
      schedule_c_line: "L11"
      deduction_percentage: 100
      
    # Line 13 - Depreciation
    - name: "Equipment Depreciation"
      schedule_c_line: "L13"
      deduction_percentage: 100
      examples: ["Computer", "Camera", "Tools", "Furniture"]
      
    - name: "Software"
      schedule_c_line: "L13"
      deduction_percentage: 100
      examples: ["Adobe Creative Suite", "Microsoft Office", "Development tools"]
      note: "Can elect Section 179 for immediate deduction"
      
    # Line 15 - Insurance
    - name: "Business Insurance"
      schedule_c_line: "L15"
      deduction_percentage: 100
      examples: ["Liability insurance", "Professional insurance", "Equipment insurance"]
      
    # Line 16b - Interest
    - name: "Business Loan Interest"
      schedule_c_line: "L16b"
      deduction_percentage: 100
      
    - name: "Business Credit Card Interest"
      schedule_c_line: "L16b"
      deduction_percentage: 100
      
    # Line 17 - Legal and professional
    - name: "Legal & Professional Services"
      schedule_c_line: "L17"
      deduction_percentage: 100
      examples: ["Attorney fees", "Accountant", "Business consultant"]
      
    - name: "Tax Preparation"
      schedule_c_line: "L17"
      deduction_percentage: 100
      
    # Line 18 - Office expense
    - name: "Office Supplies"
      schedule_c_line: "L18"
      deduction_percentage: 100
      examples: ["Paper", "Pens", "Printer ink", "Postage"]
      
    - name: "Small Office Equipment"
      schedule_c_line: "L18"
      deduction_percentage: 100
      examples: ["Calculator", "Stapler", "Under $2,500 equipment"]
      
    # Line 20b - Rent
    - name: "Office Rent"
      schedule_c_line: "L20b"
      deduction_percentage: 100
      
    - name: "Coworking Space"
      schedule_c_line: "L20b"
      deduction_percentage: 100
      
    - name: "Storage Unit"
      schedule_c_line: "L20b"
      deduction_percentage: 100
      
    # Line 21 - Repairs and maintenance
    - name: "Equipment Repairs"
      schedule_c_line: "L21"
      deduction_percentage: 100
      examples: ["Computer repair", "Phone repair", "Office equipment"]
      
    - name: "Website Maintenance"
      schedule_c_line: "L21"
      deduction_percentage: 100
      
    # Line 22 - Supplies
    - name: "Business Supplies"
      schedule_c_line: "L22"
      deduction_percentage: 100
      examples: ["Materials", "Inventory", "Production supplies"]
      
    # Line 23 - Taxes and licenses
    - name: "Business Licenses"
      schedule_c_line: "L23"
      deduction_percentage: 100
      
    - name: "Professional Licenses"
      schedule_c_line: "L23"
      deduction_percentage: 100
      
    # Line 24a - Travel
    - name: "Business Travel"
      schedule_c_line: "L24a"
      deduction_percentage: 100
      examples: ["Flights", "Hotels", "Car rentals", "Parking"]
      
    # Line 24b - Meals (50% deductible)
    - name: "Business Meals"
      schedule_c_line: "L24b"
      deduction_percentage: 50
      note: "Must be business-related, with business purpose documented"
      
    # Line 25 - Utilities
    - name: "Internet"
      schedule_c_line: "L25"
      deduction_percentage: 100
      business_use_adjustment: true
      
    - name: "Phone"
      schedule_c_line: "L25"
      deduction_percentage: 100
      business_use_adjustment: true
      
    - name: "Utilities"
      schedule_c_line: "L25"
      deduction_percentage: 100
      note: "For business-only utilities or home office portion"
      
    # Line 27a - Other expenses
    - name: "Bank Fees"
      schedule_c_line: "L27a"
      deduction_percentage: 100
      
    - name: "Subscriptions"
      schedule_c_line: "L27a"
      deduction_percentage: 100
      examples: ["Business magazines", "Online services", "SaaS tools"]
      
    - name: "Education & Training"
      schedule_c_line: "L27a"
      deduction_percentage: 100
      examples: ["Courses", "Books", "Conferences", "Certifications"]
      
    - name: "Miscellaneous Business Expense"
      schedule_c_line: "L27a"
      deduction_percentage: 100
```

---

## 3. Rules for Categorizing Common Business Expenses

### Rule-Based Categorization Engine Enhancement

```rust
// Add to src/categorization/rules.rs

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduleCRule {
    pub line_number: String,
    pub deduction_percentage: Decimal,
    pub requires_business_purpose: bool,
    pub substantiation_requirements: Vec<String>,
    pub common_audit_flags: Vec<String>,
}

impl Category {
    pub fn schedule_c_info(&self) -> Option<ScheduleCRule> {
        match self.schedule_c_line.as_deref() {
            Some("L24b") => Some(ScheduleCRule {
                line_number: "L24b".to_string(),
                deduction_percentage: dec!(50.0),
                requires_business_purpose: true,
                substantiation_requirements: vec![
                    "Receipt".to_string(),
                    "Business purpose".to_string(),
                    "Attendees (if applicable)".to_string(),
                ],
                common_audit_flags: vec![
                    "High meal expenses relative to income".to_string(),
                    "Round dollar amounts".to_string(),
                ],
            }),
            Some(line) if line.starts_with('L') => Some(ScheduleCRule {
                line_number: line.to_string(),
                deduction_percentage: dec!(100.0),
                requires_business_purpose: false,
                substantiation_requirements: vec!["Receipt".to_string()],
                common_audit_flags: vec![],
            }),
            _ => None,
        }
    }
}
```

### Categorization Rules by Transaction Patterns

```yaml
categorization_rules:
  # Income Detection
  income_patterns:
    - pattern: "DEPOSIT.*PAYPAL|VENMO.*PAYMENT|ZELLE.*PAYMENT"
      category: "Business Income"
      confidence: "medium"
      
    - pattern: "ACH.*CREDIT|WIRE.*INCOMING|CHECK.*DEPOSIT"
      category: "Business Income"
      confidence: "low"
      note: "Manual review recommended"

  # Expense Patterns by Schedule C Line
  expense_patterns:
    # Line 8 - Advertising
    advertising:
      - pattern: "GOOGLE ADS|FACEBOOK ADS|INSTAGRAM ADS|LINKEDIN ADS"
        category: "Advertising & Marketing"
        confidence: "high"
        
      - pattern: "VISTAPRINT|MOOCOM|CANVA|MAILCHIMP"
        category: "Advertising & Marketing" 
        confidence: "high"

    # Line 9 - Vehicle
    vehicle:
      - pattern: "SHELL|EXXON|BP|CHEVRON|MOBIL.*GAS"
        category: "Vehicle Expenses"
        confidence: "medium"
        note: "Requires business use percentage"
        
      - pattern: "AAA|GEICO|STATE FARM.*AUTO|PROGRESSIVE"
        category: "Vehicle Expenses"
        confidence: "medium"

    # Line 10 - Fees
    fees:
      - pattern: "UPWORK|FIVERR|ETSY.*FEE|PAYPAL.*FEE"
        category: "Platform Fees"
        confidence: "high"
        
      - pattern: "STRIPE|SQUARE.*FEE|MERCHANT.*FEE"
        category: "Payment Processing Fees"
        confidence: "high"

    # Line 13 - Software/Equipment
    software:
      - pattern: "ADOBE|MICROSOFT.*365|OFFICE|CREATIVE.*CLOUD"
        category: "Software"
        confidence: "high"
        
      - pattern: "AMAZON.*COMPUTER|BEST BUY.*LAPTOP|APPLE.*MACBOOK"
        category: "Equipment Depreciation"
        confidence: "medium"
        note: "May qualify for Section 179"

    # Line 17 - Professional Services
    professional:
      - pattern: "ATTORNEY|LAWYER|CPA|ACCOUNTANT|TAX.*PREP"
        category: "Legal & Professional Services"
        confidence: "high"

    # Line 18 - Office Supplies
    office:
      - pattern: "STAPLES|OFFICE.*DEPOT|AMAZON.*OFFICE|FEDEX.*PRINT"
        category: "Office Supplies"
        confidence: "high"

    # Line 20b - Rent
    rent:
      - pattern: "REGUS|WEWORK|OFFICE.*
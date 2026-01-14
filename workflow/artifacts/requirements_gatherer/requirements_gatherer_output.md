I've analyzed your input and identified several areas where I need clarification before generating the complete requirements document. Let me start with the most critical questions:

## Critical Questions (Blocking)

1. **Which financial institutions should be supported for CSV/QFX import initially?**
   - Context: Different banks use vastly different CSV formats and field names. Parser logic must be built for specific formats.
   - Examples: Chase uses "Description,Amount,Date" while Bank of America uses "Posted Date,Reference Number,Payee,Address,Amount"
   - My assumption if unanswered: Chase, Bank of America, Wells Fargo, Amex, Discover (top 5 US institutions)

2. **For PDF statement parsing, which specific bank PDF formats should be supported?**
   - Context: PDF parsing is complex and bank-specific. Each institution has different layouts, fonts, and table structures.
   - This may require OCR or specific PDF text extraction logic per bank.
   - Routed to: Human Proxy (may need technical feasibility assessment)

3. **For Schedule C mapping, should the app support multiple businesses/sole proprietorships, or single business only for MVP?**
   - Context: Affects data model (single vs multi-tenant), report generation complexity, and encryption key management.
   - Single business: Simpler data model, one set of categories
   - Multiple businesses: Need business entity separation, category sets per business
   - Routed to: Human Proxy (may need CPA input for tax compliance)

4. **For encryption key management, what's your preferred approach?**
   - Master password (user must remember, no recovery if lost)
   - Recovery phrase like crypto wallets (12/24 words, lose phrase = lose data)  
   - Key derivation from password with optional recovery questions
   - Context: This is a foundational architecture decision affecting user experience and security model.

## Important Questions (Should Resolve)

5. **What date ranges should reports cover?**
   - Calendar year only, tax year only, or custom date ranges?
   - Should historical data from previous years be supported?

6. **For automatic categorization, should the ML model:**
   - Train only on user's own transaction history?
   - Use a pre-trained model with common business expense categories?
   - Both (pre-trained + user customization)?

7. **Should recurring transactions be auto-detected and auto-categorized?**
   - Context: Helps with automation but requires pattern detection logic.

8. **What level of transaction editing should be supported?**
   - Read-only (import and categorize only)?
   - Edit descriptions and amounts?
   - Add manual transactions?
   - Delete/hide transactions?

## Assumptions Made (Minor Items)

- **A-001**: Single user per installation. No multi-user support. (Risk: low)
- **A-002**: US tax jurisdiction only. No international tax code support. (Risk: low)  
- **A-003**: English language only for MVP. (Risk: low)
- **A-004**: Command-line interface only. No GUI for MVP. (Risk: low)
- **A-005**: DuckDB file stored locally in user's home directory or configurable path. (Risk: low)

## Technical Architecture Questions (For Specialist Review)

These questions may need Rust engineering expertise:

9. **For ML categorization in Rust, preferred approach?**
   - Use Python subprocess with scikit-learn/pandas?
   - Pure Rust ML crates (candle, smartcore)?
   - Simple rule-based system for MVP?
   - Context: Affects dependencies, binary size, and cross-platform compatibility.

10. **For PDF parsing, preferred Rust crate?**
    - pdf-extract (simple text extraction)
    - lopdf (more control, complex)
    - External tool like pdftotext?
    - Context: Different crates have different capabilities and maintenance status.

Please answer the critical questions (1-4) so I can proceed with generating the complete requirements document. The technical questions (9-10) can be deferred to the Architecture phase if you prefer.
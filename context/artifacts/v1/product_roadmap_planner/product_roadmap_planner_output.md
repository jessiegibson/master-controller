# Product Roadmap: Privacy-First Personal Finance CLI

Version: 1
Date: 2024-12-28
Status: Draft
Requirements Version: 1

## Executive Summary

A phased approach to building a privacy-first personal finance CLI in Rust. MVP focuses on core transaction processing, categorization, and tax reporting with 8 major banks supported. Phase 2 adds advanced features like recurring detection and PDF parsing.

## MVP Scope

### Included in MVP

| ID | Requirement | Priority | Work Stream |
|----|-------------|----------|-------------|
| FR-001 | Multi-Bank Transaction Import | must-have | Data Ingestion |
| FR-002 | Local Data Storage | must-have | Data Storage |
| FR-003 | Rule-Based Transaction Categorization | must-have | Business Logic |
| FR-005 | Transaction CRUD Operations | must-have | Business Logic |
| FR-006 | Profit & Loss Report Generation | must-have | Reporting |
| FR-007 | Cash Flow Report Generation | must-have | Reporting |
| FR-008 | IRS Schedule C Line Item Mapping | must-have | Tax Integration |
| FR-009 | CLI Interface | must-have | User Interface |
| NFR-001 | Local Data Encryption | must-have | Security |
| NFR-003 | Reliability | must-have | Quality |
| NFR-005 | Privacy | must-have | Security |

### Deferred to Post-MVP

| ID | Requirement | Reason | Target Phase |
|----|-------------|--------|--------------|
| FR-004 | Recurring Transaction Detection | Complex algorithm, should-have priority | Phase 2 |
| FR-010 | Data Backup and Restore | Should-have, can use manual file copies initially | Phase 2 |
| NFR-002 | Performance | Should-have, optimize after core functionality | Phase 2 |
| NFR-004 | Usability | Should-have, basic CLI acceptable for MVP | Phase 2 |

## Work Streams

### Stream: Infrastructure

**Focus**: Project scaffolding, build system, testing framework
**Key Agents**: Rust Scaffolder, Test Developer
**Dependencies**: None

Sprints in this stream:
- S1-03-scaffolding
- S1-14-testing-framework

### Stream: Security

**Focus**: Encryption, key management, secure data handling
**Key Agents**: Encryption Developer, Security Architect
**Dependencies**: None

Sprints in this stream:
- S1-04-security-architecture
- S1-08-encryption-implementation

### Stream: Data Storage

**Focus**: DuckDB integration, schema design, migrations
**Key Agents**: DuckDB Integration Developer, Data Architect
**Dependencies**: Security (for encryption integration)

Sprints in this stream:
- S1-05-data-architecture
- S1-09-duckdb-implementation

### Stream: Data Ingestion

**Focus**: Multi-bank parsers, file format handling, duplicate detection
**Key Agents**: Parser Developer, Data Architect
**Dependencies**: Data Storage (for persistence)

Sprints in this stream:
- S1-10-parser-implementation
- S1-11-bank-format-support

### Stream: Business Logic

**Focus**: Categorization engine, transaction operations, business rules
**Key Agents**: Categorization Engine Developer, Financial Calculator Developer
**Dependencies**: Data Storage, Data Ingestion

Sprints in this stream:
- S1-12-categorization-engine
- S1-13-transaction-crud

### Stream: Tax Integration

**Focus**: IRS Schedule C mapping, tax calculations, compliance
**Key Agents**: Tax Integration Developer, Financial Calculator Developer
**Dependencies**: Business Logic

Sprints in this stream:
- S1-15-schedule-c-mapping

### Stream: Reporting

**Focus**: P&L reports, cash flow analysis, export formats
**Key Agents**: Financial Calculator Developer, Report Generator Developer
**Dependencies**: Business Logic, Tax Integration

Sprints in this stream:
- S1-16-financial-reports

### Stream: User Interface

**Focus**: CLI commands, interactive prompts, user experience
**Key Agents**: CLI Developer, CLI UX Designer
**Dependencies**: All other streams (integrates everything)

Sprints in this stream:
- S1-06-cli-design
- S1-17-cli-implementation
- S1-18-integration-testing

## Sprint Sequence

### Phase: MVP

```
S1-01 ─────┐
           ├──→ S1-02 ──────────────────────────────────────────┐
S1-06 ─────┘      │                                              │
                  ├──→ S1-03 ──────────────────────────┐        │
                  │                                     │        │
                  ├──→ S1-04 ──→ S1-08 ─────────────────┤        │
                  │                                     │        │
                  └──→ S1-05 ──→ S1-09 ──→ S1-10 ──→ S1-11     │
                                   │        │                    │
                                   │        └──→ S1-12 ──→ S1-13 │
                                   │                       │     │
                                   └────────────────────────┤     │
                                                           │     │
                                   S1-15 ◄─────────────────┘     │
                                     │                           │
                                     └──→ S1-16                  │
                                            │                    │
                                            └──→ S1-17 ◄─────────┘
                                                   │
                                                   └──→ S1-18
                                                          │
                                                          └──→ S1-14
```

| Sprint | Name | Work Stream | Dependencies | Agents |
|--------|------|-------------|--------------|--------|
| S1-01 | Requirements Analysis | Foundation | None | Requirements Gatherer |
| S1-02 | System Architecture | Foundation | S1-01 | System Architect |
| S1-03 | Project Scaffolding | Infrastructure | S1-02 | Rust Scaffolder |
| S1-04 | Security Architecture | Security | S1-02 | Security Architect |
| S1-05 | Data Architecture | Data Storage | S1-02 | Data Architect |
| S1-06 | CLI Design | User Interface | S1-01 | CLI UX Designer |
| S1-08 | Encryption Implementation | Security | S1-04 | Encryption Developer |
| S1-09 | DuckDB Implementation | Data Storage | S1-05, S1-08 | DuckDB Integration Developer |
| S1-10 | Parser Implementation | Data Ingestion | S1-09 | Parser Developer |
| S1-11 | Bank Format Support | Data Ingestion | S1-10 | Parser Developer |
| S1-12 | Categorization Engine | Business Logic | S1-11 | Categorization Engine Developer |
| S1-13 | Transaction CRUD | Business Logic | S1-12 | Financial Calculator Developer |
| S1-15 | Schedule C Mapping | Tax Integration | S1-13 | Tax Integration Developer |
| S1-16 | Financial Reports | Reporting | S1-15 | Report Generator Developer |
| S1-17 | CLI Implementation | User Interface | S1-16, S1-06 | CLI Developer |
| S1-18 | Integration Testing | Quality | S1-17 | Test Developer |
| S1-14 | Testing Framework | Infrastructure | S1-18 | Test Developer |

## Sprint Summaries

### S1-01: Requirements Analysis

**Work Stream**: Foundation
**Dependencies**: None

**Scope**:
Analyze and validate requirements document, create roadmap, define sprint structure.

**Entry Criteria**:
- Requirements document available

**Exit Criteria**:
- Roadmap approved
- Sprint definitions complete
- All agents briefed on project scope

**Agents**:
- Primary: Product Roadmap Planner
- Supporting: Requirements Gatherer
- Review: Human

**Deliverables**:
- roadmap-v1.md
- roadmap-v1.yaml
- Sprint definition files (S1-01 through S1-18)

**Risks**:
- Requirements may need clarification

---

### S1-02: System Architecture

**Work Stream**: Foundation
**Dependencies**: S1-01

**Scope**:
Design overall system architecture, module boundaries, data flow, and integration patterns.

**Entry Criteria**:
- Requirements approved
- Roadmap approved

**Exit Criteria**:
- Architecture document complete
- Module interfaces defined
- Technology stack validated
- Data flow diagrams complete

**Agents**:
- Primary: System Architect
- Supporting: Data Architect, Security Architect
- Review: Staff Engineer Rust, Human

**Deliverables**:
- system-architecture.md
- module-interfaces.yaml
- data-flow-diagrams/

**Risks**:
- DuckDB integration complexity unknown
- Rust async requirements unclear

---

### S1-03: Project Scaffolding

**Work Stream**: Infrastructure
**Dependencies**: S1-02

**Scope**:
Create Rust project structure, configure build system, set up development environment.

**Entry Criteria**:
- System architecture approved
- Module structure defined

**Exit Criteria**:
- Cargo.toml configured with dependencies
- Module structure created
- Build system working
- Development environment documented

**Agents**:
- Primary: Rust Scaffolder
- Supporting: System Architect
- Review: Staff Engineer Rust

**Deliverables**:
- Cargo.toml
- src/ module structure
- README.md with setup instructions
- .gitignore and project config

**Risks**:
- Dependency version conflicts
- Build complexity for encryption libraries

---

### S1-04: Security Architecture

**Work Stream**: Security
**Dependencies**: S1-02

**Scope**:
Design encryption system, key management, secure memory handling, and recovery mechanisms.

**Entry Criteria**:
- System architecture approved
- Security requirements understood

**Exit Criteria**:
- Encryption architecture documented
- Key derivation strategy defined
- Recovery code system designed
- Security threat model complete

**Agents**:
- Primary: Security Architect
- Supporting: System Architect
- Review: Staff Engineer Rust, Human

**Deliverables**:
- security-architecture.md
- encryption-design.yaml
- threat-model.md
- recovery-system-design.md

**Risks**:
- Complexity of secure key management
- Recovery code UX challenges

---

### S1-05: Data Architecture

**Work Stream**: Data Storage
**Dependencies**: S1-02

**Scope**:
Design database schema, transaction models, categorization data structures, and migration system.

**Entry Criteria**:
- System architecture approved
- Data requirements understood

**Exit Criteria**:
- Database schema defined
- Data models documented
- Migration strategy designed
- Query patterns optimized

**Agents**:
- Primary: Data Architect
- Supporting: System Architect, Security Architect
- Review: Staff Engineer Rust

**Deliverables**:
- database-schema.sql
- data-models.yaml
- migration-strategy.md
- query-optimization-plan.md

**Risks**:
- DuckDB limitations for encryption
- Schema evolution complexity

---

### S1-06: CLI Design

**Work Stream**: User Interface
**Dependencies**: S1-01

**Scope**:
Design CLI command structure, user workflows, help system, and interactive prompts.

**Entry Criteria**:
- Requirements approved
- User workflows understood

**Exit Criteria**:
- CLI command structure defined
- User workflow diagrams complete
- Help system designed
- Error handling patterns defined

**Agents**:
- Primary: CLI UX Designer
- Supporting: Requirements Gatherer
- Review: Human

**Deliverables**:
- cli-design.md
- command-structure.yaml
- user-workflows/
- help-system-design.md

**Risks**:
- CLI complexity for non-technical users
- Command discoverability

---

### S1-08: Encryption Implementation

**Work Stream**: Security
**Dependencies**: S1-04

**Scope**:
Implement AES-256-GCM encryption, PBKDF2 key derivation, recovery code generation, and secure memory handling.

**Entry Criteria**:
- Security architecture approved
- Project scaffolding complete

**Exit Criteria**:
- Encryption module implemented
- Key derivation working
- Recovery code system functional
- Unit tests passing (>90% coverage)

**Agents**:
- Primary: Encryption Developer
- Supporting: Security Architect, Debugger
- Review: Code Reviewer, Staff Engineer Rust

**Deliverables**:
- src/encryption/mod.rs
- src/encryption/key_derivation.rs
- src/encryption/recovery.rs
- tests/encryption/

**Risks**:
- Crypto library integration complexity
- Secure memory handling in Rust
- Recovery code entropy requirements

---

### S1-09: DuckDB Implementation

**Work Stream**: Data Storage
**Dependencies**: S1-05, S1-08

**Scope**:
Implement DuckDB integration with encryption, connection management, schema creation, and migrations.

**Entry Criteria**:
- Data architecture approved
- Encryption module complete
- Database schema defined

**Exit Criteria**:
- DuckDB connection working
- Encrypted database creation
- Schema migrations implemented
- Basic CRUD operations functional

**Agents**:
- Primary: DuckDB Integration Developer
- Supporting: Data Architect, Encryption Developer, Debugger
- Review: Code Reviewer, Staff Engineer Rust

**Deliverables**:
- src/database/mod.rs
- src/database/connection.rs
- src/database/migrations.rs
- src/database/models.rs

**Risks**:
- DuckDB encryption integration
- Migration system complexity
- Connection pool management

---

### S1-10: Parser Implementation

**Work Stream**: Data Ingestion
**Dependencies**: S1-09

**Scope**:
Implement CSV and QFX parsers with format detection, error handling, and duplicate detection.

**Entry Criteria**:
- Database implementation complete
- Data models defined
- File format specifications available

**Exit Criteria**:
- CSV parser working for generic format
- QFX parser implemented
- Format detection functional
- Duplicate detection working
- Error handling comprehensive

**Agents**:
- Primary: Parser Developer
- Supporting: Data Architect, Debugger
- Review: Code Reviewer

**Deliverables**:
- src/parsers/mod.rs
- src/parsers/csv.rs
- src/parsers/qfx.rs
- src/parsers/detection.rs

**Risks**:
- File format variations
- Large file memory usage
- Encoding issues (UTF-8, Windows-1252)

---

### S1-11: Bank Format Support

**Work Stream**: Data Ingestion
**Dependencies**: S1-10

**Scope**:
Implement bank-specific CSV parsers for all 8 supported institutions with field mapping and validation.

**Entry Criteria**:
- Generic parser implementation complete
- Bank format specifications available
- Test data available for each bank

**Exit Criteria**:
- All 8 bank CSV formats supported
- Field mapping accurate for each bank
- Date format handling complete
- Amount parsing handles all formats
- Comprehensive test coverage

**Agents**:
- Primary: Parser Developer
- Supporting: Data Architect, Debugger
- Review: Code Reviewer

**Deliverables**:
- src/parsers/banks/chase.rs
- src/parsers/banks/wealthfront.rs
- src/parsers/banks/bofa.rs
- src/parsers/banks/ally.rs
- src/parsers/banks/amex.rs
- src/parsers/banks/discover.rs
- src/parsers/banks/citi.rs
- src/parsers/banks/capital_one.rs

**Risks**:
- Bank format changes over time
- Missing test data for some banks
- Date format variations
- Currency symbol handling

---

### S1-12: Categorization Engine

**Work Stream**: Business Logic
**Dependencies**: S1-11

**Scope**:
Implement rule-based categorization system with rule creation, testing, and application.

**Entry Criteria**:
- Transaction import working
- Data models support categorization
- Rule engine architecture defined

**Exit Criteria**:
- Rule creation interface working
- Rule testing functionality complete
- Batch categorization implemented
- Rule priority system functional
- Performance adequate for 10K+ transactions

**Agents**:
- Primary: Categorization Engine Developer
- Supporting: Data Architect, Debugger
- Review: Code Reviewer

**Deliverables**:
- src/categorization/mod.rs
- src/categorization/rules
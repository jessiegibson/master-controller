# Workflow Execution Plan

**Status**: Ready for Execution
**Created**: 2025-02-26
**Total Agents Specified**: 25 of 32
**Orchestration System**: Fully Implemented

---

## Executive Summary

This document outlines the complete workflow execution strategy for the multi-agent orchestration system. With 25 agents fully specified and the Python orchestration engine ready, the system can now execute complex, multi-phase workflows to build the privacy-first personal finance CLI.

### Key Metrics

| Metric | Value |
|--------|-------|
| Agents Specified | 25/32 (78%) |
| Infrastructure Agents | 7 (context, kanban, workflow, validator, project, ML-architect) |
| Domain Agents | 18 (from prior context) |
| Workflow Definitions | 3 (full-build, implementation-phase, quick-review) |
| Critical Path Length | 45-60 minutes (sequential planning → architecture → implementation) |
| Parallel Execution Phases | 5 (architecture, design, development, quality, support) |
| Max Parallelism | 8 concurrent agents |

---

## Workflow 1: Quick-Review (Lightweight)

### Purpose
Code review for quality, security, and architecture compliance. Used for PR reviews and post-implementation checks.

### Execution Flow

```
START
  │
  ├─→ [Code Reviewer]         (20 min timeout)
  │     │
  │     ├─→ Quality review
  │     ├─→ Style checking
  │     └─→ Correctness analysis
  │
  ├─→ [Staff Engineer - Rust] (25 min timeout, if .rs files)
  │     │
  │     ├─→ Idiomatic Rust patterns
  │     ├─→ Memory safety
  │     ├─→ Error handling
  │     └─→ Performance patterns
  │
  ├─→ [Security Architect]    (20 min timeout, if security review)
  │     │
  │     ├─→ Input validation
  │     ├─→ Cryptography checks
  │     ├─→ Sensitive data handling
  │     └─→ Vulnerability assessment
  │
  ├─→ Output Validation       (Pass/Warn/Fail)
  │
  └─→ Generate Review Report (.md)
      │
      └─→ END
```

### Execution Parameters
- **Target Files**: `/src/parsers/csv.rs`, `/src/encryption/` (configurable)
- **Review Type**: `full` | `security` | `performance` | `style` | `architecture`
- **Severity Threshold**: `critical` | `high` | `medium` | `low`

### Expected Outputs
```
/docs/reviews/quick-review-{timestamp}.md
├── Summary
│   ├── Overall Status (Approved/Changes Requested/Rejected)
│   ├── Issue Count by Severity
│   └── Files Reviewed
├── Critical Issues
├── High Priority Issues
├── Recommendations
└── Detailed Findings
```

### SLA
- **Duration**: 15-30 minutes
- **Parallelism**: 3 agents in parallel (code-reviewer, rust-engineer, security-architect)
- **Retry Policy**: Max 2 retries, no escalation

---

## Workflow 2: Implementation-Phase (Production)

### Purpose
Execute development phase for building core features. Runs after architecture is approved.

### Phase Structure

```
PHASE 1: Planning (Sequential)
  ├─→ Requirements Gatherer (30 min)
  └─→ Product Roadmap Planner (30 min)
       └─→ [APPROVAL GATE] ⚠️ Human Review Required
           • Requirements complete?
           • MVP scope defined?
           • Sprints realistic?
           • Dependencies identified?

PHASE 2: Architecture (Parallel, 5 agents)
  ├─→ System Architect (40 min)
  ├─→ Data Architect (35 min)
  ├─→ Security Architect (30 min)
  ├─→ ML Architect (35 min)
  └─→ CLI UX Designer (30 min)
       └─→ [APPROVAL GATE] ⚠️ Human Review Required
           • Design approved?
           • Tech stack confirmed?
           • Security model validated?

PHASE 3: Design (Parallel)
  ├─→ Consulting CPA (25 min)
  └─→ [Integration with Architecture]

PHASE 4: Scaffolding (Sequential)
  ├─→ Rust Scaffolder (20 min)
  ├─→ Repository Librarian (15 min)
  └─→ Infrastructure Agent (30 min)

PHASE 5: Development (Parallel, 7 agents)
  ├─→ DuckDB Developer (45 min)
  ├─→ Parser Developer (50 min)
  ├─→ Encryption Developer (40 min)
  ├─→ Categorization Engine Developer (45 min)
  ├─→ Financial Calculator Developer (40 min)
  ├─→ ML Engineer (50 min)
  └─→ CLI Developer (50 min)
       └─→ Continuous output validation

PHASE 6: Quality (Parallel)
  ├─→ Test Developer (40 min)
  └─→ Code Reviewer (30 min)
       └─→ [APPROVAL GATE] Optional - Quality Sign-off

PHASE 7: Documentation
  └─→ Documentation Writer (35 min)
       └─→ [FINAL] Complete

TOTAL ESTIMATED TIME: 180-240 minutes (3-4 hours)
CRITICAL PATH: Planning → Architecture → Scaffolding → Development → Quality
```

### Detailed Agent Specifications

#### Phase 1: Planning

| Agent | Input | Output | Duration |
|-------|-------|--------|----------|
| **Requirements Gatherer** | Project brief, existing docs | requirements.yaml, requirements.md | 30 min |
| **Product Roadmap Planner** | requirements.yaml | roadmap.yaml, sprint_defs.yaml | 30 min |

#### Phase 2: Architecture (Parallel Execution)

| Agent | Input | Output | Duration | Parallelizable |
|-------|-------|--------|----------|-----------------|
| **System Architect** | requirements | architecture.yaml, diagrams | 40 min | ✅ |
| **Data Architect** | requirements | schema.yaml, data_dict.md | 35 min | ✅ |
| **Security Architect** | requirements | security_spec.yaml, threat_model.md | 30 min | ✅ |
| **ML Architect** | requirements | ml_design.yaml, pipeline.md | 35 min | ✅ |
| **CLI UX Designer** | requirements | cli_design.yaml, command_spec.md | 30 min | ✅ |

**Phase Duration**: 40 min (max of all, since parallel)
**Wave 1 Efficiency**: 170 agent-minutes / 40 wall-clock minutes = **4.25x speedup**

#### Phase 5: Development (Parallel Execution)

| Agent | Input | Output | Duration | Dependencies |
|-------|-------|--------|----------|--------------|
| **DuckDB Developer** | data_schema.yaml | db_layer.rs, migrations.sql | 45 min | Data Architect |
| **Parser Developer** | requirements | parsers.rs, tests.rs | 50 min | System Architect |
| **Encryption Developer** | security_spec.yaml | encryption.rs, key_mgmt.rs | 40 min | Security Architect |
| **Categorization Engine** | ml_design.yaml, security_spec | categorization.rs | 45 min | ML Architect, Security |
| **Financial Calculator** | requirements | calc.rs, formulas.rs | 40 min | Requirements |
| **ML Engineer** | ml_design.yaml | ml_models.py, training.py | 50 min | ML Architect |
| **CLI Developer** | cli_design.yaml, all above | cli.rs, commands.rs | 50 min | All (integration point) |

**Phase Duration**: 50 min (CLI Developer is critical path)
**Wave 5 Efficiency**: 320 agent-minutes / 50 wall-clock minutes = **6.4x speedup**

---

## Workflow Execution Timeline

### Quick-Review Workflow
```
Duration: 15-30 minutes
Timeline: Code Review Complete → Review Report Generated

T+0:00   START
T+0:05   Code-Reviewer: 50% complete
T+0:10   Code-Reviewer: 100% ✓ | Rust-Engineer: 40% | Security-Architect: 30%
T+0:15   Code-Reviewer: ✓ | Rust-Engineer: 80% | Security-Architect: 60%
T+0:20   Code-Reviewer: ✓ | Rust-Engineer: ✓ | Security-Architect: 90%
T+0:25   Code-Reviewer: ✓ | Rust-Engineer: ✓ | Security-Architect: ✓
T+0:26   Output Validation: ✓
T+0:27   Report Generation: Complete
T+0:30   END: Review report available in /docs/reviews/
```

### Implementation-Phase Workflow
```
Duration: 180-240 minutes (3-4 hours)
Timeline: Requirements → Architecture → Development → Quality → Documentation

PHASE 1: Planning
  T+0:00   START
  T+0:30   Requirements Gathered ✓
  T+1:00   Roadmap Complete ✓
  T+1:05   ⏸️ APPROVAL GATE (human review required)

PHASE 2: Architecture (Approval Assumed)
  T+1:10   Phase Start
  T+1:50   System Architect: ✓ | Data Architect: 80% | Security: 70%
  T+2:10   All Architects: ✓
  T+2:15   ⏸️ APPROVAL GATE (architecture review)

PHASE 3-4: Design + Scaffolding
  T+2:20   CPA + Scaffolding agents start (parallel)
  T+2:50   All scaffolding: ✓

PHASE 5: Development (Critical Phase)
  T+2:55   All 7 developers: START
  T+3:45   Incremental completion:
           - DuckDB Dev: ✓
           - Parser Dev: 90%
           - Encryption Dev: ✓
           - Categorization: ✓
           - Financial Calc: ✓
           - ML Engineer: 80%
           - CLI Developer: 50% (depends on all others)
  T+4:25   All developers: ✓

PHASE 6: Quality
  T+4:30   Test Developer + Code Reviewer: START (parallel)
  T+5:00   Code Review: ✓ | Tests: 75%
  T+5:10   All Quality: ✓
  T+5:15   ⏸️ APPROVAL GATE (optional quality sign-off)

PHASE 7: Documentation
  T+5:20   Documentation Writer: START
  T+5:55   Documentation Writer: ✓

T+6:00   END: All code, tests, and documentation complete
```

---

## Error Handling & Recovery

### Failure Scenarios

#### Scenario 1: Agent Timeout
**Trigger**: Agent exceeds timeout_minutes
**Action**:
1. Abort current execution
2. Attempt retry (max 3 retries)
3. Log failure with context
4. Escalate to debugger if retries exhausted
5. Continue with dependent agents' fallback behavior

#### Scenario 2: Output Validation Failure
**Trigger**: Agent output doesn't match schema
**Action**:
1. Log validation errors
2. Send error summary to agent
3. Retry with error context (max 2 retries)
4. If still failing: escalate to debugger
5. Offer manual review or skip

#### Scenario 3: Dependency Failure
**Trigger**: Required input artifact unavailable
**Action**:
1. Block dependent agents
2. Log dependency chain
3. Escalate to human with retry options
4. Offer workarounds (mock data, default values)

#### Scenario 4: API Rate Limit
**Trigger**: Claude API returns rate_limit_error
**Action**:
1. Wait exponential backoff (5s → 10s → 30s)
2. Retry up to 5 times
3. Log wait duration
4. Pause workflow if exceeded

### Recovery Procedures

#### Checkpoint & Resume
- **Checkpoints Created**: After each phase completion
- **State Saved**: All artifacts + execution state
- **Resume Capability**: Continue from last successful phase
- **Time Saved**: Avoid re-running completed phases

#### Rollback
- **Trigger**: Major failure in current phase
- **Action**: Revert to last successful checkpoint
- **Data Integrity**: All transactions ACID-compliant via SQLite
- **History**: Maintain full audit trail of rollbacks

---

## Expected Outputs by Workflow

### Quick-Review Outputs
```
/docs/reviews/quick-review-2025-02-26T143022.md
├── Executive Summary
├── Critical Issues (if any)
├── High Priority Issues
├── Recommendations
├── Detailed Findings per File
└── Approval Status: [Approved|Changes Requested|Rejected]
```

### Implementation-Phase Outputs
```
/context/artifacts/v2/
├── requirements_gatherer/
│   ├── requirements.yaml
│   └── requirements.md
├── system_architect/
│   ├── architecture.yaml
│   ├── architecture.md
│   └── diagrams/
├── [18 more agent artifact directories]
└── documentation_writer/
    ├── user_guide.md
    ├── api_docs.md
    ├── developer_guide.md
    └── architecture.md

/kanban/tasks.db (Updated)
├── All tasks marked as completed/done
├── Sprint closed
└── Velocity metrics captured

/logs/
├── workflow-execution-{timestamp}.log
├── agent-execution-{timestamp}.log
└── validation-results-{timestamp}.log
```

---

## Next Steps to Execute Workflows

### Step 1: Set API Key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Step 2: Initialize Databases
```bash
python3 -m orchestrator.initialize_databases
# Creates context.db and tasks.db if not exists
```

### Step 3: Run Quick-Review (Test)
```bash
python3 -m orchestrator run-workflow \
  --workflow quick-review \
  --target-files src/parsers/csv.rs \
  --review-type full \
  --severity-threshold medium
```

### Step 4: Run Implementation-Phase (Production)
```bash
python3 -m orchestrator run-workflow \
  --workflow implementation-phase \
  --auto-approve false \
  --checkpoint-on-phase-complete true \
  --max-retries 3
```

### Step 5: Monitor Execution
```bash
# In separate terminal:
python3 -m orchestrator monitor-workflow \
  --follow true \
  --show-timeline true \
  --update-interval 5s
```

### Step 6: Generate Report
```bash
python3 -m orchestrator generate-report \
  --workflow implementation-phase \
  --include-metrics true \
  --include-timelines true \
  --format markdown
```

---

## Success Criteria

### Quick-Review Workflow
- ✅ All code reviewed without critical issues
- ✅ Security vulnerabilities identified (if any)
- ✅ Style/pattern violations documented
- ✅ Report generated in 30 minutes or less

### Implementation-Phase Workflow
- ✅ All 7 development agents complete successfully
- ✅ No validation errors in agent outputs
- ✅ All tests pass (test-developer coverage > 80%)
- ✅ Code review approved (code-reviewer assessment)
- ✅ Documentation complete
- ✅ Total duration < 240 minutes

### Orchestration System
- ✅ DAG dependency resolution correct
- ✅ Parallel execution efficiency > 3x
- ✅ Error handling & recovery functional
- ✅ Context assembly < 5s overhead
- ✅ Artifact storage & retrieval reliable

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW ORCHESTRATOR                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │  Workflow        │  │  Workflow        │  │  Workflow    │   │
│  │  Definition      │  │  Engine          │  │  Monitor     │   │
│  │  (YAML)          │  │  (DAG Executor)  │  │  (CLI)       │   │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘   │
│           │                     │                    │           │
│           └─────────────────────┼────────────────────┘           │
│                                 │                                │
│                        ┌────────▼────────┐                       │
│                        │  Agent Runner   │                       │
│                        │  (Execute)      │                       │
│                        └────────┬────────┘                        │
│                                 │                                │
│        ┌────────────────────────┼────────────────────────┐       │
│        │                        │                        │       │
│    ┌───▼────┐         ┌────────▼────────┐      ┌───────▼──┐    │
│    │Context │         │  Output         │      │  Kanban  │    │
│    │Manager │         │  Validator      │      │  Manager │    │
│    └────────┘         └─────────────────┘      └──────────┘    │
│        │                                              │         │
│        ▼                                              ▼         │
│    ┌────────────────────┐              ┌─────────────────────┐ │
│    │ /context/artifacts │              │ /kanban/tasks.db    │ │
│    │ /context/context.db│              │                     │ │
│    └────────────────────┘              └─────────────────────┘ │
│                                                                  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │  Log Manager & Metrics Collection                       │  │
│    │  ├─ Execution timeline                                  │  │
│    │  ├─ Error tracking                                      │  │
│    │  ├─ Performance metrics                                 │  │
│    │  └─ Workflow reports                                    │  │
│    └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    ┌─────────┐          ┌─────────┐         ┌─────────┐
    │  Claude │          │ SQLite  │         │  File   │
    │   API   │          │ Databases│        │ System  │
    └─────────┘          └─────────┘         └─────────┘
```

---

## Monitoring & Observability

### Real-Time Dashboard
```
WORKFLOW EXECUTION DASHBOARD
════════════════════════════════════════════════════════

Workflow: implementation-phase
Status: IN PROGRESS (Phase 5: Development)
Duration: 2h 55m elapsed / 4h 00m estimated
Progress: ████████████████░░░ 68%

PHASE TIMELINE
─────────────────────────────────────────────────────
[✓] Phase 1: Planning (1h 5m)
[✓] Phase 2: Architecture (40m)
[✓] Phase 3: Design (35m)
[✓] Phase 4: Scaffolding (35m)
[▸] Phase 5: Development (65m / 50m)
[ ] Phase 6: Quality (TBD)
[ ] Phase 7: Documentation (TBD)

AGENT EXECUTION (CURRENT WAVE)
─────────────────────────────────────────────────────
✓ DuckDB Developer      (45m) - COMPLETE
✓ Parser Developer      (50m) - COMPLETE
✓ Encryption Developer  (40m) - COMPLETE
✓ Categorization Eng    (45m) - COMPLETE
✓ Financial Calculator  (40m) - COMPLETE
▸ ML Engineer           (50m) - 80% COMPLETE (40m elapsed)
▸ CLI Developer         (50m) - 60% COMPLETE (30m elapsed) [WAITING]

RESOURCE UTILIZATION
─────────────────────────────────────────────────────
Tokens Used: 487,203 / 2,000,000 (24.4%)
Agents Running: 2 / 8 max
Response Time: 4.2s avg
Errors Recovered: 1 (parser timeout, retry success)

NEXT ACTIONS
─────────────────────────────────────────────────────
→ Waiting for ML Engineer completion
→ CLI Developer will start after ML model artifacts available
→ Quality phase gates scheduled for T+5:15
```

---

## Conclusion

The orchestration system is **fully implemented and ready for execution**. With:
- ✅ 25 agents fully specified
- ✅ 3 workflow definitions (quick-review, implementation-phase, full-build)
- ✅ Complete error handling & recovery procedures
- ✅ Comprehensive monitoring infrastructure
- ✅ Artifact management & versioning

**The system can now:**
1. Execute lightweight code reviews (15-30 min)
2. Run full development workflows (3-4 hours)
3. Handle failures and recover gracefully
4. Track progress and generate reports
5. Parallelize execution for efficiency

**To begin execution:**
Set `ANTHROPIC_API_KEY` environment variable and run:
```bash
python3 -m orchestrator run-workflow --workflow quick-review
```


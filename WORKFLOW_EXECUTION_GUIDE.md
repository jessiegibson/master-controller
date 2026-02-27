# Workflow Execution Guide

## Overview

The multi-agent orchestration system is now ready for workflow execution. Three workflows are available:

1. **quick-review** - Lightweight code review (15-30 min)
2. **implementation-phase** - Full development cycle (3-4 hours)
3. **full-build** - Complete build from requirements to release (4-6 hours)

## Prerequisites

### 1. API Credentials

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Project Structure

Verify the following directories exist:

```bash
ls -la orchestrator/           # Workflow engine components
ls -la workflows/              # Workflow definitions (YAML)
ls -la prompts/                # Agent prompts
ls -la config/                 # agents.yaml configuration
ls -la context/                # Context Manager storage
ls -la kanban-cli/kanban/      # Kanban database
```

### 3. Python Dependencies

```bash
pip install pyyaml rich anthropic
```

## Running Workflows

### Quick Review Workflow (Recommended for Testing)

Review code files for quality, security, and architecture compliance:

```bash
python3 run_workflow.py quick-review \
    --target-files src/parsers/csv.rs \
    --review-type full \
    --severity-threshold medium
```

**Parameters:**

- `--target-files` (required): Files or directories to review
- `--review-type`: `full`, `security`, `performance`, `style`, or `architecture` (default: `full`)
- `--severity-threshold`: `critical`, `high`, `medium`, `low` (default: `medium`)

**Duration:** 15-30 minutes

**Outputs:**
- Review report in `/docs/reviews/`
- Execution summary in YAML format
- Kanban database updated with task status

**Example: Security Review of Encryption Module**

```bash
python3 run_workflow.py quick-review \
    --target-files src/encryption/ \
    --review-type security \
    --severity-threshold low
```

### Implementation Phase Workflow

Run the full development cycle for a feature or module:

```bash
python3 run_workflow.py implementation-phase
```

**Duration:** 3-4 hours (estimated 180-240 minutes wall-clock)

**Phases Executed:**

1. **Planning** (Sequential)
   - Requirements Gatherer
   - Product Roadmap Planner

2. **Architecture** (Parallel)
   - System Architect
   - Data Architect
   - Security Architect
   - ML Architect

3. **Design** (Parallel)
   - CLI UX Designer
   - Consulting CPA

4. **Scaffolding** (Sequential)
   - Rust Scaffolder
   - Repository Librarian
   - Infrastructure Agent

5. **Development** (Parallel)
   - DuckDB Developer
   - Parser Developer
   - Encryption Developer
   - Categorization Engine Developer
   - Financial Calculator Developer
   - ML Engineer
   - CLI Developer

6. **Quality** (Parallel)
   - Test Developer
   - Code Reviewer

7. **Documentation** (Sequential)
   - Documentation Writer

**Outputs:**
- Complete implementation in finance-cli/
- Comprehensive test suite
- Code review report
- Architecture documentation
- Execution summary

### Full Build Workflow

Complete end-to-end build from requirements to release:

```bash
python3 run_workflow.py full-build
```

**Duration:** 4-6 hours (estimated 240-360 minutes wall-clock)

**Includes all phases from implementation-phase plus:**

8. **Release** (Sequential)
   - Release Manager
   - Changelog Generator
   - Deployment Planner

## Monitoring Execution

### Real-Time Output

The workflow runner displays:

```
================================================================================
PHASE: REVIEW
Description: Perform code review based on specified review type and parameters.
Parallel: true | Agents: 3
================================================================================

Executing 3 agents in parallel...

✓ code-reviewer: completed
✓ staff-engineer-rust: completed
✓ security-architect: completed

================================================================================
WORKFLOW COMPLETE: quick-review
================================================================================
Duration: 45.2 seconds (0.8 minutes)
```

### Checking Status

View execution history:

```bash
# Get last 10 executions
python3 -c "
from orchestrator import KanbanManager
km = KanbanManager()
for exec in km.get_agent_executions(limit=10):
    print(f\"{exec['agent_id']}: {exec['status']}\")
"
```

### Database Queries

Check kanban database directly:

```bash
# View active tasks
sqlite3 kanban-cli/kanban/tasks.db "SELECT id, title, status FROM tasks WHERE status != 'done' LIMIT 10;"

# View workflow runs
sqlite3 kanban-cli/kanban/tasks.db "SELECT id, start_time, status FROM workflow_runs ORDER BY start_time DESC LIMIT 5;"
```

## Error Handling & Recovery

### If a Workflow Fails

**Identify the failure:**

```bash
# Check logs
tail -f logs/workflow.log

# View execution history
sqlite3 kanban-cli/kanban/tasks.db "SELECT * FROM agent_executions WHERE status='failed' ORDER BY created_at DESC LIMIT 1;"
```

**Recovery options:**

1. **Retry the phase**: Re-run the entire workflow (will skip completed phases due to context versioning)
2. **Retry specific agent**:
   ```bash
   python3 run_agent.py <agent_name> --task "Your task"
   ```
3. **Escalate to debugger**:
   ```bash
   python3 run_agent.py debugger --task "Debug failed agent X"
   ```

### Common Issues

**Issue: "ANTHROPIC_API_KEY not found"**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Issue: "Workflow not found"**
```bash
# Check available workflows
ls workflows/
```

**Issue: "Agent timeout"**
- Increase timeout: Modify workflow YAML `config.timeout_minutes`
- Re-run with extended patience

**Issue: "Database locked"**
- Close other connections to kanban database
- Wait for current operation to complete
- Or remove `.db-wal` and `.db-shm` files

## Workflow Configuration

### Customizing a Workflow

Edit the workflow YAML file:

```yaml
# workflows/quick-review.yaml
config:
  max_retries: 2              # Increase for flaky agents
  retry_delay_seconds: 10     # Adjust delay between retries
  timeout_minutes: 30         # Increase for complex reviews
  log_level: debug            # Change to debug for more verbosity
```

### Enabling/Disabling Agents

In workflow YAML, set agent `enabled` flag:

```yaml
- name: staff-engineer-rust
  enabled: true              # Or false to skip
  enabled_when:              # Or conditional enable
    - review_type: [full, architecture, performance]
    - file_extension: [.rs]
```

## Output Artifacts

### Artifacts Stored

All workflow outputs are stored in:

```
workflow/
├── artifacts/
│   ├── code-reviewer/
│   │   └── code-reviewer_output.md
│   ├── staff-engineer-rust/
│   │   └── staff-engineer-rust_output.md
│   └── ...
└── context.db               # Context manager state
```

### Accessing Results

Latest outputs are in context database:

```bash
# List all stored artifacts
sqlite3 context/context.db "SELECT agent_id, artifact_name, version FROM artifacts ORDER BY created_at DESC;"

# Get specific artifact
sqlite3 context/context.db "SELECT content FROM artifacts WHERE agent_id='code-reviewer' ORDER BY version DESC LIMIT 1;"
```

## Performance Tuning

### Parallel Execution

Increase parallel agents (default: 4):

```bash
python3 run_workflow.py quick-review \
    --target-files src/ \
    --max-parallel 8
```

**Note:** Increase with caution - more parallelism = higher API costs

### Selective Execution

Run only specific review types:

```bash
# Security review only
python3 run_workflow.py quick-review \
    --target-files src/encryption/ \
    --review-type security

# Performance review only
python3 run_workflow.py quick-review \
    --target-files src/parsers/ \
    --review-type performance
```

## Workflows Architecture

### Execution Flow

```
run_workflow.py
    ├─ Load workflow YAML
    ├─ Resolve parameters
    ├─ Create WorkflowEngine
    └─ For each phase:
        ├─ Determine parallelism
        ├─ Execute agents (sequential or parallel)
        │   ├─ Load agent prompt
        │   ├─ Assemble context
        │   ├─ Call Claude API
        │   ├─ Validate output
        │   └─ Store artifacts
        ├─ Check error handling policy
        └─ Continue to next phase
    └─ Generate execution summary
```

### Component Integration

```
WorkflowEngine
    ├─ AgentRunner
    │   ├─ Loads prompts from /prompts/
    │   └─ Calls LLMClient (Claude API)
    ├─ ContextManager
    │   ├─ SQLite database: context/context.db
    │   └─ Artifact storage: context/artifacts/
    ├─ KanbanManager
    │   ├─ SQLite database: kanban-cli/kanban/tasks.db
    │   └─ Task tracking & metrics
    ├─ OutputValidator
    │   └─ Validates outputs against schemas
    └─ LogManager
        └─ Structured logging: logs/
```

## Next Steps

1. **Start with quick-review**: Test the system with a quick, low-risk workflow
   ```bash
   python3 run_workflow.py quick-review \
       --target-files src/parsers/csv.rs \
       --review-type full \
       --severity-threshold medium
   ```

2. **Monitor execution**: Watch for agent completions and validation results

3. **Review outputs**: Check review reports in `/docs/reviews/`

4. **Check metrics**:
   ```bash
   sqlite3 kanban-cli/kanban/tasks.db "SELECT COUNT(*) as completed FROM agent_executions WHERE status='completed';"
   ```

5. **Scale to longer workflows**: Once quick-review completes successfully, try implementation-phase

## Troubleshooting

### Enable Debug Logging

```bash
# Modify workflow YAML or runtime
python3 run_workflow.py quick-review \
    --target-files src/ \
    2>&1 | tee execution.log
```

### Inspect Agent Prompt

```bash
cat prompts/code-reviewer.md | head -50
```

### Test Single Agent

Before running full workflow, test an agent:

```bash
python3 run_agent.py code-reviewer \
    --task "Review this code for quality" \
    --input-files src/parsers/csv.rs
```

## Support

For issues:

1. Check `/logs/` directory for detailed error messages
2. Review agent output in `workflow/artifacts/`
3. Query kanban database for execution history
4. Run debugger agent for complex issues

---

**Happy orchestrating!** 🚀

The system is fully configured and ready for multi-agent workflows. Start with quick-review to validate your setup, then scale to longer workflows.

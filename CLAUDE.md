# CLAUDE.md - Multi-Agent Orchestrator Project Context

## Project Overview

This is a **multi-agent software development orchestration system** designed to coordinate 31 specialized AI agents to build a privacy-first personal finance CLI application. The system is designed to be run by Claude Code or similar AI coding assistants.

## Current State

### Completed Work

**All 31 agent prompts are complete** and located in `/agents/prompts/`. Each agent has a detailed prompt defining:
- Identity and role
- Core objectives
- Input/output formats
- Domain-specific instructions
- Interaction patterns with other agents

### Directory Structure

```
agent-orchestrator/
├── CLAUDE.md                    # This file - project context
├── agents/
│   ├── config/
│   │   └── agents.yaml          # Agent registry (all 31 active)
│   └── prompts/                 # All 31 agent prompts
│       ├── requirements-gatherer.md
│       ├── product-roadmap-planner.md
│       ├── system-architect.md
│       ├── data-architect.md
│       ├── security-architect.md
│       ├── consulting-cpa.md
│       ├── workflow-orchestrator.md
│       ├── staff-engineer-python.md
│       ├── staff-engineer-rust.md
│       ├── ml-architect.md
│       ├── cli-ux-designer.md
│       ├── debugger.md
│       ├── repository-librarian.md
│       ├── project-manager.md
│       ├── code-reviewer.md
│       ├── rust-scaffolder.md
│       ├── kanban-manager.md
│       ├── output-validator.md
│       ├── duckdb-developer.md
│       ├── parser-developer.md
│       ├── context-manager.md
│       ├── categorization-engine-developer.md
│       ├── financial-calculator-developer.md
│       ├── encryption-developer.md
│       ├── cli-developer.md
│       ├── test-developer.md
│       ├── ml-engineer.md
│       ├── documentation-writer.md
│       ├── prompt-skill-engineer.md
│       └── infrastructure-agent.md
├── context/                     # Context Manager storage (to be created)
├── kanban/                      # Kanban task database (to be created)
└── schemas/                     # Output validation schemas (to be created)
```

## What Needs to Be Built Next: Orchestration System

The orchestration system coordinates agent execution. Build these components:

### 1. Workflow Engine (`/orchestrator/`)

```
orchestrator/
├── mod.rs                 # Module exports
├── engine.rs              # Main orchestration engine
├── workflow.rs            # Workflow definitions
├── task.rs                # Task management
├── agent_runner.rs        # Execute individual agents
├── context_bridge.rs      # Interface with Context Manager
└── scheduler.rs           # Task scheduling and dependencies
```

**Key responsibilities:**
- Load workflow definitions (YAML)
- Schedule tasks based on dependencies
- Execute agents by loading prompts and providing context
- Collect and route outputs between agents
- Handle failures and retries
- Track progress and state

### 2. Workflow Definitions (`/workflows/`)

```yaml
# workflows/full-build.yaml
name: full-build
description: Complete project build from requirements to release

phases:
  - name: planning
    agents:
      - requirements-gatherer
      - product-roadmap-planner
    parallel: false
    
  - name: architecture
    agents:
      - system-architect
      - data-architect
      - security-architect
      - ml-architect
    parallel: true
    depends_on: [planning]
    
  - name: design
    agents:
      - cli-ux-designer
      - consulting-cpa
    parallel: true
    depends_on: [architecture]
    
  - name: scaffolding
    agents:
      - rust-scaffolder
      - repository-librarian
      - infrastructure-agent
    parallel: false
    depends_on: [architecture]
    
  - name: development
    agents:
      - duckdb-developer
      - parser-developer
      - encryption-developer
      - categorization-engine-developer
      - financial-calculator-developer
      - ml-engineer
      - cli-developer
    parallel: true
    depends_on: [scaffolding, design]
    
  - name: quality
    agents:
      - test-developer
      - code-reviewer
    parallel: true
    depends_on: [development]
    
  - name: documentation
    agents:
      - documentation-writer
    depends_on: [development, quality]
```

### 3. Agent Runner

The agent runner:
1. Loads agent prompt from `/agents/prompts/{agent_name}.md`
2. Assembles context from Context Manager (dependent artifacts)
3. Formats the task input
4. Executes the agent (calls Claude API or runs in Claude Code)
5. Validates output using Output Validator schemas
6. Stores artifacts via Context Manager
7. Updates Kanban task status

### 4. Context Management Integration

The Context Manager agent prompt defines the storage schema:
- SQLite database for metadata (`context/context.db`)
- File storage for artifacts (`context/artifacts/`)
- Version tracking for all artifacts
- Access control per agent type

**Key tables:**
- `project_context` - shared state
- `artifacts` - artifact metadata
- `execution_history` - agent run audit trail
- `agent_context_requirements` - what each agent needs

### 5. Kanban Integration

The Kanban Manager agent prompt defines task tracking:
- SQLite database (`kanban/tasks.db`)
- Task states: backlog → ready → in_progress → review → done
- Sprint management
- Dependency tracking
- Blocking issue management

## Agent Categories and Execution Order

### Phase 1: Planning (Sequential)
1. **Requirements Gatherer** - Elicits and documents requirements
2. **Product Roadmap Planner** - Creates phased delivery plan

### Phase 2: Architecture (Parallel)
3. **System Architect** - Overall system design
4. **Data Architect** - Data models and storage
5. **Security Architect** - Security model and encryption
6. **ML Architect** - ML pipeline design

### Phase 3: Design (Parallel)
7. **CLI UX Designer** - Command structure and UX
8. **Consulting CPA** - Tax categories and Schedule C mapping

### Phase 4: Scaffolding (Sequential)
9. **Rust Scaffolder** - Project structure
10. **Repository Librarian** - Git setup, structure
11. **Infrastructure Agent** - CI/CD, build config

### Phase 5: Development (Parallel)
12. **DuckDB Developer** - Database layer
13. **Parser Developer** - File parsing
14. **Encryption Developer** - Crypto implementation
15. **Categorization Engine Developer** - Rule engine
16. **Financial Calculator Developer** - Report calculations
17. **ML Engineer** - ML models
18. **CLI Developer** - CLI implementation

### Phase 6: Quality (Parallel)
19. **Test Developer** - Tests and fixtures
20. **Code Reviewer** - Code review

### Phase 7: Documentation
21. **Documentation Writer** - All documentation

### Support Agents (Run as needed)
- **Workflow Orchestrator** - Coordinates execution
- **Project Manager** - Tracks progress
- **Kanban Manager** - Task management
- **Context Manager** - Artifact storage
- **Output Validator** - Validates outputs
- **Debugger** - Fixes issues
- **Prompt/Skill Engineer** - Optimizes prompts
- **Staff Engineer Python** - Python guidance
- **Staff Engineer Rust** - Rust guidance

## Key Design Decisions

### Agent Communication
- Agents communicate via **artifacts** stored by Context Manager
- No direct agent-to-agent calls
- Orchestrator routes outputs to dependent agents

### Execution Model
- Each agent runs in isolation with assembled context
- Agents produce structured outputs (Markdown, YAML, code)
- Output Validator ensures format compliance
- Failed validations trigger retry or Debugger

### State Management
- All state persisted to disk (SQLite + files)
- Workflow can be resumed after interruption
- Version control on all artifacts

### Error Handling
- Retry failed agents up to 3 times
- Route persistent failures to Debugger agent
- Workflow can continue with non-blocking failures
- All errors logged to execution history

## Target Application: Finance CLI

The agents are building a **privacy-first personal finance CLI** with:

- **Transaction import**: CSV, QFX/OFX, PDF parsing
- **Categorization**: Rules + ML-based
- **Reports**: P&L, Cash Flow, Schedule C
- **Encryption**: AES-256-GCM, Argon2id key derivation
- **Local-first**: No cloud, no internet required
- **Tax-ready**: IRS Schedule C line item mapping

Tech stack: **Rust**, **DuckDB**, **clap**, **AES-GCM**, **Argon2**

## How to Use This System

### Option 1: Manual Agent Execution

Run agents one at a time:
1. Read agent prompt from `/agents/prompts/{agent}.md`
2. Provide relevant context (previous agent outputs)
3. Execute agent task
4. Save output to `/context/artifacts/`

### Option 2: Build Orchestrator (Recommended)

Implement the orchestration system to automate:
1. Build workflow engine in Rust or Python
2. Create workflow YAML definitions
3. Implement agent runner
4. Connect to Context Manager storage
5. Run workflows end-to-end

### Option 3: Claude Code Interactive

Use Claude Code to:
1. Read an agent prompt
2. Act as that agent
3. Produce the specified outputs
4. Save to appropriate locations

## Next Steps

1. **Build orchestrator engine** - Core workflow execution
2. **Create workflow definitions** - YAML workflow files
3. **Implement context storage** - SQLite + file system
4. **Build agent runner** - Prompt loading and execution
5. **Run first workflow** - Execute planning phase
6. **Iterate** - Run subsequent phases

## Important Files to Reference

| File | Purpose |
|------|---------|
| `agents/config/agents.yaml` | Agent registry with all 31 agents |
| `agents/prompts/workflow-orchestrator.md` | Orchestration patterns |
| `agents/prompts/context-manager.md` | Storage architecture |
| `agents/prompts/kanban-manager.md` | Task tracking schema |
| `agents/prompts/output-validator.md` | Validation schemas |
| `agents/prompts/project-manager.md` | Progress tracking |

## Commands for Claude Code

```bash
# View all agent prompts
ls agents/prompts/

# View specific agent prompt
cat agents/prompts/workflow-orchestrator.md

# View agent registry
cat agents/config/agents.yaml

# Create orchestrator directory
mkdir -p orchestrator workflows context kanban schemas
```

## Questions to Consider

When building the orchestrator, decide:

1. **Language**: Rust (consistent with target app) or Python (faster to build)?
2. **Execution**: Sequential or parallel agent execution?
3. **API**: Direct Claude API calls or Claude Code subprocess?
4. **Storage**: Exact SQLite schema for context and kanban?
5. **Validation**: JSON Schema or custom validators?

The agent prompts provide guidance, but implementation details are yours to decide.

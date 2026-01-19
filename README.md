# master-controller

Multi-agent workflow coordinator for software development.

## Directory Structure

```
agent-orchestrator/
├── agents/
│   ├── config/
│   │   └── agents.yaml          # Agent registry and metadata
│   └── prompts/                 # Individual agent prompts
├── orchestrator/                # Python orchestration code
│   ├── workflow_engine.py       # DAG execution, parallel agents
│   ├── context_manager.py       # Selective context passing
│   ├── agent_runner.py          # LLM API interaction
│   ├── output_validator.py      # Schema validation
│   ├── llm_client.py            # Claude API client
│   ├── kanban_manager.py        # Task tracking
│   ├── log_manager.py           # Execution logging
│   └── state_store.py           # Workflow state persistence
├── kanban/                      # SQLite database for tasks
├── logs/                        # Execution logs
├── workflow/                    # Runtime state
├── config/                      # Orchestrator configuration
├── context/                     # Context snapshots
├── infrastructure/              # Setup scripts
└── tests/                       # Orchestrator tests
```

## Setup

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run orchestrator
uv python -m orchestrator
```

## Configuration

See `config/workflow-config.yaml` for orchestrator settings.
See `agents/config/agents.yaml` for agent definitions.

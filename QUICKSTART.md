# Quickstart Guide

Get started with the Agent Orchestrator MVP in 3 minutes.

## Prerequisites

- Python 3.8+
- Anthropic API key ([Get one here](https://console.anthropic.com/))

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API key

Create a `.env` file (or export environment variable):

```bash
cp .env.example .env
# Edit .env and add your API key
```

Or export directly:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. Run your first agent

```bash
python test_agent.py requirements_gatherer
```

This will:
- Load the Requirements Gatherer agent prompt from `prompts/requirements_gatherer.md`
- Execute it via Claude API with a sample finance CLI project description
- Save output to `workflow/artifacts/requirements_gatherer/`
- Display formatted results

## What Just Happened?

The orchestrator:

1. **Loaded the agent prompt** - Read the full agent identity and instructions from the prompt file
2. **Assembled context** - Prepared project context (project name, current phase)
3. **Called Claude API** - Sent the prompt + context + user task to Claude
4. **Saved output** - Stored the agent's response as an artifact
5. **Recorded execution** - Logged the execution in `workflow/executions.json`

## Output Location

```
workflow/
├── artifacts/
│   └── requirements_gatherer/
│       └── requirements_gatherer_output.md  # Agent output
├── executions.json                           # Execution history
└── current_state.json                        # Workflow state
```

## Try Other Agents

```bash
# Run system architect (requires requirements_gatherer output as context)
python test_agent.py system_architect

# Run any agent by ID
python test_agent.py <agent_id>
```

See `config/agents.yaml` for the full list of 31 available agents.

## MVP Scope

This MVP demonstrates:
- ✅ Loading agent prompts from markdown files
- ✅ Executing single agents via Claude API
- ✅ Simple context assembly
- ✅ Artifact storage and retrieval
- ✅ Execution history tracking

**Not yet implemented (future):**
- ❌ Full DAG-based workflow orchestration
- ❌ Parallel agent execution
- ❌ Context Manager with SQLite
- ❌ Output validation schemas
- ❌ Approval gates
- ❌ Error recovery with Debugger agent
- ❌ Kanban task management

## Next Steps

1. Review agent output in `workflow/artifacts/`
2. Read the agent prompts in `prompts/` to understand each agent's role
3. Check `CLAUDE.md` for the full orchestration architecture
4. Extend the MVP to support multi-agent workflows

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
- Make sure you've set the environment variable or created a `.env` file

**"Agent not found in configuration"**
- Check `config/agents.yaml` for valid agent IDs
- Agent IDs use underscores (e.g., `requirements_gatherer`, not `requirements-gatherer`)

**"Prompt file not found"**
- Verify the prompt file exists in `prompts/`
- Check the `prompt_file` path in `config/agents.yaml`

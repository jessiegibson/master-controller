# Installing the Agents MCP Server with Zed

This guide explains how to configure the Agents MCP server for use with [Zed](https://zed.dev/), a high-performance code editor with built-in AI assistant capabilities.

## Prerequisites

- Zed editor installed (download from [zed.dev](https://zed.dev/))
- Python 3.10 or higher
- The `agents` repository cloned locally

## Installation Steps

### 1. Install Python Dependencies

First, ensure the MCP dependencies are installed:

```bash
cd /path/to/agents
pip install -r agents-mcp/requirements.txt
```

Or using the project's pyproject.toml:

```bash
pip install mcp>=1.0.0 pyyaml>=6.0
```

### 2. Configure Zed Settings

Open Zed's settings file. You can do this by:
- Press `Cmd+,` (macOS) or `Ctrl+,` (Linux) to open settings
- Or open the command palette (`Cmd+Shift+P`) and search for "Open Settings"

Add the MCP server configuration to your `settings.json`:

```json
{
  "context_servers": {
    "agents-mcp": {
      "command": {
        "path": "python3",
        "args": [
          "/absolute/path/to/agents/agents-mcp/server.py"
        ],
        "env": {}
      },
      "settings": {}
    }
  }
}
```

**Important:** Replace `/absolute/path/to/agents` with the actual absolute path to your `agents` repository.

### 3. Alternative: Using a Virtual Environment

If you're using a Python virtual environment, update the configuration to use the venv's Python:

```json
{
  "context_servers": {
    "agents-mcp": {
      "command": {
        "path": "/absolute/path/to/agents/.venv/bin/python",
        "args": [
          "/absolute/path/to/agents/agents-mcp/server.py"
        ],
        "env": {}
      },
      "settings": {}
    }
  }
}
```

### 4. Set Working Directory (Recommended)

The MCP server expects to run from the project root directory. You can set this via the `cwd` option:

```json
{
  "context_servers": {
    "agents-mcp": {
      "command": {
        "path": "python3",
        "args": [
          "agents-mcp/server.py"
        ],
        "cwd": "/absolute/path/to/agents",
        "env": {}
      },
      "settings": {}
    }
  }
}
```

## Verification

After configuring:

1. Restart Zed or reload the window
2. Open the AI assistant panel
3. The MCP tools should now be available

You can verify the connection by asking the assistant to use one of the available tools:

- `list_agents` - List all available agents
- `list_workflows` - List available workflows
- `suggest_agent` - Get agent suggestions for a task

## Available Tools

Once connected, the following MCP tools become available:

| Tool | Description |
|------|-------------|
| `list_agents` | List all available agents with descriptions and roles |
| `run_agent` | Execute a specific agent with a task |
| `run_workflow` | Run a predefined multi-agent workflow |
| `get_agent_artifact` | Retrieve the most recent output from an agent |
| `get_agent_dependencies` | Show agent dependency relationships |
| `suggest_agent` | Get agent recommendations for a task |
| `list_workflows` | List all available workflow definitions |

## Troubleshooting

### Server Not Starting

1. Check that Python 3.10+ is installed: `python3 --version`
2. Verify the MCP package is installed: `pip show mcp`
3. Check Zed's logs for error messages (Help > View Logs)

### Tools Not Appearing

1. Ensure the path in settings is absolute, not relative
2. Verify the server.py file exists at the specified path
3. Try restarting Zed completely

### Permission Errors

If you see permission errors, ensure the Python interpreter has read access to:
- `agents-mcp/server.py`
- `config/agents.yaml`
- `workflows/` directory
- `context/artifacts/` directory

## Example Configuration

Complete example for a typical setup:

```json
{
  "context_servers": {
    "agents-mcp": {
      "command": {
        "path": "/Users/yourname/workspace/agents/.venv/bin/python",
        "args": [
          "agents-mcp/server.py"
        ],
        "cwd": "/Users/yourname/workspace/agents",
        "env": {
          "PYTHONUNBUFFERED": "1"
        }
      },
      "settings": {}
    }
  }
}
```

## Additional Resources

- [Zed MCP Documentation](https://zed.dev/docs/assistant/context-servers)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Project README](../README.md)

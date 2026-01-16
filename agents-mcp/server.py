#!/usr/bin/env python3
"""
MCP Server for Finance CLI Agent System
Exposes 31 specialized agents as tools for Claude Code
"""

import os
import subprocess
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, List
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("finance-agents")

# Configuration
AGENTS_DIR = Path("agents")
PROMPTS_DIR = AGENTS_DIR / "prompts"
CONFIG_FILE = AGENTS_DIR / "config" / "agents.yaml"
ARTIFACTS_DIR = Path("context") / "artifacts"
WORKFLOWS_DIR = Path("workflows")


def load_agent_registry() -> Dict:
    """Load agent configuration from YAML"""
    if not CONFIG_FILE.exists():
        return {"agents": {}}
    
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
        
        # Handle both formats:
        # Format 1 (simple list): agents: [...]
        # Format 2 (rich dict): agents: {agent_key: {...}}
        agents = config.get('agents', {})
        
        if isinstance(agents, list):
            # Already in simple format
            return config
        elif isinstance(agents, dict):
            # Convert rich format to flat list for compatibility
            agent_list = []
            for agent_key, agent_data in agents.items():
                # Only include active agents
                if agent_data.get('status') == 'active':
                    agent_list.append({
                        'name': agent_key.replace('_', '-'),  # Convert underscores to hyphens
                        'display_name': agent_data.get('name', agent_key),
                        'description': agent_data.get('description', ''),
                        'role': agent_data.get('phase', ''),
                        'prompt_file': agent_data.get('prompt_file', f'agents/prompts/{agent_key}.md'),
                        'inputs': agent_data.get('inputs', []),
                        'outputs': agent_data.get('outputs', []),
                        'dependencies': agent_data.get('dependencies', {}),
                        'approval_required': agent_data.get('approval_gate', {}).get('required', False)
                    })
            return {'agents': agent_list}
        else:
            return {"agents": []}


def get_agent_names() -> List[str]:
    """Get list of all available agent names"""
    registry = load_agent_registry()
    agents = registry.get('agents', [])
    
    if isinstance(agents, list):
        return [agent['name'] for agent in agents]
    elif isinstance(agents, dict):
        # Return only active agents
        return [
            key.replace('_', '-') 
            for key, data in agents.items() 
            if data.get('status') == 'active'
        ]
    return []


def get_agent_info(agent_name: str) -> Optional[Dict]:
    """Get detailed info about a specific agent"""
    registry = load_agent_registry()
    agents = registry.get('agents', [])
    
    if isinstance(agents, list):
        for agent in agents:
            if agent['name'] == agent_name:
                return agent
    elif isinstance(agents, dict):
        # Handle both underscore and hyphen versions
        agent_key = agent_name.replace('-', '_')
        if agent_key in agents:
            data = agents[agent_key]
            # Only return if active
            if data.get('status') == 'active':
                return {
                    'name': agent_name,
                    'display_name': data.get('name', agent_name),
                    'description': data.get('description', ''),
                    'role': data.get('phase', ''),
                    'prompt_file': data.get('prompt_file', f'agents/prompts/{agent_key}.md').lstrip('/'),
                    'inputs': data.get('inputs', []),
                    'outputs': data.get('outputs', []),
                    'dependencies': data.get('dependencies', {}),
                    'approval_required': data.get('approval_gate', {}).get('required', False)
                }
    return None


def read_artifact(agent_name: str) -> Optional[str]:
    """Read the most recent artifact from an agent"""
    artifact_files = list(ARTIFACTS_DIR.glob(f"{agent_name}_*.md"))
    if not artifact_files:
        return None
    
    # Get most recent artifact
    latest = max(artifact_files, key=lambda p: p.stat().st_mtime)
    return latest.read_text()


@mcp.tool()
def list_agents() -> str:
    """
    List all available agents in the system.
    Returns agent names with their descriptions, roles, and status.
    """
    registry = load_agent_registry()
    agents = registry.get('agents', [])
    
    if not agents:
        return "No agents found in registry"
    
    # Convert dict format to list if needed
    agent_list = []
    if isinstance(agents, dict):
        for key, data in agents.items():
            if data.get('status') == 'active':
                agent_list.append({
                    'name': key.replace('_', '-'),
                    'display_name': data.get('name', key),
                    'description': data.get('description', ''),
                    'phase': data.get('phase', ''),
                    'approval_required': data.get('approval_gate', {}).get('required', False)
                })
    else:
        agent_list = agents
    
    # Group by phase if available
    phases = {}
    for agent in agent_list:
        phase = agent.get('phase', agent.get('role', 'other'))
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(agent)
    
    output = ["Available Agents:", ""]
    
    for phase, phase_agents in sorted(phases.items()):
        output.append(f"## {phase.replace('_', ' ').title()}")
        output.append("")
        for agent in phase_agents:
            name = agent.get('name', agent.get('display_name', 'unknown'))
            display = agent.get('display_name', name)
            desc = agent.get('description', 'N/A')
            approval = " [Requires Approval]" if agent.get('approval_required') else ""
            
            output.append(f"• **{name}** - {display}{approval}")
            output.append(f"  {desc}")
            output.append("")
    
    return "\n".join(output)


@mcp.tool()
def run_agent(
    agent_name: str,
    task_description: str,
    context: Optional[str] = None,
    input_files: Optional[str] = None
) -> str:
    """
    Run a specific agent with a task.
    
    Args:
        agent_name: Name of the agent to run (e.g., 'system-architect')
        task_description: What you want the agent to do
        context: Optional context from previous agents or artifacts
        input_files: Optional comma-separated list of file paths to provide
    
    Returns:
        Agent output and path to generated artifact
    """
    # Validate agent exists
    if agent_name not in get_agent_names():
        return f"Error: Agent '{agent_name}' not found. Use list_agents() to see available agents."
    
    # Build command
    cmd = [
        "python3",
        "run_agent.py",
        agent_name,
        "--task", task_description
    ]
    
    if context:
        cmd.extend(["--context", context])
    
    if input_files:
        cmd.extend(["--input-files", input_files])
    
    # Run agent
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            return f"Error running agent: {result.stderr}"
        
        # Try to read the generated artifact
        artifact = read_artifact(agent_name)
        
        output = [
            f"Agent '{agent_name}' completed successfully",
            "",
            "Output:",
            result.stdout,
        ]
        
        if artifact:
            output.extend([
                "",
                "Generated Artifact:",
                "---",
                artifact[:2000] + "..." if len(artifact) > 2000 else artifact
            ])
        
        return "\n".join(output)
        
    except subprocess.TimeoutExpired:
        return f"Error: Agent '{agent_name}' timed out after 5 minutes"
    except Exception as e:
        return f"Error running agent: {str(e)}"


@mcp.tool()
def run_workflow(workflow_name: str, initial_context: Optional[str] = None) -> str:
    """
    Run a predefined workflow that chains multiple agents.
    
    Args:
        workflow_name: Name of the workflow (e.g., 'feature-development')
        initial_context: Optional starting context for the workflow
    
    Returns:
        Workflow execution results
    """
    workflow_file = WORKFLOWS_DIR / f"{workflow_name}.yaml"
    
    if not workflow_file.exists():
        available = [f.stem for f in WORKFLOWS_DIR.glob("*.yaml")]
        return f"Workflow '{workflow_name}' not found. Available: {', '.join(available)}"
    
    # Build command
    cmd = [
        "python3",
        "run_workflow.py",
        workflow_name
    ]
    
    if initial_context:
        cmd.extend(["--context", initial_context])
    
    # Run workflow
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for workflows
        )
        
        if result.returncode != 0:
            return f"Error running workflow: {result.stderr}"
        
        return result.stdout
        
    except subprocess.TimeoutExpired:
        return f"Error: Workflow '{workflow_name}' timed out after 10 minutes"
    except Exception as e:
        return f"Error running workflow: {str(e)}"


@mcp.tool()
def get_agent_artifact(agent_name: str) -> str:
    """
    Retrieve the most recent artifact from a specific agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        Contents of the agent's artifact file
    """
    artifact = read_artifact(agent_name)
    
    if not artifact:
        return f"No artifact found for agent '{agent_name}'"
    
    return artifact




@mcp.tool()
def get_agent_dependencies(agent_name: str) -> str:
    """
    Show what agents this agent depends on and what agents depend on it.
    Useful for understanding workflow order and planning parallel execution.
    
    Args:
        agent_name: Name of the agent (e.g., 'system-architect')
    
    Returns:
        Dependency information including inputs, outputs, and workflow relationships
    """
    agent_info = get_agent_info(agent_name)
    
    if not agent_info:
        return f"Agent '{agent_name}' not found"
    
    deps = agent_info.get('dependencies', {})
    
    output = [f"# Dependencies for {agent_info.get('display_name', agent_name)}", ""]
    
    # What this agent needs before running
    runs_after = deps.get('runs_after', [])
    if runs_after:
        output.append("## Must Run After:")
        for dep in runs_after:
            output.append(f"  • {dep}")
        output.append("")
    else:
        output.append("## Must Run After: None (can run first)")
        output.append("")
    
    # What must wait for this agent
    runs_before = deps.get('runs_before', [])
    if runs_before:
        output.append("## Must Complete Before:")
        for dep in runs_before:
            output.append(f"  • {dep}")
        output.append("")
    else:
        output.append("## Must Complete Before: None (no blocking dependencies)")
        output.append("")
    
    # What agents can be consulted
    can_consult = deps.get('can_consult', [])
    if can_consult:
        output.append("## Can Consult:")
        for dep in can_consult:
            output.append(f"  • {dep}")
        output.append("")
    
    # Inputs
    inputs = agent_info.get('inputs', [])
    if inputs:
        output.append("## Required Inputs:")
        for inp in inputs:
            name = inp.get('name', 'unknown')
            required = " (required)" if inp.get('required') else " (optional)"
            source = inp.get('source', 'unknown')
            output.append(f"  • {name}{required} from {source}")
        output.append("")
    
    # Outputs
    outputs = agent_info.get('outputs', [])
    if outputs:
        output.append("## Outputs:")
        for out in outputs:
            name = out.get('name', 'unknown')
            fmt = out.get('format', 'unknown')
            output.append(f"  • {name} ({fmt})")
        output.append("")
    
    # Approval gate
    if agent_info.get('approval_required'):
        output.append("⚠️  **This agent requires human approval before proceeding**")
    
    return "\n".join(output)


@mcp.tool()
def suggest_agent(task_description: str) -> str:
    """
    Suggest which agent(s) to use for a given task.
    
    Args:
        task_description: Description of what needs to be done
    
    Returns:
        Recommended agent(s) and reasoning
    """
    registry = load_agent_registry()
    agents = registry.get('agents', [])
    
    task_lower = task_description.lower()
    suggestions = []
    
    # Simple keyword matching for agent suggestion
    keywords_map = {
        'requirements-gatherer': ['requirements', 'features', 'gather', 'elicit'],
        'system-architect': ['architecture', 'design', 'system', 'structure'],
        'rust-scaffolder': ['scaffold', 'setup', 'project structure', 'initialize'],
        'code-reviewer': ['review', 'check', 'quality', 'audit'],
        'test-developer': ['test', 'testing', 'unit test', 'integration'],
        'crypto-developer': ['encryption', 'crypto', 'security', 'aes', 'argon2'],
        'transaction-developer': ['transaction', 'import', 'csv', 'qfx', 'pdf'],
        'categorization-developer': ['categorize', 'categorization', 'ml', 'rules'],
        'tax-developer': ['tax', 'schedule c', 'p&l', 'cash flow'],
    }
    
    for agent in agents:
        agent_name = agent['name']
        keywords = keywords_map.get(agent_name, [])
        
        # Check if any keywords match
        if any(keyword in task_lower for keyword in keywords):
            suggestions.append({
                'name': agent_name,
                'description': agent.get('description', ''),
                'confidence': 'high' if len([k for k in keywords if k in task_lower]) > 1 else 'medium'
            })
    
    if not suggestions:
        return "No specific agent matches found. Consider:\n• requirements-gatherer for new features\n• system-architect for design decisions\n• code-reviewer for code quality checks"
    
    output = ["Suggested agents for your task:", ""]
    for s in suggestions:
        output.append(f"• {s['name']} (confidence: {s['confidence']})")
        output.append(f"  {s['description']}")
        output.append("")
    
    return "\n".join(output)


@mcp.tool()
def list_workflows() -> str:
    """
    List all available workflows.
    
    Returns:
        List of workflow names and descriptions
    """
    if not WORKFLOWS_DIR.exists():
        return "No workflows directory found"
    
    workflows = list(WORKFLOWS_DIR.glob("*.yaml"))
    
    if not workflows:
        return "No workflows found"
    
    output = ["Available Workflows:", ""]
    
    for wf in workflows:
        try:
            with open(wf, 'r') as f:
                config = yaml.safe_load(f)
                name = wf.stem
                description = config.get('description', 'No description')
                steps = len(config.get('steps', []))
                
                output.append(f"• {name}")
                output.append(f"  {description}")
                output.append(f"  Steps: {steps}")
                output.append("")
        except Exception as e:
            output.append(f"• {wf.stem} (error reading: {e})")
            output.append("")
    
    return "\n".join(output)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()

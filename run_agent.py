#!/usr/bin/env python3
"""
Run a single agent with task and context.

Usage:
    python run_agent.py <agent_name> --task "task description" [--context "context"] [--input-files "file1,file2"]
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import WorkflowEngine

def main():
    parser = argparse.ArgumentParser(description="Run a single agent")
    parser.add_argument("agent_name", help="Name of the agent to run")
    parser.add_argument("--task", required=True, help="Task description for the agent")
    parser.add_argument("--context", help="Optional context string")
    parser.add_argument("--input-files", help="Comma-separated list of input files")

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not found in environment", file=sys.stderr)
        sys.exit(1)

    # Convert agent name format (hyphens to underscores for internal use)
    agent_id = args.agent_name.replace("-", "_")

    # Build context dict
    context = {}
    if args.context:
        context["additional_context"] = args.context

    # Read input files if provided
    if args.input_files:
        input_contents = []
        for file_path in args.input_files.split(","):
            file_path = file_path.strip()
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    input_contents.append(f"## Contents of {file_path}\n\n{f.read()}")
        if input_contents:
            context["input_files"] = "\n\n".join(input_contents)

    # Create workflow engine
    engine = WorkflowEngine(
        prompts_dir="prompts",
        agents_config="config/agents.yaml",
        state_dir="workflow",
    )

    # Build user input with task and any file contents
    user_input = args.task
    if context.get("input_files"):
        user_input = f"{args.task}\n\n{context['input_files']}"

    # Run agent
    try:
        result = engine.run_agent(
            agent_id=agent_id,
            user_input=user_input,
            context=context if context else None,
            save_output=True,
        )

        # Output results
        print(f"Agent: {agent_id}")
        print(f"Status: completed")
        print(f"Model: {result.get('model', 'N/A')}")
        print(f"Input tokens: {result.get('usage', {}).get('input_tokens', 'N/A')}")
        print(f"Output tokens: {result.get('usage', {}).get('output_tokens', 'N/A')}")
        print(f"Artifact: {result.get('artifact_path', 'N/A')}")
        print()
        print("--- Output ---")
        print(result.get("content", "No content"))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

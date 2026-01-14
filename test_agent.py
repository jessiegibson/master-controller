#!/usr/bin/env python3
"""
Test script to run a single agent.

Usage:
    python test_agent.py requirements_gatherer

This MVP test script demonstrates:
1. Loading agent prompts
2. Executing an agent via Claude API
3. Saving outputs to workflow/artifacts/
4. Displaying results

Before running:
    export ANTHROPIC_API_KEY="your-api-key"
    pip install -r requirements.txt
"""

import sys
import os
from dotenv import load_dotenv
from orchestrator import WorkflowEngine

# Load environment variables from .env file
load_dotenv()


def main():
    """Run a single agent test."""
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not found in environment")
        print("Please set it via: export ANTHROPIC_API_KEY='your-key'")
        print("Or create a .env file with: ANTHROPIC_API_KEY=your-key")
        sys.exit(1)

    # Get agent ID from command line
    if len(sys.argv) < 2:
        print("Usage: python test_agent.py <agent_id>")
        print("\nAvailable agents:")
        print("  - requirements_gatherer")
        print("  - system_architect")
        print("  - data_architect")
        print("  - ... (see config/agents.yaml for full list)")
        sys.exit(1)

    agent_id = sys.argv[1]

    # Create workflow engine
    print(f"\n🚀 Initializing Agent Orchestrator...")
    engine = WorkflowEngine(
        prompts_dir="prompts",
        agents_config="config/agents.yaml",
        state_dir="workflow",
    )

    # Example task for requirements gatherer
    if agent_id == "requirements_gatherer":
        user_input = """
I want to build a privacy-first personal finance CLI application.

Key features:
- Import transactions from CSV, QFX, and PDF bank statements
- Categorize transactions automatically using rules and ML
- Generate Profit & Loss and Cash Flow reports
- Map expenses to IRS Schedule C line items for tax preparation
- Encrypt all data locally with AES-256-GCM
- No cloud, no internet required - completely local

Tech stack: Rust, DuckDB for storage, clap for CLI

Target users: Freelancers and small business owners who need simple bookkeeping
"""
    else:
        # Generic task for other agents
        user_input = input("\nEnter task description for agent:\n> ")

    # Add context
    context = {
        "project_name": "Finance CLI",
        "current_phase": "planning",
    }

    print(f"\n📋 Task:")
    print(f"   {user_input[:100]}..." if len(user_input) > 100 else f"   {user_input}")
    print()

    # Run agent
    try:
        result = engine.run_agent(
            agent_id=agent_id,
            user_input=user_input,
            context=context,
            save_output=True,
        )

        print(f"\n{'=' * 80}")
        print("✅ Execution completed successfully!")
        print(f"{'=' * 80}")
        print(f"\n📊 Stats:")
        print(f"   Model: {result['model']}")
        print(f"   Input tokens: {result['usage']['input_tokens']}")
        print(f"   Output tokens: {result['usage']['output_tokens']}")
        print(f"   Output saved to: {result.get('artifact_path', 'N/A')}")

        # Show execution history
        print(f"\n📜 Recent executions:")
        history = engine.get_execution_history(limit=5)
        for i, exec_record in enumerate(history, 1):
            status_icon = "✓" if exec_record["status"] == "completed" else "✗"
            print(f"   {i}. {status_icon} {exec_record['agent_id']} - {exec_record['status']} - {exec_record['timestamp']}")

    except Exception as e:
        print(f"\n❌ Execution failed!")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

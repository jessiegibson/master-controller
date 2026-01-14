#!/usr/bin/env python3
"""
Validate orchestrator setup without making API calls.

Checks:
- Python imports work
- Configuration files exist
- Prompts are loadable
- Directory structure is correct
"""

import os
import sys
from pathlib import Path


def check_imports():
    """Test that all orchestrator modules can be imported."""
    print("✓ Checking imports...")
    try:
        from orchestrator import WorkflowEngine, AgentRunner, LLMClient, StateStore
        print("  ✓ All orchestrator modules imported successfully")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def check_config_files():
    """Check that configuration files exist."""
    print("\n✓ Checking configuration files...")

    required_files = [
        "config/agents.yaml",
        "prompts/requirements_gatherer.md",
        "prompts/workflow_orchestrator.md",
        "prompts/context_manager.md",
    ]

    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} NOT FOUND")
            all_exist = False

    return all_exist


def check_directory_structure():
    """Check that required directories exist."""
    print("\n✓ Checking directory structure...")

    required_dirs = [
        "orchestrator",
        "prompts",
        "config",
        "context",
        "kanban",
        "workflow",
        "logs",
    ]

    all_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ NOT FOUND")
            all_exist = False

    return all_exist


def check_prompt_loading():
    """Test loading an agent prompt."""
    print("\n✓ Checking prompt loading...")
    try:
        # Import modules without creating LLM client
        import yaml
        from pathlib import Path

        # Load config
        with open("config/agents.yaml", 'r') as f:
            config = yaml.safe_load(f)
            agents = config.get('agents', {})

        # Get prompt file for requirements_gatherer
        agent_config = agents.get('requirements_gatherer', {})
        prompt_file = agent_config.get('prompt_file', '')

        # Try to load the prompt file directly
        prompt_path = Path("prompts") / "requirements_gatherer.md"
        if not prompt_path.exists():
            print(f"  ✗ Prompt file not found: {prompt_path}")
            return False

        with open(prompt_path, 'r') as f:
            prompt = f.read()

        if prompt and len(prompt) > 100:
            print(f"  ✓ requirements_gatherer prompt loaded ({len(prompt)} chars)")
            return True
        else:
            print(f"  ✗ Prompt too short or empty")
            return False

    except Exception as e:
        print(f"  ✗ Failed to load prompt: {e}")
        return False


def check_agent_count():
    """Count available agents."""
    print("\n✓ Checking agent registry...")
    try:
        import yaml

        with open("config/agents.yaml", 'r') as f:
            config = yaml.safe_load(f)
            agents = config.get("agents", {})
            count = len(agents)

            print(f"  ✓ Found {count} agents in configuration")

            # List a few
            agent_list = list(agents.keys())[:5]
            print(f"  ✓ Sample agents: {', '.join(agent_list)}...")

            return count > 0

    except Exception as e:
        print(f"  ✗ Failed to load agents config: {e}")
        return False


def main():
    """Run all validation checks."""
    print("=" * 80)
    print("Agent Orchestrator - Setup Validation")
    print("=" * 80)

    checks = [
        check_imports(),
        check_config_files(),
        check_directory_structure(),
        check_agent_count(),
        check_prompt_loading(),
    ]

    print("\n" + "=" * 80)
    if all(checks):
        print("✅ All checks passed! Setup is valid.")
        print("\nNext steps:")
        print("  1. Set ANTHROPIC_API_KEY environment variable")
        print("  2. Run: python test_agent.py requirements_gatherer")
        print("\nSee QUICKSTART.md for detailed instructions.")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

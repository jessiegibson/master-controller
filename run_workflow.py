#!/usr/bin/env python3
"""
Run a multi-agent workflow.

Usage:
    python run_workflow.py <workflow_name> [--target-files FILES] [--review-type TYPE] [--severity-threshold LEVEL]

Examples:
    # Quick review workflow
    python run_workflow.py quick-review \
        --target-files src/parsers/csv.rs \
        --review-type full \
        --severity-threshold medium

    # Implementation phase workflow
    python run_workflow.py implementation-phase

    # Full build workflow
    python run_workflow.py full-build
"""

import argparse
import sys
import os
import yaml
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import WorkflowEngine


def load_workflow_definition(workflow_name: str, workflows_dir: str = "workflows") -> dict:
    """Load a workflow definition from YAML."""
    workflow_path = Path(workflows_dir) / f"{workflow_name}.yaml"
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow not found: {workflow_path}")

    with open(workflow_path, "r") as f:
        return yaml.safe_load(f)


def resolve_parameters(workflow: dict, cli_args: dict) -> dict:
    """Resolve workflow parameters from CLI arguments and defaults."""
    parameters = {}

    if "parameters" not in workflow:
        return parameters

    for param_def in workflow["parameters"]:
        param_name = param_def["name"]

        # Check if provided via CLI
        if param_name in cli_args and cli_args[param_name] is not None:
            parameters[param_name] = cli_args[param_name]
        # Check if there's a default
        elif "default" in param_def:
            parameters[param_name] = param_def["default"]
        # Check if required
        elif param_def.get("required", False):
            raise ValueError(f"Required parameter not provided: {param_name}")

    return parameters


def execute_phase(engine: WorkflowEngine, phase: dict, parameters: dict, parallel_limit: int = 4) -> dict:
    """Execute a workflow phase (can contain multiple agents)."""
    phase_name = phase["name"]
    agents = phase.get("agents", [])
    parallel = phase.get("parallel", False)

    print(f"\n{'='*80}")
    print(f"PHASE: {phase_name.upper()}")
    print(f"Description: {phase.get('description', 'N/A')}")
    print(f"Parallel: {parallel} | Agents: {len(agents)}")
    print(f"{'='*80}\n")

    results = {}

    if not agents:
        print(f"No agents in phase {phase_name}")
        return results

    if parallel and len(agents) > 1:
        # Execute agents in parallel
        print(f"Executing {len(agents)} agents in parallel...\n")

        with ThreadPoolExecutor(max_workers=min(len(agents), parallel_limit)) as executor:
            futures = {}

            for agent_spec in agents:
                agent_name = agent_spec["name"]
                agent_id = agent_name.replace("-", "_")

                # Check if agent is enabled
                if not agent_spec.get("enabled", True):
                    enabled_when = agent_spec.get("enabled_when", [])
                    # Simple check: if any enabled_when condition matches, enable it
                    should_enable = False
                    for condition in enabled_when:
                        # For now, just enable if there's any enabled_when condition
                        # In production, would need more sophisticated logic
                        should_enable = True

                    if not should_enable:
                        print(f"Skipping {agent_name} (disabled)")
                        continue

                # Prepare task for agent
                task = prepare_agent_task(agent_spec, parameters)

                # Submit to executor
                future = executor.submit(
                    engine.run_agent,
                    agent_id=agent_id,
                    user_input=task,
                    context={"parameters": parameters, "phase": phase_name},
                    save_output=True,
                )
                futures[future] = agent_name

            # Collect results as they complete
            for future in as_completed(futures):
                agent_name = futures[future]
                try:
                    result = future.result()
                    results[agent_name] = {
                        "status": "completed",
                        "validation": result.get("validation_status", "unknown"),
                    }
                    print(f"✓ {agent_name}: completed")
                except Exception as e:
                    results[agent_name] = {
                        "status": "failed",
                        "error": str(e),
                    }
                    print(f"✗ {agent_name}: failed - {e}")
    else:
        # Execute agents sequentially
        print(f"Executing {len(agents)} agents sequentially...\n")

        for agent_spec in agents:
            agent_name = agent_spec["name"]
            agent_id = agent_name.replace("-", "_")

            # Check if agent is enabled
            if not agent_spec.get("enabled", True):
                print(f"Skipping {agent_name} (disabled)")
                continue

            # Prepare task for agent
            task = prepare_agent_task(agent_spec, parameters)

            try:
                result = engine.run_agent(
                    agent_id=agent_id,
                    user_input=task,
                    context={"parameters": parameters, "phase": phase_name},
                    save_output=True,
                )
                results[agent_name] = {
                    "status": "completed",
                    "validation": result.get("validation_status", "unknown"),
                }
                print(f"✓ {agent_name}: completed")
            except Exception as e:
                results[agent_name] = {
                    "status": "failed",
                    "error": str(e),
                }
                print(f"✗ {agent_name}: failed - {e}")

    return results


def prepare_agent_task(agent_spec: dict, parameters: dict) -> str:
    """Prepare the task/input for an agent."""
    description = agent_spec.get("description", agent_spec["name"])

    # Build task with description and config
    task = f"Task: {description}\n\n"

    if "config" in agent_spec:
        task += "Configuration:\n"
        for key, value in agent_spec["config"].items():
            task += f"  - {key}: {value}\n"
        task += "\n"

    if "inputs" in agent_spec:
        task += "Inputs:\n"
        for input_item in agent_spec["inputs"]:
            for key, source in input_item.items():
                task += f"  - {key}: {source}\n"

    return task


def main():
    parser = argparse.ArgumentParser(
        description="Run a multi-agent workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("workflow_name", help="Name of the workflow to run")
    parser.add_argument("--target-files", help="Files to review (for quick-review workflow)")
    parser.add_argument("--review-type", help="Type of review (for quick-review workflow)")
    parser.add_argument("--severity-threshold", help="Severity threshold (for quick-review workflow)")
    parser.add_argument("--max-parallel", type=int, default=4, help="Maximum parallel agents")

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not found in environment", file=sys.stderr)
        print("\nTo set up your API key:", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY='sk-ant-...'", file=sys.stderr)
        sys.exit(1)

    try:
        # Load workflow definition
        print(f"Loading workflow: {args.workflow_name}")
        workflow = load_workflow_definition(args.workflow_name)
        print(f"✓ Loaded: {workflow.get('name')} v{workflow.get('version', '?')}")
        print(f"  Description: {workflow.get('description', 'N/A')}\n")

        # Collect CLI arguments as a dict
        cli_args = {
            "target_files": args.target_files,
            "review_type": args.review_type,
            "severity_threshold": args.severity_threshold,
        }

        # Resolve parameters
        parameters = resolve_parameters(workflow, cli_args)
        if parameters:
            print("Parameters:")
            for key, value in parameters.items():
                print(f"  {key}: {value}")
            print()

        # Create workflow engine
        engine = WorkflowEngine(
            prompts_dir="prompts",
            agents_config="config/agents.yaml",
            state_dir="workflow",
        )

        # Execute phases
        start_time = datetime.now()
        workflow_results = {}

        phases = workflow.get("phases", [])
        if not phases:
            print("Error: No phases defined in workflow", file=sys.stderr)
            sys.exit(1)

        for phase_index, phase in enumerate(phases, 1):
            try:
                phase_results = execute_phase(
                    engine,
                    phase,
                    parameters,
                    parallel_limit=args.max_parallel,
                )
                workflow_results[phase["name"]] = phase_results
            except Exception as e:
                print(f"✗ Phase {phase['name']} failed: {e}", file=sys.stderr)

                # Check error handling policy
                error_handling = workflow.get("error_handling", {})
                on_agent_failure = error_handling.get("on_agent_failure", {})
                action = on_agent_failure.get("action", "continue")

                if action == "fail":
                    sys.exit(1)
                elif action == "continue":
                    print(f"Continuing to next phase...")
                    continue

        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n{'='*80}")
        print(f"WORKFLOW COMPLETE: {args.workflow_name}")
        print(f"{'='*80}")
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"\nPhase Results:")
        for phase_name, phase_results in workflow_results.items():
            completed = sum(1 for r in phase_results.values() if r["status"] == "completed")
            failed = sum(1 for r in phase_results.values() if r["status"] == "failed")
            print(f"  {phase_name}: {completed} completed, {failed} failed")

        # Save workflow execution summary
        output_dir = Path(workflow.get("output", {}).get("path", "docs/reviews")).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        summary_file = output_dir / f"workflow_execution_{args.workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        with open(summary_file, "w") as f:
            yaml.dump({
                "workflow": args.workflow_name,
                "status": "completed",
                "duration_seconds": duration,
                "parameters": parameters,
                "results": workflow_results,
            }, f)

        print(f"\nExecution summary saved to: {summary_file}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

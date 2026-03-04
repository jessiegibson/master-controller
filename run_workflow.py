#!/usr/bin/env python3
"""
Run a multi-agent workflow from a YAML definition.

Usage:
    python run_workflow.py full-build                    # Run full workflow
    python run_workflow.py full-build --phase planning   # Run single phase
    python run_workflow.py full-build --dry-run          # Preview execution
    python run_workflow.py --list                        # List workflows
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dotenv import load_dotenv
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import WorkflowEngine


class WorkflowRunner:
    """Runs a multi-agent workflow from YAML definition."""

    def __init__(self, workflows_dir: str = "workflows"):
        """Initialize workflow runner.

        Args:
            workflows_dir: Directory containing workflow YAML files
        """
        self.console = Console()
        self.workflows_dir = Path(workflows_dir)
        self.engine = WorkflowEngine(
            prompts_dir="prompts",
            agents_config="config/agents.yaml",
            state_dir="workflow",
        )
        self.outputs: Dict[str, str] = {}  # agent_id -> output content
        self.workflow: Optional[Dict[str, Any]] = None
        self.workflow_name: str = ""

    def list_workflows(self) -> None:
        """List available workflows."""
        workflows = sorted(self.workflows_dir.glob("*.yaml"))

        if not workflows:
            self.console.print("[yellow]No workflows found[/yellow]")
            return

        table = Table(title="Available Workflows", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Description")

        for wf_path in workflows:
            try:
                with open(wf_path) as f:
                    data = yaml.safe_load(f)
                    name = data.get("name", wf_path.stem)
                    desc = data.get("description", "").split("\n")[0]
                    table.add_row(name, desc)
            except Exception as e:
                table.add_row(wf_path.stem, f"[red]Error: {e}[/red]")

        self.console.print(table)

    def load_workflow(self, workflow: str) -> bool:
        """Load workflow from YAML.

        Args:
            workflow: Workflow name or path

        Returns:
            True if loaded successfully, False otherwise
        """
        # Try as path first
        wf_path = Path(workflow)
        if not wf_path.exists():
            # Try in workflows directory
            wf_path = self.workflows_dir / f"{workflow}.yaml"

        if not wf_path.exists():
            self.console.print(f"[red]Error: Workflow not found: {workflow}[/red]")
            return False

        try:
            with open(wf_path) as f:
                self.workflow = yaml.safe_load(f)
                self.workflow_name = self.workflow.get("name", wf_path.stem)
                return True
        except Exception as e:
            self.console.print(f"[red]Error loading workflow: {e}[/red]")
            return False

    def get_phases(self) -> List[Dict[str, Any]]:
        """Get phases from loaded workflow.

        Returns:
            List of phase definitions
        """
        return self.workflow.get("phases", [])

    def get_phase_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get phase definition by name.

        Args:
            name: Phase name

        Returns:
            Phase definition or None
        """
        for phase in self.get_phases():
            if phase.get("name") == name:
                return phase
        return None

    def _topologically_sort_agents(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Topologically sort agents based on wait_for dependencies.

        Args:
            agents: List of agent configurations

        Returns:
            Sorted list of agents
        """
        # Build dependency graph
        dependencies: Dict[str, Set[str]] = {}
        agent_map: Dict[str, Dict[str, Any]] = {}

        for agent in agents:
            name = agent.get("name")
            agent_map[name] = agent
            wait_for = agent.get("wait_for", [])
            dependencies[name] = set(wait_for) if isinstance(wait_for, list) else {wait_for}

        # Topological sort
        sorted_agents = []
        visited = set()

        def visit(name: str, visiting: Set[str]) -> None:
            if name in visited:
                return
            if name in visiting:
                self.console.print(f"[red]Error: Circular dependency detected for agent {name}[/red]")
                raise ValueError(f"Circular dependency: {name}")

            visiting.add(name)
            for dep in dependencies.get(name, set()):
                if dep in agent_map:  # Only visit if dependency is in this phase
                    visit(dep, visiting)
            visiting.remove(name)

            visited.add(name)
            sorted_agents.append(agent_map[name])

        for agent in agents:
            visit(agent.get("name"), set())

        return sorted_agents

    def _check_phase_dependencies(self, phase: Dict[str, Any], completed_phases: Set[str]) -> bool:
        """Check if phase dependencies are satisfied.

        Args:
            phase: Phase definition
            completed_phases: Set of completed phase names

        Returns:
            True if dependencies are satisfied
        """
        depends_on = phase.get("depends_on", [])
        if not depends_on:
            return True

        depends_on = depends_on if isinstance(depends_on, list) else [depends_on]
        missing = [p for p in depends_on if p not in completed_phases]

        if missing:
            self.console.print(
                f"[red]Error: Phase '{phase.get('name')}' depends on {missing} which haven't completed[/red]"
            )
            return False

        return True

    def _run_agent(self, agent_config: Dict[str, Any]) -> bool:
        """Run a single agent.

        Args:
            agent_config: Agent configuration from workflow YAML

        Returns:
            True if successful, False otherwise
        """
        agent_name = agent_config.get("name")
        agent_id = agent_name.replace("-", "_")

        self.console.print(f"\n[cyan]→ Running agent: {agent_name}[/cyan]")

        try:
            # Assemble context from prior agent outputs
            context = self._assemble_context(agent_config)

            # Build user input
            user_input = f"Execute your role as defined in your system prompt for the {self.workflow_name} project."

            # Run agent
            result = self.engine.run_agent(
                agent_id=agent_id,
                user_input=user_input,
                context=context if context else None,
                save_output=True,
            )

            # Store output for downstream agents
            if result:
                self.outputs[agent_id] = result.get("content", "")
                return True
            return False

        except Exception as e:
            self.console.print(f"[red]✗ Agent failed: {e}[/red]")
            return False

    def _assemble_context(self, agent_config: Dict[str, Any]) -> Dict[str, str]:
        """Assemble context from prior agent outputs.

        Args:
            agent_config: Agent configuration with inputs specification

        Returns:
            Context dictionary
        """
        context = {}
        inputs = agent_config.get("inputs", {})

        if isinstance(inputs, list):
            # List of input specs
            for input_spec in inputs:
                if isinstance(input_spec, dict):
                    for key, value in input_spec.items():
                        if isinstance(value, str) and value.startswith("from:"):
                            source_agent = value.replace("from:", "").replace("-", "_")
                            if source_agent in self.outputs:
                                context[key] = self.outputs[source_agent]
        elif isinstance(inputs, dict):
            # Dict of input specs
            for key, value in inputs.items():
                if isinstance(value, str) and value.startswith("from:"):
                    source_agent = value.replace("from:", "").replace("-", "_")
                    if source_agent in self.outputs:
                        context[key] = self.outputs[source_agent]

        return context

    def _handle_approval_gate(self, gate: Dict[str, Any]) -> bool:
        """Handle approval gate prompt.

        Args:
            gate: Gate configuration

        Returns:
            True if approved, False if rejected
        """
        if not gate.get("required", False):
            return True

        description = gate.get("description", "Review outputs before proceeding")
        criteria = gate.get("criteria", [])

        self.console.print(
            Panel(
                f"[bold yellow]⚠ Approval Gate[/bold yellow]\n\n{description}",
                border_style="yellow",
                expand=False,
            )
        )

        if criteria:
            self.console.print("[yellow]Criteria:[/yellow]")
            for criterion in criteria:
                self.console.print(f"  • {criterion}")

        approved = Confirm.ask("[yellow]Proceed?[/yellow]", default=False)

        if not approved:
            self.console.print("[yellow]Workflow cancelled by user[/yellow]")
            return False

        return True

    def _run_phase(self, phase: Dict[str, Any], skip_gates: bool = False) -> bool:
        """Run a phase.

        Args:
            phase: Phase definition
            skip_gates: Whether to skip approval gates

        Returns:
            True if all agents succeeded, False otherwise
        """
        phase_name = phase.get("name")
        description = phase.get("description", "").split("\n")[0]

        self.console.print(
            Panel(
                f"[bold green]Phase: {phase_name}[/bold green]\n{description}",
                border_style="green",
                expand=False,
            )
        )

        # Get agents in this phase
        agents = phase.get("agents", [])
        is_parallel = phase.get("parallel", False)

        # Sort agents topologically by wait_for dependencies
        agents = self._topologically_sort_agents(agents)

        # Run agents
        all_succeeded = True
        for agent_config in agents:
            if not self._run_agent(agent_config):
                all_succeeded = False
                self.console.print(f"[yellow]Warning: Agent failed, continuing...[/yellow]")

        # Handle approval gate
        gate = phase.get("approval_gate", {})
        if not skip_gates and gate.get("required", False):
            if not self._handle_approval_gate(gate):
                return False

        return all_succeeded

    def _dry_run(self, phase_filter: Optional[str] = None, from_phase: Optional[str] = None) -> None:
        """Print execution plan without running.

        Args:
            phase_filter: Optional phase name to filter
            from_phase: Optional phase to start from
        """
        phases = self.get_phases()

        # Filter phases
        if phase_filter:
            phases = [p for p in phases if p.get("name") == phase_filter]
        elif from_phase:
            start_idx = next(
                (i for i, p in enumerate(phases) if p.get("name") == from_phase),
                0
            )
            phases = phases[start_idx:]

        table = Table(title="Workflow Execution Plan", show_header=True, header_style="bold cyan")
        table.add_column("Phase", style="green")
        table.add_column("Mode")
        table.add_column("Agents", style="yellow")
        table.add_column("Gate")

        for phase in phases:
            name = phase.get("name")
            mode = "Parallel" if phase.get("parallel", False) else "Sequential"
            agents = ", ".join(a.get("name", "") for a in phase.get("agents", []))
            gate = "Required" if phase.get("approval_gate", {}).get("required", False) else "Optional"

            table.add_row(name, mode, agents, gate)

        self.console.print(table)
        self.console.print(f"\n[cyan]Total agents: {sum(len(p.get('agents', [])) for p in phases)}[/cyan]")

    def run(
        self,
        phase: Optional[str] = None,
        from_phase: Optional[str] = None,
        skip_gates: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Run workflow.

        Args:
            phase: Optional phase name to run only that phase
            from_phase: Optional phase name to start from
            skip_gates: Whether to skip approval gates
            dry_run: Whether to print plan without running

        Returns:
            True if all phases completed successfully
        """
        if not self.workflow:
            self.console.print("[red]Error: No workflow loaded[/red]")
            return False

        phases = self.get_phases()

        # Filter phases
        if phase:
            phases = [p for p in phases if p.get("name") == phase]
            if not phases:
                self.console.print(f"[red]Error: Phase '{phase}' not found[/red]")
                return False
        elif from_phase:
            start_idx = next(
                (i for i, p in enumerate(phases) if p.get("name") == from_phase),
                None
            )
            if start_idx is None:
                self.console.print(f"[red]Error: Phase '{from_phase}' not found[/red]")
                return False
            phases = phases[start_idx:]

        # Dry run mode
        if dry_run:
            self._dry_run(phase_filter=phase, from_phase=from_phase)
            return True

        # Execute phases
        completed_phases: Set[str] = set()

        for phase_def in phases:
            phase_name = phase_def.get("name")

            # Check dependencies
            if not self._check_phase_dependencies(phase_def, completed_phases):
                return False

            # Run phase
            if not self._run_phase(phase_def, skip_gates=skip_gates):
                self.console.print(f"[yellow]Phase '{phase_name}' had warnings but continuing[/yellow]")

            completed_phases.add(phase_name)

        # Success
        self.console.print(
            Panel(
                f"[bold green]✓ Workflow '{self.workflow_name}' completed successfully[/bold green]",
                border_style="green",
                expand=False,
            )
        )
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run a multi-agent workflow from YAML definition"
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        help="Workflow name or path (e.g., 'full-build' or 'workflows/full-build.yaml')",
    )
    parser.add_argument(
        "--phase",
        help="Run only a single named phase",
    )
    parser.add_argument(
        "--from-phase",
        help="Start execution from this phase (skip earlier ones)",
    )
    parser.add_argument(
        "--skip-gates",
        action="store_true",
        help="Bypass approval gates (for CI/automation)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print execution plan without calling the API",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available workflows and exit",
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not found in environment", file=sys.stderr)
        sys.exit(1)

    # Create runner
    runner = WorkflowRunner(workflows_dir="workflows")

    # Handle --list
    if args.list:
        runner.list_workflows()
        return

    # Require workflow argument unless --list
    if not args.workflow:
        parser.print_help()
        sys.exit(1)

    # Load workflow
    if not runner.load_workflow(args.workflow):
        sys.exit(1)

    # Run workflow
    success = runner.run(
        phase=args.phase,
        from_phase=args.from_phase,
        skip_gates=args.skip_gates,
        dry_run=args.dry_run,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

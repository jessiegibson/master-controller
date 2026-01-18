"""
Workflow Engine

Orchestrates agent execution.

For MVP: Simple single-agent execution
Future: Full DAG-based workflow with parallel execution, dependencies, error handling
"""

from typing import Dict, Any, Optional
import traceback
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from .agent_runner import AgentRunner
from .state_store import StateStore
from .llm_client import LLMClient
from .context_manager import ContextManager
from .kanban_manager import KanbanManager
from .output_validator import OutputValidator
from .log_manager import LogManager


class WorkflowEngine:
    """Orchestrates multi-agent workflows."""

    def __init__(
        self,
        prompts_dir: str = "prompts",
        agents_config: str = "config/agents.yaml",
        state_dir: str = "workflow",
    ):
        """Initialize workflow engine.

        Args:
            prompts_dir: Directory containing agent prompts
            agents_config: Path to agents.yaml configuration
            state_dir: Directory for workflow state
        """
        self.console = Console()
        self.llm_client = LLMClient()
        self.agent_runner = AgentRunner(
            prompts_dir=prompts_dir,
            agents_config_path=agents_config,
            llm_client=self.llm_client,
        )
        self.state_store = StateStore(state_dir=state_dir)

        # Initialize new components
        self.context_manager = ContextManager(context_dir="context")
        self.kanban_manager = KanbanManager(db_path="kanban/tasks.db")
        self.output_validator = OutputValidator(schemas_dir="schemas")
        self.log_manager = LogManager(log_dir="logs")

    def run_agent(
        self,
        agent_id: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        save_output: bool = True,
    ) -> Dict[str, Any]:
        """Run a single agent.

        Args:
            agent_id: Agent to run
            user_input: User task/input for agent
            context: Optional context dictionary
            save_output: Whether to save output to state store

        Returns:
            Execution result dict
        """
        # Display start message
        self.console.print(
            Panel(
                f"[bold cyan]Running agent:[/bold cyan] {agent_id}",
                expand=False,
            )
        )

        # Record execution start
        execution_id = self.state_store.record_execution(
            agent_id=agent_id,
            status="started",
        )

        # Log execution start
        self.log_manager.log_execution_start(
            execution_id=execution_id,
            agent_id=agent_id,
            user_input=user_input
        )

        try:
            # Assemble context from Context Manager if not provided
            if context is None:
                try:
                    context = self.context_manager.assemble_context(
                        agent_id=agent_id,
                        max_tokens=100000
                    )
                except Exception as ctx_error:
                    # If context assembly fails, log but continue with empty context
                    self.console.print(f"[yellow]Warning: Could not assemble context: {ctx_error}[/yellow]")
                    context = {}

            # Run agent
            result = self.agent_runner.run_agent(
                agent_id=agent_id,
                user_input=user_input,
                context=context,
            )

            # Display result
            self._display_result(result)

            # Validate output
            validation_result = self.output_validator.validate(
                agent_id=agent_id,
                output_content=result["content"]
            )

            if validation_result["overall_status"] == "fail":
                # Log validation failure
                self.log_manager.log_validation(
                    execution_id=execution_id,
                    agent_id=agent_id,
                    status="fail",
                    errors=validation_result["errors"]
                )

                # Display validation errors
                self.console.print(f"[bold yellow]⚠ Validation failed:[/bold yellow]")
                for error in validation_result["errors"]:
                    self.console.print(f"  [yellow]•[/yellow] {error.get('message', str(error))}")

                result["validation_status"] = "failed"
                result["validation_errors"] = validation_result["errors"]
            else:
                result["validation_status"] = "passed"
                if validation_result["overall_status"] == "warn":
                    self.console.print(f"[yellow]⚠ Validation passed with warnings[/yellow]")

            # Save artifacts if requested
            if save_output:
                artifact_path = self.state_store.save_artifact(
                    agent_id=agent_id,
                    artifact_name=f"{agent_id}_output.md",
                    content=result["content"],
                )
                result["artifact_path"] = artifact_path

                # Store in Context Manager with versioning
                try:
                    artifacts_stored = self.context_manager.store_artifact(
                        agent_id=agent_id,
                        artifacts=[{
                            "name": f"{agent_id}_output.md",
                            "type": "markdown",
                            "content": result["content"],
                            "description": f"Output from {agent_id}"
                        }]
                    )
                    result["context_version"] = artifacts_stored["version"]
                except Exception as store_error:
                    self.console.print(f"[yellow]Warning: Could not store in Context Manager: {store_error}[/yellow]")

            # Record execution completion
            self.state_store.record_execution(
                agent_id=agent_id,
                status="completed",
                result=result,
            )

            # Record in Context Manager execution history
            try:
                self.context_manager.record_execution(
                    execution_id=execution_id,
                    agent_id=agent_id,
                    status="completed",
                    context_version=result.get("context_version", 1),
                    input_token_count=result.get("prompt_tokens", 0),
                    output_token_count=result.get("usage", {}).get("output_tokens", 0),
                    completed_at=None  # Will use current timestamp
                )
            except Exception as ctx_exec_error:
                # Non-critical error
                pass

            # Log execution completion
            self.log_manager.log_execution_complete(
                execution_id=execution_id,
                agent_id=agent_id,
                status="completed",
                tokens_in=result.get("usage", {}).get("input_tokens", 0),
                tokens_out=result.get("usage", {}).get("output_tokens", 0)
            )

            # Display success
            self.console.print(
                f"[bold green]✓[/bold green] Agent completed successfully"
            )
            self.console.print(
                f"[dim]Tokens - Input: {result['usage']['input_tokens']}, "
                f"Output: {result['usage']['output_tokens']}[/dim]"
            )

            if save_output:
                self.console.print(
                    f"[dim]Output saved to: {artifact_path}[/dim]"
                )

            return result

        except Exception as e:
            # Record execution failure
            self.state_store.record_execution(
                agent_id=agent_id,
                status="failed",
                error=str(e),
            )

            # Log execution error
            self.log_manager.log_execution_error(
                execution_id=execution_id,
                agent_id=agent_id,
                error=str(e),
                traceback=traceback.format_exc()
            )

            # Display error
            self.console.print(
                f"[bold red]✗[/bold red] Agent execution failed: {e}"
            )

            raise

    def _display_result(self, result: Dict[str, Any]):
        """Display agent result in formatted output."""
        content = result["content"]

        # Try to detect content type and format accordingly
        if content.strip().startswith("```yaml") or content.strip().startswith("```markdown"):
            # Extract code block
            lines = content.strip().split("\n")
            if lines[0].startswith("```"):
                language = lines[0].replace("```", "").strip() or "text"
                code = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                syntax = Syntax(code, language, theme="monokai", line_numbers=False)
                self.console.print(syntax)
            else:
                self.console.print(content)
        else:
            # Plain output
            self.console.print(Panel(content, title="Agent Output", border_style="green"))

    def get_execution_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> list:
        """Get execution history.

        Args:
            agent_id: Filter by agent (optional)
            limit: Maximum results

        Returns:
            List of execution records
        """
        return self.state_store.get_executions(agent_id=agent_id, limit=limit)

    def get_last_output(self, agent_id: str) -> Optional[str]:
        """Get last output from an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Last output content or None
        """
        return self.state_store.load_artifact(
            agent_id=agent_id,
            artifact_name=f"{agent_id}_output.md",
        )

"""
State Store

Simple state persistence for workflow execution.
Stores execution history and state as JSON files.

For MVP: File-based storage
Future: Migrate to SQLite as specified in context_manager.md
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class StateStore:
    """Manages workflow execution state."""

    def __init__(self, state_dir: str = "workflow"):
        """Initialize state store.

        Args:
            state_dir: Directory for state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.executions_file = self.state_dir / "executions.json"
        self.current_state_file = self.state_dir / "current_state.json"

        # Initialize files if they don't exist
        if not self.executions_file.exists():
            self._save_json(self.executions_file, [])

        if not self.current_state_file.exists():
            self._save_json(self.current_state_file, {
                "current_sprint": None,
                "current_phase": None,
                "last_execution_id": None,
            })

    def record_execution(
        self,
        agent_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> str:
        """Record an agent execution.

        Args:
            agent_id: Agent that was executed
            status: 'started', 'completed', 'failed'
            result: Execution result (if completed)
            error: Error message (if failed)

        Returns:
            Execution ID
        """
        # Load existing executions
        executions = self._load_json(self.executions_file)

        # Generate execution ID
        execution_id = f"exec_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create execution record
        execution = {
            "id": execution_id,
            "agent_id": agent_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "error": error,
        }

        # Append to executions
        executions.append(execution)

        # Save
        self._save_json(self.executions_file, executions)

        # Update current state
        self._update_current_state({"last_execution_id": execution_id})

        return execution_id

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            Execution record or None
        """
        executions = self._load_json(self.executions_file)
        for execution in executions:
            if execution["id"] == execution_id:
                return execution
        return None

    def get_executions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get executions with optional filters.

        Args:
            agent_id: Filter by agent ID
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of execution records
        """
        executions = self._load_json(self.executions_file)

        # Apply filters
        filtered = executions
        if agent_id:
            filtered = [e for e in filtered if e["agent_id"] == agent_id]
        if status:
            filtered = [e for e in filtered if e["status"] == status]

        # Sort by timestamp (newest first) and limit
        filtered.sort(key=lambda e: e["timestamp"], reverse=True)
        return filtered[:limit]

    def get_current_state(self) -> Dict[str, Any]:
        """Get current workflow state.

        Returns:
            Current state dict
        """
        return self._load_json(self.current_state_file)

    def update_current_state(self, updates: Dict[str, Any]):
        """Update current workflow state.

        Args:
            updates: State updates to apply
        """
        self._update_current_state(updates)

    def save_artifact(
        self,
        agent_id: str,
        artifact_name: str,
        content: str,
    ) -> str:
        """Save an agent artifact.

        Args:
            agent_id: Agent that produced the artifact
            artifact_name: Name of the artifact
            content: Artifact content

        Returns:
            Path to saved artifact
        """
        # Create artifacts directory
        artifacts_dir = self.state_dir / "artifacts" / agent_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Save artifact
        artifact_path = artifacts_dir / artifact_name
        with open(artifact_path, 'w') as f:
            f.write(content)

        return str(artifact_path)

    def load_artifact(
        self,
        agent_id: str,
        artifact_name: str,
    ) -> Optional[str]:
        """Load an agent artifact.

        Args:
            agent_id: Agent that produced the artifact
            artifact_name: Name of the artifact

        Returns:
            Artifact content or None if not found
        """
        artifact_path = self.state_dir / "artifacts" / agent_id / artifact_name
        if not artifact_path.exists():
            return None

        with open(artifact_path, 'r') as f:
            return f.read()

    def _load_json(self, file_path: Path) -> Any:
        """Load JSON from file."""
        with open(file_path, 'r') as f:
            return json.load(f)

    def _save_json(self, file_path: Path, data: Any):
        """Save data as JSON to file."""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _update_current_state(self, updates: Dict[str, Any]):
        """Update current state with given updates."""
        state = self._load_json(self.current_state_file)
        state.update(updates)
        self._save_json(self.current_state_file, state)

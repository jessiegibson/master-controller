"""
Context Manager - Manages shared context, artifacts, and execution history.

Provides SQLite-based storage for:
- Project context (shared state)
- Artifact metadata with versioning
- Execution history and audit trail
- Access control per agent
- Token budget management for context assembly
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3
import json
import hashlib
from datetime import datetime


class ContextManager:
    """Manages shared context, artifacts, and execution history for the orchestrator."""

    def __init__(self, context_dir: str = "context"):
        """Initialize Context Manager.

        Args:
            context_dir: Directory for context database and artifacts
        """
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.context_dir / "context.db"
        self.artifacts_dir = self.context_dir / "artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)

        # Initialize database
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory.

        Returns:
            SQLite connection with Row factory
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
        return conn

    def _init_database(self):
        """Initialize SQLite database with full schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # ============================================
            # Project Context (shared state)
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_context (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT NOT NULL CHECK(value_type IN ('string', 'integer', 'boolean', 'json')),
                    description TEXT,
                    updated_by TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Initialize with defaults if empty
            cursor.execute("SELECT COUNT(*) as count FROM project_context")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany("""
                    INSERT INTO project_context (key, value, value_type, description, updated_by)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    ('project_name', 'Finance CLI', 'string', 'Project name', 'system'),
                    ('current_sprint', 'S1-01', 'string', 'Active sprint ID', 'system'),
                    ('current_phase', 'planning', 'string', 'Current phase', 'system'),
                    ('context_version', '1', 'integer', 'Current context version', 'system'),
                ])

            # ============================================
            # Artifacts (metadata only, files on disk)
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL CHECK(artifact_type IN ('yaml', 'markdown', 'code', 'json', 'text')),
                    name TEXT NOT NULL,
                    description TEXT,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    token_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(agent_id, name, version)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_agent ON artifacts(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_version ON artifacts(version)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type)")

            # ============================================
            # Artifact Dependencies
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artifact_dependencies (
                    artifact_id TEXT NOT NULL,
                    depends_on_artifact_id TEXT NOT NULL,
                    dependency_type TEXT NOT NULL CHECK(dependency_type IN ('required', 'optional', 'reference')),
                    PRIMARY KEY (artifact_id, depends_on_artifact_id),
                    FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
                    FOREIGN KEY (depends_on_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
                )
            """)

            # ============================================
            # Context Versions
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_versions (
                    version INTEGER PRIMARY KEY,
                    description TEXT,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parent_version INTEGER,
                    FOREIGN KEY (parent_version) REFERENCES context_versions(version)
                )
            """)

            # Initialize with version 1 if empty
            cursor.execute("SELECT COUNT(*) as count FROM context_versions")
            if cursor.fetchone()["count"] == 0:
                cursor.execute("""
                    INSERT INTO context_versions (version, description, created_by)
                    VALUES (1, 'Initial context', 'system')
                """)

            # ============================================
            # Execution History
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    task_id TEXT,
                    sprint_id TEXT,
                    status TEXT NOT NULL CHECK(status IN ('started', 'completed', 'failed')),
                    context_version INTEGER NOT NULL,
                    input_artifacts TEXT,
                    input_token_count INTEGER,
                    output_artifacts TEXT,
                    output_token_count INTEGER,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    duration_seconds REAL,
                    error_message TEXT,
                    FOREIGN KEY (context_version) REFERENCES context_versions(version)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_agent ON execution_history(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_task ON execution_history(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_sprint ON execution_history(sprint_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_status ON execution_history(status)")

            # ============================================
            # Access Control
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS access_control (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL CHECK(resource_type IN ('artifact', 'context', 'history')),
                    resource_pattern TEXT NOT NULL,
                    permission TEXT NOT NULL CHECK(permission IN ('read', 'write', 'none')),
                    priority INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(agent_id, resource_type, resource_pattern)
                )
            """)

            # Default access rules if empty
            cursor.execute("SELECT COUNT(*) as count FROM access_control")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany("""
                    INSERT OR IGNORE INTO access_control (agent_id, resource_type, resource_pattern, permission, priority)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    ('*', 'artifact', 'self', 'read', 1),
                    ('*', 'artifact', 'self', 'write', 1),
                    ('workflow_orchestrator', 'artifact', '*', 'read', 10),
                    ('workflow_orchestrator', 'artifact', '*', 'write', 10),
                    ('workflow_orchestrator', 'context', '*', 'read', 10),
                    ('workflow_orchestrator', 'context', '*', 'write', 10),
                    ('project_manager', 'artifact', '*', 'read', 20),
                    ('project_manager', 'context', '*', 'read', 20),
                    ('project_manager', 'history', '*', 'read', 20),
                    ('staff_engineer_rust', 'artifact', '*', 'read', 30),
                    ('staff_engineer_python', 'artifact', '*', 'read', 30),
                    ('debugger', 'artifact', '*', 'read', 30),
                    ('debugger', 'history', '*', 'read', 30),
                ])

            # ============================================
            # Context Summaries (cached)
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_summaries (
                    artifact_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    summary_token_count INTEGER NOT NULL,
                    original_token_count INTEGER NOT NULL,
                    compression_ratio REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
                )
            """)

            # ============================================
            # Agent Context Requirements
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_context_requirements (
                    agent_id TEXT NOT NULL,
                    required_artifact_pattern TEXT NOT NULL,
                    requirement_type TEXT NOT NULL CHECK(requirement_type IN ('required', 'optional', 'if_exists')),
                    max_tokens INTEGER,
                    use_summary BOOLEAN DEFAULT 0,
                    priority INTEGER DEFAULT 100,
                    PRIMARY KEY (agent_id, required_artifact_pattern)
                )
            """)

            # Initialize with default requirements if empty
            cursor.execute("SELECT COUNT(*) as count FROM agent_context_requirements")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany("""
                    INSERT OR IGNORE INTO agent_context_requirements (agent_id, required_artifact_pattern, requirement_type, priority)
                    VALUES (?, ?, ?, ?)
                """, [
                    ('requirements_gatherer', 'project_context', 'required', 1),
                    ('system_architect', 'requirements_gatherer/*', 'required', 1),
                    ('system_architect', 'project_context', 'required', 2),
                    ('data_architect', 'requirements_gatherer/*', 'required', 1),
                    ('data_architect', 'system_architect/*', 'required', 2),
                    ('parser_developer', 'system_architect/*', 'required', 1),
                    ('parser_developer', 'data_architect/*', 'required', 2),
                    ('parser_developer', 'cli_ux_designer/*', 'optional', 3),
                    ('code_reviewer', 'system_architect/*', 'optional', 1),
                    ('code_reviewer', 'task_context', 'required', 2),
                    ('debugger', 'error_context', 'required', 1),
                    ('debugger', 'execution_history', 'optional', 2),
                ])

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to initialize database: {e}")
        finally:
            conn.close()

    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content.

        Args:
            content: Content to hash

        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count (4 chars per token).

        Args:
            content: Content to estimate

        Returns:
            Estimated token count
        """
        return len(content) // 4

    def get_project_context(self) -> Dict[str, Any]:
        """Get all project context key-value pairs.

        Returns:
            Dict of context keys and values
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT key, value, value_type FROM project_context")
            context = {}

            for row in cursor.fetchall():
                key = row["key"]
                value = row["value"]
                value_type = row["value_type"]

                # Convert based on type
                if value_type == "integer":
                    context[key] = int(value)
                elif value_type == "boolean":
                    context[key] = value.lower() == "true"
                elif value_type == "json":
                    context[key] = json.loads(value)
                else:
                    context[key] = value

            return context

        finally:
            conn.close()

    def update_project_context(self, updates: Dict[str, Any], updated_by: str):
        """Update project context.

        Args:
            updates: Dict of key-value pairs to update
            updated_by: Agent or user making update
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            for key, value in updates.items():
                # Determine value type
                if isinstance(value, bool):
                    value_type = "boolean"
                    value_str = str(value)
                elif isinstance(value, int):
                    value_type = "integer"
                    value_str = str(value)
                elif isinstance(value, (dict, list)):
                    value_type = "json"
                    value_str = json.dumps(value)
                else:
                    value_type = "string"
                    value_str = str(value)

                cursor.execute("""
                    INSERT OR REPLACE INTO project_context (key, value, value_type, updated_by, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, value_str, value_type, updated_by))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to update project context: {e}")
        finally:
            conn.close()

    # ========================================
    # Artifact Operations
    # ========================================

    def store_artifact(
        self,
        agent_id: str,
        artifacts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store agent artifacts with versioning.

        Args:
            agent_id: Agent that produced artifacts
            artifacts: List of artifact dicts with name, type, content, description

        Returns:
            Dict with version and artifact IDs
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get current version
            cursor.execute("SELECT value FROM project_context WHERE key = 'context_version'")
            version = int(cursor.fetchone()["value"])

            # Create version directory
            version_dir = self.artifacts_dir / f"v{version}" / agent_id
            version_dir.mkdir(parents=True, exist_ok=True)

            artifact_ids = []

            for artifact in artifacts:
                name = artifact["name"]
                artifact_type = artifact.get("type", "text")
                content = artifact["content"]
                description = artifact.get("description", "")

                # Calculate hash and tokens
                file_hash = self._calculate_hash(content)
                token_count = self._estimate_tokens(content)

                # Write file
                file_path = version_dir / name
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Store metadata
                artifact_id = f"{agent_id}_{name}_{version}"
                relative_path = f"v{version}/{agent_id}/{name}"

                cursor.execute("""
                    INSERT OR REPLACE INTO artifacts
                    (id, agent_id, artifact_type, name, description, file_path, file_hash, version, token_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (artifact_id, agent_id, artifact_type, name, description, relative_path, file_hash, version, token_count))

                artifact_ids.append(artifact_id)

            conn.commit()

            return {
                "version": version,
                "artifact_ids": artifact_ids,
                "artifact_count": len(artifact_ids)
            }

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to store artifacts: {e}")
        finally:
            conn.close()

    def get_artifact(
        self,
        agent_id: str,
        artifact_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve artifact by ID.

        Args:
            agent_id: Requesting agent (for access control)
            artifact_id: Artifact ID

        Returns:
            Artifact dict with content, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # TODO: Implement access control check
            # For MVP, allow all reads

            cursor.execute("""
                SELECT id, agent_id, artifact_type, name, description, file_path, file_hash, version, token_count, created_at
                FROM artifacts
                WHERE id = ?
            """, (artifact_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # Read file content
            file_path = self.artifacts_dir / row["file_path"]
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "id": row["id"],
                "agent_id": row["agent_id"],
                "artifact_type": row["artifact_type"],
                "name": row["name"],
                "description": row["description"],
                "file_path": row["file_path"],
                "file_hash": row["file_hash"],
                "version": row["version"],
                "token_count": row["token_count"],
                "created_at": row["created_at"],
                "content": content
            }

        finally:
            conn.close()

    def list_artifacts(
        self,
        agent_id: str,
        version: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List artifacts for an agent.

        Args:
            agent_id: Agent whose artifacts to list
            version: Specific version (None = current)

        Returns:
            List of artifact metadata dicts
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if version is None:
                # Get current version
                cursor.execute("SELECT value FROM project_context WHERE key = 'context_version'")
                version = int(cursor.fetchone()["value"])

            cursor.execute("""
                SELECT id, agent_id, artifact_type, name, description, file_path, version, token_count, created_at
                FROM artifacts
                WHERE agent_id = ? AND version = ?
                ORDER BY created_at DESC
            """, (agent_id, version))

            artifacts = []
            for row in cursor.fetchall():
                artifacts.append({
                    "id": row["id"],
                    "agent_id": row["agent_id"],
                    "artifact_type": row["artifact_type"],
                    "name": row["name"],
                    "description": row["description"],
                    "file_path": row["file_path"],
                    "version": row["version"],
                    "token_count": row["token_count"],
                    "created_at": row["created_at"]
                })

            return artifacts

        finally:
            conn.close()

    # ========================================
    # Context Assembly
    # ========================================

    def assemble_context(
        self,
        agent_id: str,
        task_id: Optional[str] = None,
        max_tokens: int = 100000
    ) -> Dict[str, Any]:
        """Assemble context for agent execution.

        Args:
            agent_id: Agent to assemble context for
            task_id: Optional task ID for task-specific context
            max_tokens: Token budget (reserve 5K for prompt, 2K for task = ~93K for artifacts)

        Returns:
            Context package dict with project_context, artifacts, metadata
        """
        # Reserve tokens for prompt and task
        available_tokens = max_tokens - 5000 - 2000  # ~93K for artifacts

        # Get project context
        project_context = self.get_project_context()

        # Get agent's context requirements
        requirements = self.get_context_requirements(agent_id)

        # Build context package
        context = {
            "project_name": project_context.get("project_name", "Unknown Project"),
            "current_sprint": project_context.get("current_sprint"),
            "current_phase": project_context.get("current_phase"),
            "context_version": project_context.get("context_version", 1),
            "artifacts": {},
            "metadata": {
                "agent_id": agent_id,
                "task_id": task_id,
                "max_tokens": max_tokens,
                "available_tokens": available_tokens,
                "assembled_at": datetime.now().isoformat()
            }
        }

        # For MVP: simple artifact loading without complex dependency resolution
        # Load artifacts from requirements if available
        token_count = 0

        for req in requirements:
            pattern = req["required_artifact_pattern"]
            req_type = req["requirement_type"]

            # Simple pattern matching: exact agent_id match
            if pattern == "project_context":
                # Already included
                continue

            # Extract agent_id from pattern (e.g., "requirements_gatherer/*" -> "requirements_gatherer")
            if "/*" in pattern:
                source_agent_id = pattern.split("/*")[0]
            else:
                source_agent_id = pattern

            # Get artifacts from that agent
            artifacts = self.list_artifacts(source_agent_id)

            for artifact in artifacts:
                # Check token budget
                if token_count + artifact["token_count"] > available_tokens:
                    if req_type == "required":
                        # Required artifact doesn't fit - warning but continue
                        context["metadata"]["warnings"] = context["metadata"].get("warnings", [])
                        context["metadata"]["warnings"].append(
                            f"Required artifact {artifact['id']} exceeds token budget"
                        )
                    break

                # Load full artifact with content
                full_artifact = self.get_artifact(agent_id, artifact["id"])
                if full_artifact:
                    context["artifacts"][artifact["id"]] = full_artifact
                    token_count += artifact["token_count"]

        context["metadata"]["tokens_used"] = token_count

        return context

    def get_context_requirements(
        self,
        agent_id: str
    ) -> List[Dict[str, Any]]:
        """Get context requirements for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of requirement dicts
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT agent_id, required_artifact_pattern, requirement_type, max_tokens, use_summary, priority
                FROM agent_context_requirements
                WHERE agent_id = ?
                ORDER BY priority ASC
            """, (agent_id,))

            requirements = []
            for row in cursor.fetchall():
                requirements.append({
                    "agent_id": row["agent_id"],
                    "required_artifact_pattern": row["required_artifact_pattern"],
                    "requirement_type": row["requirement_type"],
                    "max_tokens": row["max_tokens"],
                    "use_summary": bool(row["use_summary"]),
                    "priority": row["priority"]
                })

            return requirements

        finally:
            conn.close()

    # ========================================
    # Execution History
    # ========================================

    def record_execution(
        self,
        execution_id: str,
        agent_id: str,
        status: str,
        context_version: int,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        **kwargs
    ) -> str:
        """Record agent execution in history.

        Args:
            execution_id: Execution ID
            agent_id: Agent that executed
            status: started|completed|failed
            context_version: Context version used
            started_at: Start timestamp (ISO format)
            completed_at: Completion timestamp
            **kwargs: Additional fields (task_id, tokens, error, etc.)

        Returns:
            Execution ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Prepare timestamps
            if started_at is None:
                started_at = datetime.now().isoformat()

            # Calculate duration if completed
            duration_seconds = None
            if completed_at and started_at:
                start = datetime.fromisoformat(started_at)
                end = datetime.fromisoformat(completed_at)
                duration_seconds = (end - start).total_seconds()

            cursor.execute("""
                INSERT OR REPLACE INTO execution_history
                (id, agent_id, task_id, sprint_id, status, context_version,
                 input_artifacts, input_token_count, output_artifacts, output_token_count,
                 started_at, completed_at, duration_seconds, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                agent_id,
                kwargs.get("task_id"),
                kwargs.get("sprint_id"),
                status,
                context_version,
                json.dumps(kwargs.get("input_artifacts", [])),
                kwargs.get("input_token_count", 0),
                json.dumps(kwargs.get("output_artifacts", [])),
                kwargs.get("output_token_count", 0),
                started_at,
                completed_at,
                duration_seconds,
                kwargs.get("error_message")
            ))

            conn.commit()
            return execution_id

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to record execution: {e}")
        finally:
            conn.close()

    def query_history(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Query execution history.

        Args:
            filters: Dict with agent_id, status, sprint_id filters
            limit: Max results

        Returns:
            List of execution records
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM execution_history WHERE 1=1"
            params = []

            if filters:
                if "agent_id" in filters:
                    query += " AND agent_id = ?"
                    params.append(filters["agent_id"])
                if "status" in filters:
                    query += " AND status = ?"
                    params.append(filters["status"])
                if "sprint_id" in filters:
                    query += " AND sprint_id = ?"
                    params.append(filters["sprint_id"])

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            executions = []
            for row in cursor.fetchall():
                executions.append({
                    "id": row["id"],
                    "agent_id": row["agent_id"],
                    "task_id": row["task_id"],
                    "sprint_id": row["sprint_id"],
                    "status": row["status"],
                    "context_version": row["context_version"],
                    "input_artifacts": json.loads(row["input_artifacts"]) if row["input_artifacts"] else [],
                    "input_token_count": row["input_token_count"],
                    "output_artifacts": json.loads(row["output_artifacts"]) if row["output_artifacts"] else [],
                    "output_token_count": row["output_token_count"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "duration_seconds": row["duration_seconds"],
                    "error_message": row["error_message"]
                })

            return executions

        finally:
            conn.close()

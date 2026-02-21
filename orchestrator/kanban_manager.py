"""
Kanban Manager - Manages tasks, features, and agent assignments.

Provides SQLite-based task tracking with:
- Feature management
- Task state machine (todo → in-progress → in-qa → done)
- Blocker tracking with auto-status changes
- Agent workload management
- Execution history and metrics
- Workflow run and agent execution tracking
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3
import json
import uuid
from datetime import datetime, date


class KanbanManager:
    """Manages tasks, features, and agent assignments with state machine validation."""

    # State transition matrix
    VALID_TRANSITIONS = {
        'todo': ['in-progress'],
        'in-progress': ['todo', 'blocked', 'in-qa'],
        'blocked': ['todo', 'in-progress'],
        'in-qa': ['in-progress', 'done'],
        'done': [],  # Terminal state
    }

    def __init__(self, db_path: str = "kanban-cli/kanban/tasks.db"):
        """Initialize Kanban Manager.

        Args:
            db_path: Path to tasks database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

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
            # Features
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS features (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    color TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ============================================
            # Tasks
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    feature_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'todo',
                    priority INTEGER NOT NULL DEFAULT 100,
                    assigned_agent TEXT,
                    estimated_hours REAL,
                    actual_hours REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (feature_id) REFERENCES features(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_status ON features(status)")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_feature ON tasks(feature_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(assigned_agent)")

            # ============================================
            # Task Dependencies
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_task_id TEXT NOT NULL,
                    PRIMARY KEY (task_id, depends_on_task_id),
                    FOREIGN KEY (task_id) REFERENCES tasks(id),
                    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id)
                )
            """)

            # ============================================
            # Blockers
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blockers (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    blocking_task_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    escalated_at TIMESTAMP,
                    resolution_notes TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id),
                    FOREIGN KEY (blocking_task_id) REFERENCES tasks(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blockers_task ON blockers(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blockers_status ON blockers(status)")

            # ============================================
            # Agents Registry
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'available',
                    max_concurrent_tasks INTEGER DEFAULT 2,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Populate with all 31 agents if empty
            cursor.execute("SELECT COUNT(*) as count FROM agents")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany("""
                    INSERT INTO agents (id, name, type, status, max_concurrent_tasks)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    ('requirements_gatherer', 'Requirements Gatherer', 'specialist', 'available', 1),
                    ('product_roadmap_planner', 'Product Roadmap Planner', 'specialist', 'available', 1),
                    ('system_architect', 'System Architect', 'architect', 'available', 1),
                    ('data_architect', 'Data Architect', 'architect', 'available', 1),
                    ('security_architect', 'Security Architect', 'architect', 'available', 1),
                    ('ml_architect', 'ML Architect', 'architect', 'available', 1),
                    ('cli_ux_designer', 'CLI UX Designer', 'specialist', 'available', 1),
                    ('rust_scaffolder', 'Rust Scaffolder', 'developer', 'available', 1),
                    ('parser_developer', 'Parser Developer', 'developer', 'available', 2),
                    ('categorization_engine_developer', 'Categorization Developer', 'developer', 'available', 2),
                    ('duckdb_developer', 'DuckDB Developer', 'developer', 'available', 2),
                    ('encryption_developer', 'Encryption Developer', 'developer', 'available', 2),
                    ('cli_developer', 'CLI Developer', 'developer', 'available', 2),
                    ('ml_engineer', 'ML Engineer', 'developer', 'available', 2),
                    ('test_developer', 'Test Developer', 'developer', 'available', 2),
                    ('code_reviewer', 'Code Reviewer', 'reviewer', 'available', 3),
                    ('staff_engineer_rust', 'Staff Engineer Rust', 'reviewer', 'available', 2),
                    ('staff_engineer_python', 'Staff Engineer Python', 'reviewer', 'available', 2),
                    ('debugger', 'Debugger', 'specialist', 'available', 3),
                    ('project_manager', 'Project Manager', 'manager', 'available', 1),
                    ('repository_librarian', 'Repository Librarian', 'specialist', 'available', 2),
                    ('consulting_cpa', 'Consulting CPA', 'specialist', 'available', 1),
                    ('workflow_orchestrator', 'Workflow Orchestrator', 'manager', 'available', 1),
                    ('context_manager', 'Context Manager', 'specialist', 'available', 1),
                    ('kanban_manager', 'Kanban Manager', 'specialist', 'available', 1),
                    ('output_validator', 'Output Validator', 'specialist', 'available', 1),
                    ('documentation_writer', 'Documentation Writer', 'specialist', 'available', 1),
                    ('prompt_skill_engineer', 'Prompt Skill Engineer', 'specialist', 'available', 1),
                    ('infrastructure_agent', 'Infrastructure Agent', 'specialist', 'available', 1),
                    ('financial_calculator_developer', 'Financial Calculator Developer', 'developer', 'available', 2),
                ])

            # ============================================
            # Task History (audit trail)
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    field_changed TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_changed_at ON task_history(changed_at)")

            # ============================================
            # Task Comments
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_comments (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_task ON task_comments(task_id)")

            # ============================================
            # Workflow Runs
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    feature_id TEXT,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (feature_id) REFERENCES features(id)
                )
            """)

            # ============================================
            # Agent Executions
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id TEXT PRIMARY KEY,
                    workflow_run_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    task_id TEXT,
                    status TEXT NOT NULL,
                    attempt_number INTEGER DEFAULT 1,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    output_path TEXT,
                    output_valid BOOLEAN,
                    error_message TEXT,
                    context_token_count INTEGER,
                    response_token_count INTEGER,
                    duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id),
                    FOREIGN KEY (agent_id) REFERENCES agents(id),
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_workflow ON agent_executions(workflow_run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_agent ON agent_executions(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_status ON agent_executions(status)")

            # ============================================
            # Workflow Checkpoints
            # ============================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                    id TEXT PRIMARY KEY,
                    workflow_run_id TEXT NOT NULL,
                    checkpoint_type TEXT NOT NULL,
                    checkpoint_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id)
                )
            """)

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to initialize database: {e}")
        finally:
            conn.close()

    # ========================================
    # Task Operations
    # ========================================

    def create_task(
        self,
        feature_id: str,
        title: str,
        description: Optional[str] = None,
        priority: int = 100,
        estimated_hours: Optional[float] = None,
        dependencies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new task.

        Args:
            feature_id: Feature this task belongs to
            title: Task title
            description: Detailed description
            priority: Priority (lower = higher priority)
            estimated_hours: Time estimate
            dependencies: List of task IDs this depends on

        Returns:
            Task dict

        Raises:
            Exception: If feature doesn't exist or task creation fails
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Generate task ID
            task_id = self._generate_task_id(feature_id, cursor)

            # Insert task
            cursor.execute("""
                INSERT INTO tasks (id, feature_id, title, description, status, priority, estimated_hours)
                VALUES (?, ?, ?, ?, 'todo', ?, ?)
            """, (task_id, feature_id, title, description, priority, estimated_hours))

            # Insert dependencies if provided
            if dependencies:
                for dep_task_id in dependencies:
                    cursor.execute("""
                        INSERT INTO task_dependencies (task_id, depends_on_task_id)
                        VALUES (?, ?)
                    """, (task_id, dep_task_id))

            # Record creation in history
            cursor.execute("""
                INSERT INTO task_history (task_id, field_changed, new_value, changed_by)
                VALUES (?, 'created', 'todo', 'system')
            """, (task_id,))

            conn.commit()

            # Return created task
            return self.get_task(task_id)

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create task: {e}")
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID with full details.

        Args:
            task_id: Task ID

        Returns:
            Task dict with dependencies, blockers, history
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, feature_id, title, description, status, priority, assigned_agent,
                       estimated_hours, actual_hours, created_at, updated_at, started_at, completed_at
                FROM tasks
                WHERE id = ?
            """, (task_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # Get dependencies
            cursor.execute("""
                SELECT depends_on_task_id
                FROM task_dependencies
                WHERE task_id = ?
            """, (task_id,))
            dependencies = [r["depends_on_task_id"] for r in cursor.fetchall()]

            # Get active blockers
            cursor.execute("""
                SELECT id, type, description, status, created_at
                FROM blockers
                WHERE task_id = ? AND status = 'active'
            """, (task_id,))
            blockers = [dict(r) for r in cursor.fetchall()]

            return {
                "id": row["id"],
                "feature_id": row["feature_id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "priority": row["priority"],
                "assigned_agent": row["assigned_agent"],
                "estimated_hours": row["estimated_hours"],
                "actual_hours": row["actual_hours"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "dependencies": dependencies,
                "blockers": blockers
            }

        finally:
            conn.close()

    def update_task_status(
        self,
        task_id: str,
        new_status: str,
        changed_by: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update task status with validation.

        Args:
            task_id: Task ID
            new_status: New status
            changed_by: Agent or user making change
            comment: Optional comment

        Returns:
            Success dict or error dict with code and message
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get current task
            cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return {
                    "success": False,
                    "error_code": "NOT_FOUND",
                    "message": f"Task {task_id} not found"
                }

            current_status = row["status"]

            # Validate transition
            if not self.is_valid_transition(current_status, new_status):
                return {
                    "success": False,
                    "error_code": "INVALID_TRANSITION",
                    "message": f"Cannot transition from '{current_status}' to '{new_status}'",
                    "current_status": current_status,
                    "requested_status": new_status,
                    "valid_transitions": self.VALID_TRANSITIONS.get(current_status, [])
                }

            # Update task
            update_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [new_status]

            if new_status == "in-progress" and current_status == "todo":
                update_fields.append("started_at = CURRENT_TIMESTAMP")
            elif new_status == "done":
                update_fields.append("completed_at = CURRENT_TIMESTAMP")

            update_fields.append("WHERE id = ?")
            params.append(task_id)

            cursor.execute(f"UPDATE tasks SET {', '.join(update_fields)}", params)

            # Record in history
            cursor.execute("""
                INSERT INTO task_history (task_id, field_changed, old_value, new_value, changed_by)
                VALUES (?, 'status', ?, ?, ?)
            """, (task_id, current_status, new_status, changed_by))

            # Add comment if provided
            if comment:
                comment_id = f"{task_id}_comment_{int(datetime.now().timestamp())}"
                cursor.execute("""
                    INSERT INTO task_comments (id, task_id, author, content)
                    VALUES (?, ?, ?, ?)
                """, (comment_id, task_id, changed_by, comment))

            conn.commit()

            return {
                "success": True,
                "task_id": task_id,
                "old_status": current_status,
                "new_status": new_status,
                "changed_by": changed_by
            }

        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error_code": "DATABASE_ERROR",
                "message": str(e)
            }
        finally:
            conn.close()

    def assign_task(
        self,
        task_id: str,
        agent_id: str,
        changed_by: str
    ) -> Dict[str, Any]:
        """Assign task to agent.

        Args:
            task_id: Task ID
            agent_id: Agent to assign to
            changed_by: Who is making the assignment

        Returns:
            Updated task dict
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Check agent exists
            cursor.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
            if not cursor.fetchone():
                raise Exception(f"Agent {agent_id} not found")

            # Get current assignment
            cursor.execute("SELECT assigned_agent FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise Exception(f"Task {task_id} not found")

            old_agent = row["assigned_agent"]

            # Update assignment
            cursor.execute("""
                UPDATE tasks
                SET assigned_agent = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (agent_id, task_id))

            # Record in history
            cursor.execute("""
                INSERT INTO task_history (task_id, field_changed, old_value, new_value, changed_by)
                VALUES (?, 'assigned_agent', ?, ?, ?)
            """, (task_id, old_agent, agent_id, changed_by))

            conn.commit()

            return self.get_task(task_id)

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to assign task: {e}")
        finally:
            conn.close()

    # ========================================
    # Blocker Operations
    # ========================================

    def add_blocker(
        self,
        task_id: str,
        type: str,
        description: str,
        blocking_task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add blocker to task.

        Args:
            task_id: Task being blocked
            type: Blocker type (dependency|technical|clarification|etc)
            description: What's blocking
            blocking_task_id: Optional task that's blocking

        Returns:
            Dict with blocker and updated task
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Generate blocker ID
            blocker_id = f"{task_id}_blocker_{int(datetime.now().timestamp())}"

            # Insert blocker
            cursor.execute("""
                INSERT INTO blockers (id, task_id, type, description, blocking_task_id, status)
                VALUES (?, ?, ?, ?, ?, 'active')
            """, (blocker_id, task_id, type, description, blocking_task_id))

            # Auto-transition task to 'blocked' status
            cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
            current_status = cursor.fetchone()["status"]

            if current_status != "blocked":
                cursor.execute("""
                    UPDATE tasks
                    SET status = 'blocked', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (task_id,))

                # Record status change
                cursor.execute("""
                    INSERT INTO task_history (task_id, field_changed, old_value, new_value, changed_by)
                    VALUES (?, 'status', ?, 'blocked', 'system')
                """, (task_id, current_status))

            conn.commit()

            return {
                "blocker_id": blocker_id,
                "task": self.get_task(task_id)
            }

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to add blocker: {e}")
        finally:
            conn.close()

    def resolve_blocker(
        self,
        blocker_id: str,
        resolution_notes: str,
        resolved_by: str = "system"
    ) -> Dict[str, Any]:
        """Resolve a blocker.

        Args:
            blocker_id: Blocker ID
            resolution_notes: How it was resolved
            resolved_by: Who resolved it

        Returns:
            Dict with resolved blocker and task
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get blocker
            cursor.execute("SELECT task_id FROM blockers WHERE id = ?", (blocker_id,))
            row = cursor.fetchone()
            if not row:
                raise Exception(f"Blocker {blocker_id} not found")

            task_id = row["task_id"]

            # Update blocker
            cursor.execute("""
                UPDATE blockers
                SET status = 'resolved', resolution_notes = ?, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (resolution_notes, blocker_id))

            # Check if all blockers for task are resolved
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM blockers
                WHERE task_id = ? AND status = 'active'
            """, (task_id,))

            active_blockers = cursor.fetchone()["count"]

            # If no more active blockers, auto-transition to 'in-progress'
            if active_blockers == 0:
                cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
                current_status = cursor.fetchone()["status"]

                if current_status == "blocked":
                    cursor.execute("""
                        UPDATE tasks
                        SET status = 'in-progress', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (task_id,))

                    # Record status change
                    cursor.execute("""
                        INSERT INTO task_history (task_id, field_changed, old_value, new_value, changed_by)
                        VALUES (?, 'status', 'blocked', 'in-progress', ?)
                    """, (task_id, resolved_by))

            conn.commit()

            return {
                "blocker_id": blocker_id,
                "task": self.get_task(task_id)
            }

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to resolve blocker: {e}")
        finally:
            conn.close()

    def get_active_blockers(
        self,
        feature_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all active blockers.

        Args:
            feature_id: Filter by feature

        Returns:
            List of blocker dicts with task info
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if feature_id:
                cursor.execute("""
                    SELECT b.id, b.task_id, b.type, b.description, b.blocking_task_id,
                           b.status, b.created_at, t.title as task_title
                    FROM blockers b
                    JOIN tasks t ON b.task_id = t.id
                    WHERE b.status = 'active' AND t.feature_id = ?
                    ORDER BY b.created_at DESC
                """, (feature_id,))
            else:
                cursor.execute("""
                    SELECT b.id, b.task_id, b.type, b.description, b.blocking_task_id,
                           b.status, b.created_at, t.title as task_title
                    FROM blockers b
                    JOIN tasks t ON b.task_id = t.id
                    WHERE b.status = 'active'
                    ORDER BY b.created_at DESC
                """)

            blockers = []
            for row in cursor.fetchall():
                blockers.append(dict(row))

            return blockers

        finally:
            conn.close()

    # ========================================
    # Feature Operations
    # ========================================

    def get_feature(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """Get feature with task counts.

        Args:
            feature_id: Feature ID

        Returns:
            Feature dict with task breakdowns
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, description, status, color, created_at, updated_at
                FROM features
                WHERE id = ?
            """, (feature_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # Get task counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM tasks
                WHERE feature_id = ?
                GROUP BY status
            """, (feature_id,))

            task_counts = {r["status"]: r["count"] for r in cursor.fetchall()}

            return {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "status": row["status"],
                "color": row["color"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "task_counts": task_counts,
                "total_tasks": sum(task_counts.values())
            }

        finally:
            conn.close()

    def get_feature_metrics(self, feature_id: str) -> Dict[str, Any]:
        """Calculate feature metrics.

        Args:
            feature_id: Feature ID

        Returns:
            Metrics dict with completion rate, velocity, burndown
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get task counts
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
                    SUM(estimated_hours) as total_estimated,
                    SUM(CASE WHEN status = 'done' THEN actual_hours ELSE 0 END) as total_actual
                FROM tasks
                WHERE feature_id = ?
            """, (feature_id,))

            row = cursor.fetchone()

            total = row["total"] or 0
            done = row["done"] or 0
            blocked = row["blocked"] or 0
            completion_rate = (done / total * 100) if total > 0 else 0

            return {
                "feature_id": feature_id,
                "total_tasks": total,
                "completed_tasks": done,
                "blocked_tasks": blocked,
                "completion_rate": round(completion_rate, 2),
                "total_estimated_hours": row["total_estimated"] or 0,
                "total_actual_hours": row["total_actual"] or 0
            }

        finally:
            conn.close()

    # ========================================
    # Agent Operations
    # ========================================

    def get_agent_workload(self, agent_id: str) -> Dict[str, Any]:
        """Get agent's current workload.

        Args:
            agent_id: Agent ID

        Returns:
            Dict with agent info, current tasks, stats
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get agent info
            cursor.execute("""
                SELECT id, name, type, status, max_concurrent_tasks
                FROM agents
                WHERE id = ?
            """, (agent_id,))

            agent = dict(cursor.fetchone())

            # Get current tasks
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE assigned_agent = ? AND status IN ('todo', 'in-progress', 'blocked', 'in-qa')
            """, (agent_id,))

            current_tasks = cursor.fetchone()["count"]

            agent["current_tasks"] = current_tasks
            agent["available_capacity"] = agent["max_concurrent_tasks"] - current_tasks
            agent["at_capacity"] = current_tasks >= agent["max_concurrent_tasks"]

            return agent

        finally:
            conn.close()

    # ========================================
    # Query Operations
    # ========================================

    def query_tasks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "priority",
        sort_order: str = "asc",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query tasks with filters.

        Args:
            filters: Dict with feature_id, status, assigned_agent filters
            sort_by: Field to sort by
            sort_order: asc or desc
            limit: Max results

        Returns:
            List of task dicts
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []

            if filters:
                if "feature_id" in filters:
                    query += " AND feature_id = ?"
                    params.append(filters["feature_id"])
                if "status" in filters:
                    query += " AND status = ?"
                    params.append(filters["status"])
                if "assigned_agent" in filters:
                    query += " AND assigned_agent = ?"
                    params.append(filters["assigned_agent"])

            query += f" ORDER BY {sort_by} {sort_order.upper()} LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            tasks = []
            for row in cursor.fetchall():
                tasks.append(dict(row))

            return tasks

        finally:
            conn.close()

    # ========================================
    # Workflow Run Operations
    # ========================================

    def create_workflow_run(self, feature_id: Optional[str] = None) -> str:
        """Create a new workflow run.

        Args:
            feature_id: Optional feature this run belongs to

        Returns:
            Workflow run ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            run_id = f"wfr_{uuid.uuid4().hex[:12]}"
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO workflow_runs (id, feature_id, status, started_at)
                VALUES (?, ?, 'running', ?)
            """, (run_id, feature_id, now))

            conn.commit()
            return run_id

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create workflow run: {e}")
        finally:
            conn.close()

    def complete_workflow_run(
        self,
        run_id: str,
        status: str = "completed",
        error_message: Optional[str] = None
    ):
        """Complete a workflow run.

        Args:
            run_id: Workflow run ID
            status: Final status (completed or failed)
            error_message: Error message if failed
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE workflow_runs
                SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
            """, (status, error_message, run_id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to complete workflow run: {e}")
        finally:
            conn.close()

    def get_or_create_active_workflow_run(self) -> str:
        """Get the latest running workflow run, or create one.

        Returns:
            Workflow run ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id FROM workflow_runs
                WHERE status = 'running'
                ORDER BY started_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return row["id"]
        finally:
            conn.close()

        return self.create_workflow_run()

    # ========================================
    # Agent Execution Operations
    # ========================================

    def start_agent_execution(
        self,
        workflow_run_id: str,
        agent_id: str,
        task_id: Optional[str] = None
    ) -> str:
        """Record the start of an agent execution.

        Args:
            workflow_run_id: Parent workflow run
            agent_id: Agent being executed
            task_id: Optional associated task

        Returns:
            Execution ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            execution_id = f"exec_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            cursor.execute("""
                INSERT INTO agent_executions
                    (id, workflow_run_id, agent_id, task_id, status, started_at)
                VALUES (?, ?, ?, ?, 'running', CURRENT_TIMESTAMP)
            """, (execution_id, workflow_run_id, agent_id, task_id))

            conn.commit()
            return execution_id

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to start agent execution: {e}")
        finally:
            conn.close()

    def complete_agent_execution(
        self,
        execution_id: str,
        status: str,
        output_path: Optional[str] = None,
        output_valid: Optional[bool] = None,
        error_message: Optional[str] = None,
        context_token_count: Optional[int] = None,
        response_token_count: Optional[int] = None,
        duration_seconds: Optional[float] = None,
    ):
        """Record the completion of an agent execution.

        Args:
            execution_id: Execution to update
            status: Final status (completed or failed)
            output_path: Path to output artifact
            output_valid: Whether output passed validation
            error_message: Error message if failed
            context_token_count: Input tokens used
            response_token_count: Output tokens used
            duration_seconds: Execution duration
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE agent_executions
                SET status = ?,
                    completed_at = CURRENT_TIMESTAMP,
                    output_path = ?,
                    output_valid = ?,
                    error_message = ?,
                    context_token_count = ?,
                    response_token_count = ?,
                    duration_seconds = ?
                WHERE id = ?
            """, (
                status, output_path, output_valid, error_message,
                context_token_count, response_token_count, duration_seconds,
                execution_id
            ))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to complete agent execution: {e}")
        finally:
            conn.close()

    def get_agent_executions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Query agent executions with optional filters.

        Args:
            agent_id: Filter by agent
            status: Filter by status
            limit: Max results

        Returns:
            List of execution dicts
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM agent_executions WHERE 1=1"
            params: list = []

            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    def get_current_workflow_state(self) -> Dict[str, Any]:
        """Derive current workflow state from DB data.

        Returns:
            Dict with completed_agents, next_agents, current_phase, last_execution
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get completed agents
            cursor.execute("""
                SELECT DISTINCT agent_id FROM agent_executions
                WHERE status = 'completed'
            """)
            completed_agents = [row["agent_id"] for row in cursor.fetchall()]

            # Get last execution
            cursor.execute("""
                SELECT * FROM agent_executions
                ORDER BY started_at DESC
                LIMIT 1
            """)
            last_exec_row = cursor.fetchone()
            last_execution = dict(last_exec_row) if last_exec_row else None

            # Get task summary
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
            """)
            task_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            # Get latest workflow run
            cursor.execute("""
                SELECT id, status FROM workflow_runs
                ORDER BY started_at DESC
                LIMIT 1
            """)
            run_row = cursor.fetchone()
            latest_run = dict(run_row) if run_row else None

            return {
                "completed_agents": completed_agents,
                "task_counts": task_counts,
                "last_execution": last_execution,
                "latest_workflow_run": latest_run,
            }

        finally:
            conn.close()

    # ========================================
    # Validation
    # ========================================

    def is_valid_transition(
        self,
        from_status: str,
        to_status: str
    ) -> bool:
        """Check if status transition is valid.

        Args:
            from_status: Current status
            to_status: Desired status

        Returns:
            True if transition is valid
        """
        return to_status in self.VALID_TRANSITIONS.get(from_status, [])

    def _generate_task_id(self, feature_id: str, cursor) -> str:
        """Generate next task ID for feature.

        Args:
            feature_id: Feature ID
            cursor: Database cursor

        Returns:
            Task ID in format T-{feature_id}-{sequence}
        """
        cursor.execute("""
            SELECT id FROM tasks
            WHERE feature_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (feature_id,))

        row = cursor.fetchone()
        if row:
            # Extract sequence from last task ID
            last_id = row["id"]
            parts = last_id.split("-")
            if len(parts) == 3:
                sequence = int(parts[2]) + 1
            else:
                sequence = 1
        else:
            sequence = 1

        return f"T-{feature_id}-{sequence:03d}"

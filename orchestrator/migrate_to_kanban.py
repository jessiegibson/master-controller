"""
Migration script: Backfill kanban DB with historical data from StateStore JSON files.

Reads workflow/current_state.json and workflow/executions.json, then populates
the kanban-cli/kanban/tasks.db with features, tasks, workflow_runs, and agent_executions.

Usage:
    python -m orchestrator.migrate_to_kanban [--dry-run]
"""

import argparse
import json
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


# Agent-to-phase mapping (matches CLAUDE.md workflow phases)
AGENT_PHASES = {
    "requirements_gatherer": "planning",
    "product_roadmap_planner": "planning",
    "system_architect": "architecture",
    "data_architect": "architecture",
    "security_architect": "architecture",
    "ml_architect": "architecture",
    "cli_ux_designer": "design",
    "consulting_cpa": "design",
    "rust_scaffolder": "scaffolding",
    "repository_librarian": "scaffolding",
    "infrastructure_agent": "scaffolding",
    "duckdb_developer": "development",
    "duckdb_integration_developer": "development",  # alias used in executions
    "parser_developer": "development",
    "encryption_developer": "development",
    "categorization_engine_developer": "development",
    "financial_calculator_developer": "development",
    "ml_engineer": "development",
    "cli_developer": "development",
    "test_developer": "quality",
    "code_reviewer": "quality",
    "documentation_writer": "documentation",
}

# Phase feature IDs and names
PHASE_FEATURES = {
    "planning": ("phase-planning", "Planning", "Requirements gathering and roadmap planning"),
    "architecture": ("phase-architecture", "Architecture", "System, data, security, and ML architecture"),
    "design": ("phase-design", "Design", "CLI UX design and CPA consulting"),
    "scaffolding": ("phase-scaffolding", "Scaffolding", "Rust project scaffolding and repo setup"),
    "development": ("phase-development", "Development", "Core module implementation"),
    "quality": ("phase-quality", "Quality", "Testing and code review"),
    "documentation": ("phase-documentation", "Documentation", "Documentation writing"),
}

# All 31 agents from the project (minus support agents that don't have tasks)
TASK_AGENTS = [
    "requirements_gatherer",
    "product_roadmap_planner",
    "system_architect",
    "data_architect",
    "security_architect",
    "ml_architect",
    "cli_ux_designer",
    "consulting_cpa",
    "rust_scaffolder",
    "repository_librarian",
    "infrastructure_agent",
    "duckdb_developer",
    "parser_developer",
    "encryption_developer",
    "categorization_engine_developer",
    "financial_calculator_developer",
    "ml_engineer",
    "cli_developer",
    "test_developer",
    "code_reviewer",
    "documentation_writer",
]


def load_current_state(state_dir: Path) -> dict:
    state_file = state_dir / "current_state.json"
    if not state_file.exists():
        print(f"Warning: {state_file} not found")
        return {"completed_agents": []}
    with open(state_file) as f:
        return json.load(f)


def load_executions(state_dir: Path) -> list:
    exec_file = state_dir / "executions.json"
    if not exec_file.exists():
        print(f"Warning: {exec_file} not found")
        return []
    with open(exec_file) as f:
        return json.load(f)


def get_completed_agent_ids(current_state: dict) -> set:
    """Extract set of agent IDs that have completed from current_state."""
    completed = set()
    for entry in current_state.get("completed_agents", []):
        agent_id = entry.get("agent_id", "")
        # Normalize: duckdb_integration_developer -> duckdb_developer for task matching
        if agent_id == "duckdb_integration_developer":
            completed.add("duckdb_developer")
        elif agent_id == "implementation_orchestrator":
            # This is a meta-agent, skip for task purposes
            continue
        else:
            completed.add(agent_id)
    return completed


def pair_executions(executions: list) -> list:
    """Pair started+completed/failed records into single execution rows."""
    paired = []
    pending_starts = {}  # keyed by (agent_id, approximate_id)

    for rec in executions:
        agent_id = rec["agent_id"]
        status = rec["status"]
        rec_id = rec["id"]

        if status == "started":
            pending_starts[rec_id] = rec
        elif status in ("completed", "failed"):
            # Find matching start
            start_rec = pending_starts.pop(rec_id, None)
            if start_rec:
                paired.append({
                    "exec_id": rec_id,
                    "agent_id": agent_id,
                    "status": status,
                    "started_at": start_rec["timestamp"],
                    "completed_at": rec["timestamp"],
                    "result": rec.get("result"),
                    "error": rec.get("error"),
                })
            else:
                # No matching start found, record as standalone
                paired.append({
                    "exec_id": rec_id,
                    "agent_id": agent_id,
                    "status": status,
                    "started_at": rec["timestamp"],
                    "completed_at": rec["timestamp"],
                    "result": rec.get("result"),
                    "error": rec.get("error"),
                })

    return paired


def migrate(db_path: Path, state_dir: Path, dry_run: bool = False):
    current_state = load_current_state(state_dir)
    executions = load_executions(state_dir)
    completed_agents = get_completed_agent_ids(current_state)
    paired = pair_executions(executions)

    print(f"Source data:")
    print(f"  Completed agents in current_state: {len(completed_agents)}")
    print(f"  Execution records: {len(executions)}")
    print(f"  Paired executions: {len(paired)}")
    print(f"  Target DB: {db_path}")
    print()

    if dry_run:
        print("=== DRY RUN - no changes will be made ===\n")

    # Backup DB
    if not dry_run and db_path.exists():
        backup_path = db_path.with_suffix(f".db.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(db_path, backup_path)
        print(f"Backed up DB to: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # ============================
        # 1. Create phase features
        # ============================
        print("\n--- Features ---")
        existing_features = {row["id"] for row in cursor.execute("SELECT id FROM features").fetchall()}

        for phase, (fid, name, desc) in PHASE_FEATURES.items():
            if fid in existing_features:
                print(f"  [skip] Feature '{fid}' already exists")
            else:
                print(f"  [add]  Feature '{fid}' - {name}")
                if not dry_run:
                    cursor.execute("""
                        INSERT OR IGNORE INTO features (id, name, description, status)
                        VALUES (?, ?, ?, 'active')
                    """, (fid, name, desc))

        # ============================
        # 2. Create/update agent tasks
        # ============================
        print("\n--- Tasks ---")
        existing_tasks = {}
        for row in cursor.execute("SELECT id, assigned_agent, status FROM tasks").fetchall():
            existing_tasks[row["id"]] = dict(row)
            if row["assigned_agent"]:
                existing_tasks[row["assigned_agent"]] = dict(row)

        # Map existing stale tasks from mvp-phase-1 to their correct status
        stale_task_fixes = {
            "S1-02": "done",  # system_architect completed
            "S1-03": "done",  # rust_scaffolder completed
            "S1-04": "done",  # security_architect completed
            "S1-05": "done",  # data_architect completed
            "S1-06": "done",  # cli_ux_designer completed
        }

        for task_id, new_status in stale_task_fixes.items():
            if task_id in existing_tasks:
                old_status = existing_tasks[task_id]["status"]
                if old_status != new_status:
                    print(f"  [fix]  Task '{task_id}': {old_status} -> {new_status}")
                    if not dry_run:
                        cursor.execute("""
                            UPDATE tasks SET status = ?, completed_at = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (new_status, "2026-01-20", task_id))

        # Create tasks for all 21 development agents
        completed_dates = {}
        for entry in current_state.get("completed_agents", []):
            aid = entry.get("agent_id", "")
            if aid == "duckdb_integration_developer":
                aid = "duckdb_developer"
            completed_dates[aid] = entry.get("completed_at", "2026-01-20")

        tasks_created = 0
        tasks_skipped = 0
        for agent_id in TASK_AGENTS:
            phase = AGENT_PHASES.get(agent_id)
            if not phase:
                continue
            feature_id = PHASE_FEATURES[phase][0]
            task_id = f"agent-{agent_id}"
            title = f"Run {agent_id.replace('_', ' ').title()}"

            # Check if task already exists (by ID or by assigned_agent)
            if task_id in existing_tasks or agent_id in existing_tasks:
                tasks_skipped += 1
                continue

            is_done = agent_id in completed_agents
            status = "done" if is_done else "todo"
            completed_at = completed_dates.get(agent_id) if is_done else None

            print(f"  [add]  Task '{task_id}' ({status}) -> feature '{feature_id}'")
            tasks_created += 1
            if not dry_run:
                cursor.execute("""
                    INSERT OR IGNORE INTO tasks
                        (id, feature_id, title, description, status, priority, assigned_agent, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id, feature_id, title,
                    f"Execute {agent_id} agent",
                    status, 100, agent_id, completed_at
                ))

        print(f"  Summary: {tasks_created} created, {tasks_skipped} skipped")

        # ============================
        # 3. Create workflow run
        # ============================
        print("\n--- Workflow Runs ---")
        existing_runs = cursor.execute("SELECT COUNT(*) as c FROM workflow_runs").fetchone()["c"]
        if existing_runs > 0:
            print(f"  [skip] {existing_runs} workflow run(s) already exist")
            cursor.execute("SELECT id FROM workflow_runs ORDER BY started_at DESC LIMIT 1")
            wf_run_id = cursor.fetchone()["id"]
        else:
            wf_run_id = f"wfr_migration_{datetime.now().strftime('%Y%m%d')}"
            # Use the earliest execution timestamp as start
            earliest = min((p["started_at"] for p in paired), default=datetime.now().isoformat())
            latest = max((p["completed_at"] for p in paired), default=datetime.now().isoformat())
            print(f"  [add]  Workflow run '{wf_run_id}' (completed)")
            if not dry_run:
                cursor.execute("""
                    INSERT INTO workflow_runs (id, feature_id, status, started_at, completed_at)
                    VALUES (?, ?, 'completed', ?, ?)
                """, (wf_run_id, "phase-planning", earliest, latest))

        # ============================
        # 4. Create agent executions
        # ============================
        print("\n--- Agent Executions ---")
        existing_execs = {
            row["id"]
            for row in cursor.execute("SELECT id FROM agent_executions").fetchall()
        }

        execs_created = 0
        for p in paired:
            exec_id = p["exec_id"]
            if exec_id in existing_execs:
                continue

            agent_id = p["agent_id"]
            # Normalize agent_id for DB FK (DB uses shortened names)
            db_agent_id = agent_id
            if agent_id == "duckdb_integration_developer":
                db_agent_id = "duckdb_developer"
            elif agent_id == "categorization_engine_developer":
                db_agent_id = "categorization_developer"
            elif agent_id == "requirements_orchestrator":
                db_agent_id = None  # Not in agents table
            elif agent_id == "implementation_orchestrator":
                db_agent_id = None

            # Check agent exists in DB
            if db_agent_id:
                exists = cursor.execute(
                    "SELECT 1 FROM agents WHERE id = ?", (db_agent_id,)
                ).fetchone()
                if not exists:
                    print(f"  [skip] Agent '{db_agent_id}' not in agents table")
                    continue

            if db_agent_id is None:
                continue

            result = p.get("result") or {}
            usage = result.get("usage", {}) if isinstance(result, dict) else {}
            output_path = result.get("artifact_path") if isinstance(result, dict) else None
            validation = result.get("validation_status") if isinstance(result, dict) else None
            output_valid = True if validation == "passed" else (False if validation == "failed" else None)

            # Calculate duration
            try:
                started = datetime.fromisoformat(p["started_at"])
                completed = datetime.fromisoformat(p["completed_at"])
                duration = (completed - started).total_seconds()
            except (ValueError, TypeError):
                duration = None

            execs_created += 1
            if not dry_run:
                cursor.execute("""
                    INSERT OR IGNORE INTO agent_executions
                        (id, workflow_run_id, agent_id, status, started_at, completed_at,
                         output_path, output_valid, error_message,
                         context_token_count, response_token_count, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exec_id, wf_run_id, db_agent_id, p["status"],
                    p["started_at"], p["completed_at"],
                    output_path, output_valid, p.get("error"),
                    usage.get("input_tokens"), usage.get("output_tokens"),
                    duration,
                ))

        print(f"  Created: {execs_created} agent execution records")

        if not dry_run:
            conn.commit()
            print("\n=== Migration complete ===")
        else:
            print("\n=== Dry run complete - no changes made ===")

        # Print summary
        print("\nDB state after migration:")
        for table in ["features", "tasks", "workflow_runs", "agent_executions"]:
            count = cursor.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()["c"]
            print(f"  {table}: {count} rows")

        if not dry_run:
            # Show task status breakdown
            print("\nTask status breakdown:")
            for row in cursor.execute("SELECT status, COUNT(*) as c FROM tasks GROUP BY status").fetchall():
                print(f"  {row['status']}: {row['c']}")

    except Exception as e:
        conn.rollback()
        raise Exception(f"Migration failed: {e}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate StateStore data to kanban DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying DB")
    parser.add_argument("--db-path", default="kanban-cli/kanban/tasks.db", help="Path to kanban DB")
    parser.add_argument("--state-dir", default="workflow", help="Path to workflow state directory")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    state_dir = Path(args.state_dir)

    if not db_path.exists():
        print(f"Error: DB not found at {db_path}")
        return 1

    if not state_dir.exists():
        print(f"Error: State directory not found at {state_dir}")
        return 1

    migrate(db_path, state_dir, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    exit(main())

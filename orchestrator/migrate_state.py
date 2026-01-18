"""
Migrate existing StateStore data to Context Manager.

Run once after implementing Context Manager to preserve existing execution history
and artifacts.
"""

import json
import os
from pathlib import Path
from orchestrator.state_store import StateStore
from orchestrator.context_manager import ContextManager


def migrate_executions():
    """Migrate execution history from StateStore to Context Manager."""
    print("=" * 60)
    print("Migrating execution history to Context Manager...")
    print("=" * 60)

    state_store = StateStore(state_dir="workflow")
    context_manager = ContextManager(context_dir="context")

    # Load existing executions
    executions_file = Path(state_store.state_dir) / "executions.json"
    if not executions_file.exists():
        print("No executions file found. Skipping migration.")
        return 0

    with open(executions_file, 'r', encoding='utf-8') as f:
        executions = json.load(f)

    migrated = 0
    skipped = 0

    for execution in executions:
        if execution["status"] == "completed" and execution.get("result"):
            try:
                # Record in Context Manager
                context_manager.record_execution(
                    execution_id=execution["id"],
                    agent_id=execution["agent_id"],
                    status=execution["status"],
                    context_version=1,  # Default to version 1
                    started_at=execution["timestamp"],
                    completed_at=execution["timestamp"],
                    input_token_count=execution.get("result", {}).get("prompt_tokens", 0),
                    output_token_count=execution.get("result", {}).get("usage", {}).get("output_tokens", 0)
                )
                migrated += 1
                print(f"  ✓ Migrated execution: {execution['id']}")

            except Exception as e:
                print(f"  ✗ Failed to migrate {execution['id']}: {e}")
                skipped += 1
        else:
            skipped += 1

    print(f"\nMigrated {migrated} executions, skipped {skipped}")
    return migrated


def migrate_artifacts():
    """Migrate artifacts from workflow/artifacts/ to context/artifacts/."""
    print("\n" + "=" * 60)
    print("Migrating artifacts to Context Manager...")
    print("=" * 60)

    context_manager = ContextManager(context_dir="context")
    artifacts_dir = Path("workflow/artifacts")

    if not artifacts_dir.exists():
        print("No artifacts directory found. Skipping migration.")
        return 0

    migrated = 0
    skipped = 0

    for agent_dir in artifacts_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        agent_id = agent_dir.name

        for artifact_file in agent_dir.iterdir():
            if not artifact_file.is_file():
                continue

            try:
                with open(artifact_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Determine type from extension
                suffix = artifact_file.suffix
                artifact_type = {
                    '.md': 'markdown',
                    '.yaml': 'yaml',
                    '.yml': 'yaml',
                    '.json': 'json',
                    '.py': 'code',
                    '.rs': 'code'
                }.get(suffix, 'text')

                # Store in Context Manager
                context_manager.store_artifact(
                    agent_id=agent_id,
                    artifacts=[{
                        "name": artifact_file.name,
                        "type": artifact_type,
                        "content": content,
                        "description": f"Migrated from StateStore"
                    }]
                )

                migrated += 1
                print(f"  ✓ Migrated artifact: {agent_id}/{artifact_file.name}")

            except Exception as e:
                print(f"  ✗ Failed to migrate {agent_id}/{artifact_file.name}: {e}")
                skipped += 1

    print(f"\nMigrated {migrated} artifacts, skipped {skipped}")
    return migrated


def main():
    """Run migration."""
    print("\n" + "=" * 60)
    print("StateStore to Context Manager Migration")
    print("=" * 60)
    print("\nThis script migrates existing execution history and artifacts")
    print("from the StateStore (JSON files) to the Context Manager (SQLite).")
    print("\nNote: Original StateStore files will remain in workflow/ for reference.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled.")
        return

    # Run migrations
    total_executions = migrate_executions()
    total_artifacts = migrate_artifacts()

    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"Total executions migrated: {total_executions}")
    print(f"Total artifacts migrated: {total_artifacts}")
    print("\nOriginal files preserved in workflow/ directory")
    print("Context Manager databases:")
    print("  - context/context.db")
    print("  - context/artifacts/v1/")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

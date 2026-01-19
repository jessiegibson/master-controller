//! Task CRUD operations

use chrono::{DateTime, Utc};
use rusqlite::{params, Row};
use uuid::Uuid;

use crate::db::Database;
use crate::models::{CreateTaskRequest, Task, TaskHistory};
use crate::state_machine::{StateMachine, TaskStatus};

use super::{OperationError, Result};

/// Parse a task from a database row
fn task_from_row(row: &Row) -> rusqlite::Result<Task> {
    Ok(Task {
        id: row.get("id")?,
        feature_id: row.get("feature_id")?,
        title: row.get("title")?,
        description: row.get("description")?,
        status: row
            .get::<_, String>("status")?
            .parse()
            .unwrap_or(TaskStatus::Todo),
        priority: row.get("priority")?,
        assigned_agent: row.get("assigned_agent")?,
        estimated_hours: row.get("estimated_hours")?,
        actual_hours: row.get("actual_hours")?,
        created_at: parse_datetime(row.get::<_, String>("created_at")?),
        updated_at: parse_datetime(row.get::<_, String>("updated_at")?),
        started_at: row
            .get::<_, Option<String>>("started_at")?
            .map(parse_datetime),
        completed_at: row
            .get::<_, Option<String>>("completed_at")?
            .map(parse_datetime),
    })
}

/// Parse a datetime string from SQLite
fn parse_datetime(s: String) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(&s)
        .map(|dt| dt.with_timezone(&Utc))
        .unwrap_or_else(|_| {
            chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%d %H:%M:%S")
                .map(|dt| dt.and_utc())
                .unwrap_or_else(|_| Utc::now())
        })
}

/// Generate a task ID based on feature and sequence
pub fn generate_task_id(db: &Database, feature_id: &str) -> Result<String> {
    let count: i64 = db.conn().query_row(
        "SELECT COUNT(*) FROM tasks WHERE feature_id = ?",
        params![feature_id],
        |row| row.get(0),
    )?;
    Ok(format!("T-{}-{:03}", feature_id, count + 1))
}

/// Create a new task
pub fn create_task(db: &Database, request: CreateTaskRequest) -> Result<Task> {
    let task_id = generate_task_id(db, &request.feature_id)?;
    let now = Utc::now().to_rfc3339();

    db.conn().execute(
        r#"
        INSERT INTO tasks (id, feature_id, title, description, status, priority, estimated_hours, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'todo', ?, ?, ?, ?)
        "#,
        params![
            task_id,
            request.feature_id,
            request.title,
            request.description,
            request.priority,
            request.estimated_hours,
            now,
            now,
        ],
    )?;

    // Add dependencies
    for dep_id in &request.dependencies {
        db.conn().execute(
            "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
            params![task_id, dep_id],
        )?;
    }

    get_task(db, &task_id)
}

/// Get a task by ID
pub fn get_task(db: &Database, task_id: &str) -> Result<Task> {
    db.conn()
        .query_row(
            "SELECT * FROM tasks WHERE id = ?",
            params![task_id],
            task_from_row,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                OperationError::NotFound(format!("Task not found: {}", task_id))
            }
            _ => OperationError::Database(e),
        })
}

/// List tasks with optional filters
pub fn list_tasks(
    db: &Database,
    feature_id: Option<&str>,
    status: Option<TaskStatus>,
    agent_id: Option<&str>,
) -> Result<Vec<Task>> {
    let mut sql = String::from("SELECT * FROM tasks WHERE 1=1");
    let mut params_vec: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();

    if let Some(fid) = feature_id {
        sql.push_str(" AND feature_id = ?");
        params_vec.push(Box::new(fid.to_string()));
    }

    if let Some(st) = status {
        sql.push_str(" AND status = ?");
        params_vec.push(Box::new(st.to_string()));
    }

    if let Some(aid) = agent_id {
        sql.push_str(" AND assigned_agent = ?");
        params_vec.push(Box::new(aid.to_string()));
    }

    sql.push_str(" ORDER BY priority ASC, created_at ASC");

    let params_refs: Vec<&dyn rusqlite::ToSql> = params_vec.iter().map(|p| p.as_ref()).collect();

    let mut stmt = db.conn().prepare(&sql)?;
    let tasks = stmt
        .query_map(params_refs.as_slice(), task_from_row)?
        .collect::<std::result::Result<Vec<_>, _>>()?;

    Ok(tasks)
}

/// Update task status with state machine validation
pub fn update_task_status(
    db: &Database,
    task_id: &str,
    new_status: TaskStatus,
    changed_by: &str,
) -> Result<Task> {
    let task = get_task(db, task_id)?;

    // Validate transition
    if !StateMachine::can_transition(&task.status, &new_status) {
        return Err(OperationError::InvalidTransition(format!(
            "Cannot transition from '{}' to '{}'",
            task.status, new_status
        )));
    }

    let now = Utc::now().to_rfc3339();
    let old_status = task.status.to_string();
    let new_status_str = new_status.to_string();

    // Update the task
    let mut update_sql = String::from("UPDATE tasks SET status = ?, updated_at = ?");

    // Set started_at when moving to in-progress
    if new_status == TaskStatus::InProgress && task.started_at.is_none() {
        update_sql.push_str(", started_at = ?");
    }

    // Set completed_at when moving to done
    if new_status == TaskStatus::Done {
        update_sql.push_str(", completed_at = ?");
    }

    update_sql.push_str(" WHERE id = ?");

    match (new_status, task.started_at.is_none()) {
        (TaskStatus::InProgress, true) => {
            db.conn()
                .execute(&update_sql, params![new_status_str, now, now, task_id])?;
        }
        (TaskStatus::Done, _) => {
            db.conn()
                .execute(&update_sql, params![new_status_str, now, now, task_id])?;
        }
        _ => {
            db.conn()
                .execute(&update_sql, params![new_status_str, now, task_id])?;
        }
    }

    // Record history
    record_history(db, task_id, "status", Some(&old_status), &new_status_str, changed_by)?;

    get_task(db, task_id)
}

/// Assign a task to an agent
pub fn assign_task(db: &Database, task_id: &str, agent_id: &str, changed_by: &str) -> Result<Task> {
    let task = get_task(db, task_id)?;
    let now = Utc::now().to_rfc3339();

    // Check agent exists and has capacity
    let current_tasks: i64 = db.conn().query_row(
        "SELECT COUNT(*) FROM tasks WHERE assigned_agent = ? AND status IN ('in-progress', 'blocked')",
        params![agent_id],
        |row| row.get(0),
    )?;

    let max_tasks: i64 = db
        .conn()
        .query_row(
            "SELECT max_concurrent_tasks FROM agents WHERE id = ?",
            params![agent_id],
            |row| row.get(0),
        )
        .map_err(|_| OperationError::NotFound(format!("Agent not found: {}", agent_id)))?;

    if current_tasks >= max_tasks {
        return Err(OperationError::AgentUnavailable(format!(
            "Agent {} is at capacity ({}/{})",
            agent_id, current_tasks, max_tasks
        )));
    }

    db.conn().execute(
        "UPDATE tasks SET assigned_agent = ?, updated_at = ? WHERE id = ?",
        params![agent_id, now, task_id],
    )?;

    // Record history
    record_history(
        db,
        task_id,
        "assigned_agent",
        task.assigned_agent.as_deref(),
        agent_id,
        changed_by,
    )?;

    get_task(db, task_id)
}

/// Update task priority
pub fn update_task_priority(
    db: &Database,
    task_id: &str,
    priority: i32,
    changed_by: &str,
) -> Result<Task> {
    let task = get_task(db, task_id)?;
    let now = Utc::now().to_rfc3339();

    db.conn().execute(
        "UPDATE tasks SET priority = ?, updated_at = ? WHERE id = ?",
        params![priority, now, task_id],
    )?;

    record_history(
        db,
        task_id,
        "priority",
        Some(&task.priority.to_string()),
        &priority.to_string(),
        changed_by,
    )?;

    get_task(db, task_id)
}

/// Record a change in task history
fn record_history(
    db: &Database,
    task_id: &str,
    field: &str,
    old_value: Option<&str>,
    new_value: &str,
    changed_by: &str,
) -> Result<()> {
    let now = Utc::now().to_rfc3339();
    db.conn().execute(
        "INSERT INTO task_history (task_id, field_changed, old_value, new_value, changed_by, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
        params![task_id, field, old_value, new_value, changed_by, now],
    )?;
    Ok(())
}

/// Get task history
pub fn get_task_history(db: &Database, task_id: &str) -> Result<Vec<TaskHistory>> {
    let mut stmt = db.conn().prepare(
        "SELECT id, task_id, field_changed, old_value, new_value, changed_by, changed_at FROM task_history WHERE task_id = ? ORDER BY changed_at ASC"
    )?;

    let history = stmt
        .query_map(params![task_id], |row| {
            Ok(TaskHistory {
                id: row.get("id")?,
                task_id: row.get("task_id")?,
                field_changed: row.get("field_changed")?,
                old_value: row.get("old_value")?,
                new_value: row.get("new_value")?,
                changed_by: row.get("changed_by")?,
                changed_at: parse_datetime(row.get::<_, String>("changed_at")?),
            })
        })?
        .collect::<std::result::Result<Vec<_>, _>>()?;

    Ok(history)
}

/// Get task dependencies
pub fn get_task_dependencies(db: &Database, task_id: &str) -> Result<Vec<Task>> {
    let mut stmt = db.conn().prepare(
        "SELECT t.* FROM tasks t JOIN task_dependencies d ON t.id = d.depends_on_task_id WHERE d.task_id = ?",
    )?;

    let tasks = stmt
        .query_map(params![task_id], task_from_row)?
        .collect::<std::result::Result<Vec<_>, _>>()?;

    Ok(tasks)
}

/// Add a dependency between tasks
pub fn add_task_dependency(db: &Database, task_id: &str, depends_on: &str) -> Result<()> {
    // Verify both tasks exist
    get_task(db, task_id)?;
    get_task(db, depends_on)?;

    // Check for circular dependency
    if would_create_cycle(db, task_id, depends_on)? {
        return Err(OperationError::Dependency(
            "Cannot add dependency: would create circular reference".to_string(),
        ));
    }

    db.conn().execute(
        "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
        params![task_id, depends_on],
    )?;

    Ok(())
}

/// Check if adding a dependency would create a cycle
fn would_create_cycle(db: &Database, task_id: &str, depends_on: &str) -> Result<bool> {
    // Simple cycle check: see if depends_on already depends on task_id (directly or indirectly)
    let mut visited = std::collections::HashSet::new();
    let mut stack = vec![depends_on.to_string()];

    while let Some(current) = stack.pop() {
        if current == task_id {
            return Ok(true);
        }
        if visited.contains(&current) {
            continue;
        }
        visited.insert(current.clone());

        let deps = get_task_dependencies(db, &current)?;
        for dep in deps {
            stack.push(dep.id);
        }
    }

    Ok(false)
}

/// Add a comment to a task
pub fn add_task_comment(db: &Database, task_id: &str, author: &str, content: &str) -> Result<()> {
    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();

    db.conn().execute(
        "INSERT INTO task_comments (id, task_id, author, content, created_at) VALUES (?, ?, ?, ?, ?)",
        params![id, task_id, author, content, now],
    )?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::TaskBuilder;
    use crate::operations::features;

    fn setup_test_db() -> Database {
        let db = Database::in_memory().unwrap();
        // Create a test feature
        features::create_feature(
            &db,
            crate::models::CreateFeatureRequest {
                name: "Test Feature".to_string(),
                description: None,
                color: None,
            },
        )
        .unwrap();
        db
    }

    #[test]
    fn test_create_task() {
        let db = setup_test_db();
        let request = TaskBuilder::new()
            .feature_id("test-feature")
            .title("Test task")
            .priority(1)
            .build()
            .unwrap();

        let task = create_task(&db, request).unwrap();
        assert_eq!(task.title, "Test task");
        assert_eq!(task.status, TaskStatus::Todo);
        assert_eq!(task.priority, 1);
    }

    #[test]
    fn test_status_transition() {
        let db = setup_test_db();
        let request = TaskBuilder::new()
            .feature_id("test-feature")
            .title("Test task")
            .build()
            .unwrap();

        let task = create_task(&db, request).unwrap();

        // Valid transition: todo -> in-progress
        let task = update_task_status(&db, &task.id, TaskStatus::InProgress, "test").unwrap();
        assert_eq!(task.status, TaskStatus::InProgress);
        assert!(task.started_at.is_some());

        // Valid transition: in-progress -> in-qa
        let task = update_task_status(&db, &task.id, TaskStatus::InQa, "test").unwrap();
        assert_eq!(task.status, TaskStatus::InQa);

        // Valid transition: in-qa -> done
        let task = update_task_status(&db, &task.id, TaskStatus::Done, "test").unwrap();
        assert_eq!(task.status, TaskStatus::Done);
        assert!(task.completed_at.is_some());
    }

    #[test]
    fn test_invalid_transition() {
        let db = setup_test_db();
        let request = TaskBuilder::new()
            .feature_id("test-feature")
            .title("Test task")
            .build()
            .unwrap();

        let task = create_task(&db, request).unwrap();

        // Invalid transition: todo -> done
        let result = update_task_status(&db, &task.id, TaskStatus::Done, "test");
        assert!(result.is_err());
    }

    #[test]
    fn test_task_history() {
        let db = setup_test_db();
        let request = TaskBuilder::new()
            .feature_id("test-feature")
            .title("Test task")
            .build()
            .unwrap();

        let task = create_task(&db, request).unwrap();
        update_task_status(&db, &task.id, TaskStatus::InProgress, "tester").unwrap();

        let history = get_task_history(&db, &task.id).unwrap();
        assert!(!history.is_empty());
        assert_eq!(history[0].field_changed, "status");
        assert_eq!(history[0].changed_by, "tester");
    }
}

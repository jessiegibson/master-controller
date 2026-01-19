//! Blocker operations

use chrono::Utc;
use rusqlite::{params, Row};

use crate::db::Database;
use crate::models::{Blocker, CreateBlockerRequest};
use crate::state_machine::{BlockerStatus, BlockerType, TaskStatus};

use super::tasks::{get_task, update_task_status};
use super::{OperationError, Result};

/// Parse a blocker from a database row
fn blocker_from_row(row: &Row) -> rusqlite::Result<Blocker> {
    Ok(Blocker {
        id: row.get("id")?,
        task_id: row.get("task_id")?,
        blocker_type: row
            .get::<_, String>("type")?
            .parse()
            .unwrap_or(BlockerType::Technical),
        description: row.get("description")?,
        blocking_task_id: row.get("blocking_task_id")?,
        status: row
            .get::<_, String>("status")?
            .parse()
            .unwrap_or(BlockerStatus::Active),
        created_at: parse_datetime(row.get::<_, String>("created_at")?),
        resolved_at: row
            .get::<_, Option<String>>("resolved_at")?
            .map(parse_datetime),
        escalated_at: row
            .get::<_, Option<String>>("escalated_at")?
            .map(parse_datetime),
        resolution_notes: row.get("resolution_notes")?,
    })
}

fn parse_datetime(s: String) -> chrono::DateTime<Utc> {
    chrono::DateTime::parse_from_rfc3339(&s)
        .map(|dt| dt.with_timezone(&Utc))
        .unwrap_or_else(|_| {
            chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%d %H:%M:%S")
                .map(|dt| dt.and_utc())
                .unwrap_or_else(|_| Utc::now())
        })
}

/// Generate a blocker ID
pub fn generate_blocker_id(db: &Database) -> Result<String> {
    let count: i64 = db
        .conn()
        .query_row("SELECT COUNT(*) FROM blockers", [], |row| row.get(0))?;
    Ok(format!("B-{:03}", count + 1))
}

/// Add a blocker to a task
pub fn add_blocker(db: &Database, request: CreateBlockerRequest) -> Result<Blocker> {
    // Verify task exists
    let task = get_task(db, &request.task_id)?;

    // Generate blocker ID
    let blocker_id = generate_blocker_id(db)?;
    let now = Utc::now().to_rfc3339();

    db.conn().execute(
        r#"
        INSERT INTO blockers (id, task_id, type, description, blocking_task_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?)
        "#,
        params![
            blocker_id,
            request.task_id,
            request.blocker_type.to_string(),
            request.description,
            request.blocking_task_id,
            now,
        ],
    )?;

    // Auto-transition task to blocked if it's in progress
    if task.status == TaskStatus::InProgress {
        update_task_status(db, &request.task_id, TaskStatus::Blocked, "system")?;
    }

    get_blocker(db, &blocker_id)
}

/// Get a blocker by ID
pub fn get_blocker(db: &Database, blocker_id: &str) -> Result<Blocker> {
    db.conn()
        .query_row(
            "SELECT * FROM blockers WHERE id = ?",
            params![blocker_id],
            blocker_from_row,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                OperationError::NotFound(format!("Blocker not found: {}", blocker_id))
            }
            _ => OperationError::Database(e),
        })
}

/// List active blockers
pub fn list_active_blockers(db: &Database, feature_id: Option<&str>) -> Result<Vec<Blocker>> {
    let sql = if feature_id.is_some() {
        r#"
        SELECT b.* FROM blockers b
        JOIN tasks t ON b.task_id = t.id
        WHERE b.status = 'active' AND t.feature_id = ?
        ORDER BY b.created_at DESC
        "#
    } else {
        "SELECT * FROM blockers WHERE status = 'active' ORDER BY created_at DESC"
    };

    let mut stmt = db.conn().prepare(sql)?;

    let blockers = if let Some(fid) = feature_id {
        stmt.query_map(params![fid], blocker_from_row)?
    } else {
        stmt.query_map([], blocker_from_row)?
    }
    .collect::<std::result::Result<Vec<_>, _>>()?;

    Ok(blockers)
}

/// List all blockers for a task
pub fn list_task_blockers(db: &Database, task_id: &str) -> Result<Vec<Blocker>> {
    let mut stmt = db
        .conn()
        .prepare("SELECT * FROM blockers WHERE task_id = ? ORDER BY created_at DESC")?;

    let blockers = stmt
        .query_map(params![task_id], blocker_from_row)?
        .collect::<std::result::Result<Vec<_>, _>>()?;

    Ok(blockers)
}

/// Resolve a blocker
pub fn resolve_blocker(
    db: &Database,
    blocker_id: &str,
    resolution_notes: Option<&str>,
) -> Result<Blocker> {
    let blocker = get_blocker(db, blocker_id)?;
    let now = Utc::now().to_rfc3339();

    db.conn().execute(
        "UPDATE blockers SET status = 'resolved', resolved_at = ?, resolution_notes = ? WHERE id = ?",
        params![now, resolution_notes, blocker_id],
    )?;

    // Check if task has any remaining active blockers
    let active_count: i64 = db.conn().query_row(
        "SELECT COUNT(*) FROM blockers WHERE task_id = ? AND status = 'active'",
        params![blocker.task_id],
        |row| row.get(0),
    )?;

    // If no more active blockers, transition task back to in-progress
    if active_count == 0 {
        let task = get_task(db, &blocker.task_id)?;
        if task.status == TaskStatus::Blocked {
            update_task_status(db, &blocker.task_id, TaskStatus::InProgress, "system")?;
        }
    }

    get_blocker(db, blocker_id)
}

/// Escalate a blocker
pub fn escalate_blocker(db: &Database, blocker_id: &str) -> Result<Blocker> {
    let now = Utc::now().to_rfc3339();

    db.conn().execute(
        "UPDATE blockers SET status = 'escalated', escalated_at = ? WHERE id = ?",
        params![now, blocker_id],
    )?;

    get_blocker(db, blocker_id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{CreateFeatureRequest, TaskBuilder};
    use crate::operations::{features, tasks};

    fn setup_test_db() -> (Database, String) {
        let db = Database::in_memory().unwrap();

        // Create a test feature
        features::create_feature(
            &db,
            CreateFeatureRequest {
                name: "Test Feature".to_string(),
                description: None,
                color: None,
            },
        )
        .unwrap();

        // Create a test task
        let request = TaskBuilder::new()
            .feature_id("test-feature")
            .title("Test task")
            .build()
            .unwrap();
        let task = tasks::create_task(&db, request).unwrap();

        // Move task to in-progress
        tasks::update_task_status(&db, &task.id, TaskStatus::InProgress, "test").unwrap();

        (db, task.id)
    }

    #[test]
    fn test_add_blocker() {
        let (db, task_id) = setup_test_db();

        let blocker = add_blocker(
            &db,
            CreateBlockerRequest {
                task_id: task_id.clone(),
                blocker_type: BlockerType::Technical,
                description: "Waiting for API".to_string(),
                blocking_task_id: None,
            },
        )
        .unwrap();

        assert_eq!(blocker.status, BlockerStatus::Active);
        assert_eq!(blocker.blocker_type, BlockerType::Technical);

        // Task should be auto-blocked
        let task = get_task(&db, &task_id).unwrap();
        assert_eq!(task.status, TaskStatus::Blocked);
    }

    #[test]
    fn test_resolve_blocker() {
        let (db, task_id) = setup_test_db();

        let blocker = add_blocker(
            &db,
            CreateBlockerRequest {
                task_id: task_id.clone(),
                blocker_type: BlockerType::Technical,
                description: "Waiting for API".to_string(),
                blocking_task_id: None,
            },
        )
        .unwrap();

        let resolved = resolve_blocker(&db, &blocker.id, Some("API now ready")).unwrap();
        assert_eq!(resolved.status, BlockerStatus::Resolved);
        assert!(resolved.resolution_notes.is_some());

        // Task should be auto-unblocked
        let task = get_task(&db, &task_id).unwrap();
        assert_eq!(task.status, TaskStatus::InProgress);
    }
}

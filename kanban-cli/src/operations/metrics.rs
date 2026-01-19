//! Feature metrics and agent workload calculations

use chrono::Utc;
use rusqlite::params;
use serde::{Deserialize, Serialize};

use crate::db::Database;
use crate::models::AgentWorkload;
use crate::state_machine::{AgentStatus, AgentType};

use super::features::get_feature;
use super::{OperationError, Result};

/// Feature metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureMetrics {
    pub feature_id: String,

    // Progress
    pub total_tasks: i64,
    pub completed_tasks: i64,
    pub completion_rate: f64,

    // Effort
    pub estimated_hours: f64,
    pub actual_hours: f64,
    pub hours_remaining: f64,

    // Health
    pub blocked_tasks: i64,
    pub active_blockers: i64,
}

/// Calculate feature metrics
pub fn get_feature_metrics(db: &Database, feature_id: &str) -> Result<FeatureMetrics> {
    // Verify feature exists
    get_feature(db, feature_id)?;

    // Task counts
    let (total, done, blocked): (i64, i64, i64) = db.conn().query_row(
        r#"
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked
        FROM tasks WHERE feature_id = ?
        "#,
        params![feature_id],
        |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
    )?;

    // Hours
    let (estimated, actual): (f64, f64) = db.conn().query_row(
        r#"
        SELECT
            COALESCE(SUM(estimated_hours), 0) as estimated,
            COALESCE(SUM(actual_hours), 0) as actual
        FROM tasks WHERE feature_id = ?
        "#,
        params![feature_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    )?;

    // Active blockers
    let active_blockers: i64 = db.conn().query_row(
        r#"
        SELECT COUNT(*) FROM blockers b
        JOIN tasks t ON b.task_id = t.id
        WHERE t.feature_id = ? AND b.status = 'active'
        "#,
        params![feature_id],
        |row| row.get(0),
    )?;

    // Completion rate
    let completion_rate = if total > 0 {
        done as f64 / total as f64
    } else {
        0.0
    };

    // Hours remaining (estimated for incomplete tasks)
    let hours_remaining: f64 = db.conn().query_row(
        r#"
        SELECT COALESCE(SUM(estimated_hours), 0)
        FROM tasks WHERE feature_id = ? AND status != 'done'
        "#,
        params![feature_id],
        |row| row.get(0),
    )?;

    Ok(FeatureMetrics {
        feature_id: feature_id.to_string(),
        total_tasks: total,
        completed_tasks: done,
        completion_rate,
        estimated_hours: estimated,
        actual_hours: actual,
        hours_remaining,
        blocked_tasks: blocked,
        active_blockers,
    })
}

/// Get overall metrics across all active features
pub fn get_overall_metrics(db: &Database) -> Result<FeatureMetrics> {
    // Task counts
    let (total, done, blocked): (i64, i64, i64) = db.conn().query_row(
        r#"
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked
        FROM tasks t
        JOIN features f ON t.feature_id = f.id
        WHERE f.status = 'active'
        "#,
        [],
        |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
    )?;

    // Hours
    let (estimated, actual): (f64, f64) = db.conn().query_row(
        r#"
        SELECT
            COALESCE(SUM(estimated_hours), 0) as estimated,
            COALESCE(SUM(actual_hours), 0) as actual
        FROM tasks t
        JOIN features f ON t.feature_id = f.id
        WHERE f.status = 'active'
        "#,
        [],
        |row| Ok((row.get(0)?, row.get(1)?)),
    )?;

    // Active blockers
    let active_blockers: i64 = db.conn().query_row(
        r#"
        SELECT COUNT(*) FROM blockers b
        WHERE b.status = 'active'
        "#,
        [],
        |row| row.get(0),
    )?;

    // Completion rate
    let completion_rate = if total > 0 {
        done as f64 / total as f64
    } else {
        0.0
    };

    // Hours remaining
    let hours_remaining: f64 = db.conn().query_row(
        r#"
        SELECT COALESCE(SUM(estimated_hours), 0)
        FROM tasks t
        JOIN features f ON t.feature_id = f.id
        WHERE f.status = 'active' AND t.status != 'done'
        "#,
        [],
        |row| row.get(0),
    )?;

    Ok(FeatureMetrics {
        feature_id: "all".to_string(),
        total_tasks: total,
        completed_tasks: done,
        completion_rate,
        estimated_hours: estimated,
        actual_hours: actual,
        hours_remaining,
        blocked_tasks: blocked,
        active_blockers,
    })
}

/// Get agent workload
pub fn get_agent_workload(db: &Database, agent_id: &str) -> Result<AgentWorkload> {
    // Get agent info
    let agent = db
        .conn()
        .query_row(
            "SELECT id, name, type, status, max_concurrent_tasks, created_at FROM agents WHERE id = ?",
            params![agent_id],
            |row| {
                Ok(crate::models::Agent {
                    id: row.get("id")?,
                    name: row.get("name")?,
                    agent_type: row
                        .get::<_, String>("type")?
                        .parse()
                        .unwrap_or(AgentType::Developer),
                    status: row
                        .get::<_, String>("status")?
                        .parse()
                        .unwrap_or(AgentStatus::Available),
                    max_concurrent_tasks: row.get("max_concurrent_tasks")?,
                    created_at: chrono::DateTime::parse_from_rfc3339(
                        &row.get::<_, String>("created_at")?,
                    )
                    .map(|dt| dt.with_timezone(&Utc))
                    .unwrap_or_else(|_| Utc::now()),
                })
            },
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                OperationError::NotFound(format!("Agent not found: {}", agent_id))
            }
            _ => OperationError::Database(e),
        })?;

    // Get current tasks
    let mut stmt = db.conn().prepare(
        "SELECT id FROM tasks WHERE assigned_agent = ? AND status IN ('in-progress', 'blocked')",
    )?;
    let task_ids: Vec<String> = stmt
        .query_map(params![agent_id], |row| row.get(0))?
        .collect::<std::result::Result<Vec<_>, _>>()?;

    // Get completed tasks count (all time)
    let tasks_completed: i64 = db.conn().query_row(
        "SELECT COUNT(*) FROM tasks WHERE assigned_agent = ? AND status = 'done'",
        params![agent_id],
        |row| row.get(0),
    )?;

    // Get average completion time
    let avg_time: Option<f64> = db
        .conn()
        .query_row(
            r#"
        SELECT AVG(actual_hours) FROM tasks
        WHERE assigned_agent = ? AND status = 'done' AND actual_hours IS NOT NULL
        "#,
            params![agent_id],
            |row| row.get(0),
        )
        .ok();

    Ok(AgentWorkload {
        agent,
        current_tasks: task_ids.len() as i32,
        task_ids,
        tasks_completed_this_sprint: tasks_completed as i32,
        avg_completion_time_hours: avg_time,
    })
}

/// Get available agents (with capacity)
pub fn get_available_agents(
    db: &Database,
    agent_type: Option<AgentType>,
) -> Result<Vec<AgentWorkload>> {
    let agent_ids: Vec<String> = if let Some(t) = agent_type {
        let mut stmt = db
            .conn()
            .prepare("SELECT id FROM agents WHERE type = ? AND status = 'available'")?;
        let ids: Vec<String> = stmt
            .query_map(params![t.to_string()], |row| row.get(0))?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        ids
    } else {
        let mut stmt = db
            .conn()
            .prepare("SELECT id FROM agents WHERE status = 'available'")?;
        let ids: Vec<String> = stmt
            .query_map([], |row| row.get(0))?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        ids
    };

    let mut workloads = Vec::new();
    for agent_id in agent_ids {
        let workload = get_agent_workload(db, &agent_id)?;
        if workload.has_capacity() {
            workloads.push(workload);
        }
    }

    Ok(workloads)
}

/// List all agents with their workload
pub fn list_agents(db: &Database) -> Result<Vec<AgentWorkload>> {
    let mut stmt = db.conn().prepare("SELECT id FROM agents ORDER BY name")?;
    let agent_ids: Vec<String> = stmt
        .query_map([], |row| row.get(0))?
        .collect::<std::result::Result<Vec<_>, _>>()?;

    let mut workloads = Vec::new();
    for agent_id in agent_ids {
        workloads.push(get_agent_workload(db, &agent_id)?);
    }

    Ok(workloads)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{CreateFeatureRequest, TaskBuilder};
    use crate::operations::{features, tasks};
    use crate::state_machine::TaskStatus;

    fn setup_test_db() -> Database {
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

        // Create some tasks
        for i in 1..=5 {
            let request = TaskBuilder::new()
                .feature_id("test-feature")
                .title(format!("Task {}", i))
                .estimated_hours(4.0)
                .build()
                .unwrap();
            let task = tasks::create_task(&db, request).unwrap();

            // Complete some tasks
            if i <= 2 {
                tasks::update_task_status(&db, &task.id, TaskStatus::InProgress, "test").unwrap();
                tasks::update_task_status(&db, &task.id, TaskStatus::InQa, "test").unwrap();
                tasks::update_task_status(&db, &task.id, TaskStatus::Done, "test").unwrap();
            }
        }

        db
    }

    #[test]
    fn test_feature_metrics() {
        let db = setup_test_db();
        let metrics = get_feature_metrics(&db, "test-feature").unwrap();

        assert_eq!(metrics.total_tasks, 5);
        assert_eq!(metrics.completed_tasks, 2);
        assert!((metrics.completion_rate - 0.4).abs() < 0.01);
    }

    #[test]
    fn test_agent_workload() {
        let db = setup_test_db();
        let workload = get_agent_workload(&db, "parser_developer").unwrap();

        assert_eq!(workload.agent.id, "parser_developer");
        assert!(workload.has_capacity());
    }

    #[test]
    fn test_available_agents() {
        let db = setup_test_db();
        let agents = get_available_agents(&db, Some(AgentType::Developer)).unwrap();

        assert!(!agents.is_empty());
    }
}

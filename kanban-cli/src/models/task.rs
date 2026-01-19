//! Task model and related structures

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::state_machine::TaskStatus;

/// A task in the kanban board
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub feature_id: String,
    pub title: String,
    pub description: Option<String>,
    pub status: TaskStatus,
    pub priority: i32,
    pub assigned_agent: Option<String>,
    pub estimated_hours: Option<f64>,
    pub actual_hours: Option<f64>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
}

impl Task {
    /// Create a new task with minimal required fields
    pub fn new(id: String, feature_id: String, title: String) -> Self {
        let now = Utc::now();
        Self {
            id,
            feature_id,
            title,
            description: None,
            status: TaskStatus::Todo,
            priority: 100,
            assigned_agent: None,
            estimated_hours: None,
            actual_hours: None,
            created_at: now,
            updated_at: now,
            started_at: None,
            completed_at: None,
        }
    }

    /// Check if the task is in a terminal state
    pub fn is_complete(&self) -> bool {
        self.status == TaskStatus::Done
    }

    /// Check if the task is blocked
    pub fn is_blocked(&self) -> bool {
        self.status == TaskStatus::Blocked
    }

    /// Check if the task is active (in progress)
    pub fn is_active(&self) -> bool {
        self.status == TaskStatus::InProgress
    }
}

/// Builder for creating tasks with optional fields
#[derive(Debug, Default)]
pub struct TaskBuilder {
    feature_id: Option<String>,
    title: Option<String>,
    description: Option<String>,
    priority: Option<i32>,
    estimated_hours: Option<f64>,
    dependencies: Vec<String>,
}

impl TaskBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn feature_id(mut self, feature_id: impl Into<String>) -> Self {
        self.feature_id = Some(feature_id.into());
        self
    }

    pub fn title(mut self, title: impl Into<String>) -> Self {
        self.title = Some(title.into());
        self
    }

    pub fn description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }

    pub fn priority(mut self, priority: i32) -> Self {
        self.priority = Some(priority);
        self
    }

    pub fn estimated_hours(mut self, hours: f64) -> Self {
        self.estimated_hours = Some(hours);
        self
    }

    pub fn depends_on(mut self, task_id: impl Into<String>) -> Self {
        self.dependencies.push(task_id.into());
        self
    }

    /// Get the dependencies
    pub fn dependencies(&self) -> &[String] {
        &self.dependencies
    }

    /// Build the task creation request (ID will be generated later)
    pub fn build(self) -> Result<CreateTaskRequest, &'static str> {
        let feature_id = self.feature_id.ok_or("feature_id is required")?;
        let title = self.title.ok_or("title is required")?;

        Ok(CreateTaskRequest {
            feature_id,
            title,
            description: self.description,
            priority: self.priority.unwrap_or(100),
            estimated_hours: self.estimated_hours,
            dependencies: self.dependencies,
        })
    }
}

/// Request to create a new task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateTaskRequest {
    pub feature_id: String,
    pub title: String,
    pub description: Option<String>,
    pub priority: i32,
    pub estimated_hours: Option<f64>,
    pub dependencies: Vec<String>,
}

/// Task history entry for audit trail
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskHistory {
    pub id: i64,
    pub task_id: String,
    pub field_changed: String,
    pub old_value: Option<String>,
    pub new_value: Option<String>,
    pub changed_by: String,
    pub changed_at: DateTime<Utc>,
}

/// Task comment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskComment {
    pub id: String,
    pub task_id: String,
    pub author: String,
    pub content: String,
    pub created_at: DateTime<Utc>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_task_new() {
        let task = Task::new(
            "T-001".to_string(),
            "F-001".to_string(),
            "Test task".to_string(),
        );
        assert_eq!(task.status, TaskStatus::Todo);
        assert_eq!(task.priority, 100);
        assert!(!task.is_complete());
    }

    #[test]
    fn test_task_builder() {
        let request = TaskBuilder::new()
            .feature_id("parser")
            .title("Implement feature")
            .description("A detailed description")
            .priority(1)
            .estimated_hours(8.0)
            .depends_on("T-001")
            .build()
            .unwrap();

        assert_eq!(request.feature_id, "parser");
        assert_eq!(request.title, "Implement feature");
        assert_eq!(request.priority, 1);
        assert_eq!(request.dependencies.len(), 1);
    }
}

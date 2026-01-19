//! Workflow run and execution models

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Status of a workflow run
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum WorkflowStatus {
    Running,
    Paused,
    Completed,
    Failed,
}

impl WorkflowStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            WorkflowStatus::Running => "running",
            WorkflowStatus::Paused => "paused",
            WorkflowStatus::Completed => "completed",
            WorkflowStatus::Failed => "failed",
        }
    }
}

/// Status of an agent execution
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionStatus {
    Pending,
    Running,
    Completed,
    Failed,
    Skipped,
}

impl ExecutionStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            ExecutionStatus::Pending => "pending",
            ExecutionStatus::Running => "running",
            ExecutionStatus::Completed => "completed",
            ExecutionStatus::Failed => "failed",
            ExecutionStatus::Skipped => "skipped",
        }
    }
}

/// A workflow run instance
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowRun {
    pub id: String,
    pub sprint_id: String,
    pub status: WorkflowStatus,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub error_message: Option<String>,
    pub created_at: DateTime<Utc>,
}

impl WorkflowRun {
    /// Create a new workflow run
    pub fn new(id: String, sprint_id: String) -> Self {
        let now = Utc::now();
        Self {
            id,
            sprint_id,
            status: WorkflowStatus::Running,
            started_at: now,
            completed_at: None,
            error_message: None,
            created_at: now,
        }
    }

    /// Check if the workflow is still running
    pub fn is_running(&self) -> bool {
        self.status == WorkflowStatus::Running
    }

    /// Get duration in seconds (if completed)
    pub fn duration_seconds(&self) -> Option<f64> {
        self.completed_at
            .map(|end| (end - self.started_at).num_milliseconds() as f64 / 1000.0)
    }
}

/// An agent execution within a workflow run
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentExecution {
    pub id: String,
    pub workflow_run_id: String,
    pub agent_id: String,
    pub task_id: Option<String>,
    pub status: ExecutionStatus,
    pub attempt_number: i32,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub output_path: Option<String>,
    pub output_valid: Option<bool>,
    pub error_message: Option<String>,
    pub context_token_count: Option<i32>,
    pub response_token_count: Option<i32>,
    pub duration_seconds: Option<f64>,
    pub created_at: DateTime<Utc>,
}

impl AgentExecution {
    /// Create a new pending agent execution
    pub fn new(id: String, workflow_run_id: String, agent_id: String) -> Self {
        Self {
            id,
            workflow_run_id,
            agent_id,
            task_id: None,
            status: ExecutionStatus::Pending,
            attempt_number: 1,
            started_at: None,
            completed_at: None,
            output_path: None,
            output_valid: None,
            error_message: None,
            context_token_count: None,
            response_token_count: None,
            duration_seconds: None,
            created_at: Utc::now(),
        }
    }
}

/// A workflow checkpoint for resumability
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowCheckpoint {
    pub id: String,
    pub workflow_run_id: String,
    pub checkpoint_type: String,
    pub checkpoint_data: Option<String>,
    pub created_at: DateTime<Utc>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_workflow_run_new() {
        let run = WorkflowRun::new("WF-001".to_string(), "S1".to_string());
        assert!(run.is_running());
        assert!(run.completed_at.is_none());
    }

    #[test]
    fn test_execution_status() {
        assert_eq!(ExecutionStatus::Pending.as_str(), "pending");
        assert_eq!(ExecutionStatus::Completed.as_str(), "completed");
    }
}

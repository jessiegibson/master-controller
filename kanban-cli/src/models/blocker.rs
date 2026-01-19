//! Blocker model

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::state_machine::{BlockerStatus, BlockerType};

/// A blocker on a task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Blocker {
    pub id: String,
    pub task_id: String,
    pub blocker_type: BlockerType,
    pub description: String,
    pub blocking_task_id: Option<String>,
    pub status: BlockerStatus,
    pub created_at: DateTime<Utc>,
    pub resolved_at: Option<DateTime<Utc>>,
    pub escalated_at: Option<DateTime<Utc>>,
    pub resolution_notes: Option<String>,
}

impl Blocker {
    /// Create a new blocker
    pub fn new(id: String, task_id: String, blocker_type: BlockerType, description: String) -> Self {
        Self {
            id,
            task_id,
            blocker_type,
            description,
            blocking_task_id: None,
            status: BlockerStatus::Active,
            created_at: Utc::now(),
            resolved_at: None,
            escalated_at: None,
            resolution_notes: None,
        }
    }

    /// Check if the blocker is active
    pub fn is_active(&self) -> bool {
        self.status == BlockerStatus::Active
    }

    /// Check if the blocker is resolved
    pub fn is_resolved(&self) -> bool {
        self.status == BlockerStatus::Resolved
    }

    /// Get duration in hours since created
    pub fn duration_hours(&self) -> f64 {
        let end = self.resolved_at.unwrap_or_else(Utc::now);
        (end - self.created_at).num_minutes() as f64 / 60.0
    }
}

/// Request to create a new blocker
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateBlockerRequest {
    pub task_id: String,
    pub blocker_type: BlockerType,
    pub description: String,
    pub blocking_task_id: Option<String>,
}

/// Blocker with additional context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockerDetail {
    pub blocker: Blocker,
    pub task_title: String,
    pub blocking_task_title: Option<String>,
    pub blocked_tasks: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_blocker_new() {
        let blocker = Blocker::new(
            "B-001".to_string(),
            "T-001".to_string(),
            BlockerType::Technical,
            "Waiting for API spec".to_string(),
        );
        assert!(blocker.is_active());
        assert!(!blocker.is_resolved());
    }

    #[test]
    fn test_blocker_duration() {
        let blocker = Blocker::new(
            "B-001".to_string(),
            "T-001".to_string(),
            BlockerType::Technical,
            "Waiting".to_string(),
        );
        // Duration should be very small (just created)
        assert!(blocker.duration_hours() < 0.1);
    }
}

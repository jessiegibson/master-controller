//! Feature model - organizes tasks by feature/epic

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// Re-export FeatureStatus from state_machine for convenience
pub use crate::state_machine::FeatureStatus;

/// A feature that groups related tasks
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Feature {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub status: FeatureStatus,
    pub color: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Feature {
    /// Create a new feature
    pub fn new(id: String, name: String) -> Self {
        let now = Utc::now();
        Self {
            id,
            name,
            description: None,
            status: FeatureStatus::Active,
            color: None,
            created_at: now,
            updated_at: now,
        }
    }

    /// Check if the feature is active
    pub fn is_active(&self) -> bool {
        self.status == FeatureStatus::Active
    }
}

/// Request to create a new feature
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateFeatureRequest {
    pub name: String,
    pub description: Option<String>,
    pub color: Option<String>,
}

/// Feature summary with task counts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureSummary {
    pub feature: Feature,
    pub total_tasks: i64,
    pub todo_count: i64,
    pub in_progress_count: i64,
    pub blocked_count: i64,
    pub in_qa_count: i64,
    pub done_count: i64,
}

impl FeatureSummary {
    /// Calculate completion rate as a percentage
    pub fn completion_rate(&self) -> f64 {
        if self.total_tasks == 0 {
            0.0
        } else {
            (self.done_count as f64 / self.total_tasks as f64) * 100.0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_feature_new() {
        let feature = Feature::new("F-001".to_string(), "Parser".to_string());
        assert!(feature.is_active());
        assert_eq!(feature.status, FeatureStatus::Active);
    }

    #[test]
    fn test_feature_summary_completion_rate() {
        let feature = Feature::new("F-001".to_string(), "Parser".to_string());
        let summary = FeatureSummary {
            feature,
            total_tasks: 10,
            todo_count: 2,
            in_progress_count: 3,
            blocked_count: 0,
            in_qa_count: 1,
            done_count: 4,
        };
        assert_eq!(summary.completion_rate(), 40.0);
    }
}

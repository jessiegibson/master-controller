//! Agent model

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::state_machine::{AgentStatus, AgentType};

/// An agent in the system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Agent {
    pub id: String,
    pub name: String,
    pub agent_type: AgentType,
    pub status: AgentStatus,
    pub max_concurrent_tasks: i32,
    pub created_at: DateTime<Utc>,
}

impl Agent {
    /// Create a new agent
    pub fn new(id: String, name: String, agent_type: AgentType) -> Self {
        Self {
            id,
            name,
            agent_type,
            status: AgentStatus::Available,
            max_concurrent_tasks: 2,
            created_at: Utc::now(),
        }
    }

    /// Check if the agent is available for new tasks
    pub fn is_available(&self) -> bool {
        self.status == AgentStatus::Available
    }
}

/// Agent workload information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentWorkload {
    pub agent: Agent,
    pub current_tasks: i32,
    pub task_ids: Vec<String>,
    pub tasks_completed_this_sprint: i32,
    pub avg_completion_time_hours: Option<f64>,
}

impl AgentWorkload {
    /// Check if the agent has capacity for more tasks
    pub fn has_capacity(&self) -> bool {
        self.current_tasks < self.agent.max_concurrent_tasks
    }

    /// Get remaining capacity
    pub fn remaining_capacity(&self) -> i32 {
        (self.agent.max_concurrent_tasks - self.current_tasks).max(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_new() {
        let agent = Agent::new(
            "parser_dev".to_string(),
            "Parser Developer".to_string(),
            AgentType::Developer,
        );
        assert!(agent.is_available());
        assert_eq!(agent.max_concurrent_tasks, 2);
    }

    #[test]
    fn test_agent_workload_capacity() {
        let agent = Agent {
            id: "dev1".to_string(),
            name: "Developer 1".to_string(),
            agent_type: AgentType::Developer,
            status: AgentStatus::Available,
            max_concurrent_tasks: 2,
            created_at: Utc::now(),
        };
        let workload = AgentWorkload {
            agent,
            current_tasks: 1,
            task_ids: vec!["T-001".to_string()],
            tasks_completed_this_sprint: 3,
            avg_completion_time_hours: Some(6.5),
        };
        assert!(workload.has_capacity());
        assert_eq!(workload.remaining_capacity(), 1);
    }
}

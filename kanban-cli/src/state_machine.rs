//! Task state machine for validating status transitions

use serde::{Deserialize, Serialize};
use std::fmt;
use std::str::FromStr;
use thiserror::Error;

/// Task status enum representing valid task states
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum TaskStatus {
    Todo,
    InProgress,
    Blocked,
    InQa,
    Done,
}

impl TaskStatus {
    /// Get all valid statuses
    pub fn all() -> &'static [TaskStatus] {
        &[
            TaskStatus::Todo,
            TaskStatus::InProgress,
            TaskStatus::Blocked,
            TaskStatus::InQa,
            TaskStatus::Done,
        ]
    }

    /// Convert to database string representation
    pub fn as_str(&self) -> &'static str {
        match self {
            TaskStatus::Todo => "todo",
            TaskStatus::InProgress => "in-progress",
            TaskStatus::Blocked => "blocked",
            TaskStatus::InQa => "in-qa",
            TaskStatus::Done => "done",
        }
    }
}

impl fmt::Display for TaskStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for TaskStatus {
    type Err = StateMachineError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "todo" => Ok(TaskStatus::Todo),
            "in-progress" | "in_progress" | "inprogress" => Ok(TaskStatus::InProgress),
            "blocked" => Ok(TaskStatus::Blocked),
            "in-qa" | "in_qa" | "inqa" | "review" => Ok(TaskStatus::InQa),
            "done" | "completed" => Ok(TaskStatus::Done),
            _ => Err(StateMachineError::InvalidStatus(s.to_string())),
        }
    }
}

/// Feature status enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum FeatureStatus {
    Active,
    Completed,
    Archived,
}

impl FeatureStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            FeatureStatus::Active => "active",
            FeatureStatus::Completed => "completed",
            FeatureStatus::Archived => "archived",
        }
    }
}

impl fmt::Display for FeatureStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for FeatureStatus {
    type Err = StateMachineError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "active" => Ok(FeatureStatus::Active),
            "completed" => Ok(FeatureStatus::Completed),
            "archived" => Ok(FeatureStatus::Archived),
            _ => Err(StateMachineError::InvalidStatus(s.to_string())),
        }
    }
}

/// Blocker status enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum BlockerStatus {
    Active,
    Resolved,
    Escalated,
}

impl BlockerStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            BlockerStatus::Active => "active",
            BlockerStatus::Resolved => "resolved",
            BlockerStatus::Escalated => "escalated",
        }
    }
}

impl fmt::Display for BlockerStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for BlockerStatus {
    type Err = StateMachineError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "active" => Ok(BlockerStatus::Active),
            "resolved" => Ok(BlockerStatus::Resolved),
            "escalated" => Ok(BlockerStatus::Escalated),
            _ => Err(StateMachineError::InvalidStatus(s.to_string())),
        }
    }
}

/// Blocker type enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum BlockerType {
    Dependency,
    Technical,
    Clarification,
    Resource,
    External,
    Approval,
}

impl BlockerType {
    pub fn as_str(&self) -> &'static str {
        match self {
            BlockerType::Dependency => "dependency",
            BlockerType::Technical => "technical",
            BlockerType::Clarification => "clarification",
            BlockerType::Resource => "resource",
            BlockerType::External => "external",
            BlockerType::Approval => "approval",
        }
    }
}

impl fmt::Display for BlockerType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for BlockerType {
    type Err = StateMachineError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "dependency" => Ok(BlockerType::Dependency),
            "technical" => Ok(BlockerType::Technical),
            "clarification" => Ok(BlockerType::Clarification),
            "resource" => Ok(BlockerType::Resource),
            "external" => Ok(BlockerType::External),
            "approval" => Ok(BlockerType::Approval),
            _ => Err(StateMachineError::InvalidBlockerType(s.to_string())),
        }
    }
}

/// Agent status enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AgentStatus {
    Available,
    Busy,
    Offline,
}

impl AgentStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            AgentStatus::Available => "available",
            AgentStatus::Busy => "busy",
            AgentStatus::Offline => "offline",
        }
    }
}

impl fmt::Display for AgentStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for AgentStatus {
    type Err = StateMachineError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "available" => Ok(AgentStatus::Available),
            "busy" => Ok(AgentStatus::Busy),
            "offline" => Ok(AgentStatus::Offline),
            _ => Err(StateMachineError::InvalidStatus(s.to_string())),
        }
    }
}

/// Agent type enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AgentType {
    Developer,
    Reviewer,
    Architect,
    Manager,
    Specialist,
}

impl AgentType {
    pub fn as_str(&self) -> &'static str {
        match self {
            AgentType::Developer => "developer",
            AgentType::Reviewer => "reviewer",
            AgentType::Architect => "architect",
            AgentType::Manager => "manager",
            AgentType::Specialist => "specialist",
        }
    }
}

impl fmt::Display for AgentType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for AgentType {
    type Err = StateMachineError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "developer" => Ok(AgentType::Developer),
            "reviewer" => Ok(AgentType::Reviewer),
            "architect" => Ok(AgentType::Architect),
            "manager" => Ok(AgentType::Manager),
            "specialist" => Ok(AgentType::Specialist),
            _ => Err(StateMachineError::InvalidAgentType(s.to_string())),
        }
    }
}

/// Errors from the state machine
#[derive(Debug, Error)]
pub enum StateMachineError {
    #[error("Invalid status: {0}")]
    InvalidStatus(String),

    #[error("Invalid blocker type: {0}")]
    InvalidBlockerType(String),

    #[error("Invalid agent type: {0}")]
    InvalidAgentType(String),

    #[error("Invalid transition from '{from}' to '{to}'")]
    InvalidTransition { from: TaskStatus, to: TaskStatus },
}

/// State machine for task status transitions
pub struct StateMachine;

impl StateMachine {
    /// Get valid transitions from a given status
    pub fn valid_transitions(from: &TaskStatus) -> Vec<TaskStatus> {
        match from {
            TaskStatus::Todo => vec![TaskStatus::InProgress],
            TaskStatus::InProgress => vec![TaskStatus::Todo, TaskStatus::Blocked, TaskStatus::InQa],
            TaskStatus::Blocked => vec![TaskStatus::Todo, TaskStatus::InProgress],
            TaskStatus::InQa => vec![TaskStatus::InProgress, TaskStatus::Done],
            TaskStatus::Done => vec![], // Terminal state
        }
    }

    /// Check if a transition is valid
    pub fn can_transition(from: &TaskStatus, to: &TaskStatus) -> bool {
        Self::valid_transitions(from).contains(to)
    }

    /// Attempt to transition, returning an error if invalid
    pub fn transition(from: &TaskStatus, to: &TaskStatus) -> Result<TaskStatus, StateMachineError> {
        if Self::can_transition(from, to) {
            Ok(*to)
        } else {
            Err(StateMachineError::InvalidTransition {
                from: *from,
                to: *to,
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_transitions_from_todo() {
        let transitions = StateMachine::valid_transitions(&TaskStatus::Todo);
        assert_eq!(transitions, vec![TaskStatus::InProgress]);
    }

    #[test]
    fn test_valid_transitions_from_in_progress() {
        let transitions = StateMachine::valid_transitions(&TaskStatus::InProgress);
        assert!(transitions.contains(&TaskStatus::Todo));
        assert!(transitions.contains(&TaskStatus::Blocked));
        assert!(transitions.contains(&TaskStatus::InQa));
        assert!(!transitions.contains(&TaskStatus::Done));
    }

    #[test]
    fn test_valid_transitions_from_done() {
        let transitions = StateMachine::valid_transitions(&TaskStatus::Done);
        assert!(transitions.is_empty());
    }

    #[test]
    fn test_can_transition() {
        assert!(StateMachine::can_transition(
            &TaskStatus::Todo,
            &TaskStatus::InProgress
        ));
        assert!(!StateMachine::can_transition(
            &TaskStatus::Todo,
            &TaskStatus::Done
        ));
        assert!(StateMachine::can_transition(
            &TaskStatus::InQa,
            &TaskStatus::Done
        ));
    }

    #[test]
    fn test_transition_success() {
        let result = StateMachine::transition(&TaskStatus::Todo, &TaskStatus::InProgress);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), TaskStatus::InProgress);
    }

    #[test]
    fn test_transition_failure() {
        let result = StateMachine::transition(&TaskStatus::Todo, &TaskStatus::Done);
        assert!(result.is_err());
    }

    #[test]
    fn test_status_from_str() {
        assert_eq!("todo".parse::<TaskStatus>().unwrap(), TaskStatus::Todo);
        assert_eq!(
            "in-progress".parse::<TaskStatus>().unwrap(),
            TaskStatus::InProgress
        );
        assert_eq!(
            "in_progress".parse::<TaskStatus>().unwrap(),
            TaskStatus::InProgress
        );
        assert_eq!("done".parse::<TaskStatus>().unwrap(), TaskStatus::Done);
    }

    #[test]
    fn test_status_display() {
        assert_eq!(TaskStatus::Todo.to_string(), "todo");
        assert_eq!(TaskStatus::InProgress.to_string(), "in-progress");
        assert_eq!(TaskStatus::Done.to_string(), "done");
    }
}

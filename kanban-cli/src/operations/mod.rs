//! Database operations for kanban entities

pub mod blockers;
pub mod features;
pub mod metrics;
pub mod tasks;

use thiserror::Error;

/// Errors from operations
#[derive(Debug, Error)]
pub enum OperationError {
    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Invalid transition: {0}")]
    InvalidTransition(String),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Dependency error: {0}")]
    Dependency(String),

    #[error("Agent unavailable: {0}")]
    AgentUnavailable(String),
}

pub type Result<T> = std::result::Result<T, OperationError>;

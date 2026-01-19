//! Kanban library for multi-agent orchestration
//!
//! This library provides task management, feature tracking, and agent workload
//! management for the multi-agent software development workflow.

pub mod db;
pub mod models;
pub mod operations;
pub mod state_machine;

pub use db::Database;
pub use models::{Agent, Blocker, Feature, Task, TaskHistory};
pub use operations::{blockers, features, metrics, tasks};
pub use state_machine::{StateMachine, TaskStatus};

//! TUI application state

use crate::db::Database;
use crate::models::{Blocker, Feature, Task};
use crate::operations::{blockers, features, metrics, tasks, OperationError};
use crate::state_machine::TaskStatus;

/// The focused column in the kanban board
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Column {
    Todo,
    InProgress,
    Blocked,
    InQa,
    Done,
}

impl Column {
    pub fn to_status(&self) -> TaskStatus {
        match self {
            Column::Todo => TaskStatus::Todo,
            Column::InProgress => TaskStatus::InProgress,
            Column::Blocked => TaskStatus::Blocked,
            Column::InQa => TaskStatus::InQa,
            Column::Done => TaskStatus::Done,
        }
    }

    pub fn next(&self) -> Column {
        match self {
            Column::Todo => Column::InProgress,
            Column::InProgress => Column::Blocked,
            Column::Blocked => Column::InQa,
            Column::InQa => Column::Done,
            Column::Done => Column::Done,
        }
    }

    pub fn prev(&self) -> Column {
        match self {
            Column::Todo => Column::Todo,
            Column::InProgress => Column::Todo,
            Column::Blocked => Column::InProgress,
            Column::InQa => Column::Blocked,
            Column::Done => Column::InQa,
        }
    }

    pub fn all() -> &'static [Column] {
        &[
            Column::Todo,
            Column::InProgress,
            Column::Blocked,
            Column::InQa,
            Column::Done,
        ]
    }
}

/// Current view mode
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ViewMode {
    Board,
    TaskDetail,
    Help,
}

/// Application state for the TUI
pub struct App {
    /// Current feature (if any)
    pub current_feature: Option<Feature>,

    /// All tasks in the current feature
    pub tasks: Vec<Task>,

    /// Active blockers
    pub blockers: Vec<Blocker>,

    /// Currently selected column
    pub selected_column: Column,

    /// Selected task index within the column
    pub selected_task_index: usize,

    /// Current view mode
    pub view_mode: ViewMode,

    /// Status message to display
    pub status_message: Option<String>,

    /// Feature metrics summary
    pub metrics_summary: Option<String>,
}

impl App {
    /// Create a new app state
    pub fn new(db: &Database) -> Result<Self, OperationError> {
        let mut app = Self {
            current_feature: None,
            tasks: Vec::new(),
            blockers: Vec::new(),
            selected_column: Column::Todo,
            selected_task_index: 0,
            view_mode: ViewMode::Board,
            status_message: None,
            metrics_summary: None,
        };

        // Load the first active feature if any
        let all_features = features::list_features(db, None)?;
        if let Some(feature) = all_features.first() {
            app.load_feature(db, &feature.id)?;
        }

        Ok(app)
    }

    /// Load a feature's data
    pub fn load_feature(&mut self, db: &Database, feature_id: &str) -> Result<(), OperationError> {
        self.current_feature = Some(features::get_feature(db, feature_id)?);
        self.refresh_tasks(db)?;
        self.refresh_blockers(db)?;
        self.update_metrics(db)?;
        Ok(())
    }

    /// Refresh task list
    pub fn refresh_tasks(&mut self, db: &Database) -> Result<(), OperationError> {
        if let Some(feature) = &self.current_feature {
            self.tasks = tasks::list_tasks(db, Some(&feature.id), None, None)?;
        }
        Ok(())
    }

    /// Refresh blocker list
    pub fn refresh_blockers(&mut self, db: &Database) -> Result<(), OperationError> {
        if let Some(feature) = &self.current_feature {
            self.blockers = blockers::list_active_blockers(db, Some(&feature.id))?;
        }
        Ok(())
    }

    /// Update metrics summary
    pub fn update_metrics(&mut self, db: &Database) -> Result<(), OperationError> {
        if let Some(feature) = &self.current_feature {
            let m = metrics::get_feature_metrics(db, &feature.id)?;
            self.metrics_summary = Some(format!(
                "Progress {:.0}% | {}/{} tasks | {} blockers | {:.1}h remaining",
                m.completion_rate * 100.0,
                m.completed_tasks,
                m.total_tasks,
                m.active_blockers,
                m.hours_remaining
            ));
        }
        Ok(())
    }

    /// Get tasks for a specific column
    pub fn tasks_for_column(&self, column: &Column) -> Vec<&Task> {
        let status = column.to_status();
        self.tasks
            .iter()
            .filter(|t| t.status == status)
            .collect()
    }

    /// Get the currently selected task
    pub fn selected_task(&self) -> Option<&Task> {
        let column_tasks = self.tasks_for_column(&self.selected_column);
        column_tasks.get(self.selected_task_index).copied()
    }

    /// Move selection up in current column
    pub fn select_up(&mut self) {
        if self.selected_task_index > 0 {
            self.selected_task_index -= 1;
        }
    }

    /// Move selection down in current column
    pub fn select_down(&mut self) {
        let column_tasks = self.tasks_for_column(&self.selected_column);
        if self.selected_task_index < column_tasks.len().saturating_sub(1) {
            self.selected_task_index += 1;
        }
    }

    /// Move to next column
    pub fn select_next_column(&mut self) {
        self.selected_column = self.selected_column.next();
        self.selected_task_index = 0;
    }

    /// Move to previous column
    pub fn select_prev_column(&mut self) {
        self.selected_column = self.selected_column.prev();
        self.selected_task_index = 0;
    }

    /// Set status message
    pub fn set_status(&mut self, message: impl Into<String>) {
        self.status_message = Some(message.into());
    }

    /// Clear status message
    pub fn clear_status(&mut self) {
        self.status_message = None;
    }
}

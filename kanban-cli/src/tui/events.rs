//! Keyboard event handling for the TUI

use crossterm::event::{KeyCode, KeyEvent};

use crate::db::Database;
use crate::operations::{tasks, OperationError};
use crate::state_machine::{StateMachine, TaskStatus};

use super::app::{App, ViewMode};

/// Handle a key event
pub fn handle_key_event(
    app: &mut App,
    key: KeyEvent,
    db: &Database,
) -> Result<(), OperationError> {
    // Clear status message on any key
    app.clear_status();

    match app.view_mode {
        ViewMode::Board => handle_board_keys(app, key, db),
        ViewMode::TaskDetail => handle_detail_keys(app, key),
        ViewMode::Help => handle_help_keys(app, key),
    }
}

/// Handle keys in board view
fn handle_board_keys(
    app: &mut App,
    key: KeyEvent,
    db: &Database,
) -> Result<(), OperationError> {
    match key.code {
        // Navigation
        KeyCode::Char('j') | KeyCode::Down => {
            app.select_down();
        }
        KeyCode::Char('k') | KeyCode::Up => {
            app.select_up();
        }
        KeyCode::Char('h') | KeyCode::Left => {
            app.select_prev_column();
        }
        KeyCode::Char('l') | KeyCode::Right => {
            app.select_next_column();
        }

        // View task details
        KeyCode::Enter => {
            if app.selected_task().is_some() {
                app.view_mode = ViewMode::TaskDetail;
            }
        }

        // Move task forward (to next valid state)
        KeyCode::Char('m') => {
            if let Some(task) = app.selected_task() {
                let valid = StateMachine::valid_transitions(&task.status);
                if let Some(next_status) = valid.first() {
                    match tasks::update_task_status(db, &task.id, *next_status, "tui") {
                        Ok(_) => {
                            app.refresh_tasks(db)?;
                            app.update_metrics(db)?;
                            app.set_status(format!("Moved to {}", next_status));
                        }
                        Err(e) => {
                            app.set_status(format!("Error: {}", e));
                        }
                    }
                } else {
                    app.set_status("No valid transitions from this state");
                }
            }
        }

        // Move task to in-progress
        KeyCode::Char('p') => {
            if let Some(task) = app.selected_task() {
                if StateMachine::can_transition(&task.status, &TaskStatus::InProgress) {
                    match tasks::update_task_status(db, &task.id, TaskStatus::InProgress, "tui") {
                        Ok(_) => {
                            app.refresh_tasks(db)?;
                            app.update_metrics(db)?;
                            app.set_status("Moved to in-progress");
                        }
                        Err(e) => {
                            app.set_status(format!("Error: {}", e));
                        }
                    }
                } else {
                    app.set_status("Cannot move to in-progress from current state");
                }
            }
        }

        // Move task to done (if in QA)
        KeyCode::Char('d') => {
            if let Some(task) = app.selected_task() {
                if StateMachine::can_transition(&task.status, &TaskStatus::Done) {
                    match tasks::update_task_status(db, &task.id, TaskStatus::Done, "tui") {
                        Ok(_) => {
                            app.refresh_tasks(db)?;
                            app.update_metrics(db)?;
                            app.set_status("Marked as done");
                        }
                        Err(e) => {
                            app.set_status(format!("Error: {}", e));
                        }
                    }
                } else {
                    app.set_status("Cannot mark as done from current state");
                }
            }
        }

        // Show help
        KeyCode::Char('?') => {
            app.view_mode = ViewMode::Help;
        }

        // Refresh
        KeyCode::Char('r') => {
            app.refresh_tasks(db)?;
            app.refresh_blockers(db)?;
            app.update_metrics(db)?;
            app.set_status("Refreshed");
        }

        _ => {}
    }

    Ok(())
}

/// Handle keys in task detail view
fn handle_detail_keys(app: &mut App, key: KeyEvent) -> Result<(), OperationError> {
    match key.code {
        KeyCode::Esc | KeyCode::Char('q') | KeyCode::Enter => {
            app.view_mode = ViewMode::Board;
        }
        _ => {}
    }
    Ok(())
}

/// Handle keys in help view
fn handle_help_keys(app: &mut App, key: KeyEvent) -> Result<(), OperationError> {
    match key.code {
        KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('?') => {
            app.view_mode = ViewMode::Board;
        }
        _ => {}
    }
    Ok(())
}

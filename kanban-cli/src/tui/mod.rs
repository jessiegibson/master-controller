//! TUI module for interactive kanban board

mod app;
mod events;
mod ui;
pub mod widgets;

pub use app::App;

use crate::db::Database;
use crate::operations::OperationError;

use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io;

/// Run the TUI application
pub fn run(db: &Database) -> Result<(), OperationError> {
    // Setup terminal
    enable_raw_mode().map_err(|e| OperationError::Validation(e.to_string()))?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)
        .map_err(|e| OperationError::Validation(e.to_string()))?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal =
        Terminal::new(backend).map_err(|e| OperationError::Validation(e.to_string()))?;

    // Create app state
    let mut app = App::new(db)?;

    // Main loop
    loop {
        terminal
            .draw(|f| ui::draw(f, &mut app))
            .map_err(|e| OperationError::Validation(e.to_string()))?;

        if event::poll(std::time::Duration::from_millis(100))
            .map_err(|e| OperationError::Validation(e.to_string()))?
        {
            if let Event::Key(key) = event::read()
                .map_err(|e| OperationError::Validation(e.to_string()))?
            {
                // Handle quit
                if key.code == KeyCode::Char('q')
                    || (key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL))
                {
                    break;
                }

                // Handle other keys
                events::handle_key_event(&mut app, key, db)?;
            }
        }
    }

    // Restore terminal
    disable_raw_mode().map_err(|e| OperationError::Validation(e.to_string()))?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )
    .map_err(|e| OperationError::Validation(e.to_string()))?;
    terminal
        .show_cursor()
        .map_err(|e| OperationError::Validation(e.to_string()))?;

    Ok(())
}

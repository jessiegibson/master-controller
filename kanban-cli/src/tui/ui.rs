//! UI rendering for the TUI

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

use super::app::{App, Column, ViewMode};
use super::widgets;

/// Main draw function
pub fn draw(f: &mut Frame, app: &mut App) {
    match app.view_mode {
        ViewMode::Board => draw_board(f, app),
        ViewMode::TaskDetail => draw_task_detail(f, app),
        ViewMode::Help => draw_help(f, app),
    }
}

/// Draw the main kanban board view
fn draw_board(f: &mut Frame, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header
            Constraint::Min(10),   // Board
            Constraint::Length(3), // Metrics
            Constraint::Length(1), // Status/help
        ])
        .split(f.area());

    // Header
    draw_header(f, app, chunks[0]);

    // Board columns
    draw_columns(f, app, chunks[1]);

    // Metrics bar
    draw_metrics(f, app, chunks[2]);

    // Status bar
    draw_status_bar(f, app, chunks[3]);
}

/// Draw the header
fn draw_header(f: &mut Frame, app: &App, area: Rect) {
    let feature_name = app
        .current_feature
        .as_ref()
        .map(|f| format!("{} - {}", f.id, f.name))
        .unwrap_or_else(|| "No Feature".to_string());

    let header = Paragraph::new(format!("KANBAN: {}", feature_name))
        .style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" [q]Quit [?]Help "),
        );

    f.render_widget(header, area);
}

/// Draw the kanban columns
fn draw_columns(f: &mut Frame, app: &App, area: Rect) {
    let column_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
        ])
        .split(area);

    for (i, column) in Column::all().iter().enumerate() {
        draw_column(f, app, *column, column_chunks[i]);
    }
}

/// Draw a single column
fn draw_column(f: &mut Frame, app: &App, column: Column, area: Rect) {
    let tasks = app.tasks_for_column(&column);
    let is_selected_column = app.selected_column == column;

    let title = match column {
        Column::Todo => format!("TODO ({})", tasks.len()),
        Column::InProgress => format!("IN PROGRESS ({})", tasks.len()),
        Column::Blocked => format!("BLOCKED ({})", tasks.len()),
        Column::InQa => format!("IN QA ({})", tasks.len()),
        Column::Done => format!("DONE ({})", tasks.len()),
    };

    let border_style = if is_selected_column {
        Style::default().fg(Color::Yellow)
    } else {
        Style::default().fg(Color::DarkGray)
    };

    let items: Vec<ListItem> = tasks
        .iter()
        .enumerate()
        .map(|(i, task)| {
            let is_selected = is_selected_column && i == app.selected_task_index;
            widgets::task_card::render_task_item(task, is_selected)
        })
        .collect();

    let list = List::new(items).block(
        Block::default()
            .title(title)
            .borders(Borders::ALL)
            .border_style(border_style),
    );

    f.render_widget(list, area);
}

/// Draw the metrics bar
fn draw_metrics(f: &mut Frame, app: &App, area: Rect) {
    let metrics_text = app
        .metrics_summary
        .as_deref()
        .unwrap_or("No metrics available");

    let metrics = Paragraph::new(format!("METRICS: {}", metrics_text))
        .style(Style::default().fg(Color::White))
        .block(Block::default().borders(Borders::ALL));

    f.render_widget(metrics, area);
}

/// Draw the status bar
fn draw_status_bar(f: &mut Frame, app: &App, area: Rect) {
    let status = app.status_message.as_deref().unwrap_or(
        "[j/k] Navigate  [h/l] Columns  [Enter] Details  [m] Move  [p] Progress  [d] Done  [r] Refresh",
    );

    let bar = Paragraph::new(status).style(Style::default().fg(Color::DarkGray));

    f.render_widget(bar, area);
}

/// Draw task detail view
fn draw_task_detail(f: &mut Frame, app: &App) {
    let area = centered_rect(60, 80, f.area());

    if let Some(task) = app.selected_task() {
        let mut lines = vec![
            Line::from(vec![
                Span::styled("ID: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::raw(&task.id),
            ]),
            Line::from(vec![
                Span::styled("Title: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::raw(&task.title),
            ]),
            Line::from(vec![
                Span::styled("Status: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::styled(
                    task.status.to_string(),
                    Style::default().fg(status_color(&task.status)),
                ),
            ]),
            Line::from(vec![
                Span::styled("Priority: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::raw(task.priority.to_string()),
            ]),
            Line::from(vec![
                Span::styled("Agent: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::raw(task.assigned_agent.as_deref().unwrap_or("Unassigned")),
            ]),
            Line::from(vec![
                Span::styled("Estimate: ", Style::default().add_modifier(Modifier::BOLD)),
                Span::raw(
                    task.estimated_hours
                        .map(|h| format!("{:.1}h", h))
                        .unwrap_or_else(|| "-".to_string()),
                ),
            ]),
        ];

        if let Some(desc) = &task.description {
            lines.push(Line::from(""));
            lines.push(Line::from(vec![Span::styled(
                "Description:",
                Style::default().add_modifier(Modifier::BOLD),
            )]));
            lines.push(Line::from(desc.as_str()));
        }

        let detail = Paragraph::new(lines)
            .wrap(Wrap { trim: true })
            .block(
                Block::default()
                    .title(" Task Details [Esc to close] ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(Color::Cyan)),
            );

        f.render_widget(detail, area);
    }
}

/// Draw help view
fn draw_help(f: &mut Frame, _app: &App) {
    let area = centered_rect(50, 60, f.area());

    let help_text = vec![
        Line::from(Span::styled(
            "Keyboard Shortcuts",
            Style::default()
                .add_modifier(Modifier::BOLD)
                .fg(Color::Cyan),
        )),
        Line::from(""),
        Line::from("Navigation:"),
        Line::from("  j/↓     Move down in column"),
        Line::from("  k/↑     Move up in column"),
        Line::from("  h/←     Previous column"),
        Line::from("  l/→     Next column"),
        Line::from("  Enter   View task details"),
        Line::from(""),
        Line::from("Actions:"),
        Line::from("  m       Move to next valid state"),
        Line::from("  p       Move to in-progress"),
        Line::from("  d       Mark as done (if in QA)"),
        Line::from("  r       Refresh data"),
        Line::from(""),
        Line::from("General:"),
        Line::from("  ?       Toggle help"),
        Line::from("  q       Quit"),
    ];

    let help = Paragraph::new(help_text).block(
        Block::default()
            .title(" Help [?/Esc to close] ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan)),
    );

    f.render_widget(help, area);
}

/// Helper to create a centered rect
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

/// Get color for status
fn status_color(status: &crate::state_machine::TaskStatus) -> Color {
    match status {
        crate::state_machine::TaskStatus::Todo => Color::White,
        crate::state_machine::TaskStatus::InProgress => Color::Yellow,
        crate::state_machine::TaskStatus::Blocked => Color::Red,
        crate::state_machine::TaskStatus::InQa => Color::Cyan,
        crate::state_machine::TaskStatus::Done => Color::Green,
    }
}

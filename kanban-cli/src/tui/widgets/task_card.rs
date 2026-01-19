//! Task card widget for the kanban board

use ratatui::{
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::ListItem,
};

use crate::models::Task;
use crate::state_machine::TaskStatus;

/// Render a task as a list item for the column
pub fn render_task_item(task: &Task, is_selected: bool) -> ListItem<'static> {
    let mut style = Style::default();
    if is_selected {
        style = style.bg(Color::DarkGray).add_modifier(Modifier::BOLD);
    }

    // Truncate title if needed
    let max_title_len = 18;
    let title = if task.title.len() > max_title_len {
        format!("{}...", &task.title[..max_title_len - 3])
    } else {
        task.title.clone()
    };

    // Build the display lines
    let id_line = Line::from(vec![Span::styled(
        task.id.clone(),
        Style::default()
            .fg(Color::Cyan)
            .add_modifier(Modifier::BOLD),
    )]);

    let title_line = Line::from(vec![Span::raw(title)]);

    // Info line: priority, estimate, agent
    let mut info_parts = vec![format!("P:{}", task.priority)];

    if let Some(est) = task.estimated_hours {
        info_parts.push(format!("E:{:.0}h", est));
    }

    let info_line = Line::from(vec![Span::styled(
        info_parts.join(" "),
        Style::default().fg(Color::DarkGray),
    )]);

    // Agent line if assigned
    let agent_line = if let Some(agent) = &task.assigned_agent {
        Line::from(vec![Span::styled(
            truncate(agent, 15),
            Style::default().fg(agent_color(&task.status)),
        )])
    } else {
        Line::from(vec![Span::styled(
            "Unassigned",
            Style::default().fg(Color::DarkGray),
        )])
    };

    // Combine lines
    let lines = vec![
        id_line,
        title_line,
        info_line,
        agent_line,
        Line::from(""), // Separator
    ];

    ListItem::new(lines).style(style)
}

/// Get color based on task status
fn agent_color(status: &TaskStatus) -> Color {
    match status {
        TaskStatus::Todo => Color::Gray,
        TaskStatus::InProgress => Color::Yellow,
        TaskStatus::Blocked => Color::Red,
        TaskStatus::InQa => Color::Cyan,
        TaskStatus::Done => Color::Green,
    }
}

/// Truncate a string to max length
fn truncate(s: &str, max_len: usize) -> String {
    if s.len() > max_len {
        format!("{}...", &s[..max_len - 3])
    } else {
        s.to_string()
    }
}

//! Output formatting for CLI commands

use crate::models::{AgentWorkload, Blocker, Feature, FeatureSummary, Task, TaskHistory};
use crate::operations::metrics::FeatureMetrics;
use crate::state_machine::TaskStatus;

/// Output format options
#[derive(Debug, Clone, Copy, Default)]
pub enum OutputFormat {
    #[default]
    Table,
    Json,
}

/// Format tasks as a table
pub fn format_tasks_table(tasks: &[Task]) -> String {
    if tasks.is_empty() {
        return "No tasks found.".to_string();
    }

    let mut output = String::new();
    output.push_str(&format!(
        "{:<15} {:<30} {:<12} {:<4} {:<15} {:<6}\n",
        "ID", "TITLE", "STATUS", "PRI", "AGENT", "EST"
    ));
    output.push_str(&"-".repeat(90));
    output.push('\n');

    for task in tasks {
        let title = if task.title.len() > 28 {
            format!("{}...", &task.title[..25])
        } else {
            task.title.clone()
        };
        let agent = task.assigned_agent.as_deref().unwrap_or("-");
        let est = task
            .estimated_hours
            .map(|h| format!("{:.1}h", h))
            .unwrap_or_else(|| "-".to_string());

        output.push_str(&format!(
            "{:<15} {:<30} {:<12} {:<4} {:<15} {:<6}\n",
            task.id,
            title,
            format_status(&task.status),
            task.priority,
            agent,
            est
        ));
    }

    output
}

/// Format a single task detail
pub fn format_task_detail(task: &Task, dependencies: &[Task], history: &[TaskHistory]) -> String {
    let mut output = String::new();

    output.push_str(&format!("Task: {}\n", task.id));
    output.push_str(&"-".repeat(50));
    output.push('\n');
    output.push_str(&format!("Title:       {}\n", task.title));
    output.push_str(&format!("Feature:     {}\n", task.feature_id));
    output.push_str(&format!("Status:      {}\n", format_status(&task.status)));
    output.push_str(&format!("Priority:    {}\n", task.priority));
    output.push_str(&format!(
        "Agent:       {}\n",
        task.assigned_agent.as_deref().unwrap_or("Unassigned")
    ));
    output.push_str(&format!(
        "Estimate:    {}\n",
        task.estimated_hours
            .map(|h| format!("{:.1}h", h))
            .unwrap_or_else(|| "Not set".to_string())
    ));
    output.push_str(&format!(
        "Actual:      {}\n",
        task.actual_hours
            .map(|h| format!("{:.1}h", h))
            .unwrap_or_else(|| "-".to_string())
    ));

    if let Some(desc) = &task.description {
        output.push('\n');
        output.push_str("Description:\n");
        output.push_str(desc);
        output.push('\n');
    }

    if !dependencies.is_empty() {
        output.push('\n');
        output.push_str("Dependencies:\n");
        for dep in dependencies {
            output.push_str(&format!(
                "  - {} ({}) [{}]\n",
                dep.id,
                dep.title,
                format_status(&dep.status)
            ));
        }
    }

    if !history.is_empty() {
        output.push('\n');
        output.push_str("History:\n");
        for h in history.iter().take(10) {
            output.push_str(&format!(
                "  {} {} {} -> {} (by {})\n",
                h.changed_at.format("%Y-%m-%d %H:%M"),
                h.field_changed,
                h.old_value.as_deref().unwrap_or("-"),
                h.new_value.as_deref().unwrap_or("-"),
                h.changed_by
            ));
        }
    }

    output
}

/// Format status with color codes (for terminal)
pub fn format_status(status: &TaskStatus) -> String {
    match status {
        TaskStatus::Todo => "todo".to_string(),
        TaskStatus::InProgress => "\x1b[33min-progress\x1b[0m".to_string(),
        TaskStatus::Blocked => "\x1b[31mblocked\x1b[0m".to_string(),
        TaskStatus::InQa => "\x1b[36min-qa\x1b[0m".to_string(),
        TaskStatus::Done => "\x1b[32mdone\x1b[0m".to_string(),
    }
}

/// Format features as a table
pub fn format_features_table(features: &[Feature]) -> String {
    if features.is_empty() {
        return "No features found.".to_string();
    }

    let mut output = String::new();
    output.push_str(&format!(
        "{:<25} {:<35} {:<10} {:<10}\n",
        "ID", "NAME", "STATUS", "COLOR"
    ));
    output.push_str(&"-".repeat(85));
    output.push('\n');

    for feature in features {
        let name = if feature.name.len() > 33 {
            format!("{}...", &feature.name[..30])
        } else {
            feature.name.clone()
        };

        output.push_str(&format!(
            "{:<25} {:<35} {:<10} {:<10}\n",
            feature.id,
            name,
            feature.status,
            feature.color.as_deref().unwrap_or("-")
        ));
    }

    output
}

/// Format feature summary
pub fn format_feature_summary(summary: &FeatureSummary) -> String {
    let mut output = String::new();

    output.push_str(&format!("Feature: {} - {}\n", summary.feature.id, summary.feature.name));
    output.push_str(&"-".repeat(50));
    output.push('\n');

    if let Some(desc) = &summary.feature.description {
        output.push_str(&format!("Description: {}\n\n", desc));
    }

    output.push_str(&format!("Status: {}\n\n", summary.feature.status));

    output.push_str("Task Breakdown:\n");
    output.push_str(&format!("  Total:       {}\n", summary.total_tasks));
    output.push_str(&format!("  Todo:        {}\n", summary.todo_count));
    output.push_str(&format!("  In Progress: {}\n", summary.in_progress_count));
    output.push_str(&format!("  Blocked:     {}\n", summary.blocked_count));
    output.push_str(&format!("  In QA:       {}\n", summary.in_qa_count));
    output.push_str(&format!("  Done:        {}\n", summary.done_count));
    output.push_str(&format!("\nCompletion: {:.1}%\n", summary.completion_rate()));

    output
}

/// Format feature metrics
pub fn format_feature_metrics(metrics: &FeatureMetrics) -> String {
    let mut output = String::new();

    output.push_str(&format!("Metrics for Feature: {}\n", metrics.feature_id));
    output.push_str(&"-".repeat(50));
    output.push('\n');

    output.push_str("\nProgress:\n");
    output.push_str(&format!(
        "  Completed: {}/{} ({:.1}%)\n",
        metrics.completed_tasks,
        metrics.total_tasks,
        metrics.completion_rate * 100.0
    ));

    output.push_str("\nEffort:\n");
    output.push_str(&format!("  Estimated: {:.1}h\n", metrics.estimated_hours));
    output.push_str(&format!("  Actual:    {:.1}h\n", metrics.actual_hours));
    output.push_str(&format!("  Remaining: {:.1}h\n", metrics.hours_remaining));

    output.push_str("\nHealth:\n");
    output.push_str(&format!("  Blocked tasks:   {}\n", metrics.blocked_tasks));
    output.push_str(&format!("  Active blockers: {}\n", metrics.active_blockers));

    output
}

/// Format blockers as a table
pub fn format_blockers_table(blockers: &[Blocker]) -> String {
    if blockers.is_empty() {
        return "No blockers found.".to_string();
    }

    let mut output = String::new();
    output.push_str(&format!(
        "{:<8} {:<15} {:<12} {:<35} {:<8}\n",
        "ID", "TASK", "TYPE", "DESCRIPTION", "STATUS"
    ));
    output.push_str(&"-".repeat(85));
    output.push('\n');

    for blocker in blockers {
        let desc = if blocker.description.len() > 33 {
            format!("{}...", &blocker.description[..30])
        } else {
            blocker.description.clone()
        };

        output.push_str(&format!(
            "{:<8} {:<15} {:<12} {:<35} {:<8}\n",
            blocker.id, blocker.task_id, blocker.blocker_type, desc, blocker.status
        ));
    }

    output
}

/// Format agents as a table
pub fn format_agents_table(agents: &[AgentWorkload]) -> String {
    if agents.is_empty() {
        return "No agents found.".to_string();
    }

    let mut output = String::new();
    output.push_str(&format!(
        "{:<25} {:<25} {:<12} {:<10} {:<10}\n",
        "ID", "NAME", "TYPE", "TASKS", "STATUS"
    ));
    output.push_str(&"-".repeat(85));
    output.push('\n');

    for workload in agents {
        let capacity = format!(
            "{}/{}",
            workload.current_tasks, workload.agent.max_concurrent_tasks
        );
        output.push_str(&format!(
            "{:<25} {:<25} {:<12} {:<10} {:<10}\n",
            workload.agent.id,
            workload.agent.name,
            workload.agent.agent_type,
            capacity,
            workload.agent.status
        ));
    }

    output
}

/// Format agent workload detail
pub fn format_agent_workload(workload: &AgentWorkload) -> String {
    let mut output = String::new();

    output.push_str(&format!("Agent: {} - {}\n", workload.agent.id, workload.agent.name));
    output.push_str(&"-".repeat(50));
    output.push('\n');

    output.push_str(&format!("Type:   {}\n", workload.agent.agent_type));
    output.push_str(&format!("Status: {}\n", workload.agent.status));
    output.push_str(&format!(
        "Tasks:  {}/{}\n",
        workload.current_tasks, workload.agent.max_concurrent_tasks
    ));

    if !workload.task_ids.is_empty() {
        output.push_str("\nCurrent Tasks:\n");
        for task_id in &workload.task_ids {
            output.push_str(&format!("  - {}\n", task_id));
        }
    }

    output.push_str(&format!(
        "\nCompleted (all time): {}\n",
        workload.tasks_completed_this_sprint
    ));
    if let Some(avg) = workload.avg_completion_time_hours {
        output.push_str(&format!("Avg completion time: {:.1}h\n", avg));
    }

    output
}

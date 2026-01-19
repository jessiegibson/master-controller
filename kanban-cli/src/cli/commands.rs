//! CLI command definitions using clap

use clap::{Parser, Subcommand};

use crate::db::Database;
use crate::models::{CreateBlockerRequest, CreateFeatureRequest, TaskBuilder};
use crate::operations::{blockers, features, metrics, tasks, OperationError};
use crate::state_machine::{BlockerType, FeatureStatus, TaskStatus};

use super::output::*;

/// Kanban CLI - Task management for multi-agent orchestration
#[derive(Parser)]
#[command(name = "kanban")]
#[command(about = "A CLI/TUI kanban board for multi-agent orchestration")]
#[command(version)]
pub struct Cli {
    /// Path to the database file
    #[arg(long, default_value = "kanban/tasks.db")]
    pub db: String,

    /// Output format
    #[arg(long, default_value = "table")]
    pub format: String,

    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Task management commands
    Task {
        #[command(subcommand)]
        command: TaskCommands,
    },
    /// Feature management commands
    Feature {
        #[command(subcommand)]
        command: FeatureCommands,
    },
    /// Blocker management commands
    Blocker {
        #[command(subcommand)]
        command: BlockerCommands,
    },
    /// Agent management commands
    Agent {
        #[command(subcommand)]
        command: AgentCommands,
    },
    /// Launch interactive TUI
    Tui,
    /// Alias for tui
    Board,
    /// Initialize the database
    Init,
}

#[derive(Subcommand)]
pub enum TaskCommands {
    /// List tasks
    List {
        /// Filter by feature ID
        #[arg(long)]
        feature: Option<String>,
        /// Filter by status
        #[arg(long)]
        status: Option<String>,
        /// Filter by assigned agent
        #[arg(long)]
        agent: Option<String>,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Create a new task
    Create {
        /// Task title
        title: String,
        /// Feature ID
        #[arg(long)]
        feature: String,
        /// Priority (lower is higher priority)
        #[arg(long, default_value = "100")]
        priority: i32,
        /// Estimated hours
        #[arg(long)]
        estimate: Option<f64>,
        /// Task description
        #[arg(long)]
        description: Option<String>,
        /// Task this depends on
        #[arg(long)]
        depends_on: Option<String>,
    },
    /// Show task details
    Show {
        /// Task ID
        task_id: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Move task to new status
    Move {
        /// Task ID
        task_id: String,
        /// New status
        status: String,
    },
    /// Assign task to agent
    Assign {
        /// Task ID
        task_id: String,
        /// Agent ID
        agent_id: String,
    },
    /// Update task fields
    Update {
        /// Task ID
        task_id: String,
        /// New priority
        #[arg(long)]
        priority: Option<i32>,
    },
    /// Show task history
    History {
        /// Task ID
        task_id: String,
    },
}

#[derive(Subcommand)]
pub enum FeatureCommands {
    /// List features
    List {
        /// Filter by status
        #[arg(long)]
        status: Option<String>,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Create a new feature
    Create {
        /// Feature name
        name: String,
        /// Feature description
        #[arg(long)]
        description: Option<String>,
        /// Color for display
        #[arg(long)]
        color: Option<String>,
    },
    /// Show feature details
    Show {
        /// Feature ID
        feature_id: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Show feature metrics
    Metrics {
        /// Feature ID (or "all" for overall metrics)
        feature_id: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Archive a feature
    Archive {
        /// Feature ID
        feature_id: String,
    },
    /// Complete a feature
    Complete {
        /// Feature ID
        feature_id: String,
    },
}

#[derive(Subcommand)]
pub enum BlockerCommands {
    /// List blockers
    List {
        /// Filter by feature
        #[arg(long)]
        feature: Option<String>,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Add a blocker to a task
    Add {
        /// Task ID to block
        task_id: String,
        /// Blocker type
        #[arg(long, default_value = "technical")]
        blocker_type: String,
        /// Description of the blocker
        description: String,
        /// Task ID that is blocking (for dependency blockers)
        #[arg(long)]
        blocks: Option<String>,
    },
    /// Resolve a blocker
    Resolve {
        /// Blocker ID
        blocker_id: String,
        /// Resolution notes
        #[arg(long)]
        notes: Option<String>,
    },
    /// Escalate a blocker
    Escalate {
        /// Blocker ID
        blocker_id: String,
    },
}

#[derive(Subcommand)]
pub enum AgentCommands {
    /// List all agents
    List {
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Show agent workload
    Workload {
        /// Agent ID
        agent_id: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// List agents with available capacity
    Available {
        /// Filter by type
        #[arg(long)]
        agent_type: Option<String>,
    },
}

impl Cli {
    /// Execute the CLI command
    pub fn execute(&self) -> Result<(), OperationError> {
        // Ensure database directory exists
        if let Some(parent) = std::path::Path::new(&self.db).parent() {
            std::fs::create_dir_all(parent).ok();
        }

        let db = Database::open(&self.db)?;
        let json = self.format == "json";

        match &self.command {
            Commands::Init => {
                println!("Database initialized at: {}", self.db);
                Ok(())
            }
            Commands::Tui | Commands::Board => {
                // TUI will be implemented separately
                println!("Launching TUI...");
                crate::tui::run(&db)
            }
            Commands::Task { command } => self.handle_task_command(&db, command, json),
            Commands::Feature { command } => self.handle_feature_command(&db, command, json),
            Commands::Blocker { command } => self.handle_blocker_command(&db, command, json),
            Commands::Agent { command } => self.handle_agent_command(&db, command, json),
        }
    }

    fn handle_task_command(
        &self,
        db: &Database,
        command: &TaskCommands,
        _global_json: bool,
    ) -> Result<(), OperationError> {
        match command {
            TaskCommands::List {
                feature,
                status,
                agent,
                json,
            } => {
                let status = status.as_ref().and_then(|s| s.parse().ok());
                let task_list = tasks::list_tasks(db, feature.as_deref(), status, agent.as_deref())?;

                if *json {
                    println!("{}", serde_json::to_string_pretty(&task_list).unwrap());
                } else {
                    print!("{}", format_tasks_table(&task_list));
                }
            }
            TaskCommands::Create {
                title,
                feature,
                priority,
                estimate,
                description,
                depends_on,
            } => {
                let mut builder = TaskBuilder::new()
                    .feature_id(feature)
                    .title(title)
                    .priority(*priority);

                if let Some(est) = estimate {
                    builder = builder.estimated_hours(*est);
                }
                if let Some(desc) = description {
                    builder = builder.description(desc);
                }
                if let Some(dep) = depends_on {
                    builder = builder.depends_on(dep);
                }

                let request = builder
                    .build()
                    .map_err(|e| OperationError::Validation(e.to_string()))?;
                let task = tasks::create_task(db, request)?;
                println!("Created task: {}", task.id);
            }
            TaskCommands::Show { task_id, json } => {
                let task = tasks::get_task(db, task_id)?;
                let deps = tasks::get_task_dependencies(db, task_id)?;
                let history = tasks::get_task_history(db, task_id)?;

                if *json {
                    println!("{}", serde_json::to_string_pretty(&task).unwrap());
                } else {
                    print!("{}", format_task_detail(&task, &deps, &history));
                }
            }
            TaskCommands::Move { task_id, status } => {
                let new_status: TaskStatus = status
                    .parse()
                    .map_err(|_| OperationError::Validation(format!("Invalid status: {}", status)))?;
                let task = tasks::update_task_status(db, task_id, new_status, "cli")?;
                println!("Moved {} to {}", task.id, task.status);
            }
            TaskCommands::Assign { task_id, agent_id } => {
                let task = tasks::assign_task(db, task_id, agent_id, "cli")?;
                println!(
                    "Assigned {} to {}",
                    task.id,
                    task.assigned_agent.unwrap_or_default()
                );
            }
            TaskCommands::Update { task_id, priority } => {
                if let Some(p) = priority {
                    let task = tasks::update_task_priority(db, task_id, *p, "cli")?;
                    println!("Updated {} priority to {}", task.id, task.priority);
                }
            }
            TaskCommands::History { task_id } => {
                let history = tasks::get_task_history(db, task_id)?;
                for h in history {
                    println!(
                        "{} {} {} -> {} (by {})",
                        h.changed_at.format("%Y-%m-%d %H:%M"),
                        h.field_changed,
                        h.old_value.as_deref().unwrap_or("-"),
                        h.new_value.as_deref().unwrap_or("-"),
                        h.changed_by
                    );
                }
            }
        }
        Ok(())
    }

    fn handle_feature_command(
        &self,
        db: &Database,
        command: &FeatureCommands,
        _global_json: bool,
    ) -> Result<(), OperationError> {
        match command {
            FeatureCommands::List { status, json } => {
                let status = status.as_ref().and_then(|s| s.parse().ok());
                let feature_list = features::list_features(db, status)?;

                if *json {
                    println!("{}", serde_json::to_string_pretty(&feature_list).unwrap());
                } else {
                    print!("{}", format_features_table(&feature_list));
                }
            }
            FeatureCommands::Create {
                name,
                description,
                color,
            } => {
                let request = CreateFeatureRequest {
                    name: name.clone(),
                    description: description.clone(),
                    color: color.clone(),
                };
                let feature = features::create_feature(db, request)?;
                println!("Created feature: {}", feature.id);
            }
            FeatureCommands::Show { feature_id, json } => {
                let summary = features::get_feature_summary(db, feature_id)?;

                if *json {
                    println!("{}", serde_json::to_string_pretty(&summary).unwrap());
                } else {
                    print!("{}", format_feature_summary(&summary));
                }
            }
            FeatureCommands::Metrics { feature_id, json } => {
                let feature_metrics = if feature_id == "all" {
                    metrics::get_overall_metrics(db)?
                } else {
                    metrics::get_feature_metrics(db, feature_id)?
                };

                if *json {
                    println!("{}", serde_json::to_string_pretty(&feature_metrics).unwrap());
                } else {
                    print!("{}", format_feature_metrics(&feature_metrics));
                }
            }
            FeatureCommands::Archive { feature_id } => {
                let feature = features::update_feature_status(db, feature_id, FeatureStatus::Archived)?;
                println!("Archived feature: {}", feature.id);
            }
            FeatureCommands::Complete { feature_id } => {
                let feature = features::update_feature_status(db, feature_id, FeatureStatus::Completed)?;
                println!("Completed feature: {}", feature.id);
            }
        }
        Ok(())
    }

    fn handle_blocker_command(
        &self,
        db: &Database,
        command: &BlockerCommands,
        _global_json: bool,
    ) -> Result<(), OperationError> {
        match command {
            BlockerCommands::List { feature, json } => {
                let blocker_list = blockers::list_active_blockers(db, feature.as_deref())?;

                if *json {
                    println!("{}", serde_json::to_string_pretty(&blocker_list).unwrap());
                } else {
                    print!("{}", format_blockers_table(&blocker_list));
                }
            }
            BlockerCommands::Add {
                task_id,
                blocker_type,
                description,
                blocks,
            } => {
                let bt: BlockerType = blocker_type.parse().map_err(|_| {
                    OperationError::Validation(format!("Invalid blocker type: {}", blocker_type))
                })?;

                let request = CreateBlockerRequest {
                    task_id: task_id.clone(),
                    blocker_type: bt,
                    description: description.clone(),
                    blocking_task_id: blocks.clone(),
                };
                let blocker = blockers::add_blocker(db, request)?;
                println!("Added blocker: {}", blocker.id);
            }
            BlockerCommands::Resolve { blocker_id, notes } => {
                let blocker = blockers::resolve_blocker(db, blocker_id, notes.as_deref())?;
                println!("Resolved blocker: {}", blocker.id);
            }
            BlockerCommands::Escalate { blocker_id } => {
                let blocker = blockers::escalate_blocker(db, blocker_id)?;
                println!("Escalated blocker: {}", blocker.id);
            }
        }
        Ok(())
    }

    fn handle_agent_command(
        &self,
        db: &Database,
        command: &AgentCommands,
        _global_json: bool,
    ) -> Result<(), OperationError> {
        match command {
            AgentCommands::List { json } => {
                let agents = metrics::list_agents(db)?;

                if *json {
                    println!("{}", serde_json::to_string_pretty(&agents).unwrap());
                } else {
                    print!("{}", format_agents_table(&agents));
                }
            }
            AgentCommands::Workload { agent_id, json } => {
                let workload = metrics::get_agent_workload(db, agent_id)?;

                if *json {
                    println!("{}", serde_json::to_string_pretty(&workload).unwrap());
                } else {
                    print!("{}", format_agent_workload(&workload));
                }
            }
            AgentCommands::Available { agent_type } => {
                let at = agent_type.as_ref().and_then(|t| t.parse().ok());
                let agents = metrics::get_available_agents(db, at)?;
                print!("{}", format_agents_table(&agents));
            }
        }
        Ok(())
    }
}

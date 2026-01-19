//! Kanban CLI - Task management for multi-agent orchestration

use clap::Parser;

mod cli;
mod db;
mod models;
mod operations;
mod state_machine;
mod tui;

use cli::Cli;

fn main() {
    let cli = Cli::parse();

    if let Err(e) = cli.execute() {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}

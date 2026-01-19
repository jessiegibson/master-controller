//! SQLite schema definition for the kanban database

/// SQL schema for initializing the kanban database
pub const SCHEMA_SQL: &str = r#"
-- Features table (replaces sprints - organizes tasks by feature/epic)
CREATE TABLE IF NOT EXISTS features (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    color TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    feature_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    priority INTEGER NOT NULL DEFAULT 100,
    assigned_agent TEXT,
    estimated_hours REAL,
    actual_hours REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES features(id)
);

-- Task dependencies
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    PRIMARY KEY (task_id, depends_on_task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id)
);

-- Blockers table
CREATE TABLE IF NOT EXISTS blockers (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    blocking_task_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    escalated_at TIMESTAMP,
    resolution_notes TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (blocking_task_id) REFERENCES tasks(id)
);

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    max_concurrent_tasks INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task history (audit trail)
CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    field_changed TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Comments table
CREATE TABLE IF NOT EXISTS task_comments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Workflow runs
CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    feature_id TEXT,
    status TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES features(id)
);

-- Agent executions
CREATE TABLE IF NOT EXISTS agent_executions (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL,
    attempt_number INTEGER DEFAULT 1,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    output_path TEXT,
    output_valid BOOLEAN,
    error_message TEXT,
    context_token_count INTEGER,
    response_token_count INTEGER,
    duration_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Workflow checkpoints
CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL,
    checkpoint_type TEXT NOT NULL,
    checkpoint_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_feature ON tasks(feature_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(assigned_agent);
CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id);
CREATE INDEX IF NOT EXISTS idx_blockers_task ON blockers(task_id);
CREATE INDEX IF NOT EXISTS idx_blockers_status ON blockers(status);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
"#;

/// SQL for inserting default agents
pub const DEFAULT_AGENTS_SQL: &str = r#"
INSERT OR IGNORE INTO agents (id, name, type, status, max_concurrent_tasks) VALUES
('requirements_gatherer', 'Requirements Gatherer', 'specialist', 'available', 1),
('product_roadmap_planner', 'Product Roadmap Planner', 'specialist', 'available', 1),
('system_architect', 'System Architect', 'architect', 'available', 1),
('data_architect', 'Data Architect', 'architect', 'available', 1),
('security_architect', 'Security Architect', 'architect', 'available', 1),
('ml_architect', 'ML Architect', 'architect', 'available', 1),
('cli_ux_designer', 'CLI UX Designer', 'specialist', 'available', 1),
('rust_scaffolder', 'Rust Scaffolder', 'developer', 'available', 1),
('parser_developer', 'Parser Developer', 'developer', 'available', 2),
('categorization_developer', 'Categorization Developer', 'developer', 'available', 2),
('duckdb_developer', 'DuckDB Developer', 'developer', 'available', 2),
('encryption_developer', 'Encryption Developer', 'developer', 'available', 2),
('cli_developer', 'CLI Developer', 'developer', 'available', 2),
('code_reviewer', 'Code Reviewer', 'reviewer', 'available', 3),
('staff_engineer_rust', 'Staff Engineer Rust', 'reviewer', 'available', 2),
('staff_engineer_python', 'Staff Engineer Python', 'reviewer', 'available', 2),
('debugger', 'Debugger', 'specialist', 'available', 3),
('project_manager', 'Project Manager', 'manager', 'available', 1),
('repository_librarian', 'Repository Librarian', 'specialist', 'available', 2),
('consulting_cpa', 'Consulting CPA', 'specialist', 'available', 1),
('test_developer', 'Test Developer', 'developer', 'available', 2),
('documentation_writer', 'Documentation Writer', 'specialist', 'available', 2),
('financial_calculator_developer', 'Financial Calculator Developer', 'developer', 'available', 2),
('ml_engineer', 'ML Engineer', 'developer', 'available', 2),
('prompt_skill_engineer', 'Prompt/Skill Engineer', 'specialist', 'available', 2),
('infrastructure_agent', 'Infrastructure Agent', 'specialist', 'available', 2),
('workflow_orchestrator', 'Workflow Orchestrator', 'manager', 'available', 1),
('kanban_manager', 'Kanban Manager', 'manager', 'available', 1),
('context_manager', 'Context Manager', 'manager', 'available', 1),
('output_validator', 'Output Validator', 'specialist', 'available', 3)
"#;

# Repository Structure Analysis & Recommendations

## Current Structure Assessment

Your multi-agent orchestrator project has grown organically and needs reorganization for better maintainability and clarity. Here's my analysis and recommendations:

## Current Issues Identified

1. **Mixed concerns in root directory** - orchestrator, CLIs, and prompts all at root level
2. **Unclear separation** between the orchestrator system and the finance CLI product
3. **Workflow artifacts scattered** - execution state mixed with source code
4. **No clear .gitignore strategy** for different components
5. **Branch management unclear** for multi-component project

## Recommended Repository Structure

### Option 1: Monorepo with Clear Separation (Recommended)

```
finance-cli-project/
├── .github/
│   ├── workflows/                    # CI/CD for all components
│   │   ├── finance-cli.yml          # Finance CLI tests/build
│   │   ├── orchestrator.yml         # Orchestrator tests/build
│   │   ├── kanban-cli.yml          # Kanban CLI tests/build
│   │   └── integration.yml         # Cross-component integration
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore                       # Root gitignore
├── README.md                        # Project overview
├── CHANGELOG.md                     # Unified changelog
├── LICENSE
├── 
├── finance-cli/                     # Primary product (Rust)
│   ├── src/
│   ├── tests/
│   ├── docs/
│   ├── Cargo.toml
│   ├── README.md
│   └── .gitignore                   # Finance CLI specific
├── 
├── orchestrator/                    # Multi-agent orchestration system (Python)
│   ├── src/
│   │   ├── orchestrator/
│   │   ├── context/
│   │   ├── validation/
│   │   └── integrations/
│   ├── agents/
│   │   ├── prompts/                 # All 32 agent prompts
│   │   │   ├── system_architect.md
│   │   │   ├── staff_engineer.md
│   │   │   ├── rust_developer.md
│   │   │   └── ...
│   │   └── config/                  # Agent configurations
│   ├── tests/
│   ├── docs/
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── README.md
│   └── .gitignore                   # Orchestrator specific
├── 
├── kanban-cli/                      # Kanban management tool (Rust)
│   ├── src/
│   ├── tests/
│   ├── Cargo.toml
│   ├── README.md
│   └── .gitignore                   # Kanban CLI specific
├── 
├── workspace/                       # Execution artifacts & temporary files
│   ├── .gitignore                   # Ignore most content
│   ├── artifacts/                   # Agent outputs (gitignored)
│   ├── state/                       # Execution state (gitignored)
│   ├── logs/                        # Execution logs (gitignored)
│   └── kanban/                      # Kanban database (persistent)
│       └── kanban.db
├── 
├── docs/                           # Project-wide documentation
│   ├── architecture/               # System architecture
│   ├── development/                # Development guides
│   │   ├── agent-development.md
│   │   ├── testing.md
│   │   └── deployment.md
│   └── user-guides/                # End-user documentation
└── 
└── scripts/                        # Build and utility scripts
    ├── setup.sh
    ├── build-all.sh
    ├── test-all.sh
    └── clean-workspace.sh
```

### Option 2: Separate Repositories (Alternative)

If components are truly independent:

```
finance-cli/                        # Product repository
orchestrator/                       # Orchestrator repository  
kanban-cli/                         # Kanban tool repository
finance-cli-workspace/              # Shared workspace (optional)
```

## Recommended .gitignore Strategy

### Root .gitignore
```gitignore
# Build outputs
target/
dist/
build/
*.egg-info/

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Environment files
.env
.env.local

# Logs (unless specifically needed)
*.log

# Temporary files
tmp/
temp/
.tmp/

# Workspace artifacts (most should be ignored)
workspace/artifacts/
workspace/state/
workspace/logs/
```

### finance-cli/.gitignore
```gitignore
# Rust specific
target/
Cargo.lock  # Include if this is a binary, exclude if library

# Test artifacts
test-data/
test-output/

# Local development
.env
config.local.toml

# Documentation builds
docs/build/
```

### orchestrator/.gitignore
```gitignore
# Python specific
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Local development
.env
config.local.json

# Agent outputs (development only)
debug-outputs/
```

### workspace/.gitignore
```gitignore
# Ignore most workspace content
artifacts/
state/
logs/
*.tmp
*.temp

# Keep kanban database
!kanban/
!kanban/kanban.db

# Keep important templates
!templates/
```

## Branch Management Strategy

### Recommended: Feature Branch Workflow

Given your multi-component project, use a structured branching strategy:

```
main (stable)
├── feature/S1-08-finance-cli-parser     # Finance CLI features
├── feature/S1-08-orchestrator-context   # Orchestrator features  
├── feature/S1-08-kanban-cli-reports     # Kanban CLI features
├── feature/S1-08-integration-tests      # Cross-component features
├── fix/S1-08-orchestrator-memory-leak   # Bug fixes
└── release/v0.1.0                       # Release preparation
```

### Branch Naming Convention

**Pattern**: `<type>/<sprint>-<component>-<description>`

| Type | Component | Example |
|------|-----------|---------|
| `feature` | `finance-cli` | `feature/S1-08-finance-cli-csv-parser` |
| `feature` | `orchestrator` | `feature/S1-08-orchestrator-agent-context` |
| `feature` | `kanban-cli` | `feature/S1-08-kanban-cli-reports` |
| `feature` | `integration` | `feature/S1-08-integration-e2e-tests` |
| `fix` | `finance-cli` | `fix/S1-08-finance-cli-null-amounts` |
| `docs` | `project` | `docs/S1-08-project-readme-update` |

### Component-Specific CI/CD

```yaml
# .github/workflows/finance-cli.yml
name: Finance CLI
on:
  push:
    paths: 
      - 'finance-cli/**'
      - '.github/workflows/finance-cli.yml'
  pull_request:
    paths:
      - 'finance-cli/**'

# .github/workflows/orchestrator.yml  
name: Orchestrator
on:
  push:
    paths:
      - 'orchestrator/**'
      - '.github/workflows/orchestrator.yml'
  pull_request:
    paths:
      - 'orchestrator/**'
```

## Migration Plan

### Phase 1: Reorganize Structure
1. **Create new directory structure**
2. **Move existing files to appropriate locations**:
   - `/prompts/` → `orchestrator/agents/prompts/`
   - `/orchestrator/` → `orchestrator/src/orchestrator/`
   - `/kanban-cli/` → `kanban-cli/` (stays)
   - `/finance-cli/` → `finance-cli/` (stays)
   - `/workflow/` → `workspace/`

### Phase 2: Update Configuration
3. **Create component-specific .gitignore files**
4. **Update import paths in orchestrator code**
5. **Update CI/CD workflows for new structure**
6. **Create component README files**

### Phase 3: Clean Up
7. **Remove obsolete files and directories**
8. **Update documentation links**
9. **Test all components work with new structure**
10. **Clean up workspace artifacts**

## Immediate Actions Needed

### 1. Workspace Cleanup
```bash
# Clean up old artifacts (be careful!)
rm -rf workspace/artifacts/system_architect/  # After backing up if needed
rm -rf workspace/artifacts/rust_scaffolder/   # After backing up if needed

# Keep only essential workspace files
mkdir -p workspace/{artifacts,state,logs,kanban}
```

### 2. Create Component .gitignores
```bash
# Finance CLI
echo "target/\n*.log\ntest-data/\n.env" > finance-cli/.gitignore

# Orchestrator  
echo "__pycache__/\n*.pyc\nvenv/\ndebug-outputs/\n.env" > orchestrator/.gitignore

# Workspace
echo "artifacts/\nstate/\nlogs/\n*.tmp\n!kanban/" > workspace/.gitignore
```

### 3. Update Remote Configuration
```bash
# Verify your remote setup
git remote -v

# If needed, update remote URL for new structure
git remote set-url github <new-url>
```

## Benefits of This Structure

1. **Clear Separation of Concerns**: Each component has its own space
2. **Independent Development**: Teams can work on components independently  
3. **Proper Artifact Management**: Workspace clearly separated from source
4. **Scalable CI/CD**: Component-specific pipelines
5. **Better Documentation**: Component-specific docs with project overview
6. **Flexible Deployment**: Can deploy components independently if needed

## Recommended Next Steps

1. **Backup current state** before making changes
2. **Implement the reorganization** in a feature branch
3. **Update orchestrator code** to use new prompt paths
4. **Test all components** work with new structure
5. **Update documentation** to reflect new structure
6. **Create migration guide** for other developers

Would you like me to help implement any specific part of this reorganization, such as creating the migration scripts or updating the CI/CD workflows?
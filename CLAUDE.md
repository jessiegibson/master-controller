# CLAUDE.md - Multi-Agent Orchestrator Project Context

## Project Overview

This is a **multi-agent software development orchestration system** designed to coordinate 31 specialized AI agents to build a privacy-first personal finance CLI application. The system is designed to be run by Claude Code or similar AI coding assistants.

## Current State

### Completed Work

**All 32 agent prompts are complete** and located in `/prompts/`. Each agent has a detailed prompt defining:
- Identity and role
- Core objectives
- Input/output formats
- Domain-specific instructions
- Interaction patterns with other agents

### Directory Structure

The project is split across two **independent** repositories with no submodule relationship:

```
jessiegibson/agents/             # Orchestrator repo (jessiegibson/master-controller)
├── CLAUDE.md                    # This file - project context
├── agents/
│   └── config/
│       └── agents.yaml          # Agent registry (all 31 active)
├── prompts/                     # All 32 agent prompts
├── orchestrator/                # Python orchestration engine
├── workflows/                   # Workflow YAML definitions
├── kanban-cli/                  # Task tracking TUI
├── context/                     # Context Manager storage
├── kanban/                      # Kanban task database
├── schemas/                     # Output validation schemas
└── run_workflow.py              # CLI entry point for workflows

jessiegibson/finance-cli/        # Standalone repo (separate GitHub repo)
├── src/                         # Rust source (12,000+ lines, 17 modules)
├── Cargo.toml
├── Cargo.lock
├── docs/
├── benches/
└── tests/
```

## What Needs to Be Built Next: Orchestration System

The orchestration system coordinates agent execution. Build these components:

### 1. Workflow Engine (`/orchestrator/`)

```
orchestrator/
├── mod.rs                 # Module exports
├── engine.rs              # Main orchestration engine
├── workflow.rs            # Workflow definitions
├── task.rs                # Task management
├── agent_runner.rs        # Execute individual agents
├── context_bridge.rs      # Interface with Context Manager
└── scheduler.rs           # Task scheduling and dependencies
```

**Key responsibilities:**
- Load workflow definitions (YAML)
- Schedule tasks based on dependencies
- Execute agents by loading prompts and providing context
- Collect and route outputs between agents
- Handle failures and retries
- Track progress and state

### 2. Workflow Definitions (`/workflows/`)

```yaml
# workflows/full-build.yaml
name: full-build
description: Complete project build from requirements to release

phases:
  - name: planning
    agents:
      - requirements-gatherer
      - product-roadmap-planner
    parallel: false
    
  - name: architecture
    agents:
      - system-architect
      - data-architect
      - security-architect
      - ml-architect
    parallel: true
    depends_on: [planning]
    
  - name: design
    agents:
      - cli-ux-designer
      - consulting-cpa
    parallel: true
    depends_on: [architecture]
    
  - name: scaffolding
    agents:
      - rust-scaffolder
      - repository-librarian
      - infrastructure-agent
    parallel: false
    depends_on: [architecture]
    
  - name: development
    agents:
      - duckdb-developer
      - parser-developer
      - encryption-developer
      - categorization-engine-developer
      - financial-calculator-developer
      - ml-engineer
      - cli-developer
    parallel: true
    depends_on: [scaffolding, design]
    
  - name: quality
    agents:
      - test-developer
      - code-reviewer
    parallel: true
    depends_on: [development]
    
  - name: documentation
    agents:
      - documentation-writer
    depends_on: [development, quality]
```

### 3. Agent Runner

The agent runner:
1. Loads agent prompt from `/prompts/{agent_name}.md`
2. Assembles context from Context Manager (dependent artifacts)
3. Formats the task input
4. Executes the agent (calls Claude API or runs in Claude Code)
5. Validates output using Output Validator schemas
6. Stores artifacts via Context Manager
7. Updates Kanban task status

### 4. Context Management Integration

The Context Manager agent prompt defines the storage schema:
- SQLite database for metadata (`context/context.db`)
- File storage for artifacts (`context/artifacts/`)
- Version tracking for all artifacts
- Access control per agent type

**Key tables:**
- `project_context` - shared state
- `artifacts` - artifact metadata
- `execution_history` - agent run audit trail
- `agent_context_requirements` - what each agent needs

### 5. Kanban Integration

The Kanban Manager agent prompt defines task tracking:
- SQLite database (`kanban/tasks.db`)
- Task states: backlog → ready → in_progress → review → done
- Sprint management
- Dependency tracking
- Blocking issue management

## Agent Categories and Execution Order

### Phase 1: Planning (Sequential)
1. **Requirements Gatherer** - Elicits and documents requirements
2. **Product Roadmap Planner** - Creates phased delivery plan

### Phase 2: Architecture (Parallel)
3. **System Architect** - Overall system design
4. **Data Architect** - Data models and storage
5. **Security Architect** - Security model and encryption
6. **ML Architect** - ML pipeline design

### Phase 3: Design (Parallel)
7. **CLI UX Designer** - Command structure and UX
8. **Consulting CPA** - Tax categories and Schedule C mapping

### Phase 4: Scaffolding (Sequential)
9. **Rust Scaffolder** - Project structure
10. **Repository Librarian** - Git setup, structure
11. **Infrastructure Agent** - CI/CD, build config

### Phase 5: Development (Parallel)
12. **DuckDB Developer** - Database layer
13. **Parser Developer** - File parsing
14. **Encryption Developer** - Crypto implementation
15. **Categorization Engine Developer** - Rule engine
16. **Financial Calculator Developer** - Report calculations
17. **ML Engineer** - ML models
18. **CLI Developer** - CLI implementation

### Phase 6: Quality (Parallel)
19. **Test Developer** - Tests and fixtures
20. **Code Reviewer** - Code review

### Phase 7: Documentation
21. **Documentation Writer** - All documentation

### Support Agents (Run as needed)
- **Workflow Orchestrator** - Coordinates execution
- **Project Manager** - Tracks progress
- **Kanban Manager** - Task management
- **Context Manager** - Artifact storage
- **Output Validator** - Validates outputs
- **Debugger** - Fixes issues
- **Prompt/Skill Engineer** - Optimizes prompts
- **Staff Engineer Python** - Python guidance
- **Staff Engineer Rust** - Rust guidance

## Key Design Decisions

### Agent Communication
- Agents communicate via **artifacts** stored by Context Manager
- No direct agent-to-agent calls
- Orchestrator routes outputs to dependent agents

### Execution Model
- Each agent runs in isolation with assembled context
- Agents produce structured outputs (Markdown, YAML, code)
- Output Validator ensures format compliance
- Failed validations trigger retry or Debugger

### State Management
- All state persisted to disk (SQLite + files)
- Workflow can be resumed after interruption
- Version control on all artifacts

### Error Handling
- Retry failed agents up to 3 times
- Route persistent failures to Debugger agent
- Workflow can continue with non-blocking failures
- All errors logged to execution history

## Target Application: Finance CLI

The agents are building a **privacy-first personal finance CLI** with:

- **Transaction import**: CSV, QFX/OFX, PDF parsing
- **Categorization**: Rules + ML-based
- **Reports**: P&L, Cash Flow, Schedule C
- **Encryption**: AES-256-GCM, Argon2id key derivation
- **Local-first**: No cloud, no internet required
- **Tax-ready**: IRS Schedule C line item mapping

Tech stack: **Rust**, **DuckDB**, **clap**, **AES-GCM**, **Argon2**

## Apple On-Device ML: Speaker Audio Classification

The application can leverage Apple's on-device ML frameworks to classify speaker audio locally, without sending audio data to the cloud. This aligns with the project's privacy-first philosophy.

### Relevant Apple Frameworks

| Framework | Role |
|-----------|------|
| **SoundAnalysis** | High-level API for classifying audio streams and files |
| **CoreML** | Runtime for loading and running `.mlmodel` files on-device |
| **Create ML** | Tool for training custom audio classifiers on macOS |
| **Speech** | On-device speech recognition (speaker diarization support) |

### Architecture: Audio → Classification Pipeline

```
Audio Input (microphone / file)
        │
        ▼
AVAudioEngine (capture / read)
        │
        ▼
SNAudioStreamAnalyzer  ←── SoundAnalysis framework
        │
        ├── Built-in classifier: SNClassifySoundRequest
        │       (100+ sound categories, no model file needed)
        │
        └── Custom classifier: SNClassifyRequest(mlModel:)
                (load a .mlmodel trained with Create ML)
        │
        ▼
SNClassificationResult
  └── classifications: [SNClassification]
        └── identifier: String   (e.g. "speech", "silence", "noise")
        └── confidence: Double
```

### Integration Approach (Swift / Objective-C)

The finance CLI could expose audio classification as a macOS companion tool or Swift CLI. Key steps:

**1. Stream audio from microphone:**
```swift
import SoundAnalysis
import AVFoundation

let engine = AVAudioEngine()
let inputNode = engine.inputNode
let bus = 0
let inputFormat = inputNode.outputFormat(forBus: bus)

let streamAnalyzer = SNAudioStreamAnalyzer(format: inputFormat)
```

**2. Attach a classification request:**
```swift
// Built-in sound classifier (no model needed)
let request = try SNClassifySoundRequest(classifierIdentifier: .version1)
request.windowDuration = CMTimeMakeWithSeconds(1.5, preferredTimescale: 48_000)
request.overlapFactor = 0.5

try streamAnalyzer.add(request, withObserver: resultsObserver)
```

**3. Process results in the observer:**
```swift
class ResultsObserver: NSObject, SNResultsObserving {
    func request(_ request: SNRequest, didProduce result: SNResult) {
        guard let result = result as? SNClassificationResult else { return }
        let topClass = result.classifications.first
        print("Detected: \(topClass?.identifier ?? "unknown") @ \(topClass?.confidence ?? 0)")
    }
}
```

**4. Train a custom speaker classifier with Create ML (macOS):**
```swift
// In a Swift Playground or Create ML app
import CreateML

let trainingData = try MLSoundClassifier.DataSource.labeledDirectories(at: trainingURL)
let classifier = try MLSoundClassifier(trainingData: trainingData)
try classifier.write(to: URL(fileURLWithPath: "SpeakerClassifier.mlmodel"))
```

### Privacy Guarantees

- All inference runs **on-device** via CoreML — no audio leaves the machine
- `SNClassifySoundRequest` with `.version1` uses Apple's pre-trained model bundled with macOS (no download)
- Custom `.mlmodel` files are local and version-controlled
- Compatible with macOS sandboxing (microphone entitlement required)

### Use Cases in Finance CLI Context

| Use Case | Implementation |
|----------|---------------|
| Voice memo import | Detect speech segments, transcribe with `Speech` framework |
| Speaker diarization | Label audio segments by speaker identity using a custom classifier |
| Ambient noise filtering | Use SoundAnalysis to skip non-speech frames before transcription |
| Hands-free command input | Trigger CLI commands via detected wake phrases |

### Platform Requirements

- **macOS 10.15+** for `SoundAnalysis` / `SNAudioStreamAnalyzer`
- **macOS 11+** for `SNClassifySoundRequest(classifierIdentifier:)` built-in model
- **Xcode 12+** / **Create ML** for training custom classifiers
- Microphone entitlement (`com.apple.security.device.audio-input`) if capturing live audio

### Rust Integration Strategy

Since finance-cli is Rust-based, Apple ML frameworks require a bridge layer:

```
finance-cli (Rust CLI)
        │
        └── spawns / calls ──▶ swift-audio-classifier (Swift CLI tool)
                                      │
                                      └── SoundAnalysis + CoreML
                                              │
                                              └── outputs JSON results
                                                  back to Rust via stdout
```

The Swift tool outputs structured JSON:
```json
{
  "segments": [
    { "start_ms": 0, "end_ms": 1500, "label": "speech", "confidence": 0.97 },
    { "start_ms": 1500, "end_ms": 3000, "label": "silence", "confidence": 0.99 }
  ]
}
```

Rust reads this via `std::process::Command` and parses with `serde_json`.

## Git Workflow

**Two Independent Repositories** — no submodule relationship.

- **agents** (`jessiegibson/master-controller.git`) — Orchestrator, prompts, context, kanban
  - Local path: `~/workspace/github.com/jessiegibson/agents/`
  - Remote: `github` (primary), `origin` (local backup)
- **finance-cli** (`jessiegibson/finance-cli.git`) — Standalone Rust CLI application
  - Local path: `~/workspace/github.com/jessiegibson/finance-cli/`
  - Remote: `origin` (primary)

### Feature Branch Process

1. **Start a new feature:**
   ```bash
   git checkout main && git pull
   git checkout -b feature/your-feature-name
   ```

2. **During development:**
   - Make commits as work progresses
   - Use descriptive commit messages (imperative mood)
   - Include `Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>` in commits

3. **Push to GitHub:**
   ```bash
   # From agents repo
   git push -u github feature/your-feature-name

   # From finance-cli repo
   git push -u origin feature/your-feature-name
   ```

### Branch Naming Convention

- `feature/` - New features (e.g., `feature/feedback-loop`, `feature/ml-training`)
- `fix/` - Bug fixes (e.g., `fix/categorization-bug`)
- `refactor/` - Code refactoring (e.g., `refactor/encryption-module`)
- `docs/` - Documentation updates (e.g., `docs/user-guide`)

## How to Use This System

### Option 1: Manual Agent Execution

Run agents one at a time:
1. Read agent prompt from `/prompts/{agent}.md`
2. Provide relevant context (previous agent outputs)
3. Execute agent task
4. Save output to `/context/artifacts/`

### Option 2: Build Orchestrator (Recommended)

Implement the orchestration system to automate:
1. Build workflow engine in Rust or Python
2. Create workflow YAML definitions
3. Implement agent runner
4. Connect to Context Manager storage
5. Run workflows end-to-end

### Option 3: Claude Code Interactive

Use Claude Code to:
1. Read an agent prompt
2. Act as that agent
3. Produce the specified outputs
4. Save to appropriate locations

## Next Steps

1. **Build orchestrator engine** - Core workflow execution
2. **Create workflow definitions** - YAML workflow files
3. **Implement context storage** - SQLite + file system
4. **Build agent runner** - Prompt loading and execution
5. **Run first workflow** - Execute planning phase
6. **Iterate** - Run subsequent phases

## Important Files to Reference

| File | Purpose |
|------|---------|
| `agents/config/agents.yaml` | Agent registry with all 31 agents |
| `prompts/workflow_orchestrator.md` | Orchestration patterns |
| `prompts/context_manager.md` | Storage architecture |
| `prompts/kanban_manager.md` | Task tracking schema |
| `prompts/output_validator.md` | Validation schemas |
| `prompts/project_manager.md` | Progress tracking |

## Commands for Claude Code

```bash
# View all agent prompts
ls prompts/

# View specific agent prompt
cat prompts/workflow_orchestrator.md

# View agent registry
cat agents/config/agents.yaml

# Create orchestrator directory
mkdir -p orchestrator workflows context kanban schemas
```

## Questions to Consider

When building the orchestrator, decide:

1. **Language**: Rust (consistent with target app) or Python (faster to build)?
2. **Execution**: Sequential or parallel agent execution?
3. **API**: Direct Claude API calls or Claude Code subprocess?
4. **Storage**: Exact SQLite schema for context and kanban?
5. **Validation**: JSON Schema or custom validators?

The agent prompts provide guidance, but implementation details are yours to decide.

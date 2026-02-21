# Infrastructure Agent Output: Privacy-First Personal Finance CLI

**Date**: 2026-02-20
**Status**: Complete
**Agent**: Infrastructure Agent
**Input Dependencies**: System Architect Output, Rust Scaffolder Output, Existing Cargo.toml

---

## Executive Summary

This document defines the complete build, CI/CD, release, and developer tooling infrastructure for the `finance-cli` Rust project. It covers GitHub Actions workflows for continuous integration and release automation, development environment configuration (rustfmt, clippy, pre-commit hooks), and build optimization strategies including caching. All recommendations are tailored to the actual project structure, dependency set, and the privacy-first design principles established by the system architect.

---

## 1. GitHub Actions CI/CD Workflow

### 1.1 Continuous Integration (`ci.yml`)

This workflow runs on every push to `main` and on all pull requests targeting `main`. It provides five parallel jobs: formatting check, clippy linting, compilation check, test suite (cross-platform matrix), and security audit.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  CARGO_TERM_COLOR: always
  RUST_BACKTRACE: 1
  # Reduce noise from cargo during CI
  CARGO_INCREMENTAL: 0

# Cancel in-progress runs for the same branch/PR
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  fmt:
    name: Formatting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt

      - name: Check formatting
        run: cargo fmt --all -- --check

  clippy:
    name: Clippy Lints
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy

      - name: Cache cargo registry and build artifacts
        uses: Swatinem/rust-cache@v2
        with:
          shared-key: "clippy"

      - name: Run clippy
        run: cargo clippy --all-targets -- -D warnings

  check:
    name: Compilation Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable

      - name: Cache cargo registry and build artifacts
        uses: Swatinem/rust-cache@v2
        with:
          shared-key: "check"

      - name: Check compilation
        run: cargo check --all-targets

  test:
    name: Test (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    needs: [check]
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable

      - name: Cache cargo registry and build artifacts
        uses: Swatinem/rust-cache@v2
        with:
          shared-key: "test-${{ matrix.os }}"

      - name: Run unit tests
        run: cargo test --lib

      - name: Run integration tests
        run: cargo test --test '*'

      - name: Run doc tests
        run: cargo test --doc

  security:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install cargo-audit
        uses: taiki-e/install-action@cargo-audit

      - name: Run security audit
        run: cargo audit

  coverage:
    name: Code Coverage
    runs-on: ubuntu-latest
    needs: [test]
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          components: llvm-tools-preview

      - name: Cache cargo registry and build artifacts
        uses: Swatinem/rust-cache@v2
        with:
          shared-key: "coverage"

      - name: Install cargo-llvm-cov
        uses: taiki-e/install-action@cargo-llvm-cov

      - name: Generate coverage report
        run: cargo llvm-cov --lcov --output-path lcov.info

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: lcov.info
          fail_ci_if_error: false
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  docs:
    name: Documentation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable

      - name: Cache cargo registry and build artifacts
        uses: Swatinem/rust-cache@v2
        with:
          shared-key: "docs"

      - name: Build documentation
        run: cargo doc --no-deps
        env:
          RUSTDOCFLAGS: "-D warnings"
```

### 1.2 Design Rationale for CI

**Job separation**: Formatting, clippy, check, test, security, coverage, and docs are separate jobs so that:
- Formatting failures report instantly without waiting for a full build.
- Clippy and check can run in parallel.
- The test matrix only runs after compilation succeeds (via `needs: [check]`), avoiding wasted compute.
- Coverage runs after tests pass, avoiding duplicate work if tests fail.

**Concurrency control**: The `concurrency` block cancels in-progress CI runs when a new push arrives for the same branch. This prevents resource waste during rapid iteration.

**No `--all-features` flag**: The current `Cargo.toml` defines no non-default features that would add additional code paths requiring separate testing. If features are added in the future (e.g., `async`, `ml`, `pdf`), the CI should be updated to include `--all-features` or a feature matrix.

**Cross-platform matrix**: Tests run on Ubuntu, macOS, and Windows to validate the privacy-first local storage model works across all target platforms, including path handling and file system encryption.

---

## 2. Release Automation Workflow

### 2.1 Release Workflow (`release.yml`)

Triggered by pushing a semantic version tag (e.g., `v0.1.0`). Builds cross-platform binaries and publishes a GitHub Release with attached assets.

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - "v[0-9]+.*"

permissions:
  contents: write

env:
  CARGO_TERM_COLOR: always

jobs:
  # First, validate the release builds and tests pass
  validate:
    name: Validate Release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy, rustfmt

      - name: Cache cargo
        uses: Swatinem/rust-cache@v2

      - name: Check formatting
        run: cargo fmt --all -- --check

      - name: Run clippy
        run: cargo clippy --all-targets -- -D warnings

      - name: Run tests
        run: cargo test

  # Build release binaries for all platforms
  build:
    name: Build (${{ matrix.target }})
    needs: validate
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          # Linux x86_64 (glibc)
          - target: x86_64-unknown-linux-gnu
            os: ubuntu-latest
            archive: tar.gz
            binary: finance-cli

          # Linux x86_64 (musl - static binary)
          - target: x86_64-unknown-linux-musl
            os: ubuntu-latest
            archive: tar.gz
            binary: finance-cli

          # Linux ARM64
          - target: aarch64-unknown-linux-gnu
            os: ubuntu-latest
            archive: tar.gz
            binary: finance-cli

          # macOS x86_64 (Intel)
          - target: x86_64-apple-darwin
            os: macos-13
            archive: tar.gz
            binary: finance-cli

          # macOS ARM64 (Apple Silicon)
          - target: aarch64-apple-darwin
            os: macos-latest
            archive: tar.gz
            binary: finance-cli

          # Windows x86_64
          - target: x86_64-pc-windows-msvc
            os: windows-latest
            archive: zip
            binary: finance-cli.exe

    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Cache cargo
        uses: Swatinem/rust-cache@v2
        with:
          shared-key: "release-${{ matrix.target }}"

      # Install cross-compilation dependencies for Linux ARM64
      - name: Install cross-compilation tools (aarch64)
        if: matrix.target == 'aarch64-unknown-linux-gnu'
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
          echo "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc" >> $GITHUB_ENV

      # Install musl tools for static Linux builds
      - name: Install musl tools
        if: matrix.target == 'x86_64-unknown-linux-musl'
        run: |
          sudo apt-get update
          sudo apt-get install -y musl-tools

      - name: Build release binary
        run: cargo build --release --target ${{ matrix.target }}

      # Package Unix builds as tar.gz
      - name: Package (Unix)
        if: matrix.os != 'windows-latest'
        run: |
          cd target/${{ matrix.target }}/release
          tar czf ../../../finance-cli-${{ github.ref_name }}-${{ matrix.target }}.tar.gz ${{ matrix.binary }}

      # Package Windows builds as zip
      - name: Package (Windows)
        if: matrix.os == 'windows-latest'
        shell: pwsh
        run: |
          cd target/${{ matrix.target }}/release
          Compress-Archive -Path ${{ matrix.binary }} -DestinationPath ../../../finance-cli-${{ github.ref_name }}-${{ matrix.target }}.zip

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: finance-cli-${{ matrix.target }}
          path: finance-cli-${{ github.ref_name }}-${{ matrix.target }}.*
          if-no-files-found: error

  # Create the GitHub Release and attach all binaries
  release:
    name: Create GitHub Release
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          merge-multiple: true

      - name: Generate release notes
        id: release_notes
        run: |
          # Extract version from tag
          VERSION="${GITHUB_REF_NAME#v}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT

          # Generate changelog from git log since last tag
          PREV_TAG=$(git tag --sort=-creatordate | head -2 | tail -1)
          if [ -z "$PREV_TAG" ] || [ "$PREV_TAG" = "$GITHUB_REF_NAME" ]; then
            NOTES="Initial release"
          else
            NOTES=$(git log --pretty=format:"- %s" "$PREV_TAG".."$GITHUB_REF_NAME" -- . ':!.github')
          fi

          # Write multi-line notes to file
          cat <<NOTES_EOF > release_notes.md
          ## Finance CLI $VERSION

          ### Changes

          $NOTES

          ### Checksums

          \`\`\`
          $(cd artifacts && sha256sum finance-cli-* 2>/dev/null || shasum -a 256 finance-cli-*)
          \`\`\`

          ### Installation

          Download the appropriate binary for your platform, extract it, and place it in your PATH.

          **macOS (Apple Silicon)**:
          \`\`\`bash
          tar xzf finance-cli-$GITHUB_REF_NAME-aarch64-apple-darwin.tar.gz
          chmod +x finance-cli
          sudo mv finance-cli /usr/local/bin/
          \`\`\`

          **Linux (x86_64)**:
          \`\`\`bash
          tar xzf finance-cli-$GITHUB_REF_NAME-x86_64-unknown-linux-gnu.tar.gz
          chmod +x finance-cli
          sudo mv finance-cli /usr/local/bin/
          \`\`\`
          NOTES_EOF

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          body_path: release_notes.md
          files: artifacts/finance-cli-*
          fail_on_unmatched_files: true
          generate_release_notes: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 2.2 Release Process

To create a new release:

```bash
# 1. Ensure main branch is up to date
git checkout main
git pull github main

# 2. Update version in Cargo.toml
# Edit Cargo.toml: version = "0.2.0"

# 3. Update CHANGELOG.md with release notes

# 4. Commit the version bump
git add Cargo.toml CHANGELOG.md
git commit -m "chore: release v0.2.0"

# 5. Create and push the tag
git tag v0.2.0
git push github main
git push github v0.2.0

# The release workflow will automatically:
# - Validate formatting, clippy, and tests
# - Build binaries for 6 platform targets
# - Create a GitHub Release with all binaries attached
# - Generate SHA-256 checksums
```

### 2.3 Supported Release Targets

| Target | OS | Architecture | Binary Type | Notes |
|--------|-----|-------------|-------------|-------|
| `x86_64-unknown-linux-gnu` | Linux | x86_64 | Dynamic (glibc) | Most Linux distros |
| `x86_64-unknown-linux-musl` | Linux | x86_64 | Static (musl) | Alpine, containers, portable |
| `aarch64-unknown-linux-gnu` | Linux | ARM64 | Dynamic (glibc) | AWS Graviton, Raspberry Pi 4+ |
| `x86_64-apple-darwin` | macOS | x86_64 | Dynamic | Intel Macs |
| `aarch64-apple-darwin` | macOS | ARM64 | Dynamic | Apple Silicon (M1/M2/M3/M4) |
| `x86_64-pc-windows-msvc` | Windows | x86_64 | .exe | Windows 10/11 |

---

## 3. Dependency Update Automation

### 3.1 Weekly Dependency Update Workflow (`dependencies.yml`)

```yaml
# .github/workflows/dependencies.yml
name: Dependency Updates

on:
  schedule:
    # Run weekly on Sunday at 04:00 UTC
    - cron: "0 4 * * 0"
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  update:
    name: Update Dependencies
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable

      - name: Cache cargo
        uses: Swatinem/rust-cache@v2

      - name: Update dependencies
        run: cargo update

      - name: Run tests after update
        run: cargo test

      - name: Run clippy after update
        run: cargo clippy --all-targets -- -D warnings

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore(deps): weekly dependency update"
          title: "chore(deps): weekly dependency update"
          body: |
            Automated weekly dependency update via `cargo update`.

            This PR updates `Cargo.lock` to pull in the latest compatible versions
            of all dependencies. Tests and clippy have been verified to pass.

            **Review checklist**:
            - [ ] Review updated crate versions in the diff
            - [ ] Check for any breaking changes in updated crates
            - [ ] Verify CI passes on all platforms
          branch: deps/weekly-update
          delete-branch: true
          labels: dependencies
```

---

## 4. Development Tooling Configuration

### 4.1 Rust Formatting (`rustfmt.toml`)

```toml
# rustfmt.toml
# Rust formatting configuration for finance-cli
# Requires: rustup component add rustfmt
#
# Apply with: cargo fmt --all
# Check with: cargo fmt --all -- --check

# Use the 2021 edition formatting rules
edition = "2021"

# Maximum line width before wrapping
max_width = 100

# Use block indentation (standard Rust style)
indent_style = "Block"

# 4-space indentation
tab_spaces = 4
hard_tabs = false

# Imports formatting
imports_granularity = "Crate"
group_imports = "StdExternalCrate"
reorder_imports = true
reorder_modules = true

# Function and struct formatting
fn_params_layout = "Tall"
struct_lit_single_line = true

# Control flow formatting
match_arm_blocks = true
match_block_trailing_comma = true

# String formatting
format_strings = false

# Comment formatting
wrap_comments = false
normalize_comments = false

# Macro formatting
format_macro_matchers = true

# Use field init shorthand where possible
use_field_init_shorthand = true

# Use try! shorthand (? operator)
use_try_shorthand = true

# Trailing semicolons in flow control
trailing_semicolon = true
```

### 4.2 Clippy Configuration (`.clippy.toml`)

```toml
# .clippy.toml
# Clippy linting configuration for finance-cli
# Applied automatically when running: cargo clippy
#
# Note: Lint levels are also configured in Cargo.toml under [lints.clippy].
# This file provides additional configuration parameters for specific lints.

# Cognitive complexity threshold before triggering a warning
cognitive-complexity-threshold = 30

# Maximum number of lines in a single function
too-many-lines-threshold = 150

# Maximum number of function arguments
too-many-arguments-threshold = 8

# Type complexity threshold
type-complexity-threshold = 300

# Disallowed methods - prevent accidental use of non-secure operations
# (Using Cargo.toml [lints.clippy] for the primary lint controls)
disallowed-methods = [
    # Prevent using standard HashMap in security-sensitive contexts
    # where timing attacks are a concern
    { path = "std::env::set_var", reason = "Use config module instead of environment variables for settings" },
]

# Allowed wildcard imports - limit to specific modules only
allowed-wildcard-imports = []

# Minimum number of struct fields to trigger large_types_passed_by_value
pass-by-value-size-limit = 256
```

### 4.3 Lint Configuration in Cargo.toml (Reference)

The existing `Cargo.toml` already contains appropriate lint configuration. For reference and completeness, the recommended lint settings are:

```toml
# Already present in the current Cargo.toml -- no changes needed
[lints.rust]
unsafe_code = "forbid"
unused_imports = "warn"
unused_variables = "warn"
dead_code = "warn"

[lints.clippy]
unwrap_used = "warn"
expect_used = "warn"
panic = "warn"
todo = "warn"
unimplemented = "warn"
dbg_macro = "warn"
```

These lints are appropriate for a finance application where panics and unwraps could lose user data. The `unsafe_code = "forbid"` lint is especially important for the privacy-first guarantee since unsafe code could bypass encryption boundaries.

### 4.4 Pre-commit Hook

```bash
#!/usr/bin/env bash
# scripts/pre-commit
#
# Pre-commit hook for finance-cli development.
# Install by running: cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# Or run: ./scripts/setup-hooks.sh
#
# This hook runs formatting checks, clippy lints, and unit tests
# before allowing a commit. It only checks staged files where possible
# to keep the hook fast.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running pre-commit checks...${NC}"

# Check if there are any staged Rust files
STAGED_RS_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.rs$' || true)

if [ -z "$STAGED_RS_FILES" ]; then
    echo -e "${GREEN}No Rust files staged, skipping Rust checks.${NC}"
    exit 0
fi

# 1. Formatting check
echo -e "${YELLOW}[1/3] Checking formatting...${NC}"
if ! cargo fmt --all -- --check 2>/dev/null; then
    echo -e "${RED}Formatting check failed. Run 'cargo fmt --all' to fix.${NC}"
    exit 1
fi
echo -e "${GREEN}  Formatting OK${NC}"

# 2. Clippy lints
echo -e "${YELLOW}[2/3] Running clippy...${NC}"
if ! cargo clippy --all-targets -- -D warnings 2>/dev/null; then
    echo -e "${RED}Clippy found warnings treated as errors. Fix them before committing.${NC}"
    exit 1
fi
echo -e "${GREEN}  Clippy OK${NC}"

# 3. Unit tests (lib only for speed)
echo -e "${YELLOW}[3/3] Running unit tests...${NC}"
if ! cargo test --lib 2>/dev/null; then
    echo -e "${RED}Unit tests failed. Fix failing tests before committing.${NC}"
    exit 1
fi
echo -e "${GREEN}  Tests OK${NC}"

echo -e "${GREEN}All pre-commit checks passed!${NC}"
```

### 4.5 Hook Installation Script

```bash
#!/usr/bin/env bash
# scripts/setup-hooks.sh
#
# Installs git hooks for the finance-cli project.
# Run once after cloning: ./scripts/setup-hooks.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."

# Install pre-commit hook
cp "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"
echo "  Installed pre-commit hook"

echo "Git hooks installed successfully."
echo ""
echo "To skip hooks temporarily (not recommended), use: git commit --no-verify"
```

### 4.6 Development Setup Script

```bash
#!/usr/bin/env bash
# scripts/setup.sh
#
# One-time development environment setup for finance-cli.
# Run after cloning: ./scripts/setup.sh

set -euo pipefail

echo "=== Finance CLI Development Setup ==="
echo ""

# 1. Check Rust installation
if ! command -v rustc &> /dev/null; then
    echo "Rust is not installed. Installing via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo "Rust $(rustc --version | cut -d' ' -f2) detected"
fi

# 2. Install required components
echo ""
echo "Installing Rust components..."
rustup component add rustfmt clippy llvm-tools-preview

# 3. Install development tools
echo ""
echo "Installing cargo development tools..."
cargo install --locked cargo-watch 2>/dev/null || echo "  cargo-watch already installed"
cargo install --locked cargo-audit 2>/dev/null || echo "  cargo-audit already installed"
cargo install --locked cargo-llvm-cov 2>/dev/null || echo "  cargo-llvm-cov already installed"

# 4. Install git hooks
echo ""
echo "Installing git hooks..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/setup-hooks.sh" ]; then
    bash "$SCRIPT_DIR/setup-hooks.sh"
else
    echo "  Hook setup script not found, skipping"
fi

# 5. Verify the project builds
echo ""
echo "Verifying project builds..."
cargo check
echo "  Build check passed"

# 6. Run tests
echo ""
echo "Running tests..."
cargo test --lib
echo "  Tests passed"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Useful commands:"
echo "  cargo build                    Build the project"
echo "  cargo test                     Run all tests"
echo "  cargo clippy                   Run linter"
echo "  cargo fmt                      Format code"
echo "  cargo watch -x check           Watch and check on save"
echo "  cargo watch -x 'test --lib'    Watch and test on save"
echo "  cargo audit                    Check for security advisories"
echo "  cargo llvm-cov --html          Generate coverage report"
```

### 4.7 Makefile

```makefile
# Makefile
# Common development tasks for finance-cli
#
# Usage: make <target>
# Run 'make help' for a list of available targets.

.PHONY: all build release test test-unit test-integration lint fmt fmt-check \
        clean audit coverage docs watch help setup

# Default target
all: fmt-check lint test build

## Build targets

build: ## Build debug binary
	cargo build

release: ## Build optimized release binary
	cargo build --release

## Test targets

test: ## Run all tests
	cargo test

test-unit: ## Run unit tests only
	cargo test --lib

test-integration: ## Run integration tests only
	cargo test --test '*'

## Quality targets

lint: ## Run clippy lints
	cargo clippy --all-targets -- -D warnings

fmt: ## Format all source code
	cargo fmt --all

fmt-check: ## Check formatting without modifying files
	cargo fmt --all -- --check

audit: ## Run security audit on dependencies
	cargo audit

coverage: ## Generate HTML coverage report
	cargo llvm-cov --html
	@echo "Coverage report: target/llvm-cov/html/index.html"

docs: ## Build and open documentation
	cargo doc --no-deps --open

## Development targets

watch: ## Watch for changes and run checks
	cargo watch -x check -x 'test --lib'

watch-test: ## Watch for changes and run all tests
	cargo watch -x test

## Maintenance targets

clean: ## Remove build artifacts
	cargo clean

setup: ## Run development environment setup
	./scripts/setup.sh

## Help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
```

### 4.8 VS Code Configuration (`.vscode/settings.json`)

```json
{
  "editor.formatOnSave": true,
  "rust-analyzer.check.command": "clippy",
  "rust-analyzer.check.allTargets": true,
  "rust-analyzer.procMacro.enable": true,
  "rust-analyzer.cargo.buildScripts.enable": true,
  "[rust]": {
    "editor.defaultFormatter": "rust-lang.rust-analyzer",
    "editor.rulers": [100]
  },
  "files.watcherExclude": {
    "**/target/**": true
  },
  "search.exclude": {
    "**/target/**": true
  }
}
```

### 4.9 VS Code Debug Configuration (`.vscode/launch.json`)

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "lldb",
      "request": "launch",
      "name": "Debug finance-cli",
      "cargo": {
        "args": ["build", "--bin=finance-cli", "--package=finance-cli"],
        "filter": {
          "name": "finance-cli",
          "kind": "bin"
        }
      },
      "args": [],
      "cwd": "${workspaceFolder}"
    },
    {
      "type": "lldb",
      "request": "launch",
      "name": "Debug unit tests",
      "cargo": {
        "args": ["test", "--no-run", "--lib", "--package=finance-cli"],
        "filter": {
          "name": "finance-cli",
          "kind": "lib"
        }
      },
      "args": [],
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

---

## 5. Build Optimization and Caching Strategies

### 5.1 CI Cache Strategy

The `Swatinem/rust-cache@v2` action is the recommended caching solution for Rust CI. It caches:

- `~/.cargo/registry/index` -- crate registry index
- `~/.cargo/registry/cache` -- downloaded crate archives
- `~/.cargo/git/db` -- git dependency checkouts
- `./target` -- compiled artifacts (with intelligent pruning)

**Shared cache keys**: Each CI job uses a `shared-key` parameter to avoid cache collisions between jobs while maximizing reuse:

| Job | Cache Key | Purpose |
|-----|-----------|---------|
| `clippy` | `clippy` | Separate from build since clippy metadata differs |
| `check` | `check` | Basic compilation check |
| `test-$OS` | `test-ubuntu-latest`, etc. | Platform-specific test caches |
| `coverage` | `coverage` | Instrumented build cache |
| `docs` | `docs` | Documentation build cache |

**Cache efficiency**: The `CARGO_INCREMENTAL: 0` environment variable is set globally in CI. Incremental compilation is designed for local development iteration and produces larger cache artifacts. Disabling it in CI results in smaller caches and more reproducible builds.

### 5.2 Release Build Optimization

The existing `Cargo.toml` release profile is well-configured:

```toml
[profile.release]
lto = true           # Link-Time Optimization for smaller, faster binaries
codegen-units = 1    # Single codegen unit for maximum optimization
panic = "abort"      # No unwinding overhead
strip = true         # Strip debug symbols for smaller binaries
```

These settings produce the smallest and fastest release binaries at the cost of longer compilation time, which is acceptable for release builds.

**Estimated binary size impact**:
- Without these optimizations: ~15-25 MB (estimate)
- With LTO + strip + abort: ~5-12 MB (estimate, varies with DuckDB bundled size)

### 5.3 Development Build Optimization

The current dev profile is minimal:

```toml
[profile.dev]
debug = true
```

This is appropriate. Recommended additions if compile times become an issue:

```toml
[profile.dev]
debug = true
# Uncomment if compile times are slow:
# split-debuginfo = "unpacked"  # Faster incremental builds on macOS

[profile.dev.package."*"]
# Optimize dependencies even in dev mode for faster runtime
# while keeping the finance-cli crate itself at opt-level 0 for fast compilation
opt-level = 2
```

The `opt-level = 2` for dependencies is particularly beneficial for DuckDB, which is compute-intensive. This compiles dependencies with optimizations while keeping the project code at debug optimization for fast iteration.

### 5.4 DuckDB Bundled Build Considerations

The `duckdb` crate with `features = ["bundled"]` compiles the DuckDB C++ library from source, which is the single largest contributor to build times. Strategies to mitigate:

1. **CI caching** (already addressed): The `Swatinem/rust-cache` action caches compiled DuckDB artifacts, so subsequent CI runs avoid recompiling it.

2. **`sccache` for local development** (optional): Developers with multiple branches can use `sccache` to share compiled DuckDB across branches:
   ```bash
   cargo install sccache
   export RUSTC_WRAPPER=sccache
   ```

3. **Pre-built DuckDB** (future optimization): If build times become a pain point, the `bundled` feature can be replaced with a system-installed DuckDB, but this complicates cross-platform builds and the release workflow. Not recommended at this stage.

### 5.5 Build Time Monitoring

Add the following to the CI workflow for build time visibility:

```yaml
      - name: Build with timing
        run: cargo build --timings

      - name: Upload build timing report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: build-timing-${{ matrix.os }}
          path: target/cargo-timings/cargo-timing.html
```

The `--timings` flag generates an HTML report showing how long each crate takes to compile, which dependency chains are critical paths, and where parallelism is utilized. This is useful for identifying optimization opportunities as the project grows.

---

## 6. `.gitignore` Recommendations

```gitignore
# Build artifacts
/target/

# IDE and editor files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Environment and secrets
.env
.env.local
*.key
*.pem

# Coverage reports
lcov.info
coverage/
target/llvm-cov/

# Cargo-generated timing reports (developer convenience, not checked in)
target/cargo-timings/

# Finance CLI data files (never commit user data)
*.db
*.db-journal
*.encrypted
```

---

## 7. Infrastructure Summary Report

### Build Configuration

| Item | Status | Notes |
|------|--------|-------|
| Cargo.toml | Configured | Dependencies, profiles, lints all set |
| Feature flags | Minimal | No optional features currently; ready to add `ml`, `pdf`, `async` |
| Build profiles | Optimized | Release: LTO + strip + abort; Dev: debug symbols |
| Lint configuration | Configured | `unsafe_code` forbidden, `unwrap_used` warned |

### CI/CD Pipelines

| Pipeline | Trigger | Jobs | Status |
|----------|---------|------|--------|
| CI | Push to main, PRs | fmt, clippy, check, test (3 OS), security, coverage, docs | Defined |
| Release | Tag `v*` | validate, build (6 targets), release | Defined |
| Dependencies | Weekly (Sunday) | update, test, clippy, create PR | Defined |

### Supported Build Targets

| Target | OS | Architecture | Build Type |
|--------|-----|--------------|------------|
| x86_64-unknown-linux-gnu | Linux | x86_64 | Dynamic (glibc) |
| x86_64-unknown-linux-musl | Linux | x86_64 | Static (musl) |
| aarch64-unknown-linux-gnu | Linux | ARM64 | Dynamic (glibc) |
| x86_64-apple-darwin | macOS | x86_64 | Dynamic |
| aarch64-apple-darwin | macOS | ARM64 | Dynamic |
| x86_64-pc-windows-msvc | Windows | x86_64 | MSVC |

### Development Tools

| Tool | Purpose | Configuration File |
|------|---------|-------------------|
| rustfmt | Code formatting | `rustfmt.toml` |
| clippy | Linting | `.clippy.toml` + `Cargo.toml [lints.clippy]` |
| cargo-watch | Auto-rebuild on save | N/A (CLI tool) |
| cargo-llvm-cov | Code coverage | N/A (CLI tool) |
| cargo-audit | Security advisory checking | N/A (CLI tool) |
| pre-commit hook | Pre-commit quality gates | `scripts/pre-commit` |

### Files to Create

The following files should be created in the `finance-cli/` directory to implement this infrastructure:

| File Path | Purpose |
|-----------|---------|
| `.github/workflows/ci.yml` | Continuous integration workflow |
| `.github/workflows/release.yml` | Release automation workflow |
| `.github/workflows/dependencies.yml` | Weekly dependency update workflow |
| `rustfmt.toml` | Rust formatting rules |
| `.clippy.toml` | Clippy lint parameters |
| `scripts/pre-commit` | Git pre-commit hook |
| `scripts/setup-hooks.sh` | Hook installation script |
| `scripts/setup.sh` | Development environment setup |
| `Makefile` | Common development task shortcuts |
| `.vscode/settings.json` | VS Code Rust integration settings |
| `.vscode/launch.json` | VS Code debug configurations |

### Implementation Priority

1. **Immediate**: `ci.yml`, `rustfmt.toml`, `.clippy.toml`, `Makefile` -- these provide the foundational quality gates.
2. **Soon**: `scripts/pre-commit`, `scripts/setup-hooks.sh`, `scripts/setup.sh` -- these improve developer experience.
3. **Before first release**: `release.yml` -- needed for distribution.
4. **After first release**: `dependencies.yml` -- automates ongoing maintenance.
5. **Optional**: `.vscode/` configurations -- convenience for VS Code users.

---

## 8. Security Considerations for Infrastructure

Given the privacy-first nature of this application, the infrastructure itself must follow security best practices:

1. **No secrets in CI logs**: The workflows do not echo any secret values. The `GITHUB_TOKEN` and `CODECOV_TOKEN` are only used in secure action inputs, never in shell commands.

2. **Dependency auditing**: The `cargo audit` step in CI catches known vulnerabilities in dependencies before they reach `main`.

3. **Static binary option**: The `x86_64-unknown-linux-musl` target produces a fully static binary with no dynamic library dependencies, reducing the attack surface from shared library vulnerabilities.

4. **Pinned action versions**: All GitHub Actions use `@v4` or specific major versions. For maximum security, these should be pinned to exact commit SHAs in production:
   ```yaml
   # Example of SHA pinning (recommended for production)
   - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
   ```

5. **No credential storage**: The pre-commit hook and local tooling never interact with remote services or store credentials. This aligns with the offline-first design.

6. **Release integrity**: SHA-256 checksums are generated and included in release notes so users can verify binary integrity after download.

---

*Infrastructure Agent output complete. All workflow definitions, tooling configurations, and optimization strategies are ready for implementation.*

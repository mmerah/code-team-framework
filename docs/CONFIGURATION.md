# Configuration Guide

This document describes all configuration options available in the Code Team Framework's `.codeteam/config.yml` file.

## Configuration Structure

The configuration file is organized into several sections:

### Version

```yaml
version: 1.0
```

Specifies the configuration format version. Currently supports version 1.0.

### LLM Configuration

```yaml
llm:
  planner: sonnet          # Model for the Planner agent
  coder: sonnet            # Model for the Coder agent
  prompter: sonnet         # Model for the Prompter agent
  plan_verifier: sonnet    # Model for the Plan Verifier agent
  verifier_arch: sonnet    # Model for the Architecture Verifier
  verifier_task: sonnet    # Model for the Task Completion Verifier
  verifier_sec: sonnet     # Model for the Security Verifier
  verifier_perf: sonnet    # Model for the Performance Verifier
  commit_agent: sonnet     # Model for the Commit Agent
```

Configures the Large Language Model settings with explicit per-agent configuration:
- **Available models**:
  - `sonnet`: Claude 4 Sonnet (balanced performance and speed)
  - `opus`: Claude 4 Opus (highest quality, slower)

#### Agent-Specific Model Configuration

Each agent has its own explicit model configuration:

- **planner**: Model for the Planner agent (breaking down requests into tasks)
- **coder**: Model for the Coder agent (implementing code changes)
- **prompter**: Model for the Prompter agent (generating detailed coding instructions)
- **plan_verifier**: Model for the Plan Verifier agent (reviewing implementation plans)
- **verifier_arch**: Model for the Architecture Verifier (checking architectural compliance)
- **verifier_task**: Model for the Task Completion Verifier (verifying task completion)
- **verifier_sec**: Model for the Security Verifier (security analysis)
- **verifier_perf**: Model for the Performance Verifier (performance analysis)
- **commit_agent**: Model for the Commit Agent (generating commit messages)

All agents default to `sonnet` but can be configured individually for optimal performance.

### Verification Configuration

```yaml
verification:
  commands: []  # List of verification commands
  metrics:
    max_file_lines: 500      # Maximum lines per file
    max_method_lines: 80     # Maximum lines per method
```

Configures code verification settings:
- **commands**: List of verification commands to run (see Verification Commands section)
- **metrics.max_file_lines**: Maximum allowed lines in a single file
- **metrics.max_method_lines**: Maximum allowed lines in a single method

#### Verification Commands

You can define custom verification commands that will be executed after code changes:

```yaml
verification:
  commands:
    - name: "Type Check"
      command: "mypy src/"
    - name: "Lint"
      command: "ruff check src/"
    - name: "Tests"
      command: "pytest -xvs"
```

Each command has:
- **name**: Display name for the verification step
- **command**: Shell command to execute

### Verifier Instances

```yaml
verifier_instances:
  architecture: 1      # Number of architecture verifier instances
  task_completion: 1   # Number of task completion verifier instances
  security: 0          # Number of security verifier instances
  performance: 0       # Number of performance verifier instances
```

Controls how many instances of each type of verifier agent to run:
- **architecture**: Reviews code for architectural compliance
- **task_completion**: Verifies that tasks are completed correctly
- **security**: Checks for security vulnerabilities
- **performance**: Analyzes performance implications

Set to 0 to disable a particular verifier type.

### Paths Configuration

```yaml
paths:
  plan_dir: .codeteam/planning              # Directory for planning documents
  report_dir: .codeteam/reports             # Directory for verification reports
  config_dir: .codeteam                     # Framework configuration directory
  agent_instructions_dir: .codeteam/agent_instructions  # Agent instruction templates
  template_dir: .codeteam/agent_instructions            # Template directory
```

Configures filesystem paths used by the framework:
- **plan_dir**: Where planning documents are stored
- **report_dir**: Where verification reports are temporarily stored
- **config_dir**: Main framework configuration directory
- **agent_instructions_dir**: Directory containing agent instruction templates
- **template_dir**: Directory used for template rendering

### Templates Configuration

```yaml
templates:
  guideline_files:
    - ARCHITECTURE_GUIDELINES.md
    - CODING_GUIDELINES.md
    - AGENT_OBJECTIVITY.md
  exclude_dirs:
    - .git
    - .mypy_cache
    - .ruff_cache
    - .venv
    - .idea
    - __pycache__
    - .codeteam
    - node_modules
```

Configures template rendering:
- **guideline_files**: List of guideline files to load and make available to all agents
- **exclude_dirs**: List of directories to exclude from the repository map generation. This helps reduce the size of the repository map passed to AI agents, which can prevent "Argument list too long" errors on large projects

## Customization Examples

### Python Project with Full Verification

```yaml
verification:
  commands:
    - name: "Type Check"
      command: "mypy src/"
    - name: "Lint"
      command: "ruff check src/"
    - name: "Format Check"
      command: "ruff format --check src/"
    - name: "Tests"
      command: "pytest -xvs"
    - name: "Security Check"
      command: "bandit -r src/"
  metrics:
    max_file_lines: 300
    max_method_lines: 50
```

### JavaScript/TypeScript Project

```yaml
verification:
  commands:
    - name: "Type Check"
      command: "npx tsc --noEmit"
    - name: "Lint"
      command: "npx eslint src/"
    - name: "Tests"
      command: "npm test"
    - name: "Build"
      command: "npm run build"
```

## Getting Started

1. **Initialize the framework**: `codeteam init`
2. **Review the generated config**: Edit `.codeteam/config.yml` to match your project needs
3. **Customize agent instructions**: Modify files in `.codeteam/agent_instructions/` if needed
4. **Start planning**: `codeteam plan "Your feature request"`
5. **Begin coding**: `codeteam code`

The framework will use your configuration settings throughout the planning and coding process.
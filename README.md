# Code Team Framework

This project implements the "Code Team Framework", a system that orchestrates a team of specialized AI agents to automate software development tasks. It operates on a "human-on-the-loop" principle, where the system handles the cycles of coding and verification, while strategic decisions are left to the user.

The framework is built to be stateless and resilient, deriving its state from the filesystem (Git status, plan files, logs) to allow for easy stopping and resuming of tasks.

## Features

- **State Machine Orchestration:** A central orchestrator manages the entire workflow, from planning to coding, verification, and committing.
- **Specialized AI Agents:** A roster of agents (Planner, Coder, Verifiers, etc.) each with a specific role, powered by the Claude Code SDK.
- **File-Based State:** The system is stateless. Stop it at any time and it will recover its state from the repository's condition.
- **Human-on-the-Loop:** Key decision points, like plan approval and accepting code changes, require user intervention.
- **Configurable Workflow:** Define verification steps, agent settings, and LLM providers in a simple `.codeteam/config.yml`.
- **Extensible:** Designed with SOLID principles, making it easy to add new agents or verification steps.
- **Rich Terminal UI:** Agent output is displayed in styled panels for better readability. Note: Scrolling within the panels is not supported - use your terminal's scrollback feature to review previous output.

## Prerequisites

- Python 3.10+
- Node.js
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- An Anthropic API key set as an environment variable: `export ANTHROPIC_API_KEY="your-key-here"`

## Installation

### Install from PyPI (Recommended)

```bash
pip install code-team-framework
```

### Install from Source

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd code-team-framework
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -e ".[dev]"
    ```

## Usage

The framework is controlled via the `codeteam` command.

### 1. Planning a New Feature

Start by creating a plan. The `Planner` agent will collaborate with you to break down the request into a task list.

You can provide the initial request directly as an argument:
```bash
codeteam plan "Implement a user profile feature with bio and avatar."
```

Alternatively, you can run the command without an argument to be prompted for the request interactively:
```bash
codeteam plan
```
The agent will ask clarifying questions. When you're ready, type `/save_plan`. The plan will be saved to `.codeteam/planning/{plan_id}/plan.yml`.

Review the plan and accept it to begin the coding phase.

```bash
# The tool will prompt you for this after the plan is saved
/accept_plan
```

### 2. Executing the Plan

Once a plan is accepted, start the coding and verification loop.

```bash
codeteam code
```

The orchestrator will pick up the next pending task, generate a prompt, and invoke the `Coder` agent. After the `Coder` finishes, verification checks run automatically. You will be prompted to review the changes.

-   Type `/accept_changes` to commit the work and move to the next task.
-   Type `/reject_changes [your feedback]` to send it back to the `Coder` with your notes.

### 3. Resuming Work

If you stop the process, you can resume it at any time. The orchestrator will automatically determine the current state and pick up where it left off.

```bash
# If you were in the middle of coding:
codeteam code

# If you were in the middle of planning:
codeteam plan
```

## Integration

The Code Team Framework can be easily integrated into any project:

### 1. Initialize the Framework

```bash
# Navigate to your project
cd /path/to/your/project

# Initialize the framework (creates .codeteam/ directory)
codeteam init
```

This creates a `.codeteam/` directory with:
- `config.yml` - Main configuration file
- `agent_instructions/` - Customizable agent instruction templates
- `planning/` - Planning documents (generated during use)
- `reports/` - Verification reports (temporary)

Additionally, it creates `.claude/commands/` with slash commands for manual workflows.

### 2. Start Using the Framework

```bash
# Start planning and coding
codeteam plan "Implement new feature"
codeteam code
```

### 3. Customization

After initialization, you can customize:
- **Configuration**: Edit `.codeteam/config.yml` to adjust paths, verification commands, and agent settings
- **Agent Instructions**: Modify templates in `.codeteam/agent_instructions/` to customize how agents behave
- **Slash Commands**: Use `/codeteam-planner`, `/codeteam-coder`, etc. in Claude Code for manual agent invocation

## Configuration

The framework is configured via `.codeteam/config.yml`. You can set the LLM model, define custom verification commands, and configure agent behavior. Run `codeteam init` to create the default configuration file.

For comprehensive configuration options and examples, see the [Configuration Guide](docs/CONFIGURATION.md).

## Project Structure

**Framework Source Code:**
-   `src/code_team/__main__.py`: The command-line entry point (available as `codeteam` command after installation).
-   `src/code_team/`: The main application source code.
    -   `orchestrator/`: The core state machine and orchestrator logic.
    -   `agents/`: Implementations for all specialized AI agents.
    -   `models/`: Pydantic models for configuration and plan files.
    -   `utils/`: Helper modules for filesystem, Git, LLM interaction, and templating.
    -   `templates/`: Default agent instruction templates (packaged with the framework).

**When Used in Projects:**
-   `.codeteam/`: Framework directory (created by `codeteam init`).
    -   `config.yml`: Main configuration file.
    -   `agent_instructions/`: Customizable agent instruction templates.
    -   `planning/`: Generated plans and related documents.
    -   `reports/`: Verification reports (temporary files).

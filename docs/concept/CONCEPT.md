### Code Team Framework - Concept v2.0

#### I. Core Philosophy & Guiding Principles

The framework operates on a "human-on-the-loop" principle, not "human-in-the-loop". The system automates the tedious cycles of coding and verification, but key strategic decisions and final quality judgments are explicitly deferred to the human user. Agents are powerful tools, and the user is the master craftsperson directing them. The system prioritizes transparency, reliability, and auditability through a file-based state and logging system.

#### II. System Architecture & Orchestration

**1. The Orchestrator (`orchestrator.py`)**

This is the master Python application that drives the entire system. It is implemented as a state machine.

*   **State Machine:** The Orchestrator's current state is managed using a well-defined `Enum`.
    *   `IDLE`: The system is waiting for a user command.
    *   `PLANNING_DRAFTING`: The `Planner` agent is interacting with the user to create the initial plan.
    *   `PLANNING_AWAITING_REVIEW`: The plan is complete and awaits user action (`/accept_plan` or `/request_feedback_round`).
    *   `PLANNING_VERIFYING`: The `PlanVerifier` agent is running.
    *   `CODING_AWAITING_TASK_SELECTION`: A plan is approved. The `Situation` agent runs to determine the next task.
    *   `CODING_PROMPTING`: The `Prompter` agent is generating the prompt for the current task.
    *   `CODING_IN_PROGRESS`: The `Coder` agent is actively working on the task.
    *   `VERIFYING`: The automated checks and `Verifier` agents are running.
    *   `AWAITING_VERIFICATION_REVIEW`: Verification is complete. The aggregated report is presented to the user for a final decision (`/accept_changes` or `/reject_changes`).
    *   `COMMITTING`: The `Committer` agent is creating the git commit.
    *   `HALTED_FOR_ERROR`: An unrecoverable error occurred, requires manual intervention.
    *   `PLAN_COMPLETE`: All tasks in the plan are finished.

*   **State Persistence & Recovery:** The system is stateless by design. The Orchestrator determines the current state upon startup by inspecting the environment:
    1.  **Git Status:** It checks `git status --porcelain` and `git log` to understand the commit history and working directory state.
    2.  **Plan Files:** It scans the `.codeteam/planning/{plan-id}/plan.yml` file, checking the `status` of each task (`pending`, `completed`, `failed`).
    3.  **Log Files:** It checks for the existence of `CODER_LOG.md` and verification reports.
    This allows the process to be stopped and resumed reliably.

**2. Modular Agent Builder**

A central function, `build_system_prompt(agent_type: str, context: dict) -> str`, assembles the final system prompt for an agent. It uses a templating engine (e.g., Jinja2) to stitch together the required `.md` instruction files and inject dynamic context.

*   **Placeholders:**
| Placeholder | Description | Example Value |
|---|---|---|
| `{{PLAN_ID}}` | The unique ID of the current plan. | `feature-0021` |
| `{{TASK_ID}}` | The unique ID of the current task. | `task-003` |
| `{{TASK_DESCRIPTION}}`| The detailed description of the task from `plan.yml`. | `"Refactor user authentication to use a service class."` |
| `{{REPO_MAP}}` | The full directory tree of the repo (`ls -R`). | `(output of command)` |
| `{{RELEVANT_FILES_CONTENT}}` | Content of files suggested by the Prompter. | `### FILE: src/auth.py\n\n(content)\n\n### FILE: src/models.py\n\n(content)` |
| `{{VERIFICATION_FEEDBACK}}` | Structured Markdown report from the Verifier agents. | `(See Verification Report Format below)` |

#### III. Agent Roster & I/O Contracts

See: Code Team Framework - Agent Roster & Instructions

The framework will utilize a suite of specialized agents, all invoked via the Claude Code Python SDK.

*   **New Agent: Summarizer**
    *   **Instructions:** `SUMMARIZER_INSTRUCTIONS.md`. "You are a log summarization expert. Read the provided Coder Log and create a concise summary that preserves the key actions, decisions, and outcomes. The goal is to reduce token count while retaining essential context for the Coder agent."
    *   **Trigger:** Called by the Orchestrator if `CODER_LOG.md` exceeds a token threshold defined in the configuration.
    *   **Input:** `CODER_LOG.md`.
    *   **Output:** A summarized `CODER_LOG.md` (overwriting the old one).

*   **Planner Output:**
    *   `.codeteam/planning/{PLAN_ID}/plan.yml` (Structured YAML)
    *   `.codeteam/planning/{PLAN_ID}/ACCEPTANCE_CRITERIA.md` (Human-readable goals)

    **`plan.yml` Format:**
    ```yaml
    plan_id: "feature-0021"
    description: "Implement a full user profile feature."
    tasks:
      - id: "task-001"
        description: "Create the UserProfile model with fields: bio, avatar_url, location."
        dependencies: [] # List of task IDs this task depends on
        status: "pending" # pending | completed | failed
      - id: "task-002"
        description: "Create the API endpoint GET /api/v1/users/{user_id}/profile."
        dependencies: ["task-001"]
        status: "pending"
    ```

*   **Coder Agent Interaction:**
    *   The Orchestrator invokes the `Coder` agent using the `claude-code-sdk`.
    *   `cwd` is set to the project's root directory.
    *   `allowed_tools` is set to `["Read", "Write", "Bash"]` to give the agent filesystem access.
    *   The agent's output is not a file/patch, but the *side effects* of its execution on the filesystem. The Orchestrator monitors the subprocess until completion.

*   **Verification Report Format (Structured Markdown):**
    *   Verifiers write their output to `.codeteam/reports/{task_id}-{verifier_name}.md`.
    *   The Orchestrator aggregates these into a single report for the user.
    *   **Format:**
        ```markdown
        # Verification Report for Task: task-002

        **Overall Result:** FAIL

        ---

        ## 1. Static Checks

        - **pytest:** PASS
        - **ruff format:** PASS
        - **ruff lint:** FAIL

        ### Details:
        - `src/api/profile.py:45:10: F841: local variable 'user' is assigned to but never used`

        ---

        ## 2. Metric Checks

        - **File Length (src/api/profile.py):** PASS (120/500 lines)
        - **Method Length (get_user_profile):** PASS (40/80 lines)

        ---

        ## 3. Agent: Code Verifier - Architecture

        **Result:** FAIL

        ### Feedback:
        - **File:** `src/api/profile.py`
        - **Issue:** The `get_user_profile` function directly imports and uses the `DatabaseConnection` class.
        - **Violation:** This violates the Dependency Inversion Principle.
        - **Recommendation:** The function should depend on an abstraction (e.g., a `UserRepository` protocol/interface). The concrete database implementation should be injected at a higher level.

        ---

        ## 4. User Review

        **Your Decision:**
        - `/accept_changes` - Commits the current changes, ignoring any FAIL reports.
        - `/reject_changes [Your feedback here]` - Reverts changes and sends the report back to the Coder with your additional feedback.
        ```

*   **Committer Agent:**
    *   Upon receiving the signal to commit, the Orchestrator invokes this agent.
    *   The agent simply runs `git add .` followed by `git commit -m "Generated Message"`. The message is generated based on the task ID and description.

#### IV. The Detailed Workflow

**Mode: Plan**
1.  User runs `python orchestrator.py plan "Implement user profile feature"`.
2.  Orchestrator enters `PLANNING_DRAFTING` state, creating `.codeteam/planning/feature-0021`.
3.  It starts a loop with the `Planner` agent, which asks clarifying questions.
4.  When the user is satisfied, they type `/save_plan`. The `Planner` writes `plan.yml` and `ACCEPTANCE_CRITERIA.md`.
5.  Orchestrator transitions to `PLANNING_AWAITING_REVIEW`. It prompts the user: `Plan feature-0021 created. Do you want to /accept_plan or /request_feedback_round?`
6.  If `/request_feedback_round`, Orchestrator transitions to `PLANNING_VERIFYING`. The `PlanVerifier` agent runs, writing to `FEEDBACK.md`. The user is shown the feedback and the loop returns to step 5.
7.  If `/accept_plan`, the Orchestrator transitions to `CODING_AWAITING_TASK_SELECTION`.

**Mode: Code & Verification**
1.  Orchestrator starts the main coding loop for `feature-0021`.
2.  **Situation:** It calls the `Situation` agent to find the next `pending` task in `plan.yml` with met dependencies. Let's say it's `task-002`.
3.  **Prompter:** Transitions to `CODING_PROMPTING`. The `Prompter` agent is called for `task-002`. It generates a detailed prompt.
4.  **Coder:** Transitions to `CODING_IN_PROGRESS`. The Orchestrator calls the `Coder` agent via the Claude Code SDK with the generated prompt and necessary tools enabled. The `CODER_LOG.md` is updated.
5.  **Verification:** Once the Coder subprocess finishes, Orchestrator transitions to `VERIFYING`.
    *   It runs all commands from `.codeteam/config.yml`.
    *   It runs all metric checks.
    *   It invokes all `CodeVerifier` agents in parallel.
    *   It aggregates all outputs into the structured markdown report format shown above.
6.  **User Judgment:** Transitions to `AWAITING_VERIFICATION_REVIEW`. The final report is displayed to the user.
    *   **If user types `/accept_changes`:** The Orchestrator transitions to `COMMITTING`. It calls the `Committer` agent, which runs `git add .` and commits. The status of `task-002` in `plan.yml` is updated to `completed`. The loop returns to step 2.
    *   **If user types `/reject_changes Refactor this to use the repository pattern`:** It adds the user's feedback to the verification report. It then transitions back to `CODING_IN_PROGRESS` (step 4), providing the Coder with the original prompt plus the aggregated feedback report.
7.  **Completion:** If the `Situation` agent in step 2 finds no more pending tasks, the Orchestrator transitions to `PLAN_COMPLETE`, informs the user, and suggests pushing the branch.

#### V. Configuration (`.codeteam/config.yml`)

A YAML file at the root of the repository controls the framework's behavior.

```yaml
version: 1.0

# LLM provider configuration, passed to Claude Code SDK
llm:
  provider: "anthropic" # anthropic | bedrock | vertex
  model: "claude-3-opus-20240229"

# Agent-specific configurations
agents:
  coder:
    # Token limit for the CODER_LOG.md before the Summarizer is triggered.
    log_summarize_threshold: 75000

# Definitions for the VERIFYING state
verification:
  commands:
    - name: "Unit Tests"
      command: "pytest"
    - name: "Linter"
      command: "ruff check ."
    - name: "Formatter Check"
      command: "ruff format --check ."
  metrics:
    max_file_lines: 500
    max_method_lines: 80

# The number of concurrent verifier agents to run for each category.
# Allows scaling up specific checks for critical applications.
verifier_instances:
  architecture: 1
  task_completion: 1
  security: 1
  performance: 1
```

#### VI. Technology Stack

*   **Primary Language:** Python 3.10+
*   **Orchestration:** Custom Python script (`orchestrator.py`).
*   **Agent Engine:** **Claude Code SDK (`claude-code-sdk` PyPI package)**. This is the core engine for agent execution, leveraging its built-in tool use (Read, Write, Bash), session management, and secure subprocess execution. This simplifies the Orchestrator, which no longer needs to manage raw API calls, but instead manages the lifecycle of the SDK's subprocess.
*   **State & Data:** YAML (`plan.yml`, `config.yml`) and Markdown for human-readable logs and reports.
*   **Version Control:** Git. The framework is tightly integrated with the git workflow.

#### VII. Future Improvements

*   **Dockerization:** The entire system should run inside a Docker container that encapsulates the project, dependencies, and the framework itself. This provides a hermetically sealed, secure, and reproducible environment.
*   **Vector Search for Prompter:** Instead of relying solely on descriptive names, the `Prompter` could use embeddings (e.g., via SentenceTransformers) and a vector index (e.g., FAISS) of the codebase to find semantically relevant files for a given task, improving its accuracy on large repositories.
*   **Web UI:** A simple web interface (e.g., using Streamlit or Flask) could replace the CLI for a more user-friendly experience, especially for reviewing plans and verification reports.
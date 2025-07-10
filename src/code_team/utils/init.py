"""Initialization utilities for setting up the Code Team Framework in projects."""

from pathlib import Path

try:
    # Python 3.9+
    from importlib.resources import files
except ImportError:
    # Python 3.8 fallback
    from importlib_resources import files  # type: ignore[import-not-found,no-redef]

import yaml

from code_team.models.config import CodeTeamConfig


def initialize_project(
    project_root: Path, force: bool = False
) -> tuple[bool, list[str]]:
    """
    Initialize the Code Team Framework in a project directory.

    Args:
        project_root: The root directory of the project
        force: If True, overwrite existing files

    Returns:
        Tuple of (success, list of messages about what was done)
    """
    messages = []
    codeteam_dir = project_root / ".codeteam"

    # Check if already initialized (unless force is True)
    if codeteam_dir.exists() and not force:
        config_file = codeteam_dir / "config.yml"
        if config_file.exists():
            messages.append(
                "✓ Code Team Framework is already initialized in this project"
            )
            messages.append(f"  Configuration: {config_file}")
            messages.append(
                f"  Agent instructions: {codeteam_dir / 'agent_instructions'}"
            )
            messages.append("")
            messages.append("Use 'codeteam init --force' to reinitialize")
            return True, messages

    try:
        # Create directory structure
        _create_directory_structure(codeteam_dir, messages)

        # Create default configuration file
        _create_config_file(codeteam_dir / "config.yml", force, messages)

        # Extract agent instruction templates
        _extract_agent_instructions(
            codeteam_dir / "agent_instructions", force, messages
        )

        # Create Claude commands
        _create_claude_commands(project_root, force, messages)

        messages.append("")
        messages.append("✅ Code Team Framework initialized successfully!")
        messages.append("")
        messages.append("Next steps:")
        messages.append("1. Review and customize configuration: .codeteam/config.yml")
        messages.append(
            "2. Customize agent instructions: .codeteam/agent_instructions/"
        )
        messages.append("3. Start planning: codeteam plan 'Your request here'")
        messages.append(
            "   OR use slash commands: /codeteam-planner, /codeteam-coder, etc."
        )

        return True, messages

    except Exception as e:
        messages.append(f"❌ Failed to initialize: {e}")
        return False, messages


def _create_directory_structure(codeteam_dir: Path, messages: list[str]) -> None:
    """Create the .codeteam directory structure."""
    directories = [
        codeteam_dir,
        codeteam_dir / "agent_instructions",
        codeteam_dir / "planning",
        codeteam_dir / "reports",
    ]

    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            messages.append(
                f"✓ Created directory: {directory.relative_to(codeteam_dir.parent)}"
            )


def _create_config_file(config_path: Path, force: bool, messages: list[str]) -> None:
    """Create the default configuration file."""
    file_existed = config_path.exists()
    if file_existed and not force:
        messages.append(
            f"✓ Configuration file already exists: {config_path.relative_to(config_path.parent.parent)}"
        )
        return

    # Create default configuration with consolidated paths
    config = CodeTeamConfig()

    # Convert to dict and write as YAML
    config_dict = config.model_dump()

    with open(config_path, "w") as f:
        # Write a nice header comment
        f.write("# Code Team Framework Configuration\n")
        f.write("# This file configures the behavior of the Code Team Framework\n")
        f.write(
            "# Customize paths, verification commands, and agent settings below\n\n"
        )

        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    action = "Updated" if file_existed else "Created"
    messages.append(
        f"✓ {action} configuration file: {config_path.relative_to(config_path.parent.parent)}"
    )


def _extract_agent_instructions(
    instructions_dir: Path, force: bool, messages: list[str]
) -> None:
    """Extract agent instruction templates from package resources."""
    try:
        package_templates = files("code_team.templates")

        for template_file in package_templates.iterdir():
            if template_file.is_file() and template_file.name.endswith(".md"):
                dest_file = instructions_dir / template_file.name

                file_existed = dest_file.exists()
                if file_existed and not force:
                    continue

                # Read from package resource and write to destination
                content = template_file.read_text(encoding="utf-8")
                dest_file.write_text(content, encoding="utf-8")

                action = "Updated" if file_existed else "Extracted"
                relative_path = dest_file.relative_to(dest_file.parent.parent.parent)
                messages.append(f"✓ {action} template: {relative_path}")

    except Exception as e:
        messages.append(f"⚠️  Warning: Could not extract agent instructions: {e}")
        messages.append("   Agent instructions will be loaded from package resources")


def _create_claude_commands(
    project_root: Path, force: bool, messages: list[str]
) -> None:
    """Create Claude command templates in .claude/commands directory."""
    claude_dir = project_root / ".claude"
    commands_dir = claude_dir / "commands"

    # Create .claude/commands directory
    if not commands_dir.exists():
        commands_dir.mkdir(parents=True, exist_ok=True)
        messages.append(f" Created directory: {commands_dir.relative_to(project_root)}")

    try:
        package_commands = files("code_team.templates.claude_commands")

        for command_file in package_commands.iterdir():
            if command_file.is_file() and command_file.name.endswith(".md"):
                dest_file = commands_dir / command_file.name

                file_existed = dest_file.exists()
                if file_existed and not force:
                    continue

                # Read from package resource and write to destination
                content = command_file.read_text(encoding="utf-8")
                dest_file.write_text(content, encoding="utf-8")

                action = "Updated" if file_existed else "Created"
                relative_path = dest_file.relative_to(project_root)
                messages.append(f" {action} command: {relative_path}")

    except Exception as e:
        messages.append(f" Warning: Could not create Claude commands: {e}")
        messages.append("   Claude slash commands will not be available")


def check_initialization_status(project_root: Path) -> tuple[bool, list[str]]:
    """
    Check if the Code Team Framework is initialized in the project.

    Args:
        project_root: The root directory of the project

    Returns:
        Tuple of (is_initialized, list of status messages)
    """
    messages = []
    codeteam_dir = project_root / ".codeteam"

    if not codeteam_dir.exists():
        messages.append("❌ Code Team Framework is not initialized")
        messages.append("   Run 'codeteam init' to set up the framework")
        return False, messages

    config_file = codeteam_dir / "config.yml"
    instructions_dir = codeteam_dir / "agent_instructions"

    messages.append("✅ Code Team Framework is initialized")
    messages.append(f"📁 Framework directory: {codeteam_dir.relative_to(project_root)}")

    if config_file.exists():
        messages.append(f"⚙️  Configuration: {config_file.relative_to(project_root)}")
    else:
        messages.append("⚠️  Configuration file missing")

    if instructions_dir.exists():
        template_count = len(list(instructions_dir.glob("*.md")))
        messages.append(
            f"📝 Agent instructions: {instructions_dir.relative_to(project_root)} ({template_count} templates)"
        )
    else:
        messages.append("⚠️  Agent instructions directory missing")

    return True, messages

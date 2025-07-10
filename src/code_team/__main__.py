"""Entry point for the Code Team Framework CLI."""

import asyncio
from pathlib import Path

import typer

from code_team.orchestrator.orchestrator import Orchestrator
from code_team.utils.init import check_initialization_status, initialize_project
from code_team.utils.ui import interactive

app = typer.Typer(help="Code Team Framework Orchestrator")


@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration files."
    ),
    status: bool = typer.Option(
        False,
        "--status",
        "-s",
        help="Check initialization status without making changes.",
    ),
) -> None:
    """Initialize the Code Team Framework in the current project."""
    project_root = Path.cwd()

    if status:
        is_initialized, messages = check_initialization_status(project_root)
        for message in messages:
            print(message)
        return

    success, messages = initialize_project(project_root, force=force)
    for message in messages:
        print(message)

    if not success:
        raise typer.Exit(1)


@app.command()
def plan(
    request: str | None = typer.Argument(
        None, help="The initial user request for a new plan."
    ),
    config: Path = typer.Option(  # noqa: B008
        Path(".codeteam/config.yml"),
        "--config",
        "-c",
        help="Path to the configuration file relative to project root.",
    ),
) -> None:
    """Start or resume the planning phase."""
    project_root = Path.cwd()
    config_path = project_root / config

    orchestrator = Orchestrator(project_root=project_root, config_path=config_path)

    try:
        initial_request = request
        if not initial_request:
            initial_request = interactive.get_text_input("Enter your request").strip()

        if initial_request:
            asyncio.run(orchestrator.run_plan_phase(initial_request=initial_request))
        else:
            print("No request provided. Exiting.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except BaseException as e:
        print(f"\nAn unexpected error occurred: {e}")


@app.command()
def code(
    config: Path = typer.Option(  # noqa: B008
        Path(".codeteam/config.yml"),
        "--config",
        "-c",
        help="Path to the configuration file relative to project root.",
    ),
) -> None:
    """Start or resume the coding and verification loop."""
    project_root = Path.cwd()
    config_path = project_root / config

    orchestrator = Orchestrator(project_root=project_root, config_path=config_path)

    try:
        asyncio.run(orchestrator.run_code_phase())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except BaseException as e:
        print(f"\nAn unexpected error occurred: {e}")


@app.command()
def dashboard(
    config: Path = typer.Option(  # noqa: B008
        Path(".codeteam/config.yml"),
        "--config",
        "-c",
        help="Path to the configuration file relative to project root.",
    ),
) -> None:
    """Display a quick overview of the project's status."""
    project_root = Path.cwd()
    config_path = project_root / config

    orchestrator = Orchestrator(project_root=project_root, config_path=config_path)
    orchestrator.display_dashboard()


def main() -> None:
    """Main entry point for the Code Team Framework CLI."""
    app()


if __name__ == "__main__":
    main()

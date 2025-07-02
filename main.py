import asyncio
from pathlib import Path

import typer

from code_team.orchestrator.orchestrator import Orchestrator
from code_team.utils.ui import interactive

app = typer.Typer(help="Code Team Framework Orchestrator")


@app.command()
def plan(
    request: str | None = typer.Argument(
        None, help="The initial user request for a new plan."
    ),
) -> None:
    """Start or resume the planning phase."""
    # Define paths relative to the project root where main.py is located
    project_root = Path(__file__).parent
    config_path = project_root / "config/codeteam_config.yml"

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
def code() -> None:
    """Start or resume the coding and verification loop."""
    # Define paths relative to the project root where main.py is located
    project_root = Path(__file__).parent
    config_path = project_root / "config/codeteam_config.yml"

    orchestrator = Orchestrator(project_root=project_root, config_path=config_path)

    try:
        asyncio.run(orchestrator.run_code_phase())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except BaseException as e:
        print(f"\nAn unexpected error occurred: {e}")


def main() -> None:
    """Main entry point for the Code Team Framework CLI."""
    app()


if __name__ == "__main__":
    main()

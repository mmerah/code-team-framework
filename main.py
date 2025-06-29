import argparse
import asyncio
from pathlib import Path

from src.code_team.orchestrator.orchestrator import Orchestrator


def main() -> None:
    """Main entry point for the Code Team Framework CLI."""
    parser = argparse.ArgumentParser(description="Code Team Framework Orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser(
        "plan", help="Start or resume the planning phase."
    )
    plan_parser.add_argument(
        "request",
        nargs="?",
        default=None,
        help="The initial user request for a new plan.",
    )

    subparsers.add_parser(
        "code", help="Start or resume the coding and verification loop."
    )

    args = parser.parse_args()

    # Define paths relative to the project root where main.py is located
    project_root = Path(__file__).parent
    config_path = project_root / "config/codeteam_config.yml"

    orchestrator = Orchestrator(project_root=project_root, config_path=config_path)

    try:
        if args.command == "plan":
            initial_request = args.request
            if not initial_request:
                initial_request = input("Enter your request: ").strip()

            if initial_request:
                asyncio.run(
                    orchestrator.run_plan_phase(initial_request=initial_request)
                )
            else:
                print("No request provided. Exiting.")
        elif args.command == "code":
            asyncio.run(orchestrator.run_code_phase())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

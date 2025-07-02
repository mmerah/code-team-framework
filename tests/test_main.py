"""Unit tests for CLI entry point."""

from unittest.mock import MagicMock, patch

import typer.testing

from code_team.__main__ import app, main


class TestMainEntryPoint:
    """Test the main entry point function."""

    def test_main_function_exists(self) -> None:
        """Test that the main function exists and is callable."""
        assert callable(main)

    @patch("code_team.__main__.app")
    def test_main_calls_typer_app(self, mock_app: MagicMock) -> None:
        """Test that main() calls the typer app."""
        main()
        mock_app.assert_called_once()

    def test_cli_help_command(self) -> None:
        """Test that the CLI help command works."""
        runner = typer.testing.CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Code Team Framework Orchestrator" in result.stdout

    def test_cli_plan_command_exists(self) -> None:
        """Test that the plan command is available."""
        runner = typer.testing.CliRunner()
        result = runner.invoke(app, ["plan", "--help"])

        assert result.exit_code == 0
        assert "Start or resume the planning phase" in result.stdout

    def test_cli_code_command_exists(self) -> None:
        """Test that the code command is available."""
        runner = typer.testing.CliRunner()
        result = runner.invoke(app, ["code", "--help"])

        assert result.exit_code == 0
        assert "Start or resume the coding and verification loop" in result.stdout

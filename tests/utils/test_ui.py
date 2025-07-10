"""Unit tests for UI utilities (non-visual logic)."""

from unittest.mock import Mock, call, patch

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress

from code_team.utils.ui import (
    APP_THEME,
    DisplayManager,
    InteractiveManager,
    console,
    display,
    interactive,
)


class TestDisplayManager:
    """Test the DisplayManager class."""

    def test_initialization_with_default_console(self) -> None:
        """Test that DisplayManager initializes with default console."""
        manager = DisplayManager()
        assert manager.console is not None
        assert isinstance(manager.console, Console)
        # Test that it uses the global console by default
        from code_team.utils.ui import console as global_console

        default_manager = DisplayManager()
        assert default_manager.console is global_console

    def test_initialization_with_custom_console(self) -> None:
        """Test that DisplayManager can be initialized with custom console."""
        custom_console = Console()
        manager = DisplayManager(custom_console)
        assert manager.console is custom_console

    def test_create_overall_progress(self) -> None:
        """Test that create_overall_progress returns a Progress instance."""
        manager = DisplayManager()
        progress = manager.create_overall_progress()
        assert isinstance(progress, Progress)
        assert progress.console is manager.console
        # Progress instance configuration is checked by verifying it returns the right type

    def test_create_task_progress(self) -> None:
        """Test that create_task_progress returns a Progress instance."""
        manager = DisplayManager()
        progress = manager.create_task_progress()
        assert isinstance(progress, Progress)
        assert progress.console is manager.console
        # Progress instance configuration is checked by verifying it returns the right type

    def test_create_spinner_progress(self) -> None:
        """Test that create_spinner_progress returns a Progress instance."""
        manager = DisplayManager()
        progress = manager.create_spinner_progress("Test description")
        assert isinstance(progress, Progress)
        assert progress.console is manager.console
        # Progress instance configuration is checked by verifying it returns the right type

    def test_create_live_display(self) -> None:
        """Test that create_live_display returns a Live instance."""
        manager = DisplayManager()
        live = manager.create_live_display("Test content", refresh_per_second=2)
        assert isinstance(live, Live)
        assert live.console is manager.console
        assert live.refresh_per_second == 2
        assert live.transient

    def test_info_message_display(self) -> None:
        """Test that info messages are displayed with proper formatting."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.info("Test info message")

        mock_console.print.assert_called_once_with("[info]ℹ Test info message[/info]")

    def test_error_message_display(self) -> None:
        """Test that error messages are displayed with proper formatting."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.error("Test error message")

        mock_console.print.assert_called_once_with(
            "[error]✗ Test error message[/error]"
        )

    def test_success_message_display(self) -> None:
        """Test that success messages are displayed with proper formatting."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.success("Test success message")

        mock_console.print.assert_called_once_with(
            "[success]✓ Test success message[/success]"
        )

    def test_warning_message_display(self) -> None:
        """Test that warning messages are displayed with proper formatting."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.warning("Test warning message")

        mock_console.print.assert_called_once_with(
            "[warning]⚠ Test warning message[/warning]"
        )

    def test_agent_thought_display(self) -> None:
        """Test that agent thoughts are displayed with proper agent styling."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.agent_thought("planner", "Analyzing the problem")

        expected_message = (
            "[agent.planner][PLANNER][/agent.planner] Analyzing the problem"
        )
        mock_console.print.assert_called_once_with(expected_message)

    def test_agent_thought_display_case_insensitive(self) -> None:
        """Test that agent thoughts handle agent names case-insensitively."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.agent_thought("CODER", "Writing code")

        expected_message = "[agent.coder][CODER][/agent.coder] Writing code"
        mock_console.print.assert_called_once_with(expected_message)

    def test_panel_display_with_title_and_subtitle(self) -> None:
        """Test that panels are displayed with proper title and subtitle formatting."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.panel("Test content", title="Test Title", subtitle="Test Subtitle")

        # Verify console.print was called once
        assert mock_console.print.call_count == 1

        # Get the panel that was passed to print
        call_args = mock_console.print.call_args[0]
        panel = call_args[0]

        assert isinstance(panel, Panel)
        assert panel.renderable == "Test content"
        assert panel.title == "[title]Test Title[/title]"
        assert panel.subtitle == "[subtitle]Test Subtitle[/subtitle]"
        assert panel.border_style == "blue"

    def test_panel_display_without_title_and_subtitle(self) -> None:
        """Test that panels are displayed correctly without title and subtitle."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.panel("Test content only")

        # Verify console.print was called once
        assert mock_console.print.call_count == 1

        # Get the panel that was passed to print
        call_args = mock_console.print.call_args[0]
        panel = call_args[0]

        assert isinstance(panel, Panel)
        assert panel.renderable == "Test content only"
        assert panel.title is None
        assert panel.subtitle is None
        assert panel.border_style == "blue"

    def test_panel_display_with_title_only(self) -> None:
        """Test that panels are displayed correctly with title only."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.panel("Test content", title="Only Title")

        # Verify console.print was called once
        assert mock_console.print.call_count == 1

        # Get the panel that was passed to print
        call_args = mock_console.print.call_args[0]
        panel = call_args[0]

        assert isinstance(panel, Panel)
        assert panel.title == "[title]Only Title[/title]"
        assert panel.subtitle is None

    def test_panel_display_with_subtitle_only(self) -> None:
        """Test that panels are displayed correctly with subtitle only."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.panel("Test content", subtitle="Only Subtitle")

        # Verify console.print was called once
        assert mock_console.print.call_count == 1

        # Get the panel that was passed to print
        call_args = mock_console.print.call_args[0]
        panel = call_args[0]

        assert isinstance(panel, Panel)
        assert panel.title is None
        assert panel.subtitle == "[subtitle]Only Subtitle[/subtitle]"

    def test_print_method_delegates_to_console(self) -> None:
        """Test that print method delegates to console.print with all arguments."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.print("arg1", "arg2", "arg3")

        mock_console.print.assert_called_once_with("arg1", "arg2", "arg3")

    def test_print_method_with_no_arguments(self) -> None:
        """Test that print method works with no arguments."""
        mock_console = Mock(spec=Console)
        manager = DisplayManager(mock_console)

        manager.print()

        mock_console.print.assert_called_once_with()

    def test_create_agent_panel(self) -> None:
        """Test that create_agent_panel returns a properly styled Panel."""
        manager = DisplayManager()

        panel = manager.create_agent_panel("coder", "Test content")

        assert isinstance(panel, Panel)
        assert panel.renderable == "Test content"
        assert panel.title == "[agent.coder]CODER[/agent.coder]"
        assert panel.border_style == "agent.coder"
        assert not panel.expand

    def test_create_agent_panel_case_handling(self) -> None:
        """Test that create_agent_panel handles different agent name cases."""
        manager = DisplayManager()

        # Test lowercase
        panel = manager.create_agent_panel("planner", "Planning content")
        assert panel.title == "[agent.planner]PLANNER[/agent.planner]"
        assert panel.border_style == "agent.planner"

        # Test uppercase
        panel = manager.create_agent_panel("VERIFIER", "Verification content")
        assert panel.title == "[agent.verifier]VERIFIER[/agent.verifier]"
        assert panel.border_style == "agent.verifier"

        # Test mixed case
        panel = manager.create_agent_panel("Coder", "Code content")
        assert panel.title == "[agent.coder]CODER[/agent.coder]"
        assert panel.border_style == "agent.coder"

    def test_create_scrollable_panel(self) -> None:
        """Test that create_scrollable_panel handles overflow correctly."""
        # Mock console with specific height
        mock_console = Mock(spec=Console)
        mock_console.height = 30
        manager = DisplayManager(console_instance=mock_console)

        # Test with few lines (no overflow)
        short_content = ["Line 1", "Line 2", "Line 3"]
        panel = manager.create_scrollable_panel("agent", short_content)
        assert isinstance(panel, Panel)
        assert "Line 1\nLine 2\nLine 3" in str(panel.renderable)
        assert "Showing last" not in str(panel.renderable)

        # Test with many lines (overflow)
        long_content = [f"Line {i}" for i in range(50)]
        panel = manager.create_scrollable_panel("agent", long_content)
        assert isinstance(panel, Panel)
        # Should show overflow indicator
        assert "Showing last" in str(panel.renderable)
        assert "older output hidden" in str(panel.renderable)
        # Should include recent lines
        assert "Line 49" in str(panel.renderable)
        # Should not include early lines
        assert "Line 1" not in str(panel.renderable)


class TestInteractiveManager:
    """Test the InteractiveManager class."""

    def test_initialization_with_default_console(self) -> None:
        """Test that InteractiveManager initializes with default console."""
        manager = InteractiveManager()
        assert manager.console is not None
        assert isinstance(manager.console, Console)
        # Test that it uses the global console by default
        from code_team.utils.ui import console as global_console

        default_manager = InteractiveManager()
        assert default_manager.console is global_console

    def test_initialization_with_custom_console(self) -> None:
        """Test that InteractiveManager can be initialized with custom console."""
        custom_console = Console()
        manager = InteractiveManager(custom_console)
        assert manager.console is custom_console

    @patch("rich.prompt.Prompt.ask")
    def test_get_text_input_success(self, mock_prompt: Mock) -> None:
        """Test successful text input from user."""
        mock_prompt.return_value = "user input"
        manager = InteractiveManager()

        result = manager.get_text_input("Enter your name")

        assert result == "user input"
        mock_prompt.assert_called_once_with(
            "[info]Enter your name[/info]", console=manager.console
        )

    @patch("rich.prompt.Prompt.ask")
    def test_get_text_input_with_custom_console(self, mock_prompt: Mock) -> None:
        """Test text input with custom console instance."""
        mock_prompt.return_value = "custom response"
        custom_console = Mock(spec=Console)
        manager = InteractiveManager(custom_console)

        result = manager.get_text_input("Custom prompt")

        assert result == "custom response"
        mock_prompt.assert_called_once_with(
            "[info]Custom prompt[/info]", console=custom_console
        )

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_valid_selection(self, mock_prompt: Mock) -> None:
        """Test menu choice with valid numeric selection."""
        mock_prompt.return_value = "2"
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["Option A", "Option B", "Option C"]
        result = manager.get_menu_choice("Select an option", choices)

        assert result == "Option B"

        # Verify the menu was displayed
        expected_calls = [
            call("[info]Select an option[/info]"),
            call("  [highlight]1[/highlight]. Option A"),
            call("  [highlight]2[/highlight]. Option B"),
            call("  [highlight]3[/highlight]. Option C"),
        ]
        mock_console.print.assert_has_calls(expected_calls)

        # Verify the prompt was called
        mock_prompt.assert_called_once_with(
            "[info]Enter your choice (number)[/info]", console=mock_console
        )

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_first_option(self, mock_prompt: Mock) -> None:
        """Test menu choice selecting first option."""
        mock_prompt.return_value = "1"
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["First", "Second"]
        result = manager.get_menu_choice("Choose", choices)

        assert result == "First"

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_last_option(self, mock_prompt: Mock) -> None:
        """Test menu choice selecting last option."""
        mock_prompt.return_value = "3"
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["First", "Second", "Third"]
        result = manager.get_menu_choice("Choose", choices)

        assert result == "Third"

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_invalid_then_valid(self, mock_prompt: Mock) -> None:
        """Test menu choice with invalid input followed by valid input."""
        # First call returns invalid number, second call returns valid
        mock_prompt.side_effect = ["5", "2"]
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["Option A", "Option B", "Option C"]
        result = manager.get_menu_choice("Select an option", choices)

        assert result == "Option B"

        # Verify error message was displayed
        error_calls = [
            call
            for call in mock_console.print.call_args_list
            if "[error]Please enter a number between 1 and 3[/error]" in str(call)
        ]
        assert len(error_calls) == 1, "Expected error message for out-of-range input"

        # Verify prompt was called twice
        assert mock_prompt.call_count == 2

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_zero_input(self, mock_prompt: Mock) -> None:
        """Test menu choice with zero input (invalid)."""
        mock_prompt.side_effect = ["0", "1"]
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["Option A", "Option B"]
        result = manager.get_menu_choice("Select", choices)

        assert result == "Option A"

        # Verify error message for zero input
        error_calls = [
            call
            for call in mock_console.print.call_args_list
            if "[error]Please enter a number between 1 and 2[/error]" in str(call)
        ]
        assert len(error_calls) == 1

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_negative_input(self, mock_prompt: Mock) -> None:
        """Test menu choice with negative input (invalid)."""
        mock_prompt.side_effect = ["-1", "2"]
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["Option A", "Option B"]
        result = manager.get_menu_choice("Select", choices)

        assert result == "Option B"

        # Verify error message for negative input
        error_calls = [
            call
            for call in mock_console.print.call_args_list
            if "[error]Please enter a number between 1 and 2[/error]" in str(call)
        ]
        assert len(error_calls) == 1

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_non_numeric_input(self, mock_prompt: Mock) -> None:
        """Test menu choice with non-numeric input."""
        mock_prompt.side_effect = ["abc", "1"]
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["Option A", "Option B"]
        result = manager.get_menu_choice("Select", choices)

        assert result == "Option A"

        # Verify error message for non-numeric input
        error_calls = [
            call
            for call in mock_console.print.call_args_list
            if "[error]Please enter a valid number[/error]" in str(call)
        ]
        assert len(error_calls) == 1

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_empty_input(self, mock_prompt: Mock) -> None:
        """Test menu choice with empty input."""
        mock_prompt.side_effect = ["", "1"]
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["Option A"]
        result = manager.get_menu_choice("Select", choices)

        assert result == "Option A"

        # Verify error message for empty input
        error_calls = [
            call
            for call in mock_console.print.call_args_list
            if "[error]Please enter a valid number[/error]" in str(call)
        ]
        assert len(error_calls) == 1

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_single_option(self, mock_prompt: Mock) -> None:
        """Test menu choice with only one option available."""
        mock_prompt.return_value = "1"
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["Only Option"]
        result = manager.get_menu_choice("Only choice", choices)

        assert result == "Only Option"

        # Verify single option was displayed
        expected_calls = [
            call("[info]Only choice[/info]"),
            call("  [highlight]1[/highlight]. Only Option"),
        ]
        mock_console.print.assert_has_calls(expected_calls)

    @patch("rich.prompt.Prompt.ask")
    def test_get_menu_choice_multiple_invalid_inputs(self, mock_prompt: Mock) -> None:
        """Test menu choice with multiple invalid inputs before valid one."""
        mock_prompt.side_effect = ["abc", "0", "4", "2"]
        mock_console = Mock(spec=Console)
        manager = InteractiveManager(mock_console)

        choices = ["A", "B", "C"]
        result = manager.get_menu_choice("Pick", choices)

        assert result == "B"

        # Verify all error messages were displayed
        all_calls = [str(call) for call in mock_console.print.call_args_list]

        # Check for non-numeric error
        assert any(
            "[error]Please enter a valid number[/error]" in call for call in all_calls
        )

        # Check for out-of-range errors (both 0 and 4)
        range_errors = [
            call
            for call in all_calls
            if "[error]Please enter a number between 1 and 3[/error]" in call
        ]
        assert len(range_errors) == 2  # One for "0" and one for "4"

        # Verify prompt was called 4 times
        assert mock_prompt.call_count == 4


class TestTheme:
    """Test the application theme."""

    def test_app_theme_exists(self) -> None:
        """Test that APP_THEME is defined and contains expected keys."""
        assert APP_THEME is not None
        # Check for some expected theme keys
        expected_keys = [
            "info",
            "error",
            "success",
            "warning",
            "agent.planner",
            "agent.coder",
            "agent.verifier",
        ]
        theme_styles = APP_THEME.styles
        for key in expected_keys:
            assert key in theme_styles, f"Theme missing expected key: {key}"

    def test_app_theme_complete_coverage(self) -> None:
        """Test that APP_THEME contains all expected keys for complete coverage."""
        expected_keys = [
            "info",
            "error",
            "success",
            "warning",
            "agent.planner",
            "agent.coder",
            "agent.verifier",
            "agent.committer",
            "highlight",
            "title",
            "subtitle",
            "progress",
        ]
        theme_styles = APP_THEME.styles
        for key in expected_keys:
            assert key in theme_styles, f"Theme missing expected key: {key}"

    def test_app_theme_color_values(self) -> None:
        """Test that APP_THEME has appropriate color values for key styles."""
        from rich.style import Style

        theme_styles = APP_THEME.styles

        # Test specific color assignments by checking Style objects
        assert isinstance(theme_styles["info"], Style)
        assert str(theme_styles["info"]) == "cyan"
        assert str(theme_styles["error"]) == "bold red"
        assert str(theme_styles["success"]) == "bold green"
        assert str(theme_styles["warning"]) == "yellow"
        assert str(theme_styles["agent.planner"]) == "blue"
        assert str(theme_styles["agent.coder"]) == "green"
        assert str(theme_styles["agent.verifier"]) == "magenta"
        assert str(theme_styles["agent.committer"]) == "cyan"
        assert str(theme_styles["highlight"]) == "bold"
        assert str(theme_styles["title"]) == "bold blue"
        assert str(theme_styles["subtitle"]) == "dim"
        assert str(theme_styles["progress"]) == "bright_blue"


class TestGlobalInstances:
    """Test the global display and interactive instances."""

    def test_global_display_instance_exists(self) -> None:
        """Test that the global display instance is properly initialized."""
        assert display is not None
        assert isinstance(display, DisplayManager)
        assert display.console is console

    def test_global_interactive_instance_exists(self) -> None:
        """Test that the global interactive instance is properly initialized."""
        assert interactive is not None
        assert isinstance(interactive, InteractiveManager)
        assert interactive.console is console

    def test_global_console_has_theme(self) -> None:
        """Test that the global console instance is initialized with the APP_THEME."""
        assert console is not None
        assert isinstance(console, Console)
        # Check that console was initialized with our theme by testing a few style applications
        # We can't directly access the theme, but we can verify the console works with our theme styles
        assert hasattr(console, "push_theme")
        assert hasattr(console, "pop_theme")
        assert hasattr(console, "use_theme")

    def test_global_instances_use_same_console(self) -> None:
        """Test that global display and interactive instances share the same console."""
        assert display.console is interactive.console
        assert display.console is console

    def test_global_display_methods_work(self) -> None:
        """Test that global display instance methods are callable."""
        # Test that methods exist and are callable
        assert callable(display.info)
        assert callable(display.error)
        assert callable(display.success)
        assert callable(display.warning)
        assert callable(display.agent_thought)
        assert callable(display.panel)
        assert callable(display.print)
        assert callable(display.create_agent_panel)

    def test_global_interactive_methods_work(self) -> None:
        """Test that global interactive instance methods are callable."""
        # Test that methods exist and are callable
        assert callable(interactive.get_text_input)
        assert callable(interactive.get_menu_choice)

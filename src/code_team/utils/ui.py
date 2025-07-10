"""UI utilities for consistent theming and display management."""

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Prompt
from rich.theme import Theme

# Define a consistent theme for the CLI
APP_THEME = Theme(
    {
        "info": "cyan",
        "error": "bold red",
        "success": "bold green",
        "warning": "yellow",
        "agent.planner": "blue",
        "agent.coder": "green",
        "agent.verifier": "magenta",
        "agent.committer": "cyan",
        "agent.planverifier": "bright_magenta",
        "agent.prompter": "bright_cyan",
        "agent.codeverifier": "bright_red",
        "highlight": "bold",
        "title": "bold blue",
        "subtitle": "dim",
        "progress": "bright_blue",
    }
)

# Shared console instance with our theme
console = Console(theme=APP_THEME)


class DisplayManager:
    """Centralized display manager for consistent CLI output."""

    def __init__(self, console_instance: Console = console):
        """Initialize the DisplayManager with a console instance."""
        self.console = console_instance

    def info(self, message: str) -> None:
        """Display an informational message."""
        self.console.print(f"[info]ℹ {message}[/info]")

    def error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[error]✗ {message}[/error]")

    def success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[success]✓ {message}[/success]")

    def warning(self, message: str) -> None:
        """Display a warning message."""
        self.console.print(f"[warning]⚠ {message}[/warning]")

    def agent_thought(self, agent_name: str, message: str) -> None:
        """Display an agent's thought or action."""
        agent_style = f"agent.{agent_name.lower()}"
        self.console.print(
            f"[{agent_style}][{agent_name.upper()}][/{agent_style}] {message}"
        )

    def panel(
        self, content: str, title: str | None = None, subtitle: str | None = None
    ) -> None:
        """Display content in a styled panel."""
        panel = Panel(
            content,
            title=f"[title]{title}[/title]" if title else None,
            subtitle=f"[subtitle]{subtitle}[/subtitle]" if subtitle else None,
            border_style="blue",
        )
        self.console.print(panel)

    def print(self, *args: object) -> None:
        """Direct access to console print method."""
        self.console.print(*args)

    def create_overall_progress(self) -> Progress:
        """Create a progress bar for overall plan progress.

        Returns:
            A Progress instance configured for overall plan tracking.
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

    def create_task_progress(self) -> Progress:
        """Create a progress indicator for individual task processing.

        Returns:
            A Progress instance configured for task-level tracking.
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        )

    def create_spinner_progress(self, description: str) -> Progress:
        """Create a simple spinner progress indicator.

        Args:
            description: Description text to show with the spinner.

        Returns:
            A Progress instance configured as a spinner.
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn(f"[progress.description]{description}"),
            console=self.console,
            transient=True,
        )
        return progress

    def create_live_display(
        self, initial_content: str = "", refresh_per_second: int = 4
    ) -> Live:
        """Create a Live display context for real-time updates.

        Args:
            initial_content: Initial content to display.
            refresh_per_second: How often to refresh the display.

        Returns:
            A Live instance for real-time display updates.
        """
        return Live(
            initial_content,
            console=self.console,
            refresh_per_second=refresh_per_second,
            transient=True,
        )

    def create_scrollable_panel(
        self, agent_name: str, content_lines: list[str]
    ) -> Panel:
        """Create a panel that shows the most recent lines when content exceeds terminal height.

        Args:
            agent_name: The name of the agent.
            content_lines: List of content lines to display.

        Returns:
            A styled Panel object showing the most recent content.
        """
        # Calculate how many lines we can show while leaving room for UI
        terminal_height = self.console.height
        max_visible_lines = max(
            10, terminal_height - 10
        )  # Reserve space for panel borders and other UI

        # Determine what content to show
        if len(content_lines) > max_visible_lines:
            # Show indicator and most recent lines
            visible_lines = [
                f"[dim]━━━ Showing last {max_visible_lines - 1} of {len(content_lines)} lines (older output hidden) ━━━[/dim]"
            ]
            visible_lines.extend(content_lines[-(max_visible_lines - 1) :])
            content = "\n".join(visible_lines)
        else:
            content = "\n".join(content_lines)

        return self.create_agent_panel(agent_name, content)

    def create_agent_panel(self, agent_name: str, content: str) -> Panel:
        """Create a styled panel for agent output.

        Args:
            agent_name: The name of the agent.
            content: The content to display in the panel.

        Returns:
            A styled Panel object with the agent's output.
        """
        # Sanitize agent name for theme key generation
        sanitized_name = (
            agent_name.lower().replace(" ", "").replace("(", "").replace(")", "")
        )
        agent_style = f"agent.{sanitized_name}"

        # Check if style exists in theme, fallback to default if not
        if agent_style not in APP_THEME.styles:
            agent_style = "agent.verifier"

        return Panel(
            content,
            title=f"[{agent_style}]{agent_name.upper()}[/{agent_style}]",
            border_style=agent_style,
            expand=False,
        )


class InteractiveManager:
    """Manager for interactive user input components."""

    def __init__(self, console_instance: Console = console):
        """Initialize the InteractiveManager with a console instance."""
        self.console = console_instance

    def get_text_input(self, prompt_text: str) -> str:
        """Get text input from user with a bordered Rich component.

        Args:
            prompt_text: The prompt message to display to the user.

        Returns:
            The user's text input as a string.
        """
        return Prompt.ask(f"[info]{prompt_text}[/info]", console=self.console)

    def get_menu_choice(self, prompt_text: str, choices: list[str]) -> str:
        """Get a menu selection from user with Rich components.

        Args:
            prompt_text: The prompt message to display.
            choices: List of available choices.

        Returns:
            The selected choice as a string.
        """
        # Display the menu options
        self.console.print(f"[info]{prompt_text}[/info]")
        for i, choice in enumerate(choices, 1):
            self.console.print(f"  [highlight]{i}[/highlight]. {choice}")

        while True:
            try:
                selection = Prompt.ask(
                    "[info]Enter your choice (number)[/info]", console=self.console
                )
                choice_num = int(selection)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                else:
                    self.console.print(
                        f"[error]Please enter a number between 1 and {len(choices)}[/error]"
                    )
            except ValueError:
                self.console.print("[error]Please enter a valid number[/error]")


# Global display manager instance
display = DisplayManager()

# Global interactive manager instance
interactive = InteractiveManager()

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


class TemplateManager:
    """Manages rendering of Jinja2 templates for agent prompts."""

    def __init__(self, template_dir: Path):
        self._env = Environment(loader=FileSystemLoader(template_dir))

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a template with the given context."""
        template = self._env.get_template(template_name)
        # Load common context files
        common_context = {
            "ARCHITECTURE_GUIDELINES": self._load_guideline(
                "ARCHITECTURE_GUIDELINES.md"
            ),
            "CODING_GUIDELINES": self._load_guideline("CODING_GUIDELINES.md"),
            "AGENT_OBJECTIVITY": self._load_guideline("AGENT_OBJECTIVITY.md"),
            "REPO_MAP": self._load_guideline("REPO_MAP.md"),
        }
        return template.render({**common_context, **kwargs})

    def _load_guideline(self, filename: str) -> str:
        """Safely load a guideline file."""
        try:
            if self._env.loader:
                return self._env.loader.get_source(self._env, filename)[0]
            return f"Guideline file '{filename}' not found."
        except Exception:
            # Handle cases where a specific guideline might be missing
            return f"Guideline file '{filename}' not found."

import contextlib
import importlib.resources
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, FileSystemLoader, TemplateNotFound

from code_team.utils.filesystem import get_repo_map


class HybridTemplateLoader(BaseLoader):
    """Custom Jinja2 loader that supports both file system and package resources.

    Tries to load templates from the file system first, then falls back to
    package resources.
    """

    def __init__(
        self,
        template_dir: Path,
        package_name: str = "code_team",
        package_template_dir: str = "templates",
    ):
        self.fs_loader = FileSystemLoader(template_dir)
        self.package_name = package_name
        self.package_template_dir = package_template_dir

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        """Get template source, trying file system first, then package resources."""
        # Try file system first
        try:
            return self.fs_loader.get_source(environment, template)
        except TemplateNotFound:
            pass

        # Fall back to package resources
        try:
            # Use importlib.resources for Python 3.9+ compatibility
            package_path = f"{self.package_name}.{self.package_template_dir}"
            try:
                # Try new API first (Python 3.9+)
                files = importlib.resources.files(package_path)
                template_file = files / template
                if template_file.is_file():
                    source = template_file.read_text(encoding="utf-8")
                    # Return source with package resource path as filename
                    return (
                        source,
                        f"package://{package_path}/{template}",
                        lambda: True,
                    )
            except AttributeError:
                # Fall back to legacy API for older Python versions
                if importlib.resources.is_resource(package_path, template):
                    source = importlib.resources.read_text(package_path, template)
                    return (
                        source,
                        f"package://{package_path}/{template}",
                        lambda: True,
                    )
        except (ImportError, FileNotFoundError, ModuleNotFoundError):
            pass

        # If neither location has the template, raise TemplateNotFound
        raise TemplateNotFound(template)

    def list_templates(self) -> list[str]:
        """List all available templates from both sources."""
        templates = set()

        # Add file system templates
        with contextlib.suppress(Exception):
            templates.update(self.fs_loader.list_templates())

        # Add package templates
        try:
            package_path = f"{self.package_name}.{self.package_template_dir}"
            try:
                # Try new API first (Python 3.9+)
                files = importlib.resources.files(package_path)
                for item in files.iterdir():
                    if item.is_file():
                        templates.add(item.name)
            except AttributeError:
                # Fall back to legacy API for older Python versions
                try:
                    contents = importlib.resources.contents(package_path)
                    for item_name in contents:
                        if importlib.resources.is_resource(package_path, item_name):
                            templates.add(item_name)
                except Exception:
                    pass
        except (ImportError, ModuleNotFoundError):
            pass

        return list(templates)


class TemplateManager:
    """Manages rendering of Jinja2 templates for agent prompts."""

    def __init__(
        self,
        template_dir: Path,
        project_root: Path | None = None,
        guideline_files: list[str] | None = None,
        exclude_dirs: list[str] | None = None,
    ):
        self._loader = HybridTemplateLoader(template_dir, "code_team", "templates")
        self._env = Environment(loader=self._loader)
        self._project_root = project_root
        self._guideline_files = guideline_files or [
            "ARCHITECTURE_GUIDELINES.md",
            "CODING_GUIDELINES.md",
            "AGENT_OBJECTIVITY.md",
        ]
        self._exclude_dirs = exclude_dirs

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a template with the given context."""
        template = self._env.get_template(template_name)
        # Load common context files
        common_context = {}
        for guideline_file in self._guideline_files:
            # Create context key by removing extension and converting to uppercase
            context_key = guideline_file.replace(".md", "").upper()
            common_context[context_key] = self._load_guideline(guideline_file)

        # Generate repo map content dynamically if project_root is available
        if self._project_root:
            common_context["REPO_MAP"] = get_repo_map(
                self._project_root, self._exclude_dirs
            )

        return template.render({**common_context, **kwargs})

    def _load_guideline(self, filename: str) -> str:
        """Safely load a guideline file."""
        try:
            if self._loader:
                return self._loader.get_source(self._env, filename)[0]
            return f"Guideline file '{filename}' not found."
        except (TemplateNotFound, Exception):
            # Handle cases where a specific guideline might be missing
            return f"Guideline file '{filename}' not found."

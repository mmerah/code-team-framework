"""Unit tests for template utilities."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from jinja2 import TemplateNotFound

from code_team.utils.templates import TemplateManager


class TestTemplateManager:
    """Test the TemplateManager class."""

    def test_initialization(self) -> None:
        """Test TemplateManager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            manager = TemplateManager(template_dir)
            assert manager._env is not None
            assert manager._env.loader is not None

    def test_render_simple_template(self) -> None:
        """Test rendering a simple template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("Hello {{ name }}!")

            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text(
                "Architecture content"
            )
            (template_dir / "CODING_GUIDELINES.md").write_text("Coding content")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Objectivity content")
            (template_dir / "REPO_MAP.md").write_text("Repo map content")

            manager = TemplateManager(template_dir)
            result = manager.render("test.txt", name="World")

            assert "Hello World!" in result

    def test_render_with_guidelines_context(self) -> None:
        """Test that guidelines are loaded into template context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("Guidelines: {{ ARCHITECTURE_GUIDELINES }}")

            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text(
                "Test architecture"
            )
            (template_dir / "CODING_GUIDELINES.md").write_text("Test coding")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Test objectivity")
            (template_dir / "REPO_MAP.md").write_text("Test repo map")

            manager = TemplateManager(template_dir)
            result = manager.render("test.txt")

            assert "Guidelines: Test architecture" in result

    def test_render_missing_guideline_files(self) -> None:
        """Test rendering when guideline files are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ ARCHITECTURE_GUIDELINES }}")

            manager = TemplateManager(template_dir)
            result = manager.render("test.txt")

            assert "not found" in result

    def test_render_missing_template(self) -> None:
        """Test rendering a non-existent template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            manager = TemplateManager(template_dir)

            with pytest.raises(TemplateNotFound):
                manager.render("nonexistent.txt")

    def test_render_complex_template(self) -> None:
        """Test rendering a template with loops and conditions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            # Create a complex template
            template_content = """
            {% if items %}
            Items:
            {% for item in items %}
            - {{ item.name }}: {{ item.value }}
            {% endfor %}
            {% else %}
            No items found.
            {% endif %}
            """
            template_file = template_dir / "complex.txt"
            template_file.write_text(template_content)

            # Create mock guideline files
            for filename in [
                "ARCHITECTURE_GUIDELINES.md",
                "CODING_GUIDELINES.md",
                "AGENT_OBJECTIVITY.md",
                "REPO_MAP.md",
            ]:
                (template_dir / filename).write_text(f"Content of {filename}")

            manager = TemplateManager(template_dir)

            # Test with items
            items = [
                {"name": "Item1", "value": "Value1"},
                {"name": "Item2", "value": "Value2"},
            ]
            result = manager.render("complex.txt", items=items)
            assert "- Item1: Value1" in result
            assert "- Item2: Value2" in result

            # Test without items
            result = manager.render("complex.txt", items=[])
            assert "No items found." in result

    def test_render_custom_context_overrides_guidelines(self) -> None:
        """Test that custom context can override guideline context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ ARCHITECTURE_GUIDELINES }}")

            # Create guideline file
            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text("Original content")
            (template_dir / "CODING_GUIDELINES.md").write_text("Coding content")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Objectivity content")
            (template_dir / "REPO_MAP.md").write_text("Repo map content")

            manager = TemplateManager(template_dir)
            result = manager.render(
                "test.txt", ARCHITECTURE_GUIDELINES="Override content"
            )

            assert "Override content" in result
            assert "Original content" not in result

    def test_load_guideline_exception_handling(self) -> None:
        """Test that _load_guideline handles exceptions gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ ARCHITECTURE_GUIDELINES }}")

            manager = TemplateManager(template_dir)

            with patch.object(manager, "_load_guideline") as mock_load:
                mock_load.return_value = "Guideline file 'test.md' not found."

                result = manager.render("test.txt")

                assert "not found" in result

    def test_load_guideline_no_loader(self) -> None:
        """Test _load_guideline when loader is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            manager = TemplateManager(template_dir)

            manager._env.loader = None

            result = manager._load_guideline("test.md")
            assert "not found" in result

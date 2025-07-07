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
            assert manager._project_root is None

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

            manager = TemplateManager(template_dir)
            result = manager.render("test.txt")

            assert "Guidelines: Test architecture" in result

    def test_render_missing_guideline_files(self) -> None:
        """Test rendering when guideline files are missing from both file system and package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ UNKNOWN_GUIDELINE }}")

            # Use a custom guideline file that doesn't exist anywhere
            manager = TemplateManager(
                template_dir, guideline_files=["UNKNOWN_GUIDELINE.md"]
            )
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
            manager._loader = None  # type: ignore[assignment]
            result = manager._load_guideline("test.md")
            assert "not found" in result

    def test_package_fallback_loading(self) -> None:
        """Test that templates are loaded from package when not found in file system."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            # Create a template that uses a guideline that only exists in package
            template_file = template_dir / "test.txt"
            template_file.write_text("{{ ARCHITECTURE_GUIDELINES }}")

            # Don't create the guideline file in the temp directory
            manager = TemplateManager(template_dir)
            result = manager.render("test.txt")

            # Should load from package resources
            assert "Architecture Guidelines" in result
            assert "not found" not in result

    def test_file_system_priority(self) -> None:
        """Test that file system templates take priority over package templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            # Create a template and override guideline file
            template_file = template_dir / "test.txt"
            template_file.write_text("{{ ARCHITECTURE_GUIDELINES }}")

            # Create a custom guideline file that overrides the package one
            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text(
                "Custom File System Guidelines"
            )

            # Create other required guidelines so they don't fall back to package
            (template_dir / "CODING_GUIDELINES.md").write_text("Custom Coding")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Custom Objectivity")

            manager = TemplateManager(template_dir)
            result = manager.render("test.txt")

            # Should use file system version
            assert "Custom File System Guidelines" in result
            assert "Architecture Guidelines" not in result

    def test_custom_guideline_files(self) -> None:
        """Test that custom guideline files can be configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ CUSTOM_GUIDELINE }}")

            # Create custom guideline file
            (template_dir / "CUSTOM_GUIDELINE.md").write_text("Custom Content")

            manager = TemplateManager(
                template_dir, guideline_files=["CUSTOM_GUIDELINE.md"]
            )
            result = manager.render("test.txt")

            assert "Custom Content" in result

    def test_dynamic_repo_map_generation(self) -> None:
        """Test that repo map content is generated dynamically when project_root is provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()

            # Create a simple project structure
            (project_root / "file1.txt").write_text("content1")
            (project_root / "subdir").mkdir()
            (project_root / "subdir" / "file2.txt").write_text("content2")

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ REPO_MAP }}")

            # Create required guideline files
            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text("Architecture")
            (template_dir / "CODING_GUIDELINES.md").write_text("Coding")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Objectivity")

            manager = TemplateManager(template_dir, project_root=project_root)
            result = manager.render("test.txt")

            # Should contain the dynamically generated repo map
            assert "file1.txt" in result
            assert "subdir/" in result
            assert "file2.txt" in result

    def test_no_repo_map_without_project_root(self) -> None:
        """Test that REPO_MAP context is not available when project_root is not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ REPO_MAP if REPO_MAP else 'No repo map' }}")

            # Create required guideline files
            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text("Architecture")
            (template_dir / "CODING_GUIDELINES.md").write_text("Coding")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Objectivity")

            manager = TemplateManager(template_dir)  # No project_root provided
            result = manager.render("test.txt")

            # Should not have repo map content
            assert "No repo map" in result

    def test_repo_map_with_custom_exclude_dirs(self) -> None:
        """Test that custom exclude_dirs are properly used in repo map generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()

            # Create a project structure with files to exclude
            (project_root / "keep_file.txt").write_text("content")
            (project_root / "exclude_dir").mkdir()
            (project_root / "exclude_dir" / "hidden.txt").write_text("content")
            (project_root / "another_exclude").mkdir()
            (project_root / "another_exclude" / "also_hidden.txt").write_text("content")

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ REPO_MAP }}")

            # Create required guideline files
            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text("Architecture")
            (template_dir / "CODING_GUIDELINES.md").write_text("Coding")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Objectivity")

            # Test with custom exclude_dirs
            manager = TemplateManager(
                template_dir,
                project_root=project_root,
                exclude_dirs=["exclude_dir", "another_exclude"],
            )
            result = manager.render("test.txt")

            # Should contain the kept file but not the excluded directories
            assert "keep_file.txt" in result
            assert "exclude_dir" not in result
            assert "another_exclude" not in result
            assert "hidden.txt" not in result
            assert "also_hidden.txt" not in result

    def test_repo_map_with_default_exclude_dirs(self) -> None:
        """Test that default exclude_dirs are used when none are specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()

            # Create a project structure with default excluded directories
            (project_root / "keep_file.txt").write_text("content")
            (project_root / ".git").mkdir()
            (project_root / ".git" / "config").write_text("content")
            (project_root / "__pycache__").mkdir()
            (project_root / "__pycache__" / "cache.pyc").write_text("content")

            template_file = template_dir / "test.txt"
            template_file.write_text("{{ REPO_MAP }}")

            # Create required guideline files
            (template_dir / "ARCHITECTURE_GUIDELINES.md").write_text("Architecture")
            (template_dir / "CODING_GUIDELINES.md").write_text("Coding")
            (template_dir / "AGENT_OBJECTIVITY.md").write_text("Objectivity")

            # Test with no exclude_dirs specified (should use defaults)
            manager = TemplateManager(template_dir, project_root=project_root)
            result = manager.render("test.txt")

            # Should contain the kept file but not the default excluded directories
            assert "keep_file.txt" in result
            assert ".git" not in result
            assert "__pycache__" not in result
            assert "config" not in result
            assert "cache.pyc" not in result

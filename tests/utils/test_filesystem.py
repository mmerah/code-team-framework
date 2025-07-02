"""Unit tests for filesystem utilities."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from code_team.models.plan import Plan, Task
from code_team.utils.filesystem import (
    get_repo_map,
    load_plan,
    read_file,
    save_plan,
    write_file,
)


class TestWriteFile:
    """Test the write_file function."""

    def test_write_simple_file(self) -> None:
        """Test writing a simple file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            content = "Hello, World!"

            write_file(file_path, content)

            assert file_path.exists()
            assert file_path.read_text() == content

    def test_write_file_creates_directories(self) -> None:
        """Test automatic parent directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "subdir" / "nested" / "file.py"
            content = "def hello():\n    pass"

            write_file(file_path, content)

            assert file_path.exists()
            assert file_path.read_text() == content
            assert file_path.parent.exists()

    def test_overwrite_existing_file(self) -> None:
        """Test overwriting an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "existing.txt"
            file_path.write_text("Old content")

            new_content = "New content"
            write_file(file_path, new_content)

            assert file_path.read_text() == new_content

    def test_write_empty_file(self) -> None:
        """Test writing an empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "empty.txt"
            write_file(file_path, "")

            assert file_path.exists()
            assert file_path.read_text() == ""

    def test_write_unicode_content(self) -> None:
        """Test writing unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "unicode.txt"
            content = "Unicode: 你好世界 🌍 café"

            write_file(file_path, content)

            assert file_path.read_text() == content


class TestReadFile:
    """Test the read_file function."""

    def test_read_existing_file(self) -> None:
        """Test reading an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "read_test.txt"
            content = "Test content\nWith multiple lines"
            file_path.write_text(content)

            read_content = read_file(file_path)
            assert read_content == content

    def test_read_non_existent_file(self) -> None:
        """Test reading a non-existent file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "non_existent.txt"
            assert read_file(file_path) is None

    def test_read_empty_file(self) -> None:
        """Test reading an empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "empty.txt"
            file_path.write_text("")

            assert read_file(file_path) == ""

    def test_read_unicode_content(self) -> None:
        """Test reading file with unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "unicode.txt"
            content = "Unicode: 你好世界 🌍 café"
            file_path.write_text(content, encoding="utf-8")

            assert read_file(file_path) == content


class TestGetRepoMap:
    """Test the get_repo_map function."""

    def test_simple_directory_structure(self) -> None:
        """Test mapping a simple directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create files and directories
            (root / "file1.py").write_text("content")
            (root / "file2.txt").write_text("content")
            (root / "subdir").mkdir()
            (root / "subdir" / "nested.py").write_text("content")

            repo_map = get_repo_map(root)

            assert "file1.py" in repo_map
            assert "file2.txt" in repo_map
            assert "subdir/" in repo_map
            assert "nested.py" in repo_map

    def test_excludes_default_directories(self) -> None:
        """Test that default excluded directories are not included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            (root / "file.py").write_text("content")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("content")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "cache.pyc").write_text("content")
            (root / ".venv").mkdir()
            (root / ".venv" / "lib").mkdir()

            repo_map = get_repo_map(root)

            assert "file.py" in repo_map
            assert ".git" not in repo_map
            assert "__pycache__" not in repo_map
            assert ".venv" not in repo_map

    def test_custom_exclude_directories(self) -> None:
        """Test with custom excluded directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create files and directories
            (root / "keep.py").write_text("content")
            (root / "exclude_me").mkdir()
            (root / "exclude_me" / "file.py").write_text("content")

            repo_map = get_repo_map(root, exclude_dirs=["exclude_me"])

            assert "keep.py" in repo_map
            assert "exclude_me" not in repo_map

    def test_empty_directory(self) -> None:
        """Test mapping an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_map = get_repo_map(root)
            assert repo_map == ""

    def test_nested_structure_indentation(self) -> None:
        """Test proper indentation for nested directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            (root / "level1").mkdir()
            (root / "level1" / "level2").mkdir()
            (root / "level1" / "level2" / "file.py").write_text("content")

            repo_map = get_repo_map(root)
            lines = repo_map.split("\n")

            level1_line = next(line for line in lines if "level1/" in line)
            level2_line = next(line for line in lines if "level2/" in line)
            file_line = next(line for line in lines if "file.py" in line)

            assert level1_line.startswith("|-- ")
            assert level2_line.startswith("    |-- ")
            assert file_line.startswith("        |-- ")


class TestLoadPlan:
    """Test the load_plan function."""

    def test_load_valid_plan(self) -> None:
        """Test loading a valid plan file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "plan.yml"
            plan_data = {
                "plan_id": "test-plan",
                "description": "Test plan description",
                "tasks": [
                    {"id": "task-1", "description": "First task"},
                    {"id": "task-2", "description": "Second task"},
                ],
            }
            plan_path.write_text(yaml.dump(plan_data))

            plan = load_plan(plan_path)

            assert plan is not None
            assert plan.plan_id == "test-plan"
            assert plan.description == "Test plan description"
            assert len(plan.tasks) == 2
            assert plan.tasks[0].id == "task-1"
            assert plan.tasks[1].id == "task-2"

    def test_load_non_existent_plan(self) -> None:
        """Test loading a non-existent plan file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "non_existent.yml"
            plan = load_plan(plan_path)
            assert plan is None

    def test_load_invalid_yaml(self) -> None:
        """Test loading an invalid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "invalid.yml"
            plan_path.write_text("invalid: yaml: content: [")

            with patch("builtins.print") as mock_print:
                plan = load_plan(plan_path)
                assert plan is None
                mock_print.assert_called()

    def test_load_invalid_plan_structure(self) -> None:
        """Test loading YAML with invalid plan structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "invalid_structure.yml"
            plan_data = {"tasks": [{"id": "task-1"}]}
            plan_path.write_text(yaml.dump(plan_data))

            with patch("builtins.print") as mock_print:
                plan = load_plan(plan_path)
                assert plan is None
                mock_print.assert_called()

    def test_load_empty_plan(self) -> None:
        """Test loading an empty plan file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "empty.yml"
            plan_path.write_text("")

            plan = load_plan(plan_path)
            assert plan is None


class TestSavePlan:
    """Test the save_plan function."""

    def test_save_simple_plan(self) -> None:
        """Test saving a simple plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "plan.yml"

            tasks = [
                Task(id="task-1", description="First task"),
                Task(id="task-2", description="Second task"),
            ]
            plan = Plan(plan_id="test-plan", description="Test plan", tasks=tasks)

            save_plan(plan_path, plan)

            assert plan_path.exists()

            loaded_plan = load_plan(plan_path)
            assert loaded_plan is not None
            assert loaded_plan.plan_id == "test-plan"
            assert len(loaded_plan.tasks) == 2
            assert loaded_plan.tasks[0].id == "task-1"
            assert loaded_plan.tasks[1].id == "task-2"

    def test_save_empty_plan(self) -> None:
        """Test saving an empty plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "empty_plan.yml"
            plan = Plan(plan_id="empty-plan", description="Empty plan", tasks=[])

            save_plan(plan_path, plan)

            assert plan_path.exists()
            loaded_plan = load_plan(plan_path)
            assert loaded_plan is not None
            assert len(loaded_plan.tasks) == 0

    def test_save_creates_directory(self) -> None:
        """Test that save_plan creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "subdir" / "nested" / "plan.yml"
            plan = Plan(
                plan_id="nested-plan",
                description="Nested plan",
                tasks=[Task(id="task-1", description="Test task")],
            )

            save_plan(plan_path, plan)

            assert plan_path.exists()
            assert plan_path.parent.exists()

    def test_save_overwrites_existing(self) -> None:
        """Test that save_plan overwrites existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "plan.yml"

            initial_plan = Plan(
                plan_id="initial-plan",
                description="Initial plan",
                tasks=[Task(id="initial", description="Initial task")],
            )
            save_plan(plan_path, initial_plan)

            new_plan = Plan(
                plan_id="new-plan",
                description="New plan",
                tasks=[Task(id="new", description="New task")],
            )
            save_plan(plan_path, new_plan)

            loaded_plan = load_plan(plan_path)
            assert loaded_plan is not None
            assert len(loaded_plan.tasks) == 1
            assert loaded_plan.tasks[0].id == "new"

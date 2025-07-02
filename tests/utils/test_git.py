"""Unit tests for git utilities."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from code_team.utils.git import commit_changes, get_git_diff, get_git_status


class TestGetGitStatus:
    """Test the get_git_status function."""

    @patch("subprocess.run")
    def test_git_status_success(self, mock_run: Mock) -> None:
        """Test successful git status command."""
        mock_run.return_value = Mock(stdout=" M file1.py\n?? file2.py\n", returncode=0)

        result = get_git_status(Path("/test/path"))

        assert result == "M file1.py\n?? file2.py"
        mock_run.assert_called_once_with(
            ["git", "status", "--porcelain"],
            cwd=Path("/test/path"),
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_git_status_empty(self, mock_run: Mock) -> None:
        """Test git status with no changes."""
        mock_run.return_value = Mock(stdout="", returncode=0)

        result = get_git_status(Path("/test/path"))

        assert result == ""

    @patch("subprocess.run")
    def test_git_status_command_error(self, mock_run: Mock) -> None:
        """Test git status command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = get_git_status(Path("/test/path"))

        assert result == "Error: Git command failed or not found."

    @patch("subprocess.run")
    def test_git_status_file_not_found(self, mock_run: Mock) -> None:
        """Test git status when git is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = get_git_status(Path("/test/path"))

        assert result == "Error: Git command failed or not found."


class TestGetGitDiff:
    """Test the get_git_diff function."""

    @patch("subprocess.run")
    def test_git_diff_success(self, mock_run: Mock) -> None:
        """Test successful git diff command."""
        diff_output = """diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
+    print("new line")
     pass"""
        mock_run.return_value = Mock(stdout=diff_output, returncode=0)

        result = get_git_diff(Path("/test/path"))

        assert result == diff_output
        mock_run.assert_called_once_with(
            ["git", "diff", "HEAD"],
            cwd=Path("/test/path"),
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_git_diff_no_changes(self, mock_run: Mock) -> None:
        """Test git diff with no changes."""
        mock_run.return_value = Mock(stdout="", returncode=0)

        result = get_git_diff(Path("/test/path"))

        assert result == ""

    @patch("subprocess.run")
    def test_git_diff_command_error(self, mock_run: Mock) -> None:
        """Test git diff command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = get_git_diff(Path("/test/path"))

        assert result == "Error: Git command failed or not found."

    @patch("subprocess.run")
    def test_git_diff_file_not_found(self, mock_run: Mock) -> None:
        """Test git diff when git is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = get_git_diff(Path("/test/path"))

        assert result == "Error: Git command failed or not found."


class TestCommitChanges:
    """Test the commit_changes function."""

    @patch("subprocess.run")
    def test_commit_changes_success(self, mock_run: Mock) -> None:
        """Test successful commit."""
        mock_run.return_value = Mock(returncode=0)

        result = commit_changes(Path("/test/path"), "Test commit message")

        assert result is True
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "add", "."], cwd=Path("/test/path"), check=True
        )
        mock_run.assert_any_call(
            ["git", "commit", "-m", "Test commit message"],
            cwd=Path("/test/path"),
            check=True,
        )

    @patch("subprocess.run")
    def test_commit_changes_add_fails(self, mock_run: Mock) -> None:
        """Test commit when git add fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = commit_changes(Path("/test/path"), "Test message")

        assert result is False
        mock_run.assert_called_once_with(
            ["git", "add", "."], cwd=Path("/test/path"), check=True
        )

    @patch("subprocess.run")
    def test_commit_changes_commit_fails(self, mock_run: Mock) -> None:
        """Test commit when git commit fails."""
        mock_run.side_effect = [
            Mock(returncode=0),
            subprocess.CalledProcessError(1, "git"),
        ]

        result = commit_changes(Path("/test/path"), "Test message")

        assert result is False
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_commit_changes_file_not_found(
        self, mock_print: Mock, mock_run: Mock
    ) -> None:
        """Test commit when git is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = commit_changes(Path("/test/path"), "Test message")

        assert result is False
        mock_print.assert_called_once_with("Error: Git commit failed.")

    @patch("subprocess.run")
    def test_commit_changes_empty_message(self, mock_run: Mock) -> None:
        """Test commit with empty message."""
        mock_run.return_value = Mock(returncode=0)

        result = commit_changes(Path("/test/path"), "")

        assert result is True
        mock_run.assert_any_call(
            ["git", "commit", "-m", ""], cwd=Path("/test/path"), check=True
        )

    @patch("subprocess.run")
    def test_commit_changes_multiline_message(self, mock_run: Mock) -> None:
        """Test commit with multiline message."""
        mock_run.return_value = Mock(returncode=0)
        message = "First line\nSecond line\nThird line"

        result = commit_changes(Path("/test/path"), message)

        assert result is True
        mock_run.assert_any_call(
            ["git", "commit", "-m", message], cwd=Path("/test/path"), check=True
        )

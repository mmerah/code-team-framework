import subprocess
from pathlib import Path


def get_git_status(cwd: Path) -> str:
    """Get the output of 'git status --porcelain'."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Error: Git command failed or not found."


def get_git_diff(cwd: Path) -> str:
    """Get the output of 'git diff HEAD'."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Error: Git command failed or not found."


def commit_changes(cwd: Path, message: str) -> bool:
    """Stage all changes and commit them."""
    try:
        subprocess.run(["git", "add", "."], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=cwd, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Git commit failed.")
        return False

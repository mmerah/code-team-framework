from pathlib import Path

import yaml

from code_team.models.plan import Plan


def write_file(path: Path, content: str) -> None:
    """Safely write content to a file, creating directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_file(path: Path) -> str | None:
    """Safely read content from a file."""
    return path.read_text(encoding="utf-8") if path.exists() else None


def get_repo_map(root: Path, exclude_dirs: list[str] | None = None) -> str:
    """Generate a string representation of the repository file tree."""
    if exclude_dirs is None:
        exclude_dirs = [
            ".git",
            ".mypy_cache",
            ".ruff_cache",
            ".venv",
            ".idea",
            "__pycache__",
            ".codeteam",
            "node_modules",
            "build",
        ]

    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        if any(d in path.parts for d in exclude_dirs):
            continue

        depth = len(path.relative_to(root).parts) - 1
        indent = "    " * depth
        lines.append(
            f"{indent}{'|-- ' if depth > -1 else ''}{path.name}{'/' if path.is_dir() else ''}"
        )

    return "\n".join(lines)


def load_plan(plan_path: Path) -> Plan | None:
    """Load and parse the plan.yml file."""
    content = read_file(plan_path)
    if not content:
        return None
    try:
        plan_data = yaml.safe_load(content)
        return Plan.model_validate(plan_data)
    except (yaml.YAMLError, ValueError) as e:
        print(f"Error parsing plan file {plan_path}: {e}")
        return None


def save_plan(plan_path: Path, plan: Plan) -> None:
    """Save a Plan object to a YAML file."""
    plan_dict = plan.model_dump(mode="json")
    write_file(plan_path, yaml.dump(plan_dict, sort_keys=False))

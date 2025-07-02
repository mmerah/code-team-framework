"""Unit tests for plan models."""

from typing import Any, cast

import pytest
from pydantic import ValidationError

from code_team.models.plan import Plan, Task


class TestTask:
    """Test the Task model."""

    def test_create_task(self) -> None:
        """Test creating a Task with required fields."""
        task = Task(
            id="task-1",
            description="Add login and registration endpoints",
        )
        assert task.id == "task-1"
        assert task.description == "Add login and registration endpoints"
        assert task.status == "pending"
        assert task.dependencies == []

    def test_task_requires_fields(self) -> None:
        """Test that Task requires all fields."""
        with pytest.raises(ValidationError):
            cast(Any, Task)(id="test")  # Missing description
        with pytest.raises(ValidationError):
            cast(Any, Task)(description="Test")  # Missing id

    def test_task_with_dependencies(self) -> None:
        """Test creating a task with dependencies."""
        task = Task(
            id="task-2",
            description="Test task",
            dependencies=["task-1", "task-0"],
        )
        assert task.dependencies == ["task-1", "task-0"]

    def test_task_with_status(self) -> None:
        """Test creating a task with specific status."""
        task = Task(
            id="task-3",
            description="Completed task",
            status="completed",
        )
        assert task.status == "completed"

    def test_invalid_status(self) -> None:
        """Test that invalid status raises validation error."""
        with pytest.raises(ValidationError):
            cast(Any, Task)(
                id="task-4",
                description="Invalid status task",
                status="invalid_status",  # This should fail validation
            )


class TestPlan:
    """Test the Plan model."""

    def test_create_empty_plan(self) -> None:
        """Test creating a Plan with no tasks."""
        plan = Plan(plan_id="plan-1", description="Empty test plan", tasks=[])
        assert plan.plan_id == "plan-1"
        assert plan.description == "Empty test plan"
        assert plan.tasks == []

    def test_create_plan_with_tasks(self) -> None:
        """Test creating a Plan with multiple tasks."""
        task1 = Task(id="task-1", description="Create PostgreSQL database schema")
        task2 = Task(id="task-2", description="Define ORM models for users")
        plan = Plan(
            plan_id="plan-2", description="Database setup plan", tasks=[task1, task2]
        )

        assert len(plan.tasks) == 2
        assert plan.tasks[0].id == "task-1"
        assert plan.tasks[1].id == "task-2"

    def test_plan_preserves_task_order(self) -> None:
        """Test that Plan preserves the order of tasks."""
        tasks = [Task(id=f"task-{i}", description=f"Description {i}") for i in range(5)]
        plan = Plan(plan_id="plan-3", description="Order test plan", tasks=tasks)

        for i, task in enumerate(plan.tasks):
            assert task.id == f"task-{i}"
            assert task.description == f"Description {i}"

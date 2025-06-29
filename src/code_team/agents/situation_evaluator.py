from code_team.agents.base import Agent
from code_team.models.plan import Plan


class SituationEvaluator(Agent):
    """Determines the next task to be executed from a plan."""

    async def run(self, plan: Plan) -> str:  # type: ignore[override]
        """
        Identifies the next pending task whose dependencies are met.

        Args:
            plan: The current project plan.

        Returns:
            The ID of the next task, or "PLAN_COMPLETE".
        """
        print("Situation Evaluator: Determining next task...")

        completed_task_ids = {
            task.id for task in plan.tasks if task.status == "completed"
        }

        for task in plan.tasks:
            if task.status == "pending":
                dependencies_met = all(
                    dep_id in completed_task_ids for dep_id in task.dependencies
                )
                if dependencies_met:
                    print(f"Situation Evaluator: Next task is '{task.id}'.")
                    return task.id

        print("Situation Evaluator: All tasks are complete.")
        return "PLAN_COMPLETE"

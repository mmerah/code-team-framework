from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["pending", "completed", "failed"]


class Task(BaseModel):
    id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    status: TaskStatus = "pending"


class Plan(BaseModel):
    plan_id: str
    description: str
    tasks: list[Task] = Field(default_factory=list[Task])

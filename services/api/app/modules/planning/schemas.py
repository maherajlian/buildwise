from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.specifications.schemas import Title


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Generate(Strict):
    overwrite: bool = False


class EpicCreate(Strict):
    title: Title
    description: str = Field(default="", max_length=10000)
    position: int = Field(default=0, ge=0, le=10000)


class EpicEdit(Strict):
    title: Title | None = None
    description: str | None = Field(default=None, max_length=10000)
    position: int | None = Field(default=None, ge=0, le=10000)

    @model_validator(mode="after")
    def non_null(self) -> "EpicEdit":
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Fields cannot be null")
        return self


class EpicRead(EpicCreate):
    id: UUID
    project_id: UUID


Priority = Literal["P0", "P1", "P2"]
Status = Literal["backlog", "ready", "in_progress", "review", "done"]
Criteria = Annotated[
    list[Annotated[str, Field(min_length=1, max_length=1000)]], Field(max_length=20)
]
Dependencies = Annotated[list[UUID], Field(max_length=1000)]


class TaskCreate(Strict):
    epic_id: UUID | None = None
    title: Title
    description: str = Field(default="", max_length=10000)
    priority: Priority = "P1"
    status: Status = "backlog"
    implementation_notes: str = Field(default="", max_length=20000)
    acceptance_criteria: Criteria = []
    skill: str = Field(default="", max_length=200)
    workflow: str = Field(default="", max_length=5000)
    depends_on: Dependencies = []
    requirement_id: UUID | None = None


class TaskEdit(Strict):
    epic_id: UUID | None = None
    title: Title | None = None
    description: str | None = Field(default=None, max_length=10000)
    priority: Priority | None = None
    status: Status | None = None
    implementation_notes: str | None = Field(default=None, max_length=20000)
    acceptance_criteria: Criteria | None = None
    skill: str | None = Field(default=None, max_length=200)
    workflow: str | None = Field(default=None, max_length=5000)
    depends_on: Dependencies | None = None
    requirement_id: UUID | None = None

    @model_validator(mode="after")
    def non_null(self) -> "TaskEdit":
        if any(
            getattr(self, key) is None
            for key in self.model_fields_set
            if key not in {"epic_id", "requirement_id"}
        ):
            raise ValueError("Fields cannot be null")
        return self


class TaskRead(TaskCreate):
    acceptance_criteria: list[str]
    description: str
    id: UUID
    project_id: UUID
    key: str


class Validation(Strict):
    valid: bool
    errors: list[str]


class PlanRead(Strict):
    epics: list[EpicRead]
    tasks: list[TaskRead]
    validation: Validation

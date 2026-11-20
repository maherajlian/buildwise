from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Item = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
Items = Annotated[list[Item], Field(default_factory=list, max_length=30)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    fields: tuple[str, ...]


STEPS = (
    Step("problem", "Problem", ("problem_statement",)),
    Step("users", "Users", ("target_users", "user_needs")),
    Step("goals", "Goals and success", ("goals", "success_metrics")),
    Step("scope", "Scope and constraints", ("in_scope", "out_of_scope", "constraints")),
    Step("context", "Integrations and risks", ("integrations", "assumptions", "risks")),
    Step("questions", "Open questions", ("open_questions",)),
)
StepId = Literal["problem", "users", "goals", "scope", "context", "questions", "review"]
REQUIRED = {"problem_statement", "target_users", "goals", "constraints"}


class DiscoveryAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_statement: LongText = ""
    target_users: Items
    user_needs: Items
    goals: Items
    success_metrics: Items
    in_scope: Items
    out_of_scope: Items
    constraints: Items
    integrations: Items
    assumptions: Items
    risks: Items
    open_questions: Items


def completed_steps(answers: dict[str, Any]) -> list[str]:
    def filled(field: str) -> bool:
        return bool(answers.get(field))

    return [
        step.id
        for step in STEPS
        if all(filled(field) for field in step.fields if field in REQUIRED)
        and any(filled(field) for field in step.fields)
    ]

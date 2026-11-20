from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Text = Annotated[str, StringConstraints(max_length=100000)]
Category = Literal[
    "unit",
    "integration",
    "api_contract",
    "e2e",
    "accessibility",
    "security",
    "performance",
    "manual_acceptance",
    "model_evaluation",
    "prompt_regression",
    "tool_use_evaluation",
]
TestStatus = Literal["proposed", "planned", "passed", "failed", "blocked"]
RiskCategory = Literal[
    "technical", "security", "operational", "delivery", "compliance", "cost"
]
RiskStatus = Literal["open", "mitigating", "accepted", "closed"]
SLOStatus = Literal["suggested", "adopted", "rejected"]
Kind = Literal["test_cases", "risks", "slos"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @model_validator(mode="after")
    def reject_nulls(self) -> "Strict":
        for key in self.model_fields_set:
            if key not in {"requirement_id", "executed_at", "executed_by", "kinds"}:
                if getattr(self, key) is None:
                    raise ValueError(f"{key} cannot be null")
        return self


class TestCreate(Strict):
    requirement_id: UUID | None = None
    category: Category
    title: Title
    description: Text = ""
    rationale: Text = ""
    status: TestStatus = "proposed"
    result_notes: Text = ""
    executed_at: datetime | None = None
    executed_by: Title | None = None


class TestEdit(Strict):
    requirement_id: UUID | None = None
    category: Category | None = None
    title: Title | None = None
    description: Text | None = None
    rationale: Text | None = None
    status: TestStatus | None = None
    result_notes: Text | None = None
    executed_at: datetime | None = None
    executed_by: Title | None = None


class RiskCreate(Strict):
    requirement_id: UUID | None = None
    title: Title
    description: Text = ""
    category: RiskCategory = "technical"
    likelihood: int = Field(default=3, ge=1, le=5)
    impact: int = Field(default=3, ge=1, le=5)
    mitigation: Text = ""
    owner: Annotated[str, StringConstraints(max_length=200)] = ""
    status: RiskStatus = "open"
    rationale: Text = ""


class RiskEdit(Strict):
    requirement_id: UUID | None = None
    title: Title | None = None
    description: Text | None = None
    category: RiskCategory | None = None
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    mitigation: Text | None = None
    owner: Annotated[str, StringConstraints(max_length=200)] | None = None
    status: RiskStatus | None = None
    rationale: Text | None = None


class SLOCreate(Strict):
    requirement_id: UUID | None = None
    name: Title
    sli: Text
    target: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    window: Title = "28 days"
    alert: Text = ""
    rationale: Text = ""
    status: SLOStatus = "suggested"


class SLOEdit(Strict):
    requirement_id: UUID | None = None
    name: Title | None = None
    sli: Text | None = None
    target: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
        ]
        | None
    ) = None
    window: Title | None = None
    alert: Text | None = None
    rationale: Text | None = None
    status: SLOStatus | None = None


class ReadFields(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    source: Literal["generated", "user"]
    edited: bool
    created_at: datetime
    updated_at: datetime


class TestRead(TestCreate, ReadFields):
    executed: bool


class RiskRead(RiskCreate, ReadFields):
    score: int


class SLORead(SLOCreate, ReadFields):
    pass


class OperationsGenerate(Strict):
    kinds: list[Kind] | None = Field(default=None, min_length=1, max_length=3)
    replace_edited: bool = False


class OperationsRead(BaseModel):
    test_cases: list[TestRead]
    risks: list[RiskRead]
    slos: list[SLORead]

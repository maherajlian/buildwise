from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Kind = Literal[
    "prd",
    "technical_design",
    "architecture",
    "adr",
    "data_model",
    "api_contract",
    "user_stories",
    "acceptance_criteria",
    "non_functional_requirements",
    "security",
    "test_strategy",
    "deployment",
    "observability",
]
KINDS: list[Kind] = [
    "prd",
    "technical_design",
    "architecture",
    "adr",
    "data_model",
    "api_contract",
    "user_stories",
    "acceptance_criteria",
    "non_functional_requirements",
    "security",
    "test_strategy",
    "deployment",
    "observability",
]
Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Section(Strict):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_-]+$")
    heading: Title
    body: str = Field(max_length=10000000)


Sections = Annotated[list[Section], Field(min_length=1, max_length=40)]


class Generate(Strict):
    kinds: list[Kind] | None = Field(default=None, min_length=1, max_length=13)
    overwrite_edited: bool = False


class Edit(Strict):
    title: Title | None = None
    sections: Sections | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "Edit":
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Fields cannot be null")
        if self.sections and len({s.key for s in self.sections}) != len(self.sections):
            raise ValueError("Section keys must be unique")
        return self


class CreateADR(Strict):
    kind: Literal["adr"]
    title: Title


class Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    kind: Kind
    title: str
    sections: list[Section]
    edited: bool
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime

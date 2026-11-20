from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal[
    "frontend",
    "backend",
    "database",
    "cache_queue",
    "auth",
    "hosting",
    "ci_cd",
    "observability",
    "integrations",
    "ai_layer",
]
CATEGORIES: list[Category] = [
    "frontend",
    "backend",
    "database",
    "cache_queue",
    "auth",
    "hosting",
    "ci_cd",
    "observability",
    "integrations",
    "ai_layer",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Overrides(StrictModel):
    budget: Literal["zero", "low", "flexible"] | None = None
    scale: Literal["small", "medium", "large"] | None = None
    data_shape: Literal["relational", "document", "mixed"] | None = None
    background_jobs: Literal["yes", "no"] | None = None
    realtime: Literal["yes", "no"] | None = None
    auth_needs: Literal["none", "basic", "enterprise_sso"] | None = None
    ops_capability: Literal["low", "medium", "high"] | None = None
    integrations: (
        list[Literal["payments", "email", "sms", "calendar", "maps", "generic_api"]]
        | None
    ) = None
    ai_layer: Literal["not_needed", "required"] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, value: object) -> object:
        if isinstance(value, dict) and any(v is None for v in value.values()):
            raise ValueError("Omit a signal to use auto; null is not allowed")
        return value


class Evidence(StrictModel):
    field: str
    excerpt: str


class Signal(StrictModel):
    id: str
    label: str
    value: str | list[str]
    source: Literal["explicit", "detected", "default"]
    evidence: list[Evidence] = Field(default_factory=list)


class Rule(StrictModel):
    id: str
    description: str
    when: dict[str, str | list[str]]
    weight: int
    reason: str


class Entry(StrictModel):
    id: str
    name: str
    category: Category
    summary: str
    strengths: list[str]
    constraints: list[str]
    project_fit: list[str]
    operational_complexity: Literal["low", "medium", "high"]
    operational_burden: str
    cost_category: Literal[
        "free-tier",
        "self-hosted",
        "usage-based",
        "paid",
        "open-source-self-hosted-or-managed",
    ]
    cost_note: str
    trade_offs: list[str]
    assumptions: list[str]
    change_conditions: list[str]
    selection_rules: list[str]
    optional: bool
    last_reviewed: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    links: list[str] = Field(default_factory=list)


class Catalogue(StrictModel):
    catalogue_version: str
    rules_version: str
    entries: list[Entry]
    rules: list[Rule]
    categories: list[Category] = Field(default_factory=lambda: list(CATEGORIES))

    @model_validator(mode="after")
    def validate_content(self) -> "Catalogue":
        if self.categories != CATEGORIES:
            raise ValueError("Unexpected catalogue categories")
        rules = {r.id for r in self.rules}
        if len(rules) != len(self.rules):
            raise ValueError("Duplicate rule id")
        if len({e.id for e in self.entries}) != len(self.entries):
            raise ValueError("Duplicate entry id")
        for entry in self.entries:
            if not set(entry.selection_rules) <= rules:
                raise ValueError("Unknown rule reference")
            if entry.optional != (entry.category == "ai_layer"):
                raise ValueError("Only AI entries must be optional")
            if "pricing/free-tier claims require verification" not in entry.cost_note:
                raise ValueError("Missing pricing verification notice")
            date.fromisoformat(entry.last_reviewed)
        for rule in self.rules:
            for key, value in rule.when.items():
                values = value if isinstance(value, list) else [value]
                for item in values:
                    Overrides.model_validate(
                        {key: [item] if key == "integrations" else item}
                    )
        for category in CATEGORIES:
            if sum(e.category == category for e in self.entries) < 3:
                raise ValueError("Each category needs at least three entries")
        return self


class InputWrite(StrictModel):
    overrides: Overrides


class InputRead(StrictModel):
    overrides: dict[str, str | list[str]]
    signals: list[Signal]


class Match(StrictModel):
    rule_id: str
    weight: int
    reason: str
    signals: list[Signal]


class ScoredEntry(Entry):
    score: int
    matched_rules: list[Match]
    positive_matches: list[Match]
    negative_matches: list[Match]
    reason: str


class Recommendation(StrictModel):
    category: Category
    status: Literal["recommended", "not_recommended"]
    explanation: str
    recommendation: ScoredEntry | None
    alternatives: list[ScoredEntry]
    candidates: list[ScoredEntry]
    reason: str
    trade_offs: list[str]
    operational_complexity: str | None
    operational_burden: str
    cost_category: str | None
    assumptions: list[str]
    change_conditions: list[str]


class Result(StrictModel):
    project_id: str
    catalogue_version: str
    rules_version: str
    input_fingerprint: str
    signals: list[Signal]
    recommendations: list[Recommendation]
    notes: list[str]
    disclaimer: str

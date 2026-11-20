from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.operations import generator
from app.modules.operations.models import SLO, Risk, TestCase
from app.modules.operations.schemas import OperationsRead, RiskRead, SLORead, TestRead
from app.modules.projects.models import Project, Requirement
from app.modules.recommendations.schemas import Catalogue
from app.modules.specifications.generator import snapshot

MODELS: dict[str, type[TestCase] | type[Risk] | type[SLO]] = {
    "test_cases": TestCase,
    "risks": Risk,
    "slos": SLO,
}
Operation = TestCase | Risk | SLO


def read(session: Session, project_id: UUID) -> OperationsRead:
    return OperationsRead(
        test_cases=[
            TestRead.model_validate(item)
            for item in session.scalars(
                select(TestCase)
                .where(TestCase.project_id == project_id)
                .order_by(TestCase.created_at, TestCase.id)
            )
        ],
        risks=[
            RiskRead.model_validate(item)
            for item in session.scalars(
                select(Risk)
                .where(Risk.project_id == project_id)
                .order_by(Risk.created_at, Risk.id)
            )
        ],
        slos=[
            SLORead.model_validate(item)
            for item in session.scalars(
                select(SLO)
                .where(SLO.project_id == project_id)
                .order_by(SLO.created_at, SLO.id)
            )
        ],
    )


def generate(
    session: Session,
    project: Project,
    catalogue: Catalogue,
    kinds: Sequence[str] | None = None,
    replace_edited: bool = False,
) -> OperationsRead:
    context = snapshot(session, project, catalogue)
    data = generator.generate(context, context["signals"])
    for kind in dict.fromkeys(kinds or MODELS):
        model = MODELS[kind]
        statement = delete(model).where(
            model.project_id == project.id, model.source == "generated"
        )
        if not replace_edited:
            statement = statement.where(model.edited.is_(False))
        session.execute(statement)
        for values in data[kind]:
            session.add(
                model(
                    project_id=project.id,
                    source="generated",
                    created_at=datetime.now(UTC),
                    **values,
                )
            )
    session.flush()
    return read(session, project.id)


def save(
    session: Session,
    project_id: UUID,
    model: type[TestCase] | type[Risk] | type[SLO],
    values: dict[str, Any],
    item_id: UUID | None = None,
) -> Operation:
    requirement_id = values.get("requirement_id")
    if requirement_id:
        requirement = session.get(Requirement, requirement_id)
        if requirement is None or requirement.project_id != project_id:
            raise HTTPException(422, "Requirement must belong to this project")
    item: Operation
    if item_id:
        found = session.get(model, item_id)
        if (
            not isinstance(found, (TestCase, Risk, SLO))
            or found.project_id != project_id
        ):
            raise HTTPException(404, "Operation item not found")
        item = found
        item.edited = True
    else:
        item = model(project_id=project_id, source="user")
        session.add(item)
    for key, value in values.items():
        setattr(item, key, value)
    if isinstance(item, TestCase):
        status = values.get("status", item.status or "proposed")
        if status in ("proposed", "planned"):
            item.executed_at = None
            item.executed_by = None
            item.result_notes = ""
        elif status in ("passed", "failed"):
            if not (item.result_notes or "").strip():
                raise HTTPException(
                    422, "Passed or failed tests require non-empty result_notes"
                )
            now = datetime.now(UTC)
            supplied = item.executed_at
            if supplied is not None and (supplied.tzinfo is None or supplied > now):
                raise HTTPException(
                    422, "executed_at must be timezone-aware and not in the future"
                )
            if "status" in values and "executed_at" not in values:
                item.executed_at = now
            else:
                item.executed_at = supplied or now
        else:
            item.executed_at = None
            item.executed_by = None
            item.result_notes = ""
        item.status = status
    item.updated_at = datetime.now(UTC)
    session.flush()
    session.refresh(item)
    return item

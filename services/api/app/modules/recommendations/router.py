from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.projects.access import OptionalOwnerToken, OwnerToken, get_project
from app.modules.projects.models import Discovery, Requirement
from app.modules.recommendations.engine import recommend
from app.modules.recommendations.models import RecommendationInputs
from app.modules.recommendations.schemas import (
    Catalogue,
    InputRead,
    InputWrite,
    Overrides,
    Result,
    Signal,
)
from app.modules.recommendations.signals import derive_signals
from app.telemetry.operations import observed

router = APIRouter(tags=["recommendations"])
PREFIX = "/api/v1/projects/{project_id}"


def effective(
    session: Session, project_id: UUID
) -> tuple[Overrides, list[Signal], list[str]]:
    discovery = session.get(Discovery, project_id)
    stored = session.get(RecommendationInputs, project_id)
    overrides = Overrides.model_validate(stored.overrides if stored else {})
    requirements = session.scalars(
        select(Requirement)
        .where(Requirement.project_id == project_id)
        .order_by(Requirement.title, Requirement.id)
    ).all()
    signals, notes = derive_signals(
        discovery.answers if discovery else {},
        [
            {
                "title": r.title,
                "description": r.description,
                "acceptance_criteria": r.acceptance_criteria,
            }
            for r in requirements
        ],
        overrides,
    )
    return overrides, signals, notes


@router.get("/api/v1/catalogue", response_model=Catalogue)
def read_catalogue(request: Request) -> Catalogue:
    return request.app.state.catalogue  # type: ignore[no-any-return]


@router.get(PREFIX + "/recommendations", response_model=Result)
@observed("recommendations")
def read_recommendations(
    project_id: UUID,
    request: Request,
    x_project_token: OptionalOwnerToken = None,
) -> Result:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        _, signals, notes = effective(session, project_id)
        result = recommend(signals, request.app.state.catalogue)
        result.project_id = str(project_id)
        result.notes = notes
        return result


@router.get(PREFIX + "/recommendation-inputs", response_model=InputRead)
def read_inputs(
    project_id: UUID,
    request: Request,
    x_project_token: OptionalOwnerToken = None,
) -> InputRead:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        overrides, signals, _ = effective(session, project_id)
        return InputRead(
            overrides=overrides.model_dump(exclude_unset=True), signals=signals
        )


@router.put(PREFIX + "/recommendation-inputs", response_model=InputRead)
def save_inputs(
    project_id: UUID,
    body: InputWrite,
    request: Request,
    x_project_token: OwnerToken,
) -> InputRead:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        stored = session.get(RecommendationInputs, project_id) or RecommendationInputs(
            project_id=project_id
        )
        stored.overrides = body.overrides.model_dump(exclude_unset=True)
        stored.updated_at = func.now()
        project.updated_at = func.now()
        session.add(stored)
        session.commit()
        overrides, signals, _ = effective(session, project_id)
        return InputRead(
            overrides=overrides.model_dump(exclude_unset=True), signals=signals
        )

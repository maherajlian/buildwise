from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.planning import service
from app.modules.planning.models import Epic, PlanTask
from app.modules.planning.schemas import (
    EpicCreate,
    EpicEdit,
    EpicRead,
    Generate,
    PlanRead,
    TaskCreate,
    TaskEdit,
    TaskRead,
)
from app.modules.projects.access import OptionalOwnerToken, OwnerToken, get_project
from app.modules.projects.models import Project, Requirement
from app.telemetry.operations import observed

router = APIRouter(prefix="/api/v1/projects/{project_id}/plan", tags=["planning"])


def lock_project(session: Session, project_id: UUID, token: str) -> Project:
    return get_project(session, project_id, token, write=True)


def owned_task(session: Session, project_id: UUID, tid: UUID) -> PlanTask:
    item = session.get(PlanTask, tid)
    if item is None or item.project_id != project_id:
        raise HTTPException(404, "Task not found")
    return item


def owned_epic(session: Session, project_id: UUID, eid: UUID) -> Epic:
    item = session.get(Epic, eid)
    if item is None or item.project_id != project_id:
        raise HTTPException(404, "Epic not found")
    return item


def task_values(
    session: Session, project_id: UUID, values: dict[str, Any]
) -> dict[str, Any]:
    if values.get("epic_id"):
        owned_epic(session, project_id, values["epic_id"])
    if values.get("requirement_id"):
        req = session.get(Requirement, values["requirement_id"])
        if req is None or req.project_id != project_id:
            raise HTTPException(422, "Unknown or other-project requirement")
    if "depends_on" in values:
        values["depends_on"] = list(dict.fromkeys(str(d) for d in values["depends_on"]))
    return values


@router.get("", response_model=PlanRead)
def read(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> PlanRead:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        return service.read(session, project_id)


@router.get("/export/markdown", response_class=Response)
@observed("exports")
def export(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Response:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token)
        return Response(
            service.markdown(project, service.read(session, project_id)),
            media_type="text/markdown",
        )


@router.post("/generate", response_model=PlanRead)
@observed("tasks")
def generate(
    project_id: UUID, body: Generate, request: Request, x_project_token: OwnerToken
) -> PlanRead:
    with Session(request.app.state.engine) as session:
        project = lock_project(session, project_id, x_project_token)
        result = service.generate(
            session, project, request.app.state.catalogue, body.overwrite
        )
        project.updated_at = func.now()
        session.commit()
        return result


@router.post("/tasks", response_model=TaskRead, status_code=201)
def create_task(
    project_id: UUID, body: TaskCreate, request: Request, x_project_token: OwnerToken
) -> TaskRead:
    with Session(request.app.state.engine) as session:
        project = lock_project(session, project_id, x_project_token)
        item = PlanTask(
            project_id=project_id,
            key=service.next_key(session, project_id),
            **task_values(session, project_id, body.model_dump()),
        )
        session.add(item)
        session.flush()
        service.validate(session, project_id)
        project.updated_at = func.now()
        result = TaskRead.model_validate(item)
        session.commit()
        return result


@router.patch("/tasks/{tid}", response_model=TaskRead)
def edit_task(
    project_id: UUID,
    tid: UUID,
    body: TaskEdit,
    request: Request,
    x_project_token: OwnerToken,
) -> TaskRead:
    with Session(request.app.state.engine) as session:
        project = lock_project(session, project_id, x_project_token)
        item = owned_task(session, project_id, tid)
        for key, value in task_values(
            session, project_id, body.model_dump(exclude_unset=True)
        ).items():
            setattr(item, key, value)
        session.flush()
        service.validate(session, project_id)
        project.updated_at = func.now()
        result = TaskRead.model_validate(item)
        session.commit()
        return result


@router.delete("/tasks/{tid}", status_code=204)
def delete_task(
    project_id: UUID, tid: UUID, request: Request, x_project_token: OwnerToken
) -> Response:
    with Session(request.app.state.engine) as session:
        project = lock_project(session, project_id, x_project_token)
        item = owned_task(session, project_id, tid)
        for other in service.tasks_for(session, project_id):
            if str(tid) in other.depends_on:
                other.depends_on = [d for d in other.depends_on if d != str(tid)]
        session.delete(item)
        project.updated_at = func.now()
        session.commit()
        return Response(status_code=204)


@router.post("/epics", response_model=EpicRead, status_code=201)
def create_epic(
    project_id: UUID, body: EpicCreate, request: Request, x_project_token: OwnerToken
) -> EpicRead:
    with Session(request.app.state.engine) as session:
        project = lock_project(session, project_id, x_project_token)
        item = Epic(project_id=project_id, **body.model_dump())
        session.add(item)
        session.flush()
        project.updated_at = func.now()
        result = EpicRead.model_validate(item)
        session.commit()
        return result


@router.patch("/epics/{eid}", response_model=EpicRead)
def edit_epic(
    project_id: UUID,
    eid: UUID,
    body: EpicEdit,
    request: Request,
    x_project_token: OwnerToken,
) -> EpicRead:
    with Session(request.app.state.engine) as session:
        project = lock_project(session, project_id, x_project_token)
        item = owned_epic(session, project_id, eid)
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        session.flush()
        project.updated_at = func.now()
        result = EpicRead.model_validate(item)
        session.commit()
        return result


@router.delete("/epics/{eid}", status_code=204)
def delete_epic(
    project_id: UUID, eid: UUID, request: Request, x_project_token: OwnerToken
) -> Response:
    with Session(request.app.state.engine) as session:
        project = lock_project(session, project_id, x_project_token)
        session.delete(owned_epic(session, project_id, eid))
        project.updated_at = func.now()
        session.commit()
        return Response(status_code=204)

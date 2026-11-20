from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.projects.access import OptionalOwnerToken, OwnerToken, get_project
from app.modules.specifications import generator
from app.modules.specifications.models import Artefact
from app.modules.specifications.schemas import CreateADR, Edit, Generate, Read

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/artefacts", tags=["specifications"]
)


def owned(session: Session, project_id: UUID, aid: UUID) -> Artefact:
    item = session.get(Artefact, aid)
    if item is None or item.project_id != project_id:
        raise HTTPException(404, "Artefact not found")
    return item


@router.post("/generate", response_model=list[Read])
def generate(
    project_id: UUID, body: Generate, request: Request, x_project_token: OwnerToken
) -> list[Artefact]:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        items = generator.generate(
            session,
            project,
            request.app.state.catalogue,
            body.kinds,
            body.overwrite_edited,
        )
        project.updated_at = func.now()
        session.commit()
        for item in items:
            session.refresh(item)
        return items


@router.get("", response_model=list[Read])
def list_artefacts(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> list[Artefact]:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        return generator.ordered(session, project_id)


@router.get("/export/markdown", response_class=Response)
def export(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Response:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token)
        return Response(
            generator.export(project, generator.ordered(session, project_id)),
            media_type="text/markdown",
        )


@router.post("", response_model=Read, status_code=201)
def create(
    project_id: UUID, body: CreateADR, request: Request, x_project_token: OwnerToken
) -> Artefact:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        context = generator.snapshot(session, project, request.app.state.catalogue)
        item = Artefact(
            project_id=project_id,
            kind="adr",
            title=body.title,
            sections=generator.template("adr", context),
            context=context,
            edited=True,
        )
        session.add(item)
        project.updated_at = func.now()
        session.commit()
        return item


@router.get("/{aid}", response_model=Read)
def read(
    project_id: UUID,
    aid: UUID,
    request: Request,
    x_project_token: OptionalOwnerToken = None,
) -> Artefact:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        return owned(session, project_id, aid)


@router.get("/{aid}/markdown", response_class=Response)
def markdown(
    project_id: UUID,
    aid: UUID,
    request: Request,
    x_project_token: OptionalOwnerToken = None,
) -> Response:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, x_project_token)
        return Response(
            generator.markdown(owned(session, project_id, aid)),
            media_type="text/markdown",
        )


@router.patch("/{aid}", response_model=Read)
def edit(
    project_id: UUID,
    aid: UUID,
    body: Edit,
    request: Request,
    x_project_token: OwnerToken,
) -> Artefact:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        item = owned(session, project_id, aid)
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        item.edited = True
        item.updated_at = func.now()
        project.updated_at = func.now()
        session.commit()
        session.refresh(item)
        return item


@router.delete("/{aid}", status_code=204)
def delete(
    project_id: UUID, aid: UUID, request: Request, x_project_token: OwnerToken
) -> Response:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        session.delete(owned(session, project_id, aid))
        project.updated_at = func.now()
        session.commit()
        return Response(status_code=204)

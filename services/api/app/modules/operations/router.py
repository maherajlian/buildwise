from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.operations import generator, service
from app.modules.operations.models import SLO, Risk, TestCase
from app.modules.operations.schemas import (
    OperationsGenerate,
    OperationsRead,
    RiskCreate,
    RiskEdit,
    RiskRead,
    SLOCreate,
    SLOEdit,
    SLORead,
    TestCreate,
    TestEdit,
    TestRead,
)
from app.modules.projects.access import OptionalOwnerToken, OwnerToken, get_project
from app.modules.specifications.generator import markdown, ordered

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["operations"])


@router.post("/operations/generate", response_model=OperationsRead)
def generate(
    project_id: UUID,
    body: OperationsGenerate,
    request: Request,
    x_project_token: OwnerToken,
) -> OperationsRead:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token, write=True)
        result = service.generate(
            session,
            project,
            request.app.state.catalogue,
            body.kinds,
            body.replace_edited,
        )
        project.updated_at = func.now()
        session.commit()
        return result


@router.get("/test-cases", response_model=list[TestRead])
def tests(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> list[TestRead]:
    return load(project_id, request, x_project_token).test_cases


@router.get("/risks", response_model=list[RiskRead])
def risks(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> list[RiskRead]:
    return load(project_id, request, x_project_token).risks


@router.get("/slos", response_model=list[SLORead])
def slos(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> list[SLORead]:
    return load(project_id, request, x_project_token).slos


def load(project_id: UUID, request: Request, token: str | None) -> OperationsRead:
    with Session(request.app.state.engine) as session:
        get_project(session, project_id, token)
        return service.read(session, project_id)


@router.get("/operations/export/markdown", response_class=Response)
def export_all(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Response:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, x_project_token)
        text = f"# {project.name}\n\n" + generator.markdown(
            service.read(session, project_id)
        )
        for item in ordered(session, project_id):
            if item.kind in ("deployment", "observability"):
                text += "\n" + markdown(item)
        return Response(text, media_type="text/markdown")


@router.get("/test-cases/export/markdown", response_class=Response)
def export_tests(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Response:
    return Response(
        generator.markdown(load(project_id, request, x_project_token), ["test_cases"]),
        media_type="text/markdown",
    )


@router.get("/risks/export/markdown", response_class=Response)
def export_risks(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Response:
    return Response(
        generator.markdown(load(project_id, request, x_project_token), ["risks"]),
        media_type="text/markdown",
    )


@router.get("/slos/export/markdown", response_class=Response)
def export_slos(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Response:
    return Response(
        generator.markdown(load(project_id, request, x_project_token), ["slos"]),
        media_type="text/markdown",
    )


@router.get("/test-cases/export/csv", response_class=Response)
def export_csv(
    project_id: UUID, request: Request, x_project_token: OptionalOwnerToken = None
) -> Response:
    return Response(
        generator.test_csv(load(project_id, request, x_project_token)),
        media_type="text/csv",
    )


def write(
    project_id: UUID,
    request: Request,
    token: str,
    model: type[TestCase] | type[Risk] | type[SLO],
    body: TestCreate | TestEdit | RiskCreate | RiskEdit | SLOCreate | SLOEdit,
    item_id: UUID | None = None,
) -> service.Operation:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        project = get_project(session, project_id, token, write=True)
        item = service.save(
            session,
            project_id,
            model,
            body.model_dump(exclude_unset=item_id is not None),
            item_id,
        )
        project.updated_at = func.now()
        session.commit()
        return item


@router.post("/test-cases", response_model=TestRead, status_code=201)
def create_test(
    project_id: UUID, body: TestCreate, request: Request, x_project_token: OwnerToken
) -> service.Operation:
    return write(project_id, request, x_project_token, TestCase, body)


@router.patch("/test-cases/{item_id}", response_model=TestRead)
def edit_test(
    project_id: UUID,
    item_id: UUID,
    body: TestEdit,
    request: Request,
    x_project_token: OwnerToken,
) -> service.Operation:
    return write(project_id, request, x_project_token, TestCase, body, item_id)


@router.post("/risks", response_model=RiskRead, status_code=201)
def create_risk(
    project_id: UUID, body: RiskCreate, request: Request, x_project_token: OwnerToken
) -> service.Operation:
    return write(project_id, request, x_project_token, Risk, body)


@router.patch("/risks/{item_id}", response_model=RiskRead)
def edit_risk(
    project_id: UUID,
    item_id: UUID,
    body: RiskEdit,
    request: Request,
    x_project_token: OwnerToken,
) -> service.Operation:
    return write(project_id, request, x_project_token, Risk, body, item_id)


@router.post("/slos", response_model=SLORead, status_code=201)
def create_slo(
    project_id: UUID, body: SLOCreate, request: Request, x_project_token: OwnerToken
) -> service.Operation:
    return write(project_id, request, x_project_token, SLO, body)


@router.patch("/slos/{item_id}", response_model=SLORead)
def edit_slo(
    project_id: UUID,
    item_id: UUID,
    body: SLOEdit,
    request: Request,
    x_project_token: OwnerToken,
) -> service.Operation:
    return write(project_id, request, x_project_token, SLO, body, item_id)


def remove(
    project_id: UUID,
    item_id: UUID,
    request: Request,
    token: str,
    model: type[TestCase] | type[Risk] | type[SLO],
) -> Response:
    with Session(request.app.state.engine) as session:
        project = get_project(session, project_id, token, write=True)
        item = session.get(model, item_id)
        if not isinstance(item, (TestCase, Risk, SLO)) or item.project_id != project_id:
            raise HTTPException(404, "Operation item not found")
        session.delete(item)
        project.updated_at = func.now()
        session.commit()
        return Response(status_code=204)


@router.delete("/test-cases/{item_id}", status_code=204)
def delete_test(
    project_id: UUID, item_id: UUID, request: Request, x_project_token: OwnerToken
) -> Response:
    return remove(project_id, item_id, request, x_project_token, TestCase)


@router.delete("/risks/{item_id}", status_code=204)
def delete_risk(
    project_id: UUID, item_id: UUID, request: Request, x_project_token: OwnerToken
) -> Response:
    return remove(project_id, item_id, request, x_project_token, Risk)


@router.delete("/slos/{item_id}", status_code=204)
def delete_slo(
    project_id: UUID, item_id: UUID, request: Request, x_project_token: OwnerToken
) -> Response:
    return remove(project_id, item_id, request, x_project_token, SLO)

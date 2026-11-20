import secrets
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.main import create_app
from app.modules.planning.schemas import TaskCreate
from app.modules.projects.access import SAMPLE_PROJECT_ID
from app.modules.projects.sample import seed_sample
from app.modules.specifications.schemas import KINDS


def token() -> dict[str, str]:
    return {"X-Project-Token": secrets.token_urlsafe(32)}


@pytest.fixture
def client(migrated_url: str) -> Iterator[TestClient]:
    with TestClient(
        create_app(Settings(database_url=migrated_url, otel_exporter_otlp_endpoint=""))
    ) as value:
        yield value


def project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Orbit", "description": "Coordinate launches"},
    )
    assert response.status_code == 201, response.text
    return f"/api/v1/projects/{response.json()['id']}"


@pytest.mark.parametrize(
    "kind,key", [("deployment", "release"), ("observability", "response")]
)
def test_edited_operations_plans_keep_legacy_keys_until_explicit_overwrite(
    client: TestClient, kind: str, key: str
) -> None:
    owner = token()
    base = project(client, owner) + "/artefacts"
    response = client.post(base + "/generate", headers=owner, json={"kinds": [kind]})
    assert response.status_code == 200, response.text
    item = response.json()[0]
    legacy = [
        {"key": key, "heading": "Reviewed plan", "body": "Keep the approved runbook"}
    ]
    assert (
        client.patch(
            base + "/" + item["id"], headers=owner, json={"sections": legacy}
        ).status_code
        == 200
    )
    preserved = client.post(
        base + "/generate", headers=owner, json={"kinds": [kind]}
    ).json()[0]
    assert preserved["sections"] == legacy and preserved["edited"]
    replaced = client.post(
        base + "/generate",
        headers=owner,
        json={"kinds": [kind], "overwrite_edited": True},
    ).json()[0]
    assert not replaced["edited"] and len(replaced["sections"]) > 3
    assert key in {section["key"] for section in replaced["sections"]}


def test_project_pack_and_recent_dashboard_are_owner_scoped(
    client: TestClient, migrated_url: str
) -> None:
    owner = token()
    stranger = token()
    base = project(client, owner)
    url = base + "/export/markdown"
    for headers in ({}, stranger):
        response = client.get(url, headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["correlation_id"]
    empty = client.get(url, headers=owner)
    assert empty.status_code == 200
    assert empty.headers["content-type"].startswith("text/markdown")
    assert empty.headers["cache-control"] == "private, no-store"
    assert "TODO: generate artefacts" in empty.text
    assert "TODO: generate a build plan" in empty.text

    assert client.get("/api/v1/dashboard", headers=stranger).json() == []
    items = client.get("/api/v1/dashboard", headers=owner).json()
    assert items[0]["name"] == "Orbit"
    assert items[0]["stage"] == "Discovery"

    with Session(create_engine(migrated_url)) as session:
        seed_sample(session)
    sample = client.get(f"/api/v1/projects/{SAMPLE_PROJECT_ID}/export/markdown")
    assert sample.status_code == 200
    for section in (
        "## Project brief",
        "## Technology recommendations",
        "### Product requirements document",
        "### Technical design document",
        "#### Architecture overview",
        "#### API outline",
        "### User stories",
        "Given an available slot",
        "#### Security",
        "Build plan",
        "## Validate and operate",
    ):
        assert section in sample.text


def test_specifications_generation_edit_adr_export(client: TestClient) -> None:
    owner = token()
    base = project(client, owner)
    url = base + "/artefacts"
    assert client.get(url, headers=owner).json() == []
    assert "TODO" in client.get(url + "/export/markdown", headers=owner).text
    assert (
        client.put(
            base + "/discovery",
            headers=owner,
            json={
                "answers": {
                    "problem_statement": "Launches collide",
                    "target_users": ["Operators"],
                    "goals": ["Reliable launches"],
                }
            },
        ).status_code
        == 200
    )
    for kind, title, check in [
        ("functional", "Schedule launch", "Reject collisions"),
        ("non_functional", "Fast scheduler", "p95 under 200ms"),
    ]:
        assert (
            client.post(
                base + "/requirements",
                headers=owner,
                json={"type": kind, "title": title, "acceptance_criteria": [check]},
            ).status_code
            == 201
        )
    assert (
        client.put(
            base + "/recommendation-inputs",
            headers=owner,
            json={"overrides": {"data_shape": "relational"}},
        ).status_code
        == 200
    )
    generated = client.post(url + "/generate", headers=owner, json={})
    assert generated.status_code == 200, generated.text
    items = generated.json()
    assert [a["kind"] for a in items] == KINDS
    assert items[0]["context"]["name"] == "Orbit"
    assert items[0]["context"]["requirements"][0]["title"]
    assert items[0]["context"]["technologies"]["database"]
    assert items[0]["context"]["signals"]["data_shape"] == "relational"
    assert items[0]["context"]["technology_details"]["hosting"]["constraints"]
    operations = client.post(base + "/operations/generate", headers=owner, json={})
    assert operations.status_code == 200, operations.text
    observability = next(a for a in items if a["kind"] == "observability")
    objectives = next(
        s["body"] for s in observability["sections"] if s["key"] == "slo_candidates"
    )
    for slo in operations.json()["slos"]:
        assert slo["target"] in objectives and slo["rationale"] in objectives
    second = client.post(url + "/generate", headers=owner, json={}).json()
    assert [(a["id"], a["sections"], a["context"]) for a in items] == [
        (a["id"], a["sections"], a["context"]) for a in second
    ]
    aid = items[0]["id"]
    before = client.get(base, headers=owner).json()["updated_at"]
    custom = [
        {"key": "custom", "heading": "Human decision", "body": "Keep this decision"}
    ]
    edited = client.patch(
        url + "/" + aid,
        headers=owner,
        json={"title": "Reviewed PRD", "sections": custom},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["edited"] is True
    assert client.get(base, headers=owner).json()["updated_at"] > before
    assert client.post(url + "/generate", headers=owner, json={}).status_code == 200
    persisted = client.get(url + "/" + aid, headers=owner).json()
    assert persisted["sections"] == custom
    assert persisted["title"] == "Reviewed PRD"
    adr = client.post(
        url, headers=owner, json={"kind": "adr", "title": "Choose storage"}
    )
    assert adr.status_code == 201, adr.text
    assert [s["heading"] for s in adr.json()["sections"]] == [
        "Status",
        "Context",
        "Decision",
        "Consequences",
        "Alternatives",
    ]
    single = client.get(url + "/" + aid + "/markdown", headers=owner)
    assert single.headers["content-type"].startswith("text/markdown")
    assert "Keep this decision" in single.text
    exported = client.get(url + "/export/markdown", headers=owner)
    assert exported.status_code == 200
    for value in [
        "Table of contents",
        "Orbit",
        "Launches collide",
        "Operators",
        "Schedule launch",
        "Reject collisions",
        "p95 under 200ms",
        "Choose storage",
        "Keep this decision",
    ]:
        assert value in exported.text
    overwritten = client.post(
        url + "/generate",
        headers=owner,
        json={"kinds": ["prd"], "overwrite_edited": True},
    ).json()
    assert overwritten[0]["edited"] is False
    assert overwritten[0]["title"] != "Reviewed PRD"
    assert client.delete(url + "/" + adr.json()["id"], headers=owner).status_code == 204
    assert client.get(url + "/" + adr.json()["id"], headers=owner).status_code == 404
    assert (
        client.patch(url + "/" + aid, headers=owner, json={"sections": []}).status_code
        == 422
    )


def normalized(plan: dict[str, Any]) -> dict[str, Any]:
    epics = {e["id"]: e["title"] for e in plan["epics"]}
    tasks = {t["id"]: t["key"] for t in plan["tasks"]}
    return {
        "epics": [{k: v for k, v in e.items() if k != "id"} for e in plan["epics"]],
        "tasks": [
            {
                **{
                    k: v
                    for k, v in t.items()
                    if k not in {"id", "epic_id", "depends_on"}
                },
                "epic": epics.get(t["epic_id"]),
                "deps": [tasks[d] for d in t["depends_on"]],
            }
            for t in plan["tasks"]
        ],
    }


def test_plan_generation_context_deterministic_and_export(client: TestClient) -> None:
    owner = token()
    base = project(client, owner)
    url = base + "/plan"
    assert client.get(url, headers=owner).json() == {
        "epics": [],
        "tasks": [],
        "validation": {"valid": True, "errors": []},
    }
    assert "TODO" in client.get(url + "/export/markdown", headers=owner).text
    for title in ["Schedule launch", "Cancel launch"]:
        assert (
            client.post(
                base + "/requirements",
                headers=owner,
                json={
                    "type": "functional",
                    "title": title,
                    "acceptance_criteria": [f"{title} succeeds"],
                },
            ).status_code
            == 201
        )
    assert (
        client.post(base + "/artefacts/generate", headers=owner, json={}).status_code
        == 200
    )
    docs = client.get(base + "/artefacts", headers=owner).json()
    architecture = next(a for a in docs if a["kind"] == "architecture")
    assert (
        client.patch(
            base + "/artefacts/" + architecture["id"],
            headers=owner,
            json={
                "title": "Reviewed launch architecture",
                "sections": [
                    {
                        "key": "decision",
                        "heading": "Decision",
                        "body": "Implement the reviewed launch workflow",
                    }
                ],
            },
        ).status_code
        == 200
    )
    response = client.post(url + "/generate", headers=owner, json={})
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["validation"]["valid"] is True
    assert len(plan["epics"]) == 5
    assert len(plan["tasks"]) == 5
    assert all(
        t["acceptance_criteria"] and t["skill"] and t["workflow"] for t in plan["tasks"]
    )
    assert "Reviewed launch architecture" in plan["tasks"][0]["implementation_notes"]
    assert "Backend:" in plan["tasks"][0]["implementation_notes"]
    for task in plan["tasks"]:
        assert 0 < len(task["description"]) < 200
        assert "\n" not in task["description"]
        assert (
            "Implement the reviewed launch workflow" not in task["implementation_notes"]
        )
        assert all(
            line.startswith("- ") for line in task["implementation_notes"].splitlines()
        )
        assert "Stack:" not in task["implementation_notes"]
    deployment = plan["tasks"][-1]
    assert (
        "See: Deployment plan, Observability plan" in deployment["implementation_notes"]
    )
    assert "Hosting:" in deployment["implementation_notes"]
    assert "Product requirements document" not in deployment["implementation_notes"]
    assert client.post(url + "/generate", headers=owner, json={}).json() == plan
    overwritten = client.post(
        url + "/generate", headers=owner, json={"overwrite": True}
    )
    assert overwritten.status_code == 200, overwritten.text
    assert normalized(overwritten.json()) == normalized(plan)
    exported = client.get(url + "/export/markdown", headers=owner)
    assert exported.headers["content-type"].startswith("text/markdown")
    for task in plan["tasks"]:
        for value in [
            task["title"],
            task["key"],
            task["implementation_notes"],
            task["workflow"],
            *task["acceptance_criteria"],
        ]:
            assert value in exported.text


@pytest.mark.parametrize("count", [1, 21])
def test_generated_quality_task_can_be_edited_with_long_criteria(
    client: TestClient, count: int
) -> None:
    owner = token()
    base = project(client, owner)
    for index in range(count):
        response = client.post(
            base + "/requirements",
            headers=owner,
            json={
                "type": "non_functional",
                "title": f"Budget {index:02}",
                "acceptance_criteria": ["x" * 1000],
            },
        )
        assert response.status_code == 201, response.text
    generated = client.post(base + "/plan/generate", headers=owner, json={})
    assert generated.status_code == 200, generated.text
    tasks = generated.json()["tasks"]
    for task in tasks:
        TaskCreate.model_validate(
            {
                key: value
                for key, value in task.items()
                if key in TaskCreate.model_fields
            }
        )
    quality = next(t for t in tasks if t["title"] == "Verify quality and security")
    criteria = quality["acceptance_criteria"]
    assert len(criteria) == min(count, 20)
    assert len(criteria[0]) == 1000
    if count > 20:
        assert criteria[-1] == "…and 2 more, see Acceptance criteria artefact"
    payload = {
        key: quality[key]
        for key in [
            "priority",
            "depends_on",
            "implementation_notes",
            "acceptance_criteria",
        ]
    }
    payload["title"] = "Reviewed quality checks"
    updated = client.patch(
        base + "/plan/tasks/" + quality["id"], headers=owner, json=payload
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["acceptance_criteria"] == criteria


def test_plan_crud_dependency_validation(client: TestClient) -> None:
    owner = token()
    url = project(client, owner) + "/plan"
    epic = client.post(url + "/epics", headers=owner, json={"title": "Foundation"})
    assert epic.status_code == 201, epic.text
    eid = epic.json()["id"]
    assert (
        client.patch(
            url + "/epics/" + eid, headers=owner, json={"title": "Core", "position": 2}
        ).json()["title"]
        == "Core"
    )
    first = client.post(
        url + "/tasks", headers=owner, json={"title": "First", "epic_id": eid}
    ).json()
    second = client.post(
        url + "/tasks",
        headers=owner,
        json={"title": "Second", "epic_id": eid, "depends_on": [first["id"]]},
    ).json()
    assert first["key"] == "T-001" and second["key"] == "T-002"
    first_url, second_url = [url + "/tasks/" + t["id"] for t in [first, second]]
    for body, message in [
        ({"depends_on": [first["id"]]}, "self-dependency"),
        ({"depends_on": [second["id"]]}, "cycle"),
        ({"depends_on": [str(uuid4())]}, "unknown"),
    ]:
        invalid = client.patch(first_url, headers=owner, json=body)
        assert invalid.status_code == 422, invalid.text
        assert message in invalid.text
    for status in ["in_progress", "review", "done"]:
        invalid = client.patch(second_url, headers=owner, json={"status": status})
        assert invalid.status_code == 422
        assert "must be done" in invalid.text
    assert (
        client.patch(first_url, headers=owner, json={"status": "done"}).status_code
        == 200
    )
    for status in ["in_progress", "review", "done"]:
        assert (
            client.patch(second_url, headers=owner, json={"status": status}).status_code
            == 200
        )
    assert (
        client.patch(first_url, headers=owner, json={"status": "backlog"}).status_code
        == 422
    )
    assert client.delete(first_url, headers=owner).status_code == 204
    assert client.get(url, headers=owner).json()["tasks"][0]["depends_on"] == []
    assert client.delete(url + "/epics/" + eid, headers=owner).status_code == 204
    assert client.get(url, headers=owner).json()["tasks"][0]["epic_id"] is None
    assert client.delete(second_url, headers=owner).status_code == 204
    assert client.get(url, headers=owner).json()["tasks"] == []


def test_phase4_auth_and_foreign_references(client: TestClient) -> None:
    owner, other = token(), token()
    base, foreign = project(client, owner), project(client, other)
    foreign_task = client.post(
        foreign + "/plan/tasks", headers=other, json={"title": "Foreign"}
    ).json()
    for path in [
        "/artefacts",
        "/plan",
        "/artefacts/export/markdown",
        "/plan/export/markdown",
    ]:
        assert client.get(base + path, headers=other).status_code == 404
        assert client.get(base + path).status_code == 404
    for path in ["/artefacts/generate", "/plan/generate"]:
        assert client.post(base + path, headers=other, json={}).status_code == 404
    invalid = client.post(
        base + "/plan/tasks",
        headers=owner,
        json={"title": "x", "depends_on": [foreign_task["id"]]},
    )
    assert invalid.status_code == 422 and "other-project" in invalid.text
    assert (
        client.patch(
            base + "/plan/tasks/" + foreign_task["id"],
            headers=owner,
            json={"title": "x"},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            base + "/plan/tasks/" + foreign_task["id"], headers=owner
        ).status_code
        == 404
    )
    adr = client.post(
        foreign + "/artefacts",
        headers=other,
        json={"kind": "adr", "title": "Foreign ADR"},
    ).json()
    assert (
        client.get(base + "/artefacts/" + adr["id"], headers=owner).status_code == 404
    )
    assert (
        client.patch(
            base + "/artefacts/" + adr["id"], headers=owner, json={"title": "x"}
        ).status_code
        == 404
    )
    assert (
        client.delete(base + "/artefacts/" + adr["id"], headers=owner).status_code
        == 404
    )


def test_phase4_empty_sample_and_cascade(client: TestClient, migrated_url: str) -> None:
    owner = token()
    base = project(client, owner)
    assert (
        len(client.post(base + "/artefacts/generate", headers=owner, json={}).json())
        == 13
    )
    plan = client.post(base + "/plan/generate", headers=owner, json={}).json()
    assert plan["validation"]["valid"] is True
    assert "TODO" in str(plan)
    engine = create_engine(migrated_url)
    with Session(engine) as session:
        seed_sample(session)
        seed_sample(session)
    sample = f"/api/v1/projects/{SAMPLE_PROJECT_ID}"
    artefacts = client.get(sample + "/artefacts").json()
    assert len(artefacts) == 13
    assert len(client.get(sample + "/plan").json()["tasks"]) > 3
    for path in ["/artefacts/export/markdown", "/plan/export/markdown"]:
        assert client.get(sample + path).status_code == 200
    for method, path, body in [
        ("post", "/artefacts/generate", {}),
        ("post", "/plan/generate", {}),
        ("post", "/artefacts", {"kind": "adr", "title": "x"}),
        ("patch", "/artefacts/" + artefacts[0]["id"], {"title": "x"}),
        ("delete", "/artefacts/" + artefacts[0]["id"], None),
        ("post", "/plan/tasks", {"title": "x"}),
        ("post", "/plan/epics", {"title": "x"}),
    ]:
        response = getattr(client, method)(
            sample + path, headers=owner, **({"json": body} if body is not None else {})
        )
        assert response.status_code == 403, response.text
    assert client.delete(base, headers=owner).status_code == 204
    with engine.connect() as connection:
        for table in ["artefacts", "epics", "plan_tasks"]:
            assert (
                connection.scalar(
                    text(f"SELECT count(*) FROM {table} WHERE project_id = :pid"),
                    {"pid": base.rsplit("/", 1)[1]},
                )
                == 0
            )
    engine.dispose()

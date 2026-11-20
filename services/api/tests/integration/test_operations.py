import csv
import io
import secrets
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.main import create_app
from app.modules.operations.models import Risk
from app.modules.projects.access import SAMPLE_PROJECT_ID
from app.modules.projects.sample import seed_sample


@pytest.fixture
def client(migrated_url: str) -> Iterator[TestClient]:
    with TestClient(
        create_app(Settings(database_url=migrated_url, otel_exporter_otlp_endpoint=""))
    ) as value:
        yield value


def token() -> dict[str, str]:
    return {"X-Project-Token": secrets.token_urlsafe(32)}


def project(client: TestClient, owner: dict[str, str]) -> str:
    response = client.post("/api/v1/projects", headers=owner, json={"name": "Orbit"})
    assert response.status_code == 201, response.text
    return f"/api/v1/projects/{response.json()['id']}"


def test_generation_preserves_edits_user_rows_and_exports(client: TestClient) -> None:
    owner = token()
    base = project(client, owner)
    assert client.get(base + "/test-cases", headers=owner).json() == []
    assert (
        "Executed: 0"
        in client.get(base + "/operations/export/markdown", headers=owner).text
    )
    requirement = client.post(
        base + "/requirements",
        headers=owner,
        json={
            "type": "functional",
            "title": "Book launch",
            "priority": "P0",
            "acceptance_criteria": ["Collision rejected"],
        },
    ).json()
    response = client.post(base + "/operations/generate", headers=owner, json={})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["test_cases"] and data["risks"] and data["slos"]
    assert all(
        c["status"] == "proposed" and not c["executed"] for c in data["test_cases"]
    )
    linked = next(
        c for c in data["test_cases"] if c["requirement_id"] == requirement["id"]
    )
    edited = client.patch(
        base + "/test-cases/" + linked["id"],
        headers=owner,
        json={"title": "Reviewed case"},
    )
    assert edited.status_code == 200 and edited.json()["edited"]
    user = client.post(
        base + "/risks",
        headers=owner,
        json={"title": "Human risk", "likelihood": 4, "impact": 5},
    )
    assert user.status_code == 201 and user.json()["score"] == 20
    assert user.json()["source"] == "user"
    regenerated = client.post(
        base + "/operations/generate", headers=owner, json={}
    ).json()
    assert any(
        c["id"] == linked["id"] and c["title"] == "Reviewed case"
        for c in regenerated["test_cases"]
    )
    assert any(r["id"] == user.json()["id"] for r in regenerated["risks"])
    old_unedited = {c["id"] for c in data["test_cases"] if c["id"] != linked["id"]}
    assert not old_unedited.intersection(c["id"] for c in regenerated["test_cases"])
    replaced = client.post(
        base + "/operations/generate",
        headers=owner,
        json={"kinds": ["test_cases"], "replace_edited": True},
    ).json()
    assert not any(c["id"] == linked["id"] for c in replaced["test_cases"])
    assert [r["id"] for r in replaced["risks"]] == [
        r["id"] for r in regenerated["risks"]
    ]
    client.post(
        base + "/artefacts/generate",
        headers=owner,
        json={"kinds": ["deployment", "observability"]},
    )
    exported = client.get(base + "/operations/export/markdown", headers=owner)
    assert exported.status_code == 200
    for value in [
        "Generated deterministically from requirements",
        "Book launch",
        "Collision rejected",
        "Proposed (not yet run)",
        "Executed: 0",
        "Risk register",
        "SLO suggestions",
        "Deployment plan",
        "Observability plan",
    ]:
        assert value in exported.text
    for path, heading in [
        ("test-cases", "Test plan"),
        ("risks", "Risk register"),
        ("slos", "SLO suggestions"),
    ]:
        result = client.get(base + f"/{path}/export/markdown", headers=owner)
        assert result.status_code == 200 and heading in result.text
    rows = list(
        csv.DictReader(
            io.StringIO(client.get(base + "/test-cases/export/csv", headers=owner).text)
        )
    )
    assert rows and all(row["status"] == "proposed" for row in rows)
    assert (
        client.delete(
            base + "/requirements/" + requirement["id"], headers=owner
        ).status_code
        == 204
    )
    assert all(
        c["requirement_id"] is None
        for c in client.get(base + "/test-cases", headers=owner).json()
    )


def test_regeneration_does_not_duplicate_preserved_cases_risks_or_slos(
    client: TestClient,
) -> None:
    owner = token()
    base = project(client, owner)
    requirement = client.post(
        base + "/requirements",
        headers=owner,
        json={
            "title": "Book a launch",
            "type": "functional",
            "acceptance_criteria": ["Conflict rejected", "Confirmation sent"],
        },
    ).json()
    generated = client.post(
        base + "/operations/generate", headers=owner, json={}
    ).json()
    edited = {}
    for kind, path, change in [
        (
            "test_cases",
            "test-cases",
            {
                "title": "Reviewed test",
                "category": "security",
                "status": "passed",
                "result_notes": "Run recorded",
            },
        ),
        (
            "risks",
            "risks",
            {"title": "Reviewed risk", "mitigation": "Reviewed controls"},
        ),
        (
            "slos",
            "slos",
            {"name": "Reviewed SLO", "target": "99%", "status": "adopted"},
        ),
    ]:
        row = generated[kind][0]
        result = client.patch(base + f"/{path}/{row['id']}", headers=owner, json=change)
        assert result.status_code == 200, result.text
        edited[kind] = result.json()
    assert (
        client.patch(
            base + "/requirements/" + requirement["id"],
            headers=owner,
            json={"title": "Renamed launch"},
        ).status_code
        == 200
    )
    for _ in range(2):
        response = client.post(base + "/operations/generate", headers=owner, json={})
        assert response.status_code == 200, response.text
        for kind, rows in response.json().items():
            assert len(rows) == len(generated[kind])
            assert (
                next(r for r in rows if r["id"] == edited[kind]["id"]) == edited[kind]
            )
    replaced = client.post(
        base + "/operations/generate", headers=owner, json={"replace_edited": True}
    )
    assert replaced.status_code == 200, replaced.text
    for kind, rows in replaced.json().items():
        assert len(rows) == len(generated[kind])
        assert all(r["id"] != edited[kind]["id"] and not r["edited"] for r in rows)
    assert not any(r["executed"] for r in replaced.json()["test_cases"])


@pytest.mark.parametrize("status", ["passed", "failed"])
def test_execution_requires_evidence_and_clear_on_replan(
    client: TestClient, status: str
) -> None:
    owner = token()
    base = project(client, owner)
    url = base + "/test-cases"
    payload = {"title": "Manual test", "category": "unit", "status": status}
    assert client.post(url, headers=owner, json=payload).status_code == 422
    created = client.post(
        url, headers=owner, json={"title": "Manual test", "category": "unit"}
    ).json()
    item = url + "/" + created["id"]
    assert (
        client.patch(
            item, headers=owner, json={"status": status, "result_notes": "  "}
        ).status_code
        == 422
    )
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert (
        client.patch(
            item,
            headers=owner,
            json={
                "status": status,
                "result_notes": "Run recorded",
                "executed_at": future,
            },
        ).status_code
        == 422
    )
    past = "2025-01-01T12:00:00Z"
    result = client.patch(
        item,
        headers=owner,
        json={
            "status": status,
            "result_notes": "Run recorded",
            "executed_at": past,
            "executed_by": "Reviewer",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["executed"] and result.json()["executed_at"] == past
    assert (
        client.patch(item, headers=owner, json={"result_notes": ""}).status_code == 422
    )
    text = client.get(url + "/export/markdown", headers=owner).text
    assert (
        "Executed: 1" in text and f"Status: {status}" in text and "Run recorded" in text
    )
    for next_status in ("planned", "proposed"):
        reset = client.patch(item, headers=owner, json={"status": next_status}).json()
        assert (
            not reset["executed"]
            and reset["executed_at"] is None
            and reset["executed_by"] is None
            and reset["result_notes"] == ""
        )
        stamped = client.patch(
            item, headers=owner, json={"status": status, "result_notes": "Ran locally"}
        ).json()
        assert stamped["executed"] and stamped["executed_at"]


@pytest.mark.parametrize(
    "path,payload,change",
    [
        (
            "test-cases",
            {"title": "Check", "category": "manual_acceptance"},
            {"status": "planned"},
        ),
        ("risks", {"title": "Risk"}, {"likelihood": 5, "status": "mitigating"}),
        (
            "slos",
            {"name": "Latency", "sli": "p95", "target": "< 100ms"},
            {"status": "adopted"},
        ),
    ],
)
def test_crud_isolation_validation_and_cascade(
    client: TestClient,
    migrated_url: str,
    path: str,
    payload: dict[str, str],
    change: dict[str, str | int],
) -> None:
    owner = token()
    base = project(client, owner)
    url = base + "/" + path
    assert client.get(url).status_code == 404
    assert client.post(url, json=payload).status_code == 422
    assert client.post(url, headers=token(), json=payload).status_code == 404
    assert (
        client.post(
            url, headers=owner, json={**payload, "source": "generated"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, headers=owner, json={**payload, "requirement_id": str(uuid4())}
        ).status_code
        == 422
    )
    item = client.post(url, headers=owner, json=payload)
    assert item.status_code == 201, item.text
    item_url = url + "/" + item.json()["id"]
    assert client.patch(item_url, headers=token(), json=change).status_code == 404
    assert client.delete(item_url, headers=token()).status_code == 404
    other = project(client, owner)
    foreign_requirement = client.post(
        other + "/requirements",
        headers=owner,
        json={"title": "Other project", "type": "functional"},
    ).json()
    assert (
        client.patch(
            item_url,
            headers=owner,
            json={"requirement_id": foreign_requirement["id"]},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            other + "/" + path + "/" + item.json()["id"], headers=owner, json=change
        ).status_code
        == 404
    )
    assert (
        client.patch(item_url, headers=owner, json={"status": None}).status_code == 422
    )
    patched = client.patch(item_url, headers=owner, json=change)
    assert patched.status_code == 200 and patched.json()["edited"]
    assert all(patched.json()[key] == value for key, value in change.items())
    assert client.delete(item_url, headers=owner).status_code == 204
    assert client.delete(item_url, headers=owner).status_code == 404
    assert client.get(url, headers=owner).json() == []
    if path == "risks":
        assert (
            client.post(
                url, headers=owner, json={**payload, "likelihood": 6}
            ).status_code
            == 422
        )
        created = client.post(url, headers=owner, json=payload).json()
        assert client.delete(base, headers=owner).status_code == 204
        engine = create_engine(migrated_url)
        with Session(engine) as session:
            assert session.scalar(select(Risk).where(Risk.id == created["id"])) is None
        engine.dispose()


def test_sample_seed_and_read_only(client: TestClient, migrated_url: str) -> None:
    engine = create_engine(migrated_url)
    with Session(engine) as session:
        seed_sample(session)
        seed_sample(session)
    engine.dispose()
    base = f"/api/v1/projects/{SAMPLE_PROJECT_ID}"
    owner = token()
    for path, payload in [
        ("test-cases", {"title": "Check", "category": "unit"}),
        ("risks", {"title": "Risk"}),
        ("slos", {"name": "SLO", "sli": "Requests", "target": "99%"}),
    ]:
        rows = client.get(base + "/" + path).json()
        assert rows
        assert (
            client.post(base + "/" + path, headers=owner, json=payload).status_code
            == 403
        )
        assert (
            client.patch(
                base + "/" + path + "/" + rows[0]["id"], headers=owner, json={}
            ).status_code
            == 403
        )
        assert (
            client.delete(
                base + "/" + path + "/" + rows[0]["id"], headers=owner
            ).status_code
            == 403
        )
    assert (
        client.post(base + "/operations/generate", headers=owner, json={}).status_code
        == 403
    )
    assert client.get(base + "/operations/export/markdown").status_code == 200

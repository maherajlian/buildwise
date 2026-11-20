import secrets
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.main import create_app
from app.modules.projects.access import SAMPLE_PROJECT_ID
from app.modules.projects.models import Project
from app.modules.projects.sample import REQUIREMENTS, seed_sample


def token() -> dict[str, str]:
    return {"X-Project-Token": secrets.token_urlsafe(32)}


@pytest.fixture
def client(migrated_url: str) -> Iterator[TestClient]:
    with TestClient(
        create_app(Settings(database_url=migrated_url, otel_exporter_otlp_endpoint=""))
    ) as value:
        yield value


def make_project(client: TestClient, headers: dict[str, str], name: str = "P") -> str:
    response = client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_project_get_update_delete(client: TestClient) -> None:
    owner, other = token(), token()
    project_id = make_project(client, owner, "Original")
    url = f"/api/v1/projects/{project_id}"
    assert client.get(url, headers=owner).json()["is_sample"] is False
    assert client.get(url, headers=other).status_code == 404
    assert client.get(url).status_code == 404

    before = client.get(url, headers=owner).json()["updated_at"]
    response = client.patch(
        url,
        json={"name": "  Renamed  ", "description": "New", "status": "active"},
        headers=owner,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["name"], body["description"], body["status"]) == (
        "Renamed",
        "New",
        "active",
    )
    assert body["updated_at"] > before
    assert client.get(url, headers=owner).json()["name"] == "Renamed"

    partial = client.patch(url, json={"status": "archived"}, headers=owner).json()
    assert (partial["name"], partial["status"]) == ("Renamed", "archived")

    for bad, field in [
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"status": "done"}, "status"),
        ({"owner_hash": "x"}, "owner_hash"),
        ({"description": "x" * 10001}, "description"),
    ]:
        response = client.patch(url, json=bad, headers=owner)
        assert response.status_code == 422
        assert response.json()["error"]["fields"][0]["field"] == field
    assert client.patch(url, json={"name": None}, headers=owner).status_code == 422
    assert client.patch(url, json={"name": "x"}, headers=other).status_code == 404

    assert client.delete(url, headers=other).status_code == 404
    assert client.delete(url, headers=owner).status_code == 204
    assert client.get(url, headers=owner).status_code == 404
    assert client.delete(url, headers=owner).status_code == 404


def test_discovery_partial_save_and_resume(client: TestClient) -> None:
    owner = token()
    project_id = make_project(client, owner)
    url = f"/api/v1/projects/{project_id}/discovery"
    empty = client.get(url, headers=owner).json()
    assert empty["current_step"] == "problem"
    assert empty["completed_steps"] == []
    assert [step["id"] for step in empty["steps"]][0] == "problem"
    assert empty["updated_at"] is None

    saved = client.put(
        url,
        json={
            "answers": {
                "problem_statement": " Booking is slow ",
                "target_users": ["Owners"],
            },
            "current_step": "goals",
        },
        headers=owner,
    )
    assert saved.status_code == 200, saved.text
    resumed = client.get(url, headers=owner).json()
    assert resumed["current_step"] == "goals"
    assert resumed["answers"]["problem_statement"] == "Booking is slow"
    assert resumed["answers"]["goals"] == []
    assert resumed["completed_steps"] == ["problem", "users"]

    for bad in [
        {"answers": {"target_users": [""]}},
        {"answers": {"unknown": "x"}},
        {"answers": {}, "current_step": "nope"},
        {"answers": {"goals": ["g"] * 31}},
    ]:
        assert client.put(url, json=bad, headers=owner).status_code == 422
    assert client.put(url, json={"answers": {}}, headers=token()).status_code == 404
    assert client.get(url, headers=token()).status_code == 404

    overview = client.get(f"/api/v1/projects/{project_id}/overview", headers=owner)
    assert overview.status_code == 200
    data = overview.json()
    assert data["discovery_completed"] == ["problem", "users"]
    assert "Discovery: Goals and success" in data["missing"]
    assert "At least one functional requirement" in data["missing"]


def test_requirements_crud(client: TestClient) -> None:
    owner = token()
    project_id = make_project(client, owner)
    url = f"/api/v1/projects/{project_id}/requirements"
    assert client.get(url, headers=owner).json() == []
    created = client.post(
        url,
        json={
            "type": "functional",
            "title": " Book a table ",
            "priority": "P0",
            "acceptance_criteria": ["Booking is confirmed"],
        },
        headers=owner,
    )
    assert created.status_code == 201, created.text
    requirement = created.json()
    assert requirement["title"] == "Book a table"
    assert requirement["status"] == "proposed"
    item = f"{url}/{requirement['id']}"

    updated = client.patch(
        item, json={"status": "confirmed", "acceptance_criteria": []}, headers=owner
    ).json()
    assert (updated["status"], updated["acceptance_criteria"]) == ("confirmed", [])
    assert client.get(url, headers=owner).json()[0]["status"] == "confirmed"

    for bad in [
        {"type": "other", "title": "x"},
        {"type": "functional", "title": " "},
        {"type": "functional", "title": "x", "priority": "P9"},
        {"type": "functional", "title": "x", "acceptance_criteria": [""]},
        {"title": "x"},
    ]:
        response = client.post(url, json=bad, headers=owner)
        assert response.status_code == 422
        assert response.json()["error"]["fields"]

    other = token()
    other_project = make_project(client, other)
    assert client.get(url, headers=other).status_code == 404
    assert client.patch(item, json={"title": "x"}, headers=other).status_code == 404
    wrong_parent = f"/api/v1/projects/{other_project}/requirements/{requirement['id']}"
    assert (
        client.patch(wrong_parent, json={"title": "x"}, headers=other).status_code
        == 404
    )

    overview = client.get(
        f"/api/v1/projects/{project_id}/overview", headers=owner
    ).json()
    assert overview["requirements"]["total"] == 1
    assert overview["requirements"]["confirmed"] == 1
    assert overview["requirements"]["p0"] == 1

    assert client.delete(item, headers=owner).status_code == 204
    assert client.get(url, headers=owner).json() == []
    assert (
        client.delete(f"/api/v1/projects/{project_id}", headers=owner).status_code
        == 204
    )


def test_sample_is_public_and_read_only(client: TestClient, migrated_url: str) -> None:
    assert client.get("/api/v1/projects/sample").status_code == 404
    engine = create_engine(migrated_url)
    with Session(engine) as session:
        seed_sample(session)
        seed_sample(session)
    engine.dispose()

    sample = client.get("/api/v1/projects/sample").json()
    assert sample["id"] == str(SAMPLE_PROJECT_ID)
    assert sample["is_sample"] is True
    assert "illustrative" in sample["name"].lower()
    base = f"/api/v1/projects/{SAMPLE_PROJECT_ID}"
    assert client.get(base).status_code == 200
    assert client.get(base, headers=token()).status_code == 200
    assert len(client.get(f"{base}/requirements").json()) == len(REQUIREMENTS)
    assert client.get(f"{base}/discovery").json()["current_step"] == "review"
    assert client.get(f"{base}/overview").json()["missing"] == []

    owner = token()
    for method, path, body in [
        ("patch", base, {"name": "Hacked"}),
        ("delete", base, None),
        ("put", f"{base}/discovery", {"answers": {}}),
        ("post", f"{base}/requirements", {"type": "functional", "title": "x"}),
    ]:
        kwargs = {"headers": owner} | ({"json": body} if body is not None else {})
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403, (method, path)
        assert "read-only" in response.json()["error"]["message"]
    listed = client.get("/api/v1/projects", headers=owner).json()["items"]
    assert all(item["id"] != str(SAMPLE_PROJECT_ID) for item in listed)


def test_expired_projects_purged(client: TestClient, migrated_url: str) -> None:
    owner = token()
    stale = make_project(client, owner, "Stale")
    fresh = make_project(client, owner, "Fresh")
    engine = create_engine(migrated_url)
    with Session(engine) as session:
        session.execute(
            update(Project)
            .where(Project.id == stale)
            .values(updated_at=datetime.now(UTC) - timedelta(days=31))
        )
        session.commit()
    engine.dispose()
    make_project(client, token(), "Trigger")
    assert client.get(f"/api/v1/projects/{stale}", headers=owner).status_code == 404
    assert client.get(f"/api/v1/projects/{fresh}", headers=owner).status_code == 200

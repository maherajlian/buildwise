import os
import secrets
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.settings import Settings, database_url
from app.main import create_app


@pytest.fixture(scope="module")
def migrated_url() -> Iterator[str]:
    configured = os.getenv("DATABASE_URL")
    if not configured:
        pytest.skip("DATABASE_URL not set: real PostgreSQL integration disabled")
    admin = create_engine(database_url(configured), isolation_level="AUTOCOMMIT")
    name = "buildwise_test_" + uuid4().hex
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = admin.url.set(database=name).render_as_string(hide_password=False)
    try:
        engine = create_engine(url)
        assert inspect(engine).get_table_names() == []
        previous = os.environ["DATABASE_URL"]
        os.environ["DATABASE_URL"] = url
        try:
            config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
            command.upgrade(config, "head")
            command.check(config)
        finally:
            os.environ["DATABASE_URL"] = previous
        assert "projects" in inspect(engine).get_table_names()
        engine.dispose()
        yield url
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


def test_migrations_ready_and_projects(migrated_url: str) -> None:
    headers = {"X-Project-Token": secrets.token_urlsafe(32)}
    with TestClient(
        create_app(Settings(database_url=migrated_url, otel_exporter_otlp_endpoint=""))
    ) as client:
        assert client.get("/ready").status_code == 200
        assert client.get("/api/v1/projects", headers=headers).json() == {
            "items": [],
            "next_cursor": None,
        }
        ids = set()
        for index in range(3):
            response = client.post(
                "/api/v1/projects", json={"name": f"Project {index}"}, headers=headers
            )
            assert response.status_code == 201, response.text
            value = response.json()
            assert value["status"] == "draft"
            assert value["created_at"] and value["updated_at"]
            assert "owner_hash" not in value
            ids.add(value["id"])
        page = client.get("/api/v1/projects?limit=2", headers=headers).json()
        assert len(page["items"]) == 2
        last = client.get(
            "/api/v1/projects",
            params={"limit": 2, "cursor": page["next_cursor"]},
            headers=headers,
        ).json()
        assert last["next_cursor"] is None
        assert {item["id"] for item in page["items"] + last["items"]} == ids
        other = {"X-Project-Token": secrets.token_urlsafe(32)}
        assert client.get("/api/v1/projects", headers=other).json()["items"] == []
        assert (
            client.get(
                "/api/v1/projects",
                params={"cursor": page["next_cursor"]},
                headers=other,
            ).status_code
            == 400
        )
        for body in [
            {"name": " "},
            {"name": "x", "status": "invalid"},
            {"name": "x", "description": "x" * 10001},
        ]:
            assert (
                client.post("/api/v1/projects", json=body, headers=headers).status_code
                == 422
            )


def test_database_constraints(migrated_url: str) -> None:
    engine = create_engine(migrated_url)
    try:
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO projects (id, owner_hash, name, status) "
                    "VALUES (:id, :owner, :name, :status)"
                ),
                {"id": uuid4(), "owner": "a" * 64, "name": "", "status": "draft"},
            )
    finally:
        engine.dispose()


def test_bad_database_url() -> None:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    with TestClient(
        create_app(
            Settings(
                database_url="postgresql+psycopg://bad:bad@127.0.0.1:1/bad",
                otel_exporter_otlp_endpoint="",
            )
        )
    ) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.core.settings import database_url


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

import json
import logging
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.settings import Settings
from app.main import create_app
from app.telemetry.setup import ExportFailureFilter, JsonFormatter


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(
        create_app(
            Settings(
                app_env="test",
                database_url="postgresql+psycopg://x:x@127.0.0.1:1/x",
                otel_exporter_otlp_endpoint="",
            )
        )
    ) as value:
        yield value


def assert_error(response: httpx.Response) -> None:
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message", "correlation_id"}
    assert (
        response.json()["error"]["correlation_id"]
        == response.headers["x-correlation-id"]
    )


def test_health_without_db(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/ready")
    assert response.status_code == 503
    assert_error(response)
    assert "password" not in response.text


@pytest.mark.parametrize(
    "path,method,status",
    [
        ("/missing", "get", 404),
        ("/health", "post", 405),
        ("/api/v1/projects?limit=101", "get", 422),
    ],
)
def test_errors(client: TestClient, path: str, method: str, status: int) -> None:
    response = getattr(client, method)(path)
    assert response.status_code == status
    assert_error(response)


def test_correlation(client: TestClient) -> None:
    assert (
        client.get("/health", headers={"X-Correlation-ID": "test-123"}).headers[
            "x-correlation-id"
        ]
        == "test-123"
    )
    assert (
        client.get("/health", headers={"X-Correlation-ID": "bad value"}).headers[
            "x-correlation-id"
        ]
        != "bad value"
    )


def test_body_limit(client: TestClient) -> None:
    for content in [b"x" * (256 * 1024 + 1), iter([b"x" * 200000, b"x" * 100000])]:
        response = client.post("/api/v1/projects", content=content)
        assert response.status_code == 413
        assert_error(response)


def test_cors(client: TestClient) -> None:
    allowed = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert (
        "access-control-allow-origin"
        not in client.get("/health", headers={"Origin": "https://evil.test"}).headers
    )
    response = client.options(
        "/health",
        headers={"Origin": "https://evil.test", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400
    assert_error(response)


def test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", '["https://buildwise.test"]')
    settings = Settings(_env_file=None)
    assert settings.app_env == "production"
    assert settings.cors_origins == ["https://buildwise.test"]
    assert settings.otel_traces_sampler_arg == 0.1
    with pytest.raises(ValidationError):
        Settings(cors_origins=["*"])
    with pytest.raises(ValidationError):
        Settings(otel_traces_sampler_arg=2)


def test_unhandled_error(client: TestClient) -> None:
    @client.app.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret-value")

    response = client.get("/crash")
    assert response.status_code == 500
    assert_error(response)
    assert "secret-value" not in response.text


def test_otlp_unreachable() -> None:
    with TestClient(
        create_app(
            Settings(
                otel_exporter_otlp_endpoint="http://127.0.0.1:1",
                otel_traces_sampler_arg=1,
            )
        )
    ) as client:
        assert client.get("/health").status_code == 200


def test_structured_log() -> None:
    record = logging.LogRecord(
        "buildwise", logging.INFO, "", 1, "request_completed", (), None
    )
    value = json.loads(JsonFormatter(Settings()).format(record))
    assert value["event"] == "request_completed"
    assert {
        "timestamp",
        "severity",
        "service",
        "environment",
        "trace_id",
        "span_id",
    } <= value.keys()


def test_export_failure_logged_once_without_details() -> None:
    filter_ = ExportFailureFilter()
    record = logging.LogRecord(
        "opentelemetry", logging.ERROR, "", 1, "secret endpoint %s", ("password",), None
    )
    assert filter_.filter(record)
    assert record.getMessage() == "telemetry_export_failed"
    assert not filter_.filter(record)


def test_write_rate_limit(client: TestClient) -> None:
    for _ in range(30):
        client.post("/api/v1/projects", json={})
    response = client.post("/api/v1/projects", json={})
    assert response.status_code == 429
    assert_error(response)

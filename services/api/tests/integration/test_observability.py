import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.core.settings import Settings
from app.main import create_app
from app.telemetry.operations import current
from app.telemetry.setup import configure_telemetry


@pytest.mark.parametrize("fault", ["", "recommendations:fail", "recommendations:slow"])
def test_flow(
    migrated_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault: str,
) -> None:
    monkeypatch.setenv("FAULT_INJECTION", fault)
    spans = InMemorySpanExporter()
    reader = InMemoryMetricReader()
    settings = Settings(database_url=migrated_url, otel_traces_sampler_arg=1)
    telemetry = configure_telemetry(settings, spans, reader)
    log_exporter = InMemoryLogRecordExporter()
    telemetry.logs.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
    with patch("app.main.configure_telemetry", return_value=telemetry):
        app = create_app(settings)
    private = "SecretProjectCanary"
    headers = {"X-Project-Token": "private-owner-token-" + "x" * 32}
    with TestClient(app) as client, patch("app.telemetry.operations.sleep") as sleep:
        project = client.post(
            "/api/v1/projects", json={"name": private}, headers=headers
        )
        assert project.status_code == 201
        base = "/api/v1/projects/" + project.json()["id"]
        assert (
            client.patch(base, json={"name": private}, headers=headers).status_code
            == 200
        )
        assert (
            client.put(
                base + "/discovery",
                json={"answers": {"problem_statement": "DiscoveryCanary"}},
                headers=headers,
            ).status_code
            == 200
        )
        result = client.get(base + "/recommendations", headers=headers)
        assert result.status_code == (500 if fault.endswith(":fail") else 200)
        if fault.endswith(":slow"):
            sleep.assert_called_once_with(3)
        assert (
            client.post(
                base + "/artefacts/generate", json={}, headers=headers
            ).status_code
            == 200
        )
        assert (
            client.post(base + "/plan/generate", json={}, headers=headers).status_code
            == 200
        )
        assert (
            client.get(base + "/artefacts/export/markdown", headers=headers).status_code
            == 200
        )
        assert client.get("/not/a/route").status_code == 404
        data = reader.get_metrics_data()
        assert data is not None
        metrics = [
            m for r in data.resource_metrics for s in r.scope_metrics for m in s.metrics
        ]
        names = {m.name for m in metrics}
        assert {
            "http_server_request_duration_seconds",
            "http_server_requests_total",
            "buildwise_projects_created_total",
            "buildwise_artifact_generation_total",
            "buildwise_task_generation_total",
            "buildwise_rule_evaluation_duration_seconds",
            "buildwise_export_total",
            "db_pool_connections",
            "db_query_duration_seconds",
        } <= names
        if fault.endswith(":fail"):
            assert "buildwise_operation_errors_total" in names
        else:
            assert "buildwise_recommendation_runs_total" in names
        finished = spans.get_finished_spans()
        operations = {s.name for s in finished}
        assert {
            "projects.create",
            "projects.update",
            "discovery",
            "recommendations",
            "rules",
            "artifacts",
            "tasks",
            "exports",
            "db.SELECT",
        } <= operations
        parents = {s.context.span_id: s.name for s in finished if s.context}
        assert any(
            s.name.startswith("db.")
            and s.parent
            and parents.get(s.parent.span_id) == "projects.create"
            for s in finished
        )
        attrs = json.dumps([dict(s.attributes or {}) for s in finished]) + json.dumps(
            [dict(p.attributes or {}) for m in metrics for p in m.data.data_points]
        )
        logs = capsys.readouterr().err
        for value in (private, "DiscoveryCanary", headers["X-Project-Token"]):
            assert value not in attrs + logs
        assert '"route": "unmatched"' in logs
        exported_logs = log_exporter.get_finished_logs()
        assert any(
            item.log_record.trace_id and item.log_record.span_id
            for item in exported_logs
        )
        assert all(
            private not in str(item.log_record.body) + str(item.log_record.attributes)
            for item in exported_logs
        )


def test_production_ignores_fault_and_bad_exporter(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("FAULT_INJECTION", "recommendations:fail")
    app = create_app(
        Settings(
            app_env="production",
            otel_exporter_otlp_endpoint="http://127.0.0.1:1",
            otel_traces_sampler_arg=1,
        )
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        from starlette.requests import Request

        from app.telemetry.operations import observed

        @observed("recommendations")
        def run(request: Request) -> str:
            return "ok"

        assert run(Request({"type": "http", "app": app})) == "ok"
        app.state.telemetry.traces.force_flush(timeout_millis=2000)
        assert client.get("/health").status_code == 200
    assert "fault_injection_ignored" in capsys.readouterr().err


def test_resource_and_w3c_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef0123456789")
    exporter = InMemorySpanExporter()
    telemetry = configure_telemetry(Settings(otel_traces_sampler_arg=1), exporter)
    assert telemetry.traces.resource.attributes["service.version"] == "abcdef0"
    with patch("app.main.configure_telemetry", return_value=telemetry):
        app = create_app()
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={
                "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
            },
        )
        assert response.status_code == 200
        span = exporter.get_finished_spans()[-1]
        assert span.context is not None
        assert span.context.trace_id == int("0123456789abcdef0123456789abcdef", 16)
        assert span.parent is not None
        assert span.parent.span_id == int("0123456789abcdef", 16)
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "traceparent,tracestate",
            },
        )
        assert response.status_code == 200


@pytest.mark.parametrize("scenario", ["subset", "preserved", "overwrite", "error"])
def test_artifact_counter_counts_only_generated_items(
    migrated_url: str, scenario: str
) -> None:
    reader = InMemoryMetricReader()
    settings = Settings(database_url=migrated_url)
    telemetry = configure_telemetry(settings, metric_reader=reader)
    with patch("app.main.configure_telemetry", return_value=telemetry):
        app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = {"X-Project-Token": "private-owner-token-" + "x" * 32}
        project = client.post(
            "/api/v1/projects", json={"name": "Test"}, headers=headers
        )
        base = "/api/v1/projects/" + project.json()["id"] + "/artefacts"
        response = client.post(
            base + "/generate", json={"kinds": ["prd", "architecture"]}, headers=headers
        )
        assert response.status_code == 200
        prd = next(item for item in response.json() if item["kind"] == "prd")
        if scenario in {"preserved", "overwrite"}:
            assert (
                client.patch(
                    base + "/" + prd["id"], json={"title": "Edited"}, headers=headers
                ).status_code
                == 200
            )
        body = {"kinds": ["prd", "prd"], "overwrite_edited": scenario == "overwrite"}
        if scenario == "error":
            with patch(
                "app.modules.specifications.generator.template", side_effect=ValueError
            ):
                assert (
                    client.post(
                        base + "/generate", json=body, headers=headers
                    ).status_code
                    == 500
                )
        else:
            assert (
                client.post(base + "/generate", json=body, headers=headers).status_code
                == 200
            )
        data = reader.get_metrics_data()
        assert data is not None
        points = [
            p
            for r in data.resource_metrics
            for s in r.scope_metrics
            for m in s.metrics
            if m.name == "buildwise_artifact_generation_total"
            for p in m.data.data_points
        ]
        assert {p.attributes["buildwise.artifact.type"]: p.value for p in points} == {
            "prd": 2 if scenario in {"subset", "overwrite"} else 1,
            "architecture": 1,
        }


@pytest.mark.parametrize("path", ["/artefacts", "/operations/generate"])
@pytest.mark.parametrize("scenario", ["empty", "requirements", "error"])
def test_rules_are_observed_without_business_decorator(
    migrated_url: str, path: str, scenario: str
) -> None:
    exporter = InMemorySpanExporter()
    reader = InMemoryMetricReader()
    settings = Settings(database_url=migrated_url, otel_traces_sampler_arg=1)
    telemetry = configure_telemetry(settings, exporter, reader)
    with patch("app.main.configure_telemetry", return_value=telemetry):
        app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = {"X-Project-Token": "private-owner-token-" + "x" * 32}
        project = client.post(
            "/api/v1/projects", json={"name": "Test"}, headers=headers
        )
        base = "/api/v1/projects/" + project.json()["id"]
        if scenario == "requirements":
            assert (
                client.post(
                    base + "/requirements",
                    headers=headers,
                    json={"type": "functional", "title": "Test requirement"},
                ).status_code
                == 201
            )
        body = {"kind": "adr", "title": "Decision"} if path == "/artefacts" else {}
        if scenario == "error":
            with patch("app.modules.recommendations.engine.CATEGORIES", None):
                response = client.post(base + path, headers=headers, json=body)
            assert response.status_code == 500
        else:
            response = client.post(base + path, headers=headers, json=body)
            assert response.status_code == (201 if path == "/artefacts" else 200)
        rules = [s for s in exporter.get_finished_spans() if s.name == "rules"]
        assert len(rules) == 1
        assert rules[0].parent is not None
        if scenario == "error":
            assert rules[0].attributes["error.type"] == "TypeError"
        data = reader.get_metrics_data()
        assert data is not None
        points = [
            p
            for r in data.resource_metrics
            for s in r.scope_metrics
            for m in s.metrics
            if m.name == "buildwise_rule_evaluation_duration_seconds"
            for p in m.data.data_points
        ]
        assert sum(p.count for p in points) == 1
        assert current.get() is None

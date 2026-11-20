from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from app.core.settings import Settings
from app.main import create_app
from app.telemetry.setup import Telemetry


@pytest.mark.parametrize("scenario", ["empty", "requirements", "error"])
def test_generation_emits_bounded_business_telemetry(
    migrated_url: str, scenario: str
) -> None:
    exporter = InMemorySpanExporter()
    traces = TracerProvider()
    traces.add_span_processor(SimpleSpanProcessor(exporter))
    reader = InMemoryMetricReader()
    telemetry = Telemetry(
        traces, MeterProvider(metric_readers=[reader]), LoggerProvider(), None
    )
    with patch("app.main.configure_telemetry", return_value=telemetry):
        app = create_app(
            Settings(database_url=migrated_url, otel_exporter_otlp_endpoint="")
        )
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = {"X-Project-Token": "private-owner-token-" + "x" * 32}
        project = client.post(
            "/api/v1/projects", headers=headers, json={"name": "Private project"}
        ).json()
        base = f"/api/v1/projects/{project['id']}"
        if scenario == "requirements":
            assert (
                client.post(
                    base + "/requirements",
                    headers=headers,
                    json={
                        "type": "functional",
                        "title": "Private requirement",
                    },
                ).status_code
                == 201
            )
        if scenario == "error":
            with patch(
                "app.modules.operations.service.generate",
                side_effect=ValueError("Private content"),
            ):
                response = client.post(
                    base + "/operations/generate", headers=headers, json={}
                )
            assert response.status_code == 500
        else:
            response = client.post(
                base + "/operations/generate", headers=headers, json={}
            )
            assert response.status_code == 200, response.text
        spans = [
            s for s in exporter.get_finished_spans() if s.name == "operations.generate"
        ]
        assert len(spans) == 1
        outcome = "error" if scenario == "error" else "success"
        assert spans[0].attributes == {"outcome": outcome}
        assert not spans[0].events
        assert spans[0].status.description is None
        assert spans[0].status.status_code == (
            StatusCode.ERROR if scenario == "error" else StatusCode.UNSET
        )
        data = reader.get_metrics_data()
        assert data is not None
        metrics = {
            metric.name: metric
            for resource in data.resource_metrics
            for scope in resource.scope_metrics
            if scope.scope.name == "buildwise.operations"
            for metric in scope.metrics
        }
        counter = metrics["operations_generation_total"].data.data_points[0]
        duration = metrics["operations_generation_duration_seconds"].data.data_points[0]
        assert counter.value == 1
        assert duration.count == 1 and duration.sum >= 0
        assert counter.attributes == duration.attributes == {"outcome": outcome}

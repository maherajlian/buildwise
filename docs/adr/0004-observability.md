# ADR-0004: Observability with OpenTelemetry and Grafana

- Status: Proposed (pending Grafana Cloud Free verification in the deployment spike)
- Date: 2026-11-20

## Context
Observability is a first-class portfolio goal. Telemetry must be vendor-neutral, non-blocking, free, and free of user content.

## Decision
- Instrument the API with the OpenTelemetry Python SDK: FastAPI and SQLAlchemy auto-instrumentation plus manual spans/metrics for business operations (blueprint §11 names).
- Export OTLP/HTTP **directly from the API** to the Grafana Cloud Free OTLP gateway (no hosted Collector/Alloy, which would need a second always-on service). Credentials via `OTEL_EXPORTER_OTLP_HEADERS` only.
- Production trace sampling: `parentbased_traceidratio` at 0.1; metrics with bounded labels only; logs as structured JSON with trace/span IDs, shipped through the OTel logs exporter.
- Batch span/log processors with bounded queues; exporter failure is logged once and never fails a request or startup.
- Local fallback: a Compose profile using `grafana/otel-lgtm` (Grafana, Loki, Tempo, Prometheus, Collector in one image).
- Dashboards (4) and alerts (≤5) are JSON/YAML under `infra/grafana/` and provisioned to both local and cloud.
- Frontend: no browser telemetry in Phase 0/1; privacy-conscious web-vitals/errors considered in Phase 6.

## Consequences
- Telemetry may be lost while the free API instance sleeps or if the free quota is exceeded; documented.
- If Grafana Cloud Free proves unsuitable, the public site shows health only and the full LGTM demo runs locally (blueprint P0 fallback).

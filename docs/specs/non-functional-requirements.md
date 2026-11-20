# Non-functional, security and observability requirements

Status: draft v0.1 (2026-11-20).

## Cost and constraints (NFR)
| ID | Requirement |
|---|---|
| NFR-001 | Zero paid AI inference at runtime; no model API client is a dependency of the hosted app or CI. Enforced by a CI check that fails on known LLM SDK imports (openai, anthropic, google-generativeai, etc.). |
| NFR-002 | All hosted dependencies run on free tiers verified in `docs/hosting/free-tier-assessment.md`; no mandatory paid service. |
| NFR-003 | Core workflow works with every optional integration (Grafana, GitHub) disabled. |
| NFR-004 | Generation endpoints are deterministic for identical input + catalogue/template version. |
| NFR-005 | Modular monolith: one API deployable, one frontend deployable, one database. |
| NFR-006 | p95 API latency < 500 ms for CRUD and generation on a warm instance (excluding free-tier cold starts, which are documented). |
| NFR-007 | Frontend is responsive (≥ 360 px wide) and meets WCAG 2.1 AA for keyboard navigation and contrast; checked with axe in Playwright. |
| NFR-008 | Reproducible setup: `docker compose up` (or documented commands) runs web, API and Postgres locally from a clean checkout. |
| NFR-009 | Database schema changes only through Alembic migrations; migrations run cleanly from an empty DB in CI. |
| NFR-010 | CI on every PR: lint, format, type check, backend unit + integration tests, frontend tests, builds, migration check; stays within GitHub Free allowance. |
| NFR-011 | All artefacts exportable as Markdown that is readable outside BuildWise. |
| NFR-012 | Availability target is "best effort on free tier"; sleep/cold-start behaviour documented, no uptime guarantee claimed. |

## Security and privacy (SEC)
| ID | Requirement |
|---|---|
| SEC-001 | Validate every request and response with Pydantic schemas; request body size limit (default 256 KB). |
| SEC-002 | No shared writable public project store: anonymous projects are owned by an unguessable per-browser token (or the public demo is read-only — see decision D1). |
| SEC-003 | CORS restricted to configured `CORS_ORIGINS`. |
| SEC-004 | Rate-limit public write and generation endpoints (in-process limiter, per IP + owner token). |
| SEC-005 | ORM/parameterised queries only; no raw string SQL. |
| SEC-006 | No secrets in the repo; `.env.example` only; secret scanning + dependency scanning (Dependabot) enabled. |
| SEC-007 | Errors return a consistent error object with a correlation ID; no stack traces to clients. |
| SEC-008 | Users can delete their projects and export their data. |
| SEC-009 | No execution of generated or user-supplied code. |
| SEC-010 | Fault-injection switch exists only when `APP_ENV != production` and requires an admin token. |

## Observability (OBS)
| ID | Requirement |
|---|---|
| OBS-001 | OpenTelemetry traces for HTTP lifecycle, DB calls and each business operation (discovery, recommendation, rule evaluation, artefact/task generation, export). |
| OBS-002 | Metrics listed in blueprint §11 with bounded labels only (no project/user IDs, raw URLs, exception messages). |
| OBS-003 | Structured JSON logs with timestamp, severity, service, environment, event, trace_id, span_id, error type; no request bodies or user text. |
| OBS-004 | Telemetry export is non-blocking (batch processors, bounded queues); the app starts and serves when the exporter is unreachable. |
| OBS-005 | Exporter endpoint/credentials only via env vars; trace sampling defaults to 10 % parent-based in production to stay within free quotas. |
| OBS-006 | Four version-controlled Grafana dashboards and ≤5 actionable alerts (blueprint §11). |
| OBS-007 | Local Docker Compose observability profile (Grafana + Loki + Tempo + Prometheus/Mimir, or `grafana/otel-lgtm`) as fallback. |
| OBS-008 | Repeatable failure-injection demo diagnosable through trace → log correlation. |

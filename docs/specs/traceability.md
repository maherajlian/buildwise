# Phase 0/1 requirement traceability

Scope: the foundation API, static frontend and CI. References below are executable
test names, not claims that an entire product requirement is complete. Requirements
come from [functional requirements](functional-requirements.md) and
[non-functional/security/observability requirements](non-functional-requirements.md).

Test path abbreviations:

- **API unit**: `services/api/tests/unit/test_api.py`
- **API integration**: `services/api/tests/integration/test_postgres.py`
- **Web**: `apps/web/tests/`
- **E2E**: `apps/web/tests/e2e/stack.spec.ts` (real API/Postgres + static export)
- **CI**: `.github/workflows/ci.yml`

| Requirement | Tests / automated checks | Coverage and remaining gaps |
|---|---|---|
| FR-001 — project CRUD | API integration `test_migrations_ready_and_projects`, `test_database_constraints`; Web `projects.test.tsx`; E2E `create and list a browser-owned project through the real stack` | **Partial**: create/list, browser ownership, validation, persistence, empty/error states. Edit, single-project retrieval and delete are not implemented or tested. |
| FR-002 — paginated listing | API integration `test_migrations_ready_and_projects`; API unit `test_errors` (limit 101 rejected); Web `projects.test.tsx` (`loads existing projects and another page`), `api.test.ts` (limit 20 sent) | Cursor page traversal and cross-owner cursor rejection covered. Default/max pagination acceptance boundaries are not exhaustively tested. |
| FR-016 — health/readiness | API unit `test_health_without_db`; API integration `test_migrations_ready_and_projects`, `test_bad_database_url`; Web `status.test.tsx`; E2E `real API health and readiness` | Liveness without DB, readiness success/503, cold-start recovery and bounded retries covered. Hosted cold-start duration is unverified. |
| NFR-001 — no paid AI | `scripts/test_no_paid_ai.py`; CI `no-paid-ai` runs `scripts/no_paid_ai.py` | Listed SDKs rejected in manifests, transitive locks and imports. Tests cover allowed/empty inputs, invalid source, deny cases and CLI exit codes. A static denylist does not prevent arbitrary HTTP/model calls; code review still required. |
| NFR-008 — reproducible local setup | CI frozen installs, API migration and E2E jobs; E2E real-stack tests; root README and API README local commands | API/Postgres/static web exercised. CI uses Postgres services and uvicorn rather than Docker Compose; Compose image build and `pnpm dev` startup are manual checks, not covered by these jobs. |
| NFR-009 — Alembic-only schema changes | API integration `migrated_url` fixture asserts empty DB, runs `upgrade head` + `command.check`; CI API job runs `alembic upgrade head` + `alembic check` on a fresh service DB | Current migration and model drift covered. Rollback/data migration safety requires migration-specific tests. |
| NFR-010 — PR CI | CI `api`, `web`, `e2e`, `no-paid-ai` jobs | Lint/format/type/unit/integration/build/contracts/migrations/E2E on PRs and main pushes. Standard runners, cached installs, cancellation and timeouts bound waste; private-repo monthly allowance is not automatically enforced. |
| SEC-001 — schemas/body size | API unit `test_body_limit`, `test_errors`; API integration `test_migrations_ready_and_projects`, `test_database_constraints`; Web `projects.test.tsx` | Oversized fixed/streamed bodies return 413; invalid project fields/limit return 422; create output fields checked. No exhaustive response-schema mutation/fuzz tests. |
| SEC-003 — restricted CORS | API unit `test_cors`; E2E real browser project calls | Configured origin allowed; foreign-origin responses/preflight rejected. E2E exercises actual localhost browser CORS. |
| SEC-005 — ORM/parameterised queries | API integration project persistence and database constraint tests | **Partial / review-based**: tests prove persistence, not absence of unsafe SQL. Review `app/modules/projects/router.py` (ORM), `app/main.py` (constant `SELECT 1`), migrations and future queries. No SQL injection-focused automated test yet. |
| SEC-007 — safe standard errors/correlation | API unit `test_errors`, `test_correlation`, `test_health_without_db`, `test_unhandled_error`, `test_body_limit`, `test_cors`, `test_write_rate_limit`; Web `api.test.ts`, `projects.test.tsx`, `status.test.tsx` | Consistent code/message/correlation object, propagated/generated ID, hidden exception detail, client error rendering covered. |
| OBS-001 — HTTP/DB/business traces | API integration requests exercise instrumented HTTP/SQLAlchemy code; API unit `test_otlp_unreachable` exercises startup | **Partial, no span-content assertion**: instrumentation is configured, but no test captures HTTP/DB parent-child spans. Discovery/recommendation/generation operations are not implemented. Successful collector ingestion is unverified. |
| OBS-003 — structured logs | API unit `test_structured_log`, `test_export_failure_logged_once_without_details` | JSON timestamp/severity/service/environment/event/trace/span keys and exporter-detail suppression checked. Nonzero active-span IDs, error-type field and exhaustive user-content redaction are not asserted; current formatter has no error-type field. |
| OBS-004 — resilient async export | API unit `test_otlp_unreachable`, `test_export_failure_logged_once_without_details`; E2E works with OTLP unset | Startup/liveness with unreachable endpoint and unset-exporter core flow covered. Batching/bounded queues are configured in `app/telemetry/setup.py` but queue saturation and latency bounds are not load-tested. |

See [CONTRIBUTING](../../CONTRIBUTING.md#checks-before-review) for exact commands.
Do not mark the listed gaps complete solely because CI is green.

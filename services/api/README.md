# API foundation

## Phase 4: Specify and Build planning (backend)

All generation is local deterministic rules/templates: no inference, model calls or
new paid dependencies. Under `/api/v1/projects/{id}`:

- `POST /artefacts/generate` accepts optional `kinds` and `overwrite_edited=false`.
  `GET /artefacts`, `GET/PATCH/DELETE /artefacts/{aid}` provide structured documents;
  PATCH takes `title`/`sections` and marks the document edited. Sections contain
  unique `key`, `heading`, `body` fields (1–40 sections, bounded text).
- `POST /artefacts` accepts `{kind:"adr", title}`; multiple ADRs are allowed.
  All other kinds are unique per project. `GET /artefacts/{aid}/markdown` and
  `GET /artefacts/export/markdown` return `text/markdown`, with a fixed document
  order, context header and table of contents in the combined export.
- Kinds: `prd`, `technical_design`, `architecture`, `adr`, `data_model`,
  `api_contract`, `user_stories`, `acceptance_criteria`,
  `non_functional_requirements`, `security`, `test_strategy`, `deployment`,
  `observability`. Context snapshots retain discovery, requirements and effective
  technology recommendations; missing decisions are explicitly marked TODO.
- `POST /plan/generate` accepts `overwrite=false` (preserves an existing plan);
  `GET /plan` returns `epics`, `tasks`, and `{valid, errors}` validation.
  `POST /plan/epics`, `PATCH/DELETE /plan/epics/{eid}` and
  `POST /plan/tasks`, `PATCH/DELETE /plan/tasks/{tid}` edit the plan.
  Task keys are assigned automatically, unique per project. Priorities are P0/P1/P2;
  statuses are `backlog`, `ready`, `in_progress`, `review`, `done`.
  Dependencies are task UUIDs; unknown/foreign/self/cyclic dependencies return 422.
  Active/review/done tasks require dependencies done, including on later edits.
  Deleting tasks removes incoming dependencies; deleting epics ungroups tasks.
  `GET /plan/export/markdown` exports every epic/task and planning field.

Reads use the owner token except for the public sample; all writes require an owner
token and update project activity. The sample is seeded with specifications and a
plan and rejects writes with 403. Migration `0004` adds `artefacts`, `epics` and
`plan_tasks`; project deletion cascades. No frontend is added in this phase.

Python 3.12 and uv. From the repository root: `docker compose up -d --build api`.
From this directory: `uv sync --frozen`, `uv run alembic upgrade head`, then
`uv run uvicorn app.main:create_app --factory --port 8000`.
Settings use environment variables; CORS_ORIGINS is a JSON array, never `*`.
The root `.env.example` contains local-only fake credentials, not production secrets.

Project endpoints require `X-Project-Token`: generate a browser-local secret with
`crypto.getRandomValues` (at least 32 random bytes, base64url encoded; 43 characters).
Preserve it locally and send it with both requests. Only SHA-256 hashes are stored;
losing the token loses access. Do not send user content or tokens in URLs/logs.
Tokens are bearer capabilities, not accounts. List responses contain `items` and
`next_cursor`; send the latter as `cursor`. Ordering is stable UUID order, not creation
order. Limits default to 20, maximum 100. The minimal write limiter allows 120 writes
(POST/PUT/PATCH/DELETE) per minute per direct peer IP per process; it is not distributed and ignores forwarded
headers. Review proxy trust and ownership lifecycle before public deployment.

Phase 2 adds `GET/PATCH/DELETE /api/v1/projects/{id}`, `GET /api/v1/projects/{id}/overview`,
`GET/PUT /api/v1/projects/{id}/discovery` (partial answers plus `current_step`) and
`/api/v1/projects/{id}/requirements` CRUD. Another token's project returns 404. Validation
errors include `error.fields` (`field`, `message`). Projects untouched for 30 days are
purged when a project is created. `GET /api/v1/projects/sample` returns the illustrative,
read-only sample (writes return 403); `python -m app.scripts.seed_sample` (run by the
container on start) seeds it idempotently.

`/health` does not connect to the DB; `/ready` performs SELECT 1. Requests are bounded
at 256 KiB, including streamed/chunked bodies. Correlation IDs allow ASCII letters,
digits, `_` and `-`, up to 128 characters; invalid values are replaced.

With no OTLP endpoint, telemetry stays local. With an endpoint, all three signals
export via batched OTLP/HTTP with bounded span/log queues; failures do not block
requests. Telemetry can be lost during shutdown/sleep. No collector is required.

Generate the frontend contract with `uv run python -m app.scripts.export_openapi`.
Run `uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q`.
Integration tests skip when DATABASE_URL is unset; when set they create and drop a
uniquely named test database on that server (requires CREATEDB); they never clear
the configured application's tables. Example local URL:
`postgresql+psycopg://buildwise:buildwise@localhost:5432/buildwise`.

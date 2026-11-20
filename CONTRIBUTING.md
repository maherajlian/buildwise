# Contributing to BuildWise

Read the relevant [requirements](docs/specs/functional-requirements.md),
[architecture](docs/architecture/system-design.md), and [ADRs](docs/adr/) before
changing code. Use one bounded task with explicit acceptance criteria; state
assumptions and do not silently change requirements.

## Branches and review

Branch from current `main` using `devin/<unix-timestamp>-<short-description>` for
agent work (or an agreed feature branch). Keep commits focused, open a pull
request, and obtain human review before merging. Do not push directly to `main`.
Human approval is required for architecture/deployment changes, secrets, and
destructive operations. Explain every new dependency. Never introduce model API
clients or paid inference services, even for CI.

Local setup is documented in the [root README](README.md#local-setup) and
[API README](services/api/README.md). Node 24, pnpm 12.16.1, Python 3.12 and uv
are the CI toolchain. Keep lockfiles committed and use frozen installs.

## Checks before review

Start PostgreSQL: `docker compose up -d postgres`. The integration tests require
a PostgreSQL role with `CREATEDB`; the local Compose role has it. They create and
drop a uniquely named test database, not your development database.

```sh
# From repository root
python3 scripts/no_paid_ai.py
python3 -m unittest discover -s scripts -p 'test_*.py' -v
cd services/api
uv sync --frozen
export DATABASE_URL=postgresql+psycopg://buildwise:buildwise@localhost:5432/buildwise
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -q
uv run alembic upgrade head
uv run alembic check
uv run python -m app.scripts.export_openapi
git diff --exit-code -- ../../packages/shared-types/openapi.json
cd ../..
pnpm install --frozen-lockfile
pnpm generate:types
git diff --exit-code -- packages/shared-types/api.d.ts
pnpm -C apps/web lint
pnpm -C apps/web typecheck
pnpm -C apps/web test
pnpm -C apps/web build
pnpm -C apps/web exec playwright install --with-deps chromium
docker compose up -d --build api
pnpm -C apps/web test:e2e
```

Port 3000 must be free for Playwright's static server. E2E uses real API/DB calls,
not mocks; it adds local test projects. CI also migrates its fresh service database
and checks migration drift. If changing migrations, verify against a new disposable
database as well as the existing schema. Never reset a shared or production DB.

After API changes, regenerate and commit OpenAPI and TypeScript contracts; the
diff checks above should be clean after committing the intended changes.
The no-paid-AI guard scans manifests/locks and Python/JS/TS imports, including
literal dynamic imports. It is a denylist, not proof that arbitrary runtime HTTP
calls cannot invoke paid services. Review new integrations manually.

## Definition of Done (blueprint §9)

- Acceptance criteria are met.
- Tests are added or updated, including normal, empty and error cases.
- Relevant test suites pass; report actual output, including skips or failures.
- Lint and type checks pass.
- Security implications are considered; no secrets, user content or tokens leak.
- Documentation is updated, including [traceability](docs/specs/traceability.md).
- Telemetry is added for meaningful new operations.
- No paid runtime dependency has been introduced.
- The implementation is reviewed.

For UI changes, check keyboard use, 360px layout and accessibility; attach visual
evidence where practical. Never claim deployment success without verifying the
deployed result. CI uses standard `ubuntu-latest` runners with bounded job times
and cancels superseded runs; public-repo standard runners avoid paid compute.
Private-repo usage must still be monitored against the account's free allowance.
Deployment automation is intentionally deferred.

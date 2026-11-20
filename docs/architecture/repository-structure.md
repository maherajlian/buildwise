# Repository structure

The repository uses a `pnpm` workspace and keeps API migrations in
`services/api/alembic/`.

```text
buildwise/
├── apps/web/                      # Next.js (App Router, TypeScript, static export), Tailwind + shadcn/ui
│   ├── src/app/                   # routes: dashboard, projects, catalogue, guides, observability, docs
│   ├── src/lib/api.ts             # typed client using generated OpenAPI types
│   └── tests/                     # Vitest unit + Playwright e2e/axe
├── services/api/                  # FastAPI modular monolith (Python 3.12, uv)
│   ├── app/{core,db,telemetry}/
│   ├── app/modules/               # domains and workbench composition routes
│   ├── app/main.py
│   ├── alembic/                   # migrations
│   ├── Dockerfile
│   └── tests/{unit,integration}/  # pytest; integration uses a Postgres service container
├── packages/shared-types/         # generated OpenAPI schema + TS types (committed, checked for drift in CI)
├── docs/{specs,architecture,adr,hosting,operations,plan}/
├── infra/
│   └── grafana/{dashboards,alerts}/
├── .github/workflows/             # CI, production deploy and keep-warm
├── docker-compose.yml             # API + PostgreSQL; optional grafana/otel-lgtm
├── .env.example
├── README.md
└── CONTRIBUTING.md
```

Tooling: `uv`, `ruff`, `mypy`, `pytest` for Python; `pnpm`, `eslint`,
`tsc`, `vitest`, `playwright` for the web app.

Phase 3 backend catalogue lives at
`services/api/app/modules/recommendations/catalogue/{catalogue.json,catalogue.schema.json}`
rather than root `data/`: it must ship inside the existing `services/api` Docker
build context. The JSON contains both catalogue and rules versions. The public
`GET /api/v1/catalogue` endpoint exposes the same validated data used by the engine.
`recommendation_inputs` stores project overrides; generated recommendations are
computed on read, not persisted.

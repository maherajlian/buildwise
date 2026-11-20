# Proposed repository structure

Follows blueprint §5 with three small changes (to be recorded in ADR-0005 if accepted): a `pnpm` workspace root, `services/api/alembic/`, and `docs/plan/` + `docs/runbooks/`.

```text
buildwise/
├── apps/web/                      # Next.js (App Router, TypeScript, static export), Tailwind + shadcn/ui
│   ├── src/app/                   # routes: dashboard, projects, catalogue, guides, observability, docs
│   ├── src/lib/api/               # typed client generated from OpenAPI (openapi-typescript)
│   └── tests/                     # Vitest unit + Playwright e2e/axe
├── services/api/                  # FastAPI modular monolith (Python 3.12, uv)
│   ├── app/{api,core,db,telemetry}/
│   ├── app/modules/{discovery,recommendations,specifications,planning,exports}/
│   ├── app/main.py
│   ├── alembic/                   # migrations
│   ├── Dockerfile
│   └── tests/{unit,integration}/  # pytest; integration uses a Postgres service container
├── packages/shared-types/         # generated OpenAPI schema + TS types (committed, checked for drift in CI)
├── data/technology-catalogue/     # versioned JSON entries + schema.json + CATALOGUE_VERSION
├── docs/{product,specs,architecture,adr,development,testing,observability,hosting,runbooks,plan}/
├── infra/
│   ├── docker/                    # local compose overrides
│   └── grafana/{dashboards,alerts}/
├── .github/workflows/             # ci.yml (PR), deploy.yml (main)
├── docker-compose.yml             # web + api + postgres; `--profile observability` adds grafana/otel-lgtm
├── .env.example
├── README.md
└── CONTRIBUTING.md
```

Tooling choices: `uv` (Python deps/lock), `ruff` (lint+format), `mypy` (types), `pytest`; `pnpm`, `eslint`, `prettier`, `tsc`, `vitest`, `playwright` for the web app.

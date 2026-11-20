# BuildWise

A zero-paid-AI engineering workbench, from idea to observable deployment.
Phase 1 includes the API/database foundation and a statically exported Next.js workspace.
Projects are live; catalogue, guides, documentation and full observability are clearly
labelled placeholders. No runtime model or paid inference service is used.

## Local setup

Requires Docker Compose, Node.js 22.12+ (24 LTS recommended), pnpm 12.16.1,
and Python 3.12 + uv for API development. Activate your Node environment first.

```sh
docker compose up -d --build api
pnpm install --frozen-lockfile
pnpm dev
```

Open http://localhost:3000. The API is at http://localhost:8000; Compose runs migrations
automatically and restricts browser CORS to http://localhost:3000. Use that exact web
origin (not 127.0.0.1) or explicitly configure `CORS_ORIGINS` as a JSON array.
For API-only development and tests, see [services/api/README.md](services/api/README.md).

The web app reads `NEXT_PUBLIC_API_BASE_URL` at build/dev startup (default:
`http://localhost:8000`). To change it, set the environment variable or create
`apps/web/.env.local` with that value, then rebuild. Never place secrets in
`NEXT_PUBLIC_*`. Root `.env.example` documents local fake settings; Compose reads
root `.env`, while Next.js reads its own app directory.

Projects are private to a browser-generated bearer token stored in localStorage.
Losing/clearing browser storage loses access; do not enter sensitive information.
There are no accounts or cross-device recovery yet. API cold starts are handled
with bounded retries; the dashboard checks both liveness and database readiness.

## Frontend checks

```sh
pnpm -C apps/web lint
pnpm -C apps/web typecheck
pnpm -C apps/web test
pnpm -C apps/web build
pnpm -C apps/web exec playwright install chromium
pnpm -C apps/web test:e2e
```

The build outputs **static files** to `apps/web/out` (no SSR, Server Actions or API
routes). Playwright starts a static file server on port 3000; keep that port free
and the Compose API/Postgres running. Tests use real API calls, verify project
persistence across reload, and run axe plus 360px overflow checks on every main
page. Test projects remain in the local development database. Screenshots are
written to ignored `apps/web/test-results/`. To inspect the export yourself:
`pnpm -C apps/web serve`. Development uses `pnpm dev` instead of a Compose web
service so the browser always uses the public localhost API URL.

## API contract

```sh
# After changing FastAPI routes/schemas:
cd services/api
uv run python -m app.scripts.export_openapi
cd ../..
pnpm generate:types
```

Commit both `packages/shared-types/openapi.json` and generated `api.d.ts`. The web
client uses `openapi-fetch` with those generated types. Browser owner tokens are
created from 32 cryptographically random bytes and sent only in `X-Project-Token`.

See [architecture](docs/architecture/system-design.md),
[hosting assessment](docs/hosting/free-tier-assessment.md), and
[implementation plan](docs/plan/implementation-proposal.md).

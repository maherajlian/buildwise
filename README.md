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

### Deterministic recommendations (Phase 3)

`GET /api/v1/catalogue` exposes the curated catalogue and rules without a token.
`GET /api/v1/projects/{id}/recommendations` explains scores, alternatives, input
evidence and trade-offs. Project access uses the same token/sample rules as discovery.
Read or replace overrides at `GET|PUT /api/v1/projects/{id}/recommendation-inputs`;
PUT takes `{"overrides":{"budget":"zero"}}`. Omit keys to return them to automatic
detection (an empty object resets all); null and unknown values are rejected.
The sample remains read-only. No model or external API is called during generation.
AI candidates are never recommended without explicit `ai_layer: "required"`;
they remain optional and may incur cost. Scores are a decision aid, not benchmarks.

Catalogue content and JSON Schema are in
`services/api/app/modules/recommendations/catalogue/` so Docker includes them.
Review provider terms and pricing before use; every pricing/free-tier claim requires
verification. Bump `catalogue_version` for content/rule changes and `rules_version`
for detection/scoring changes, update review dates, and run API tests.

Open a project's **Architecture** tab to inspect inputs, evidence, positive/negative
rules and expandable alternatives. Owned projects can save overrides or return
individual inputs to Auto; the sample remains read-only. The public **Technology
catalogue** page groups the same engine data by category, including costs, review
dates and operational trade-offs. Neither screen calls a model or paid AI service.

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

## Operations: optional keep-warm ping

[Keep API warm](.github/workflows/keep-warm.yml) requests `/health` every ten
minutes once merged into the default branch, or through `workflow_dispatch`.
Set the Actions repository variable `API_BASE_URL` to override the default
`https://buildwise-api-p4yq.onrender.com` (public URL, not a secret). The single
step retries until HTTP **200**, with a shared approximately 90-second request
and retry budget; it fails if the API never becomes healthy. The job has a
five-minute timeout, uses a standard Ubuntu runner, and requests no token
permissions. `/health` does not query Neon, so this does not keep the database
awake or verify database readiness.

This intentionally attempts to prevent Render's idle sleep. In a 31-day month,
one always-on service consumes approximately **744 of the workspace's 750 free
instance-hours**, leaving only six hours. A second always-on Render service
would exhaust the shared quota (approximately 1,488 hours total). Reassess usage
before adding another service; never upgrade or add a payment method to make
this ping work. The workflow itself does not change Render's Free plan.

[GitHub schedules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
can be delayed or skipped under load; this is not an availability guarantee.
Scheduled workflows in public repositories automatically disable after **60
days without repository activity**. Check Actions and re-enable if necessary,
or disable the workflow intentionally to conserve Render hours. Pushing this
feature branch alone does not activate its schedule.

## Contributing and CI

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching, required checks and the
Definition of Done, and [requirement traceability](docs/specs/traceability.md) for
test coverage and known gaps. [CI](.github/workflows/ci.yml) checks the API, web,
real-stack E2E flow and no-paid-AI policy on PRs and pushes to `main`.
Dependencies are reviewed weekly with Dependabot. Deployment automation is not
included yet. Licensed under [MIT](LICENSE).

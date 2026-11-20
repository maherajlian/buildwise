# BuildWise

BuildWise turns an idea into a project brief, explainable technology choices,
editable specifications and a delivery plan. It uses deterministic rules and
templates; there is no model, prompt or inference key.

**[Open the live demo](https://buildwise-1fy.pages.dev/)** ·
**[Explore the sample project](https://buildwise-1fy.pages.dev/projects/view/?id=sample)** ·
[Follow the walkthrough](docs/demo-walkthrough.md)

The sample is a fictional restaurant booking SaaS. No account is needed:
review its discovery, compare architecture options, inspect its tasks and
proposed tests, and download the complete Markdown pack from **Overview**.

## Known limitations

- Use synthetic data. Personal projects belong to one browser token, not an
  account. There is no collaboration or recovery if you clear that token.
- Projects inactive for 30 days are eligible for deletion when a new project
  is created. Export work you want to keep; the public sample is exempt.
- Generated plans are drafts. BuildWise does not deploy your project, execute
  tests, or call suggested integrations or AI providers.
- Free hosting has cold starts, capacity limits and no uptime guarantee. See
  the [free-tier assessment](docs/hosting/free-tier-assessment.md).

## Local setup

Requires Docker Compose, Node.js 22.12+ (24 LTS recommended), pnpm 12.16.1,
and Python 3.12 + uv for API development. Activate your Node environment first.

```sh
git clone https://github.com/maherajlian/buildwise.git
cd buildwise
docker compose up -d --build api
curl --fail --retry 20 --retry-all-errors --retry-delay 2 http://localhost:8000/ready
pnpm install --frozen-lockfile
pnpm dev
```

Open http://localhost:3000. The API is at http://localhost:8000; Compose runs migrations
and seeds the sample automatically. Browser CORS is restricted to http://localhost:3000. Use that exact web
origin (not 127.0.0.1) or explicitly configure `CORS_ORIGINS` as a JSON array.
For API-only development and tests, see [services/api/README.md](services/api/README.md).

The web app reads `NEXT_PUBLIC_API_BASE_URL` at build/dev startup (default:
`http://localhost:8000`). To change it, set the environment variable or create
`apps/web/.env.local` with that value, then rebuild. Never place secrets in
`NEXT_PUBLIC_*`. Root `.env.example` documents local fake settings; Compose reads
root `.env`, while Next.js reads its own app directory.

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

## Architecture and API

The static Next.js site calls a single FastAPI service backed by PostgreSQL.
FastAPI serves the same versioned catalogue that its rule engine uses.
See the [system design](docs/architecture/system-design.md),
[ADRs](docs/adr/), [API developer guide](services/api/README.md) and
[live OpenAPI reference](https://buildwise-api-p4yq.onrender.com/docs).
The full pack is available at `GET /api/v1/projects/{id}/export/markdown`.
Only the seeded sample can be read without its browser token.

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

## Operations

### Backend observability

```sh
OTEL_EXPORTER_OTLP_ENDPOINT=http://lgtm:4318 OTEL_TRACES_SAMPLER_ARG=1 \
  docker compose --profile observability up -d --build
```

Grafana runs at <http://localhost:3001> with four provisioned BuildWise dashboards
and five alert rules; OTLP HTTP is at localhost:4318. Both ports are loopback-only.
See the [observability runbook](docs/operations/observability.md) for Grafana Cloud
Free quotas, env-only provisioning, privacy, traffic generation and fault/recovery
demonstrations. Use sampler 0.1 outside short demos. No browser telemetry is added.

### Production deploys

Merges to `main` deploy after CI passes. The
[Deploy production](.github/workflows/deploy-production.yml) workflow builds the
tested commit's static export, triggers that same commit on the existing Render
Free API service, and publishes the export to the existing Cloudflare Pages
Direct Upload project `buildwise`, whose production branch is `main`. The site
can go live while the API is still building, so keep API changes backward compatible.

Set these GitHub Actions secrets:

- `RENDER_DEPLOY_HOOK_URL`: the API service's Deploy Hook from Render Settings.
  Keep native auto-deploy off; this service uses a public Git URL.
- `CLOUDFLARE_API_TOKEN`: an account-scoped token with **Cloudflare Pages: Edit**.
- `CLOUDFLARE_ACCOUNT_ID`: the account hosting the Pages project.

The frontend build uses the `API_BASE_URL` repository variable if set, or the
production Render URL otherwise. Check the workflow run and the Render Deploys
page for the merged commit; then verify the
[production site](https://buildwise-1fy.pages.dev/) and the
[API readiness endpoint](https://buildwise-api-p4yq.onrender.com/ready) return 200.

### Optional keep-warm ping

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
or disable the workflow intentionally to conserve Render hours.

## Contributing and CI

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching, required checks and the
Definition of Done, and [requirement traceability](docs/specs/traceability.md) for
test coverage and known gaps. [CI](.github/workflows/ci.yml) checks the API, web,
real-stack E2E flow and no-paid-AI policy on PRs and pushes to `main`.
Dependabot checks dependencies weekly. Licensed under [MIT](LICENSE).

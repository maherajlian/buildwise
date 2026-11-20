# Deployment spike results

Date: **2026-11-20 UTC**. Scope: blueprint §15 Phase 0/1 and the
[implementation proposal spike](../plan/implementation-proposal.md#8-deployment-proof-of-concept-plan).

## Outcome and live URLs

The static browser → FastAPI → Neon path works publicly. No card, payment-method,
or plan-upgrade prompt appeared. No payment method was supplied, subscription
created/upgraded, paid compute selected, or paid AI service used. Billing-account
audits and telemetry ingestion remain partly **unverified**, as detailed below;
this is not a claim that every provider's account billing page was inspected.

- Frontend: **https://buildwise-1fy.pages.dev/**
- Immutable Pages deployment: https://5c1e1c2c.buildwise-1fy.pages.dev/
- API: **https://buildwise-api-p4yq.onrender.com**
- Liveness: https://buildwise-api-p4yq.onrender.com/health
- Readiness: https://buildwise-api-p4yq.onrender.com/ready

Current Render API commit: `9b555b3709910a3efd66601efc1f93d94fb6ae99`, from
`main` after PR #2's squash merge. The original API deployment and the existing
Pages static export used `1bad006ed43af69ddf88c849601ac02bb525fd89` from
`devin/phase1-foundation`. Pages was not rebuilt for the API branch switch.
This results document was rebased onto `origin/main` on `devin/deployment-spike`.
No application or repository deployment-configuration fixes were necessary.

## Resources, plans and safety controls

| Provider | Resource / configuration | Plan evidence |
|---|---|---|
| Neon | Existing owner-provided pooled database; hostname region `eu-west-2` (London). Ran Alembic against it, without creating a project or changing compute. | Intended **Free**, but actual account plan **unverified**: only a database URL was provided, not Neon management/billing API access. Existing project billing configuration was not changed. |
| Render | `buildwise-api`, service `srv-dc08isd6e07s73c0cu6g`, Docker runtime, Frankfurt; `/health` health check. | Create-service response explicitly returned **`serviceDetails.plan: free`**. No disk, autoscaling, paid instance, Render Postgres, or paid pipeline option requested. Workspace billing details were not audited. |
| Cloudflare Pages | Direct Upload project `buildwise`, assigned `buildwise-1fy.pages.dev`; static files only, no Functions/Worker or other metered resource added. | **Free static Pages** deployment path; no paid plan or subscription selected. Account subscription inspection **unverified**: the Pages-edit token returned HTTP 403 on the read-only subscriptions endpoint. Pages project/deployment responses do not certify an account billing tier. |
| Grafana Cloud | Existing owner-provided OTLP endpoint/authentication configured on Render. No stack or subscription created/changed. | Intended **Grafana Cloud Free**, actual account plan **unverified** with the supplied ingestion credentials. |

Render's `frankfurt` region was selected as a nearby supported region to Neon's
London hostname. Render was created through `POST /v1/services` with an explicit
`plan: free`; its returned plan was checked before proceeding. API creation took
3.409 seconds. Automatic deploy triggers were set to `off` for the spike.

Render configuration:

- Repository: `https://github.com/maherajlian/buildwise`
- Branch: `main` (switched from `devin/phase1-foundation` after PR #2 merged)
- Root directory: `services/api`
- Dockerfile: `./Dockerfile`, context `.` relative to that root
- `APP_ENV=production`, `OTEL_SERVICE_NAME=buildwise-api`
- `CORS_ORIGINS=["https://buildwise-1fy.pages.dev"]`
- `DATABASE_URL`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and
  `OTEL_EXPORTER_OTLP_HEADERS` supplied directly to the provider from secret-bound
  execution environments. Their values were not printed or written to git.
- No `render.yaml`, deploy workflow, new dependency, or application code change.

The empty Pages project was created before Render to discover its assigned
subdomain for exact-origin CORS. The static export was built locally with
`NEXT_PUBLIC_API_BASE_URL=https://buildwise-api-p4yq.onrender.com`, then uploaded
using Wrangler 4.165.0:

```sh
pnpm dlx wrangler@4.165.0 pages project create buildwise --production-branch devin/phase1-foundation
pnpm -C apps/web build
pnpm dlx wrangler@4.165.0 pages deploy apps/web/out --project-name buildwise --branch devin/phase1-foundation --commit-dirty=true
```

The build used the production API URL, not the localhost default. Cloudflare
credentials were bound only in the execution environment; no Git integration,
Workers paid plan, domain purchase, R2 bucket or Pages Functions was configured.

## Neon migration and timings

```text
NEON_FIRST_SELECT_SECONDS=3.054
NEON_ALEMBIC=PASS duration_seconds=3.165
```

`alembic upgrade head` succeeded with the existing migration and pooled URL.
The preliminary SQLAlchemy `SELECT 1` probe disabled psycopg prepared statements
(`prepare_threshold=None`); Alembic itself ran with the unchanged repository
configuration and also succeeded. No prepared-statement incompatibility was
observed, so no speculative production connection setting was added. This is not
a pooled-connection stress test.

| Measurement | Result | Interpretation / limitation |
|---|---|---|
| First Neon connection + `SELECT 1` | **3.054 s** | Includes DNS/TLS/connect/query overhead from this machine. Prior Neon idle/suspension state was not observable, so this is **not a confirmed compute-resume measurement**. |
| Neon Alembic upgrade | **3.165 s** | End-to-end migration invocation after the initial connection probe. |
| Original Render deploy creation → live | **76.357 s** | API timestamps `17:55:00.171605Z` → `17:56:16.528883Z`; includes queue/build/startup, not isolated Docker build time. Deploy `dep-dc08it56e07s73c0d0jg`. |
| Local Next.js export | Approximately **2 s** observed command wall time | Build output: compilation 104 ms; TypeScript 1263 ms; static generation 158 ms. No Cloudflare build was run because this is Direct Upload. |
| Wrangler upload + deploy invocation | **6.042 s** | 52 files, reported asset-upload time **1.50 s**. Includes cached CLI startup. |
| First public `/health` request during initial bring-up | **14.208 s**, HTTP 200 | Initial deployment request; **not** a post-idle cold-start sample. |
| Subsequent public `/ready` request | **0.497 s**, HTTP 200 | Application + real Neon readiness query, measured from this machine. |
| Render wake after >15 min idle | **Not measured** | The service was not left idle for >15 minutes during this run. No always-on guarantee or measured cold-wake latency is claimed. |

## Public verification

HTTP requests against the public Render URL (Python HTTP client, equivalent to
the requested curl probes):

```text
RENDER_VERIFY /health HTTP 200 seconds 14.208 body {"status":"ok"}
RENDER_VERIFY /ready HTTP 200 seconds 0.497 body {"status":"ready"}
```

Browser-origin checks against `/api/v1/projects`:

```text
preflight:     HTTP 200  ACAO=https://buildwise-1fy.pages.dev  0.213 s
project_create: HTTP 201 ACAO=https://buildwise-1fy.pages.dev  0.346 s
foreign_origin: HTTP 400 ACAO absent                        0.198 s
```

All three responses included `X-Correlation-ID`. The successful POST used a
fresh 32-byte browser-compatible capability token and created a draft verification
project containing no personal data. One verification project remains in Neon;
the token was not logged or committed. Project deletion is not implemented yet.

Headless Chromium loaded the production Pages URL and asserted the visible
readiness strings after real cross-origin requests:

```text
PAGES_BROWSER HTTP dashboard ready: PASS
PAGES_BROWSER API responding · Database connected
PAGES_BROWSER 360px no horizontal overflow: PASS
```

Screenshots were inspected and saved outside git:

- `/home/ubuntu/screenshots/buildwise-live-desktop.png`
- `/home/ubuntu/screenshots/buildwise-live-360.png`

### Follow-up: Render deployed from main

After PR #2 was squash-merged, the service branch was changed through
`PATCH /v1/services/{serviceId}` with only `{"branch":"main"}`. The response
again confirmed `plan: free`. A subsequent `POST /v1/services/{serviceId}/deploys`
triggered a deploy of `9b555b3709910a3efd66601efc1f93d94fb6ae99`.
No plan, secret, CORS origin, or Pages configuration was changed, and no
card/payment/upgrade prompt appeared.

```text
RENDER_UPDATE HTTP 200 branch=main plan=free
RENDER_DEPLOY_TRIGGER HTTP 201 deploy_id=dep-dc08l7uk1f9s73859gk0 status=build_in_progress
RENDER_DEPLOY_STATUS status=live commit=9b555b3709910a3efd66601efc1f93d94fb6ae99
createdAt=2026-11-20T17:59:59.467415Z finishedAt=2026-11-20T18:01:02.984874Z
RENDER_MAIN_DEPLOY_SECONDS 63.517
```

After that deploy reached `live`, curl checks and a fresh Chromium visit to the
stable Pages URL produced:

```text
{"status":"ok"}
RENDER_MAIN_HEALTH HTTP 200 seconds 0.250462
{"status":"ready"}
RENDER_MAIN_READY HTTP 200 seconds 0.490784
PAGES_MAIN_BROWSER All systems ready
PAGES_MAIN_BROWSER API responding · Database connected
```

Screenshot inspected: `/home/ubuntu/screenshots/buildwise-main-dashboard.png`.

## Grafana: ingestion unverified

The configured OTLP endpoint/header values were supplied to Render. Successful
API startup does **not** prove export success. A read-only Grafana Cloud
`GET /api/instances` discovery request using the token from the supplied OTLP
authorization header returned HTTP 200 but **zero visible stacks**. Therefore no
authoritative Loki/Tempo query endpoints and tenant IDs were available from that
response. No query endpoint was guessed and no additional scope/token requested.

**Traces, logs and metrics reaching Grafana remain unverified.** The result does
not establish which read scopes the token has. To finish verification, the owner
can inspect the stack's Explore UI for `service.name=buildwise-api` (Loki's
normalised label is commonly `service_name`) or provide query endpoint/tenant
metadata and read-authorized access through the normal secret-management process.
Do not put query credentials in this document.

The live exporter was not deliberately broken in this spike. The existing
`test_otlp_unreachable` unit test covers startup/liveness with an unreachable
exporter; it is not evidence of successful hosted ingestion.

## Remaining risks and follow-up

- D3 was **not triggered**: Render accepted the Free service without requesting
  card/payment/upgrade. No fallback or billing workaround was attempted.
- A complete account billing audit remains unverified for Neon, Cloudflare and
  Grafana with these credential scopes. Existing account plan/overage settings
  were not modified. The operator must review quotas and any existing billing
  arrangements; this spike did not configure spend controls.
- Confirm Render's post-idle wake and Neon compute-resume timings separately;
  the initial bring-up timings above must not be presented as those results.
- Direct Upload requires rebuilding after changing the public API URL. CORS
  currently permits only the stable Pages origin, not immutable deployment or
  preview URLs. The preview URL can load static content but is not an allowed
  API origin.
- The public foundation supports anonymous browser-owned create/list only, not
  account recovery, project deletion, automatic retention or a seeded demo.
- No deployment automation or ADR status changes were made. This establishes
  public core-path feasibility, not completion of all observability/billing
  exit criteria in the original spike proposal.

## Official references consulted

- [Render service API](https://api-docs.render.com/reference/create-service)
- [Render free-service limitations](https://render.com/docs/free)
- [Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/)
- [Pages Free limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Grafana Cloud API / stack discovery](https://grafana.com/docs/grafana-cloud/learn-and-build/developer-resources/api-reference/cloud-api/)
- [Grafana log query authentication](https://grafana.com/docs/grafana-cloud/send-data/logs/authenticate-to-query-logs/)
- [Grafana trace-ingestion verification](https://grafana.com/docs/grafana-cloud/send-data/traces/set-up/verify-ingestion/)

# BuildWise implementation proposal (blueprint §18 first task)

Date: 2026-11-20. Status: reviewed 2026-11-20. Defaults accepted for D1, D2, D4, D5, D6, D7; D3 deferred until the deployment spike shows whether Render asks for a card.

## 1. Proposal
Build BuildWise as a deterministic, zero-paid-AI modular monolith: a static Next.js + TypeScript frontend on Cloudflare Pages, one FastAPI service on Render Free, Neon Free Postgres, and OpenTelemetry exported straight to Grafana Cloud Free. Work proceeds spec-first in small PRs: Phase 0 (skeleton, docs, deployment spike) then Phase 1 (app shell, API, DB, migrations, health/ready, typed client, CI). Feature phases 2-7 follow only after owner review.

Feasibility verdict: a low-traffic public MVP **can run with zero mandatory paid services**, conditional on account sign-up and the deployment spike; it cannot be always-on (Render sleeps after 15 min idle). See `docs/hosting/free-tier-assessment.md`.

## 2. Ambiguities and decisions needing human input
Outcome (2026-11-20): defaults accepted except D3, which stays open until the spike.

| # | Decision | Default |
|---|---|---|
| D1 | Public demo write model without accounts: read-only seeded demo, or anonymous per-browser projects (unguessable owner token, auto-deleted after 30 days)? | Anonymous per-browser projects + read-only seeded demo project |
| D2 | Database: Neon (proposed) vs Supabase (blueprint suggestion)? | Neon |
| D3 | If Render asks for a card at signup: add one (free plan only, never upgraded) or fall back to Python Workers? | Owner adds card, free plan only |
| D4 | Custom domain or provider subdomains (`*.pages.dev`, `*.onrender.com`)? | Provider subdomains |
| D5 | Licence for the public repo? | MIT |
| D6 | Grafana dashboards public (shared snapshot / public dashboard) or screenshots only? | Screenshots + local LGTM demo; public dashboard if free tier allows |
| D7 | Who owns the provider accounts (owner's personal accounts vs a shared org)? | Owner's personal accounts |

## 3. Repository structure
See `docs/architecture/repository-structure.md`.

## 4. Requirements
`docs/specs/functional-requirements.md` (FR-001..FR-023) and `docs/specs/non-functional-requirements.md` (NFR, SEC, OBS).

## 5. Architecture diagram
`docs/architecture/system-design.md`.

## 6. ADRs
- `docs/adr/0001-modular-monolith.md`
- `docs/adr/0002-no-paid-runtime-ai.md`
- `docs/adr/0003-hosting-platform.md`
- `docs/adr/0004-observability.md`

## 7. Free-tier assessment
`docs/hosting/free-tier-assessment.md` (verified 2026-11-20, sources linked).

## 8. Deployment proof-of-concept plan
Goal: prove the blueprint §12 spike with the smallest possible app, before feature work.

| Step | Action | Pass criterion |
|---|---|---|
| 1 | Minimal FastAPI with `/health`, `/ready` (DB `SELECT 1`), one `spike_items` table via Alembic | Runs locally with `docker compose up` |
| 2 | Minimal Next.js static export page calling `/health` and listing `spike_items` | Builds with `output: 'export'` |
| 3 | Create Neon project; set `DATABASE_URL` in Render (never in git) | `alembic upgrade head` succeeds against Neon |
| 4 | Deploy API to Render Free from `services/api/Dockerfile` | `curl https://<api>.onrender.com/health` → 200; `/ready` → 200 |
| 5 | Deploy frontend to Cloudflare Pages via Git integration | Page loads at `*.pages.dev` |
| 6 | Set `CORS_ORIGINS` to the Pages origin | Browser call succeeds; call from another origin is blocked |
| 7 | Set Grafana OTLP endpoint/headers in Render | One trace, metric and log visible in Grafana Cloud |
| 8 | Measure cold start (after >15 min idle) and Neon resume | Timings recorded in the assessment |
| 9 | Kill telemetry endpoint (bad URL) | API still starts and serves |
| 10 | Audit billing pages of every provider | Free plan, no payment subscription, recorded with date |

Output: updated assessment with measured numbers, ADR-0003 moved to Accepted (or revised), spike code kept as the Phase 1 starting point.

## 9. Owner actions
1. Create free accounts: Cloudflare, Render, Neon, Grafana Cloud (sign in with GitHub where offered).
2. Connect the `buildwise` repo to Render and Cloudflare Pages (GitHub app install).
3. Provide as secrets (never committed): Neon `DATABASE_URL`, Grafana OTLP endpoint + auth header, and a Render API key and Cloudflare API token if deploys should run from CI.
4. Answer D1-D7 or accept the defaults.

## 10. Agents
Phase 0/1 is sequential and small enough for one Devin session. From Phase 2, backend modules and frontend screens can run as 2-3 parallel sessions against the agreed OpenAPI contract.

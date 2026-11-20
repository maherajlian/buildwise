# ADR-0003: Frontend, backend and database hosting

- Status: Proposed (confirmed or revised by the deployment spike)
- Date: 2026-11-20
- Evidence: `docs/hosting/free-tier-assessment.md` (verified 2026-11-20)

## Decision
| Component | Choice | Key free-tier facts | Accepted limitation |
|---|---|---|---|
| Frontend | Next.js static export on **Cloudflare Pages** | Static requests unlimited; 500 builds/month; no card to start | No SSR / Server Actions / Next API routes in MVP |
| API | FastAPI Docker service on **Render Free** | 750 instance-hours/month; sleeps after 15 min idle, ~1 min wake | Cold starts; card may be requested at signup |
| Database | **Neon Free** Postgres | 1 GB/project, 100 CU-hours/month, no card, scales to zero after 5 min | Small storage; brief compute resume on first query |
| Telemetry | **Grafana Cloud Free**, OTLP direct from API | 10k active series, 50 GB logs, 50 GB traces, 14-day retention, no card | Telemetry gaps while API sleeps |
| CI | **GitHub Actions**, public repo, standard runners | Free for public repos | Keep jobs lean; no larger runners |

Neon replaces the blueprint's suggested Supabase because Supabase Free pauses projects after a week of inactivity, has 500 MB, needs the IPv4 pooler from Render, and its no-card status for Free was not verifiable; Neon states no card, never pauses projects (compute only scales to zero), and gives 1 GB. Supabase stays the documented fallback.

## Alternatives considered
- **Cloudflare Python Workers for the API**: 10 ms CPU/request on Free, Pyodide runtime, sync SQLAlchemy only, Alembic/OTel compatibility unverified. Rejected for MVP; revisit if Render becomes unavailable.
- **Next.js on Workers via OpenNext**: viable but spends the 100k/day dynamic request and CPU budget; only if static export is insufficient.
- **Render Free Postgres**: expires 30 days after creation. Rejected.
- **Koyeb / Fly.io**: card required (Koyeb pre-auth hold; Fly trial only). Rejected as mandatory dependencies.
- **Vercel Hobby**: possible commercial-use restriction; not needed given Pages.

## Consequences
- The public demo is "best effort": first request after idle can take ~1 min (frontend shows a "waking API" state).
- No service requires a card except possibly Render's account verification; if Render insists on a card, the owner decides (see proposal decision D3) — no paid plan is ever selected.

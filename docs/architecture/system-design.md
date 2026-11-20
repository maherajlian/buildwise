# System design (initial)

Status: draft v0.1 (2026-11-20). Hosting targets are proposals pending the deployment spike (ADR-0003).

## Logical architecture

Phase 3 backend derives versioned signals from discovery and requirements, with
explicit overrides in `recommendation_inputs`. Its pure scoring engine sums matching
catalogue rule weights and breaks ties by entry id. Generation performs no network
calls and stores no result timestamps; canonical signal values produce a SHA-256
fingerprint. Evidence retains field paths and short excerpts. AI text only creates
a note: only explicit `ai_layer=required` enables optional cost-dependent candidates.
The public catalogue endpoint serves the same startup-validated catalogue used by
the engine. Project endpoints reuse browser-token ownership and public read-only
sample access. The Architecture UI is deferred.

```mermaid
flowchart TD
  B[Browser] -->|HTTPS| W[Next.js static frontend\nCloudflare Pages]
  B -->|HTTPS JSON REST /api/v1| A[FastAPI modular monolith]
  subgraph A [FastAPI modular monolith]
    D[Discovery] --- R[Recommendation rules engine]
    R --- S[Specification generator]
    S --- P[Task planner]
    P --- X[Export service]
    H[/health /ready/]
  end
  R -->|reads| C[(Versioned technology\ncatalogue in API package)]
  A -->|SQLAlchemy + Alembic| DB[(PostgreSQL\nfree tier)]
  A -->|OTLP/HTTP, batched| G[Grafana Cloud Free\nMetrics · Logs · Traces]
  A -.->|local fallback| L[Local LGTM via Docker Compose]
```

## Deployment architecture (proposed)

| Component | Proposed host | Why |
|---|---|---|
| Frontend | Next.js `output: 'export'` static site on Cloudflare Pages | No server runtime needed; avoids Next.js-on-Workers adapter limits; unlimited static requests on free plan (to be verified). |
| API | FastAPI container on Render free web service (fallback: see assessment) | Runs standard CPython + SQLAlchemy + OTel without adaptation; sleeps when idle (documented). |
| Database | Supabase Free or Neon Free Postgres | Managed Postgres; pause/size limits documented. |
| Telemetry | OTel SDK in the API exporting OTLP/HTTP directly to Grafana Cloud | No extra collector service to host; collector only in the local profile. |
| CI/CD | GitHub Actions (public repo) | Free minutes for public repos. |

The browser calls the API directly (CORS restricted to the Pages origin). No secrets live in the frontend.

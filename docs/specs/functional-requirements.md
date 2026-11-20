# Functional requirements

Status: draft v0.1 (2026-11-20). Priority: P0 = first public release, P1 = after MVP is stable.
Source: BuildWise blueprint sections 3, 4, 7, 14. Each P0 requirement must map to ≥1 task, ≥1 acceptance criterion and ≥1 automated test (see `docs/specs/traceability.md`, created in Phase 1).

| ID | Pri | Requirement | Acceptance criteria (initial) |
|---|---|---|---|
| FR-001 | P0 | Create, view, edit and delete a project (name, description, status). | AC-001: POST/GET/PATCH/DELETE `/api/v1/projects` behave per OpenAPI; invalid input returns 422 with the standard error object. |
| FR-002 | P0 | List projects with pagination. | AC-002: `limit`/`cursor` params; default page size 20, max 100. |
| FR-003 | P0 | Guided, multi-step discovery questionnaire (problem, users, goals, constraints, data sensitivity, integrations, success metrics, assumptions, open questions). | AC-003: discovery can be saved partially and resumed; each step validates server-side. |
| FR-004 | P0 | Generate a structured project brief / PRD from discovery using templates and rules only. | AC-004: same discovery + template version → byte-identical output; no network call made during generation. |
| FR-005 | P0 | Rule-based technology recommendations per category (frontend, backend, database, cache/queue, auth, hosting, CI/CD, observability, integrations, optional AI layer). | AC-005: each recommendation has rationale tied to inputs, alternatives, trade-offs, complexity, operational burden, cost category, change conditions and `catalogue_version`. |
| FR-006 | P0 | Versioned, curated technology catalogue stored in the repo (`data/technology-catalogue/`). | AC-006: catalogue validated against a JSON schema in CI; every entry has `last_reviewed`. |
| FR-007 | P0 | Optional AI/model layer recommendation is clearly marked optional and cost-dependent, never default. | AC-007: rules never select the AI layer unless discovery explicitly requires it; UI labels it "optional, may incur cost". |
| FR-008 | P0 | Generate a technical design document from template. | AC-008: includes architecture overview, data model outline, API outline, security, deployment and observability sections. |
| FR-009 | P0 | Generate user stories with acceptance criteria from requirements. | AC-009: every P0 requirement in a project yields ≥1 story with ≥1 criterion. |
| FR-010 | P0 | Generate a task breakdown (epics/tasks) with priorities and dependencies. | AC-010: dependency cycles rejected with 409/422; tasks have status Backlog/Ready/In progress/Review/Done. |
| FR-011 | P0 | Edit any generated artefact, story or task; edits are versioned. | AC-011: PATCH increments `version`; regeneration never silently overwrites user edits (prompt or new version). |
| FR-012 | P0 | Export the project pack as Markdown. | AC-012: `GET /export/markdown` returns a readable document (or zip) containing brief, PRD, design, recommendations, stories, tasks. |
| FR-013 | P0 | Seeded, clearly-labelled illustrative demo project ("Restaurant Booking & Customer Engagement SaaS"). | AC-013: available on first load without an account; labelled "illustrative". |
| FR-014 | P0 | Dashboard: recent projects, stage, outstanding requirements, open tasks, recent artefacts, quick-start. | AC-014: renders with seed data; empty states for a new user. |
| FR-015 | P0 | Project workspace tabs: Overview, Discovery, Architecture, Specifications, Tasks, Testing, Operations. | AC-015: each tab reachable by keyboard and deep link. |
| FR-016 | P0 | Health (`/health`, liveness) and readiness (`/ready`, checks DB) endpoints. | AC-016: `/ready` returns 503 when DB is unreachable. |
| FR-017 | P0 | Observability demo page showing BuildWise's own health and operational metrics (or links to public Grafana dashboards). | AC-017: page works even if Grafana is unavailable (shows health only). |
| FR-018 | P0 | Technology catalogue browser and engineering guides pages (static content). | AC-018: catalogue page reads the same versioned data the engine uses. |
| FR-019 | P1 | Test-plan, deployment-plan, observability-plan, risk register and SLO generation. | — |
| FR-020 | P1 | Optional accounts with project ownership. | — |
| FR-021 | P1 | GitHub issue export with a user-supplied token, explicit permission, token never stored. | — |
| FR-022 | P1 | OpenAPI import for integration planning. | — |
| FR-023 | P1 | Import/export of a complete project pack (JSON). | — |

# ADR-0001: Modular monolith for the MVP

- Status: Proposed
- Date: 2026-11-20

## Context
BuildWise's MVP is CRUD plus deterministic generation (rules, templates, export). There is no real asynchronous workload, traffic is demo-scale, and every extra deployable costs free-tier quota and operational effort.

## Decision
Ship one FastAPI service containing the discovery, recommendations, specifications, planning, operations and exports modules (`services/api/app/modules/*`), one static Next.js frontend, and one PostgreSQL database. Modules talk through in-process Python interfaces, own their own tables, and never import each other's ORM models directly. No message queue or separate worker.

## Consequences
- One API deploy, one DB connection pool, simple local setup and tracing.
- Module boundaries are enforced by code review and an import-linter rule in CI, not by the network.
- A worker is reconsidered only when a measured operation exceeds the request budget (e.g. large exports); that change needs a new ADR and human approval.

## Alternatives considered
- Microservices per module: rejected (premature, multiplies hosting and quota use).
- Serverless functions per endpoint: rejected for MVP (cold starts per function, harder local parity).

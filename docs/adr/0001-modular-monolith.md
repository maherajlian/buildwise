# ADR-0001: Modular monolith for the MVP

- Status: Accepted
- Date: 2026-11-20

## Context
BuildWise's MVP is CRUD plus deterministic generation (rules, templates, export). There is no real asynchronous workload, traffic is demo-scale, and every extra deployable costs free-tier quota and operational effort.

## Decision
Ship one FastAPI service containing discovery, recommendations, specifications,
planning, operations and workbench routes (`services/api/app/modules/`), one
static Next.js frontend and one PostgreSQL database. Modules primarily own their
tables and use in-process functions. The workbench composes read-only views and
exports across modules. No message queue or separate worker.

## Consequences
- One API deploy, one DB connection pool, simple local setup and tracing.
- Module boundaries are maintained by code review and tests, not by the network.
- A worker is reconsidered only when a measured operation exceeds the request budget (e.g. large exports); that change needs a new ADR and human approval.

## Alternatives considered
- Microservices per module: rejected (premature, multiplies hosting and quota use).
- Serverless functions per endpoint: rejected for MVP (cold starts per function, harder local parity).

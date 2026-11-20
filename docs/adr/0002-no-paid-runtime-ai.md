# ADR-0002: No paid AI inference at runtime

- Status: Proposed
- Date: 2026-11-20

## Context
The blueprint makes zero paid inference an absolute constraint: the hosted app and CI must not call or require a paid model API.

## Decision
All "intelligence" is deterministic: a curated, versioned technology catalogue (`data/technology-catalogue/`), transparent scoring rules, decision trees, and Jinja2/Markdown templates. Every generated output records `catalogue_version` / `template_version` so it is reproducible. Scores are presented as a decision aid, not a benchmark.

Enforcement:
- No LLM SDK in any lockfile; a CI job fails on imports or dependencies such as `openai`, `anthropic`, `google-generativeai`, `litellm`, `langchain*`, `@ai-sdk/*`.
- No env var or settings field for model API keys exists in the hosted config.
- Generation endpoints are tested to make no outbound network calls.

Local inference (e.g. Ollama) may be documented later as an opt-in, developer-only extension that the hosted app never calls.

## Consequences
- Outputs are predictable, testable and free; quality depends on catalogue and template curation, which is version-controlled and reviewed.
- Free-text understanding is limited to structured questionnaire inputs; this is described accurately ("deterministic engineering assistant").

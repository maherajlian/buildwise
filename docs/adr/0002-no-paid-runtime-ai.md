# ADR-0002: No paid AI inference at runtime

- Status: Accepted
- Date: 2026-11-20

## Context
The blueprint makes zero paid inference an absolute constraint: the hosted app and CI must not call or require a paid model API.

## Decision
Generation is deterministic: a curated catalogue packaged with the
recommendations module, transparent scoring rules, and Python/Markdown
templates. Recommendation results and specification context record catalogue
and rules versions; the templates are versioned in Git. Scores are a decision
aid, not a benchmark.

Enforcement:
- No LLM SDK in any lockfile; a CI job fails on imports or dependencies such as `openai`, `anthropic`, `google-generativeai`, `litellm`, `langchain*`, `@ai-sdk/*`.
- No env var or settings field for model API keys exists in the hosted config.
- Generation endpoints are tested to make no outbound network calls.

An explicit AI-layer requirement can show optional, potentially paid
candidates in a recommendation. BuildWise has no runtime integration or
switch to invoke those providers. Any paid upgrade is outside the MVP.

## Consequences
- Outputs are predictable, testable and free; quality depends on catalogue and template curation, which is version-controlled and reviewed.
- Free-text understanding is limited to structured questionnaire inputs; this is described accurately ("deterministic engineering assistant").

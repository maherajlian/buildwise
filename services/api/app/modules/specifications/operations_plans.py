import re
from typing import Any

from app.core.operational_rules import generate_slos, requirement_text


def plan_layouts(context: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
    name = context["name"]
    stack = context.get("technologies", {})
    signals = context.get("signals", {})
    answers = context.get("discovery", {})
    details = context.get("technology_details", {})
    hosting = stack.get("hosting", "TODO: choose a hosting target")
    backend = stack.get("backend") or stack.get("api")
    database = stack.get("database")
    integrations = sorted(
        set(answers.get("integrations", []) + signals.get("integrations", []))
    )
    nfrs = sorted(
        (r for r in context.get("requirements", []) if r["type"] == "non_functional"),
        key=lambda r: (r.get("priority", "P1"), r["title"], str(r.get("id", ""))),
    )
    nfr = "\n".join(f"- {requirement_text(r)}" for r in nfrs) or (
        "TODO: agree measurable reliability, latency and privacy NFRs."
    )
    stack_text = "\n".join(f"- {k}: {v}" for k, v in sorted(stack.items())) or (
        "TODO: select the stack."
    )
    host_details = details.get("hosting", {})
    cost_note = host_details.get(
        "cost_note", "Pricing/free-tier claims require verification."
    )
    limits = "\n".join(f"- {value}" for value in host_details.get("constraints", []))
    host_notes = (
        f"Recommended target: {hosting}.\n{limits}\n"
        f"{host_details.get('operational_burden', '')}\n"
        f"{cost_note}"
    )
    if "free" in hosting.lower() or host_details.get("cost_category") == "free-tier":
        host_notes += (
            "\nVerify free-tier sleeping/cold starts, quotas, ephemeral storage, "
            "connection limits and regional availability. Keep-warm probes only "
            "where provider terms allow; alert on quotas and document the paid "
            "upgrade path."
        )
    else:
        host_notes += (
            "\nVerify capacity, billing limits, persistence, region and "
            "recovery options; "
            "do not assume this target has a free tier."
        )

    env = [
        "APP_ENV — distinguish staging and production.",
        f"OTEL_SERVICE_NAME — stable service identity for {name}.",
        "OTEL_EXPORTER_OTLP_ENDPOINT — collector URL; verify signal paths and TLS.",
        "OTEL_EXPORTER_OTLP_HEADERS — secret collector credentials, server-side only.",
        "OTEL_TRACES_SAMPLER / OTEL_TRACES_SAMPLER_ARG — parent-based ratio sampling; "
        "review volume and privacy against NFRs.",
    ]
    if database:
        env.append(
            f"DATABASE_URL — private {database} connection string; "
            "TLS and least privilege."
        )
    auth = signals.get("auth_needs", "basic" if stack.get("auth") else "none")
    if auth != "none":
        env += [
            "AUTH_SECRET — signing/session secret if required by "
            f"{stack.get('auth', auth)}; "
            "generate securely and plan rotation.",
            "AUTH_ISSUER / AUTH_AUDIENCE — validate issuer and intended resource.",
        ]
        if auth == "enterprise_sso":
            env.append(
                "AUTH_CLIENT_ID / AUTH_CLIENT_SECRET — SSO registration "
                "and private client credential."
            )
    if backend and stack.get("frontend"):
        env.append(
            "CORS_ORIGINS / public API base URL — allow exact frontend origins; "
            "only the non-secret API URL may enter browser builds."
        )
    used: set[str] = set()
    for integration in integrations:
        slug = (
            re.sub(r"[^A-Z0-9]+", "_", integration.upper()).strip("_")[:60]
            or "EXTERNAL"
        )
        key = f"INTEGRATION_{slug}_API_KEY"
        suffix = 2
        while key in used:
            key = f"INTEGRATION_{slug}_{suffix}_API_KEY"
            suffix += 1
        used.add(key)
        env.append(
            f"{key} — proposed credential name for {integration}; "
            "verify vendor-specific "
            "key/webhook requirements, scopes and rotation. Never commit a value."
        )
    if signals.get("background_jobs") in (True, "yes"):
        env.append(
            "QUEUE_URL — private worker/broker connection for "
            f"{stack.get('cache_queue', 'the selected queue')}."
        )
    environment = (
        "Proposed variable names; adapt to the selected libraries:\n"
        + "\n".join(f"- {v}" for v in env)
    )
    secrets = (
        f"Store {name} runtime secrets in {hosting}'s secret store and "
        "CI credentials in protected environment secrets or short-lived "
        "workload identity. Separate staging and production; grant least "
        "privilege, rotate keys and audit access. Never commit .env files "
        "or bake secrets into images, static assets, NEXT_PUBLIC_* variables, "
        "logs or exports. This plan contains names only, never provisioned values."
    )
    health = (
        f"For {backend}: implement /health as a cheap process-liveness check, not a "
        "dependency probe. Implement /ready with bounded timeouts; return 503 when a "
        "required dependency is unavailable. Route traffic only to ready instances."
        if backend
        else "For the static frontend, probe the deployed page and an asset. No API is "
        "selected: /health and /ready apply only if a backend is introduced."
    )
    if database:
        health += (
            f" Readiness should verify a lightweight {database} "
            "connection/query and compatible schema."
        )
    if integrations:
        health += (
            " Distinguish optional vendor outages from required dependencies; do not "
            "make liveness depend on " + ", ".join(integrations) + "."
        )
    release = (
        f"Proposed pipeline for {name} using "
        f"{stack.get('ci_cd', 'the chosen CI provider')}:\n"
        "1. Lint/typecheck and unit tests.\n"
        "2. Integration tests against disposable dependencies; API contract "
        "and end-to-end tests for acceptance criteria (mark not applicable "
        "only with a review reason).\n"
        "3. Security scan of dependencies, source and secrets; enforce "
        "NFR load/performance budgets.\n"
        "4. Build/version immutable artefacts, review approvals and back up state.\n"
        "5. Migrate using an expand/contract change compatible with the "
        "previous release "
        "(skip migrations only when no persistent store is used).\n"
        f"6. Deploy to staging then {hosting}; smoke test critical journeys and "
        "/health + /ready for any API; verify logs/metrics before shifting traffic.\n"
        "7. Rollback on readiness, error-budget or data-integrity regression; "
        "record evidence "
        "and release sign-off. These checks are recommendations, not executed results."
    )
    rollback = (
        f"For {hosting}, retain the previous immutable release and configuration; stop "
        "rollout on sustained readiness/error/latency regression and restore "
        "traffic to the last healthy version. Test restore backups and "
        "schema compatibility first; "
        "do not blindly reverse destructive migrations. Assign a release owner and "
        "record rollback/recovery evidence."
    )
    logs = (
        f"Instrument {name} "
        f"({backend or stack.get('frontend', 'stack to be selected')}) "
        "with structured JSON logs: UTC timestamp, severity, "
        "service/environment/version, "
        "event, route, status, duration, correlation ID and trace/span IDs. Redact "
        "credentials, authorization headers and personal data; restrict access and "
        "set retention from privacy NFRs. Never use user IDs as unbounded "
        "metric labels."
    )
    metrics = (
        "Measure request rate, errors, latency histograms (p95/p99), saturation and "
        "health/readiness probes. Define eligible requests, windows and dashboards "
        "before claiming SLO compliance. For a static UI, include "
        "page/asset availability "
        "and real-user web vitals.\nProject NFR instrumentation budgets:\n" + nfr
    )
    if database:
        metrics += (
            f"\nTrack {database} query latency, pool exhaustion and connection errors."
        )
    if signals.get("background_jobs") in (True, "yes"):
        metrics += (
            "\nTrack queue depth, job age, retries, failures and completion deadlines."
        )
    if signals.get("realtime") in (True, "yes"):
        metrics += "\nTrack event delivery delay, reconnects and data freshness."
    tracing = (
        f"Use OpenTelemetry instrumentation for {backend or 'the selected services'}"
        + (f" and {database} queries" if database else "")
        + "; propagate W3C trace context across HTTP/worker boundaries. "
        "Export via OTLP with bounded queues/timeouts. Set parent-based "
        "sampling and attribute redaction "
        "to satisfy the NFR latency, cost and privacy budgets above. Do not propagate "
        "sensitive baggage to third parties."
    )
    if integrations:
        tracing += " Instrument outbound calls to " + ", ".join(integrations) + "."
    slos = generate_slos(context, signals)
    candidates = "Suggested, not adopted or measured guarantees:\n\n" + "\n\n".join(
        f"### {s['name']}\nTarget: {s['target']} over {s['window']}.\n"
        f"SLI: {s['sli']}\nSource: {s['rationale']}\nAlert: {s['alert']}"
        for s in slos
    )
    alerts = (
        "Use the SLO candidates' multi-window error-budget burn rates; page on "
        "sustained fast burn and ticket slower burn. Alert on readiness failures, "
        "saturation and provider quota/cost limits. Assign an owner, severity and "
        "runbook, tune thresholds with measured traffic and avoid paging on a single "
        "cold start. These alerts are proposed, not configured."
    )
    runbook = [
        f"For {name}, record incident time, affected route, release "
        "and correlation ID; "
        "inspect sanitized logs and distributed traces before changing configuration.",
        f"Hosting ({hosting}): distinguish a cold start/sleep from a crash; "
        "check provider "
        "status, deploy logs, resource quotas and allowed keep-warm policy.",
        "Probe /health then /ready for an API; a healthy process with readiness 503 "
        "suggests required dependency/configuration failure, not successful recovery.",
    ]
    if database:
        runbook.append(
            f"Database ({database}): on /ready 503 check reachability, TLS, "
            "credentials, connection quota/pool and migration compatibility; "
            "never paste DATABASE_URL into diagnostics."
        )
    if backend and stack.get("frontend"):
        runbook.append(
            "Browser-only failure: check exact CORS origins and the baked-in "
            "API URL; rebuild static assets after public configuration changes."
        )
    if auth != "none":
        runbook.append(
            f"Auth ({stack.get('auth', auth)}): check issuer/audience, key rotation, "
            "expiry and ownership; a lost browser token may lose access, so follow "
            "the chosen auth recovery policy without logging credentials."
        )
    for integration in integrations:
        runbook.append(
            f"Integration ({integration}): inspect vendor status, request IDs, "
            "rate limits and credential scopes; use bounded retries, timeout, "
            "fallback/queue and deduplication before replaying failed requests."
        )
    if signals.get("background_jobs") in (True, "yes"):
        runbook.append(
            f"Workers ({stack.get('cache_queue', 'queue to be selected')}): "
            "inspect backlog/dead letters and worker health; replay idempotently."
        )
    runbook.append(
        "Contain or rollback using the deployment plan; verify probes and a "
        "critical journey after recovery, notify stakeholders and record a review."
    )
    response = "\n".join(f"{i}. {item}" for i, item in enumerate(runbook, 1))
    return {
        "deployment": [
            ("Target stack", stack_text),
            ("Release", release),
            ("Rollback", rollback),
            ("Hosting target and limitations", host_notes),
            ("Environment variables", environment),
            ("Secret management", secrets),
            ("Health and readiness", health),
            ("Incident runbook", response),
        ],
        "observability": [
            ("Stack", stack_text),
            ("Signals", logs),
            ("Service objectives", nfr),
            ("Response", response),
            ("Metrics", metrics),
            ("Distributed tracing", tracing),
            ("SLO candidates", candidates),
            ("Alert recommendations", alerts),
            ("Health and readiness", health),
            ("Telemetry configuration", environment),
        ],
    }

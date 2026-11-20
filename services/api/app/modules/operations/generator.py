import csv
import hashlib
import io
import json
import re
from typing import Any

from app.core.operational_rules import generate_slos, requirement_text
from app.modules.operations.schemas import OperationsRead

SECURITY = re.compile(
    r"security|auth|privacy|\bPII\b|GDPR|encrypt|isolation|consent", re.I
)
PERFORMANCE = re.compile(
    r"latency|throughput|load|users|scale|performance|\bp95\b", re.I
)
COST = re.compile(r"\bcosts?\b|\bpric(?:e|es|ing)\b|\bbudget\b|\bSMS\b", re.I)
COMPLIANCE = re.compile(r"GDPR|compliance|regulat|\bDPA\b", re.I)
NUMBERS = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ms|milliseconds?|seconds?|s\b|users|requests?/?s|rps)", re.I
)
HEADER = (
    "Generated deterministically from requirements; suggestions require human review."
)


def generation_key(*parts: str) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()


def risk_controls(
    category: str,
    source: str,
    subject: str,
    signals: dict[str, Any],
    integration_count: int,
    requirement: dict[str, Any] | None,
) -> tuple[str, int, int]:
    controls = {
        "technical": "Prototype the failure path and add a regression test "
        "before release.",
        "security": "Threat model trust boundaries; add authorization and cross-owner "
        "access tests, least-privilege controls and secret rotation.",
        "operational": "Document recovery steps, assign an incident owner "
        "and test alerts.",
        "delivery": "Assign an owner, track the dependency and review it "
        "at each milestone.",
        "compliance": "Create a personal-data map; review the DPA, retention/deletion "
        "policy and access logging with the accountable privacy owner.",
        "cost": "Estimate usage-based costs; set usage caps and budget alerts, "
        "including SMS spend, and review provider pricing before launch.",
    }
    actions = {
        "integrations": f"For {subject}: configure timeouts, bounded retries "
        "with backoff, "
        "a fallback or durable queue, contract tests and vendor status monitoring.",
        "assumptions": f"Before build, assign a validation owner to test '{subject}' "
        "with stakeholders or a prototype; record evidence and a go/no-go decision.",
        "open_questions": f"Assign a decision owner for '{subject}'; "
        "resolve and record "
        "the decision before the next implementation milestone.",
        "constraints": f"Turn '{subject}' into a release acceptance check and review "
        "it with the constraint owner before implementation.",
        "hosting": f"For {subject}: verify cold-start/sleep behavior and free-tier "
        "quotas; use keep-warm probes only where provider terms permit, set quota "
        "alerts and document an upgrade path before capacity is exhausted.",
        "ops": "Prefer managed services; rehearse a recovery runbook, configure "
        "actionable alerting and assign a primary and backup incident owner.",
        "performance_nfr": f"Load test '{subject}' with representative concurrency; "
        "enforce its latency/throughput budget in CI and profile bottlenecks.",
        "security_nfr": f"Threat model '{subject}' and enforce it with authorization, "
        "cross-owner and abuse-case regression tests before deployment.",
    }
    mitigation = " ".join(filter(None, [actions.get(source), controls[category]]))
    likelihood = {"constraints": 2, "integrations": 2, "hosting": 4, "ops": 4}.get(
        source, 3
    )
    if source == "integrations" and integration_count >= 3:
        likelihood += 1
    if signals.get("ops_capability", "low") == "low" and source in (
        "integrations",
        "security_nfr",
        "performance_nfr",
    ):
        likelihood += 1
    if signals.get("ops_capability") == "high" and category in (
        "technical",
        "operational",
    ):
        likelihood -= 1
    impact = {"security": 4, "compliance": 5, "operational": 4, "delivery": 4}.get(
        category, 3
    )
    priority = requirement.get("priority") if requirement else None
    if priority == "P0":
        impact = 5
    elif priority == "P2" and category != "compliance":
        impact -= 1
    if signals.get("scale") == "large":
        impact += 1
    return mitigation, max(1, min(5, likelihood)), max(1, min(5, impact))


def generate(
    context: dict[str, Any], signals: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    answers = context.get("discovery", {})
    requirements = sorted(
        context.get("requirements", []),
        key=lambda r: (
            r.get("priority", "P1"),
            r["title"],
            str(r.get("id", "")),
        ),
    )
    technologies = context.get("technologies", {})
    integration_count = len(
        set(answers.get("integrations", []) + signals.get("integrations", []))
    )
    tests: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []

    def test(
        category: str,
        title: str,
        description: str,
        rationale: str,
        requirement: dict[str, Any] | None = None,
    ) -> None:
        tests.append(
            dict(
                generation_key=generation_key(
                    "test",
                    category,
                    str(requirement.get("id") or requirement["title"])
                    if requirement
                    else title,
                    description if category in ("e2e", "manual_acceptance") else "",
                ),
                category=category,
                title=title[:200],
                description=description,
                rationale=rationale,
                requirement_id=requirement.get("id") if requirement else None,
                status="proposed",
                result_notes="",
                executed_at=None,
                executed_by=None,
            )
        )

    def risk(
        title: str,
        description: str,
        category: str,
        rationale: str,
        requirement: dict[str, Any] | None = None,
        source: str = "risks",
    ) -> None:
        category = (
            "compliance"
            if COMPLIANCE.search(description)
            else "cost"
            if COST.search(description)
            else category
        )
        mitigation, likelihood, impact = risk_controls(
            category, source, title, signals, integration_count, requirement
        )
        risks.append(
            dict(
                generation_key=generation_key(
                    "risk",
                    source,
                    str(requirement.get("id") or requirement["title"])
                    if requirement
                    else title,
                ),
                title=title[:200],
                description=description,
                category=category,
                likelihood=likelihood,
                impact=impact,
                mitigation=mitigation,
                owner="",
                status="open",
                rationale=rationale,
                requirement_id=requirement.get("id") if requirement else None,
            )
        )

    for req in requirements:
        rationale = f"Requirement: {req['title']} ({req.get('priority', 'P1')})."
        if req["type"] == "functional":
            test(
                "unit",
                f"Unit: {req['title']}",
                f"Verify domain rules and error paths: {requirement_text(req)}",
                rationale,
                req,
            )
            test(
                "integration",
                f"Integration: {req['title']}",
                f"Verify persistence and component boundaries: {requirement_text(req)}",
                rationale,
                req,
            )
        for criterion in req.get("acceptance_criteria", []):
            category = (
                "manual_acceptance"
                if req.get("priority") == "P2" or req.get("status") == "deferred"
                else "e2e"
            )
            test(
                category,
                f"Acceptance: {req['title']}",
                criterion,
                f"{rationale} Acceptance criterion: {criterion}",
                req,
            )
        text = requirement_text(req)
        if req["type"] == "non_functional":
            if SECURITY.search(text):
                test("security", f"Security: {req['title']}", text, rationale, req)
                risk(
                    f"Security control failure: {req['title']}",
                    text,
                    "security",
                    rationale,
                    req,
                    source="security_nfr",
                )
            if PERFORMANCE.search(text):
                measurements = ", ".join(NUMBERS.findall(text))
                test(
                    "performance",
                    f"Load: {req['title']}",
                    f"Measure latency/throughput under load: {text}. "
                    f"Budgets: {measurements or 'agree measurable budgets'}.",
                    rationale,
                    req,
                )
                risk(
                    f"Performance budget missed: {req['title']}",
                    text,
                    "technical",
                    rationale,
                    req,
                    source="performance_nfr",
                )
            if COST.search(text) and not (
                SECURITY.search(text) or PERFORMANCE.search(text)
            ):
                risk(
                    f"Usage cost exceeds budget: {req['title']}",
                    text,
                    "cost",
                    rationale,
                    req,
                )
    if technologies.get("backend") or technologies.get("api"):
        test(
            "api_contract",
            "API contract compatibility",
            "Validate request/response schemas, errors and authorization "
            "against the published contract.",
            "Recommended backend/API: "
            f"{technologies.get('backend') or technologies.get('api')}.",
        )
    accessibility = [
        r
        for r in requirements
        if re.search(r"accessib|WCAG|screen reader", requirement_text(r), re.I)
    ]
    users = " ".join(answers.get("target_users", []) + answers.get("user_needs", []))
    if (
        technologies.get("frontend")
        or accessibility
        or re.search(r"web|accessib|screen reader", users, re.I)
    ):
        reason = (
            f"Requirement: {accessibility[0]['title']}."
            if accessibility
            else f"Recommended frontend: {technologies.get('frontend', 'none')}; "
            f"discovery users/needs: {users}."
        )
        test(
            "accessibility",
            "Accessible user journeys",
            "Check keyboard navigation, focus, labels, contrast and "
            "screen-reader announcements against WCAG 2.2 AA.",
            reason,
            accessibility[0] if accessibility else None,
        )
    auth = signals.get("auth_needs", "none")
    if auth != "none":
        test(
            "security",
            "Authentication and ownership",
            "Check unauthenticated, cross-owner and privilege-escalation "
            "requests are rejected.",
            f"Recommendation signal auth_needs={auth}.",
        )
    for field in ("constraints", "integrations", "risks"):
        for answer in answers.get(field, []):
            if SECURITY.search(answer) or field == "integrations":
                test(
                    "security",
                    f"Security review: {answer}",
                    "Validate least privilege, secret handling, privacy "
                    f"and failure behavior: {answer}",
                    f"Discovery {field}: {answer}.",
                )
    for integration in signals.get("integrations", []):
        test(
            "security",
            f"Integration security: {integration}",
            "Review credentials, data minimization and failure handling "
            f"for {integration}.",
            f"Recommendation signal integrations includes {integration}.",
        )
    if signals.get("ai_layer") in (True, "required"):
        for category, title in [
            ("model_evaluation", "Model quality evaluation"),
            ("prompt_regression", "Prompt regression"),
            ("tool_use_evaluation", "Tool-use safety evaluation"),
        ]:
            test(
                category,
                title,
                "Define a versioned evaluation dataset, expected outcomes "
                "and review thresholds before running evaluations.",
                "Explicit recommendation signal ai_layer=required; "
                "future AI-enabled system only.",
            )
    for field, category in [
        ("risks", "technical"),
        ("assumptions", "technical"),
        ("constraints", "delivery"),
        ("integrations", "operational"),
        ("open_questions", "delivery"),
    ]:
        for answer in answers.get(field, []):
            title = (
                f"Assumption proves false: {answer}"
                if field == "assumptions"
                else (
                    f"Third-party dependency: {answer}"
                    if field == "integrations"
                    else answer
                )
            )
            selected = (
                "compliance"
                if re.search(r"GDPR|compliance", answer, re.I)
                else ("security" if SECURITY.search(answer) else category)
            )
            risk(title, answer, selected, f"Discovery {field}: {answer}.", source=field)
    hosting = technologies.get("hosting")
    if hosting:
        risk(
            f"Hosting free-tier limits: {hosting}",
            "Verify applicable free-tier quotas, cold starts, sleeping services, "
            "storage and upgrade costs before deployment.",
            "cost",
            f"Recommended hosting: {hosting}; "
            "pricing/free-tier claims require verification.",
            source="hosting",
        )
    ops = signals.get("ops_capability", "low")
    if ops == "low":
        risk(
            "Limited operational capacity",
            "Recovery, patching and incident response may exceed team capacity.",
            "operational",
            "Recommendation signal ops_capability=low.",
            source="ops",
        )
    return {
        "test_cases": tests,
        "risks": risks,
        "slos": [
            {**slo, "generation_key": generation_key("slo", slo["name"])}
            for slo in generate_slos(context, signals)
        ],
    }


def markdown(
    data: OperationsRead, kinds: list[str] | None = None, *, level: int = 1
) -> str:
    selected = kinds or ["test_cases", "risks", "slos"]
    lines = [f"{'#' * level} Validate and operate", HEADER]
    if "test_cases" in selected:
        executed = sum(case.executed for case in data.test_cases)
        proposed = sum(case.status == "proposed" for case in data.test_cases)
        lines += [
            f"{'#' * (level + 1)} Test plan",
            f"Proposed (not yet run): {proposed}",
            f"Executed: {executed}",
            f"Not executed: {len(data.test_cases) - executed}",
        ]
        for case in data.test_cases:
            status = (
                case.status
                if case.executed or case.status not in ("passed", "failed")
                else "proposed"
            )
            lines += [
                f"{'#' * (level + 2)} {case.title}",
                f"Category: {case.category} | Status: {status} "
                f"| Executed: {case.executed}",
                case.description,
                f"Rationale: {case.rationale}",
                f"Results: {case.result_notes}",
                f"Executed at: {case.executed_at or 'Not recorded'} "
                f"| By: {case.executed_by or 'Not recorded'}",
            ]
    if "risks" in selected:
        lines += [f"{'#' * (level + 1)} Risk register"]
        for risk in data.risks:
            lines += [
                f"{'#' * (level + 2)} {risk.title}",
                f"Category: {risk.category} | Status: {risk.status}",
                risk.description,
                f"Likelihood: {risk.likelihood} | Impact: {risk.impact} "
                f"| Score: {risk.score}",
                f"Mitigation: {risk.mitigation}",
                f"Owner: {risk.owner}",
                f"Rationale: {risk.rationale}",
            ]
    if "slos" in selected:
        lines += [f"{'#' * (level + 1)} SLO suggestions"]
        for slo in data.slos:
            lines += [
                f"{'#' * (level + 2)} {slo.name}",
                f"Status: {slo.status}",
                f"SLI: {slo.sli}",
                f"Target: {slo.target} | Window: {slo.window}",
                f"Alert: {slo.alert}",
                f"Rationale: {slo.rationale}",
            ]
    return "\n\n".join(lines) + "\n"


def test_csv(data: OperationsRead) -> str:
    output = io.StringIO(newline="")
    fields = [
        "title",
        "category",
        "description",
        "rationale",
        "status",
        "executed",
        "result_notes",
        "executed_at",
        "executed_by",
        "requirement_id",
        "source",
        "edited",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for case in data.test_cases:
        row = case.model_dump(mode="json", include=set(fields))
        if not case.executed and row["status"] in ("passed", "failed"):
            row["status"] = "proposed"
        writer.writerow(
            {
                key: "'" + value
                if isinstance(value, str)
                and value.lstrip().startswith(("=", "+", "-", "@"))
                else value
                for key, value in row.items()
            }
        )
    return output.getvalue()

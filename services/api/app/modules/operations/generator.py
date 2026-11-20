import csv
import io
import re
from typing import Any

from app.modules.operations.schemas import OperationsRead

SECURITY = re.compile(
    r"security|auth|privacy|\bPII\b|GDPR|encrypt|isolation|consent", re.I
)
PERFORMANCE = re.compile(
    r"latency|throughput|load|users|scale|performance|\bp95\b", re.I
)
NUMBERS = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ms|milliseconds?|seconds?|s\b|users|requests?/?s|rps)", re.I
)
LATENCY = re.compile(r"\d+(?:\.\d+)?\s*(?:ms\b|milliseconds?\b|seconds?\b|s\b)", re.I)
ALERT = (
    "Recommend multi-window burn-rate alerts against the error budget: "
    "page at 14.4x over 1h and 5m; ticket at 6x over 6h and 30m. "
    "Review thresholds and ownership before adoption."
)
HEADER = (
    "Generated deterministically from requirements; suggestions require human review."
)


def requirement_text(requirement: dict[str, Any]) -> str:
    return " ".join(
        [
            requirement["title"],
            requirement.get("description", ""),
            *requirement.get("acceptance_criteria", []),
        ]
    )


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
    tests: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    slos: list[dict[str, Any]] = []

    def test(
        category: str,
        title: str,
        description: str,
        rationale: str,
        requirement: dict[str, Any] | None = None,
    ) -> None:
        tests.append(
            dict(
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
    ) -> None:
        risks.append(
            dict(
                title=title[:200],
                description=description,
                category=category,
                likelihood=4 if category in ("operational", "cost") else 3,
                impact=5 if category in ("security", "compliance") else 3,
                mitigation="Validate the assumption, assign an owner "
                "and review mitigation before release.",
                owner="",
                status="open",
                rationale=rationale,
                requirement_id=requirement.get("id") if requirement else None,
            )
        )

    def slo(
        name: str,
        sli: str,
        target: str,
        rationale: str,
        requirement: dict[str, Any] | None = None,
    ) -> None:
        slos.append(
            dict(
                name=name,
                sli=sli,
                target=target[:500],
                window="28 days",
                alert=ALERT,
                rationale=rationale,
                status="suggested",
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
            risk(title, answer, selected, f"Discovery {field}: {answer}.")
    hosting = technologies.get("hosting")
    if hosting:
        risk(
            f"Hosting free-tier limits: {hosting}",
            "Verify applicable free-tier quotas, cold starts, sleeping services, "
            "storage and upgrade costs before deployment.",
            "cost",
            f"Recommended hosting: {hosting}; "
            "pricing/free-tier claims require verification.",
        )
    ops = signals.get("ops_capability", "low")
    scale = signals.get("scale", "small")
    if ops == "low":
        risk(
            "Limited operational capacity",
            "Recovery, patching and incident response may exceed team capacity.",
            "operational",
            "Recommendation signal ops_capability=low.",
        )
    target = "99.9%" if scale == "large" and ops != "low" else "99.5%"
    slo(
        "Availability",
        "Successful eligible requests / total eligible requests; "
        "exclude documented client errors.",
        target,
        f"Recommendation signals scale={scale}, ops_capability={ops}; "
        "proposed, not a measured guarantee.",
    )
    latency_req = next(
        (
            r
            for r in requirements
            if r["type"] == "non_functional" and LATENCY.search(requirement_text(r))
        ),
        None,
    )
    match = LATENCY.search(requirement_text(latency_req)) if latency_req else None
    slo(
        "Request latency",
        "p95 server request duration over eligible requests.",
        f"p95 < {match.group()}" if match else "p95 < 500 ms",
        f"NFR: {latency_req['title']}; {requirement_text(latency_req)}"
        if latency_req
        else "Default latency suggestion; no numeric latency NFR supplied.",
        latency_req,
    )
    slo(
        "Error rate",
        "Server errors / total eligible requests.",
        "< 1%",
        f"Default error-budget suggestion for scale={scale}; "
        "review against requirements.",
    )
    if technologies.get("backend"):
        slo(
            "Readiness",
            "Successful readiness probes / total probes, "
            "including required dependency checks.",
            ">= 99.5%",
            f"Recommended backend: {technologies['backend']}; "
            "prevent traffic to unready instances.",
        )
    if signals.get("background_jobs") in (True, "yes"):
        slo(
            "Background-job completion",
            "Jobs completed successfully before their documented deadline / jobs due.",
            ">= 99%",
            "Recommendation signal background_jobs=yes; agree job-specific deadlines.",
        )
    if signals.get("realtime") in (True, "yes"):
        slo(
            "Data freshness",
            "Updates delivered within 5 seconds / updates emitted.",
            ">= 99% within 5 s",
            "Recommendation signal realtime=yes; validate freshness budget with users.",
        )
    return {"test_cases": tests, "risks": risks, "slos": slos}


def markdown(data: OperationsRead, kinds: list[str] | None = None) -> str:
    selected = kinds or ["test_cases", "risks", "slos"]
    lines = ["# Validate and operate", HEADER]
    if "test_cases" in selected:
        executed = sum(case.executed for case in data.test_cases)
        proposed = sum(case.status == "proposed" for case in data.test_cases)
        lines += [
            "## Test plan",
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
                f"### {case.title}",
                f"Category: {case.category} | Status: {status} "
                f"| Executed: {case.executed}",
                case.description,
                f"Rationale: {case.rationale}",
                f"Results: {case.result_notes}",
                f"Executed at: {case.executed_at or 'Not recorded'} "
                f"| By: {case.executed_by or 'Not recorded'}",
            ]
    if "risks" in selected:
        lines += ["## Risk register"]
        for risk in data.risks:
            lines += [
                f"### {risk.title}",
                f"Category: {risk.category} | Status: {risk.status}",
                risk.description,
                f"Likelihood: {risk.likelihood} | Impact: {risk.impact} "
                f"| Score: {risk.score}",
                f"Mitigation: {risk.mitigation}",
                f"Owner: {risk.owner}",
                f"Rationale: {risk.rationale}",
            ]
    if "slos" in selected:
        lines += ["## SLO suggestions"]
        for slo in data.slos:
            lines += [
                f"### {slo.name}",
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

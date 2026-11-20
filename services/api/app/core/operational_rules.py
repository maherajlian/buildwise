import re
from typing import Any

LATENCY = re.compile(r"\d+(?:\.\d+)?\s*(?:ms\b|milliseconds?\b|seconds?\b|s\b)", re.I)
ALERT = (
    "Recommend multi-window burn-rate alerts against the error budget: "
    "page at 14.4x over 1h and 5m; ticket at 6x over 6h and 30m. "
    "Review thresholds and ownership before adoption."
)


def requirement_text(requirement: dict[str, Any]) -> str:
    return " ".join(
        [
            requirement["title"],
            requirement.get("description", ""),
            *requirement.get("acceptance_criteria", []),
        ]
    )


def generate_slos(
    context: dict[str, Any], signals: dict[str, Any]
) -> list[dict[str, Any]]:
    requirements = sorted(
        context.get("requirements", []),
        key=lambda r: (r.get("priority", "P1"), r["title"], str(r.get("id", ""))),
    )
    technologies = context.get("technologies", {})
    slos: list[dict[str, Any]] = []

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

    ops = signals.get("ops_capability", "low")
    scale = signals.get("scale", "small")
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
            f"Recommended backend: {technologies['backend']}; prevent traffic "
            "to unready instances.",
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
    return slos

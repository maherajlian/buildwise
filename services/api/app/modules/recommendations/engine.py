import hashlib
import json

from app.modules.recommendations.schemas import (
    CATEGORIES,
    Catalogue,
    Match,
    Recommendation,
    Result,
    ScoredEntry,
    Signal,
)
from app.telemetry.operations import observed


@observed("rules")
def recommend(signals: list[Signal], catalogue: Catalogue) -> Result:
    ordered = sorted(signals, key=lambda s: s.id)
    by_id = {s.id: s for s in ordered}
    values = {s.id: s.value for s in ordered}
    fingerprint = hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    recommendations = []
    for category in CATEGORIES:
        scored = []
        for entry in sorted(catalogue.entries, key=lambda e: e.id):
            if entry.category != category:
                continue
            matches = []
            for rule in sorted(catalogue.rules, key=lambda r: r.id):
                if rule.id not in entry.selection_rules:
                    continue

                def matches_value(key: str, expected: str | list[str]) -> bool:
                    actual = values.get(key)
                    allowed = expected if isinstance(expected, list) else [expected]
                    return (
                        any(v in allowed for v in actual)
                        if isinstance(actual, list)
                        else actual in allowed
                    )

                if all(matches_value(k, v) for k, v in rule.when.items()):
                    used = [by_id[k] for k in sorted(rule.when)]
                    context = "; ".join(f"{s.id}={s.value} ({s.source})" for s in used)
                    matches.append(
                        Match(
                            rule_id=rule.id,
                            weight=rule.weight,
                            reason=rule.reason
                            + (f" Inputs: {context}." if context else ""),
                            signals=used,
                        )
                    )
            reason = (
                " ".join(m.reason for m in matches)
                or "No matching preference rules; neutral baseline."
            )
            scored.append(
                ScoredEntry(
                    **entry.model_dump(),
                    score=sum(m.weight for m in matches),
                    matched_rules=matches,
                    positive_matches=[m for m in matches if m.weight > 0],
                    negative_matches=[m for m in matches if m.weight < 0],
                    reason=reason,
                )
            )
        scored.sort(key=lambda e: (-e.score, e.id))
        enabled = category != "ai_layer" or (
            by_id["ai_layer"].value == "required"
            and by_id["ai_layer"].source == "explicit"
        )
        top = scored[0] if enabled else None
        explanation = (
            "Optional, may incur cost."
            if category == "ai_layer"
            else "Ranked by matching input rules; ties use entry id."
        )
        if not enabled:
            explanation = (
                "AI layer not recommended: explicit required input is absent. "
                "Candidates are optional, may incur cost."
            )
        alternatives = scored[1:3] if enabled else []
        for alternative in alternatives:
            alternative.reason += (
                f" Ranked below {scored[0].id}: score {alternative.score} "
                f"versus {scored[0].score}; equal scores use entry id."
            )
        recommendations.append(
            Recommendation(
                category=category,
                status="recommended" if enabled else "not_recommended",
                explanation=explanation,
                recommendation=top,
                alternatives=alternatives,
                candidates=scored if not enabled else [],
                reason=top.reason if top else explanation,
                trade_offs=top.trade_offs if top else [],
                operational_complexity=top.operational_complexity if top else None,
                operational_burden=top.operational_burden
                if top
                else "No AI infrastructure required.",
                cost_category=top.cost_category if top else None,
                assumptions=top.assumptions if top else [],
                change_conditions=top.change_conditions
                if top
                else ["An explicit AI requirement is established."],
            )
        )
    return Result(
        project_id="",
        catalogue_version=catalogue.catalogue_version,
        rules_version=catalogue.rules_version,
        input_fingerprint=fingerprint,
        signals=ordered,
        recommendations=recommendations,
        notes=[],
        disclaimer=(
            "Scores are a decision aid, not an objective benchmark; "
            "pricing/free-tier claims require verification."
        ),
    )

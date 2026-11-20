import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.projects.models import Discovery, Project, Requirement
from app.modules.recommendations.engine import recommend
from app.modules.recommendations.router import effective
from app.modules.recommendations.schemas import Catalogue
from app.modules.specifications.models import Artefact
from app.modules.specifications.operations_plans import plan_layouts
from app.modules.specifications.schemas import KINDS, Kind

TITLES = {
    "prd": "Product requirements document",
    "technical_design": "Technical design document",
    "architecture": "Architecture overview",
    "adr": "Architecture decision record",
    "data_model": "Data model outline",
    "api_contract": "API contract outline",
    "user_stories": "User stories",
    "acceptance_criteria": "Acceptance criteria",
    "non_functional_requirements": "Non-functional requirements",
    "security": "Security considerations",
    "test_strategy": "Test strategy",
    "deployment": "Deployment plan",
    "observability": "Observability plan",
}


def snapshot(
    session: Session, project: Project, catalogue: Catalogue
) -> dict[str, Any]:
    discovery = session.get(Discovery, project.id)
    requirements = session.scalars(
        select(Requirement)
        .where(Requirement.project_id == project.id)
        .order_by(Requirement.priority, Requirement.title, Requirement.id)
    ).all()
    _, signals, _ = effective(session, project.id)
    result = recommend(signals, catalogue)
    return {
        "name": project.name,
        "description": project.description,
        "discovery": discovery.answers if discovery else {},
        "requirements": [
            {
                "id": str(r.id),
                "title": r.title,
                "description": r.description,
                "type": r.type,
                "priority": r.priority,
                "status": r.status,
                "acceptance_criteria": r.acceptance_criteria,
            }
            for r in requirements
        ],
        "technologies": {
            r.category: r.recommendation.name
            for r in result.recommendations
            if r.recommendation is not None
        },
        "signals": {signal.id: signal.value for signal in signals},
        "technology_details": {
            r.category: {
                "constraints": r.recommendation.constraints,
                "operational_burden": r.recommendation.operational_burden,
                "cost_category": r.recommendation.cost_category,
                "cost_note": r.recommendation.cost_note,
            }
            for r in result.recommendations
            if r.recommendation is not None
        },
        "catalogue_version": result.catalogue_version,
        "rules_version": result.rules_version,
    }


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "TODO: define with stakeholders."


def template(kind: Kind, context: dict[str, Any]) -> list[dict[str, str]]:
    if kind in ("deployment", "observability"):
        return [
            {"key": heading.lower().replace(" ", "_"), "heading": heading, "body": body}
            for heading, body in plan_layouts(context)[kind]
        ]
    answers = context.get("discovery", {})
    reqs = context.get("requirements", [])
    name = context["name"]
    problem = (
        answers.get("problem_statement")
        or context.get("description")
        or "TODO: describe the problem."
    )
    users = bullets(answers.get("target_users", []))
    goals = bullets(answers.get("goals", []))
    technologies = bullets(
        [f"{k}: {v}" for k, v in context.get("technologies", {}).items()]
    )
    functional = [r for r in reqs if r["type"] == "functional"]
    criteria = bullets(
        [f"{r['title']}: {c}" for r in reqs for c in r["acceptance_criteria"]]
    )
    scope = bullets([r["title"] for r in reqs])
    nfr = bullets(
        [
            f"{r['title']}: {r['description']}\n" + bullets(r["acceptance_criteria"])
            for r in reqs
            if r["type"] == "non_functional"
        ]
    )
    stories = bullets(
        [
            f"As a {', '.join(answers.get('target_users', [])) or 'TODO: user'}, "
            f"I want {r['title']}, "
            f"so that {r['description'] or 'TODO: define the benefit'}.\n"
            + bullets(r["acceptance_criteria"])
            for r in functional
        ]
    )
    layouts = {
        "prd": [
            ("Problem", problem),
            ("Users", users),
            ("Goals", goals),
            ("Scope", scope),
            ("Out of scope", bullets(answers.get("out_of_scope", []))),
            ("Success metrics", bullets(answers.get("success_metrics", []))),
        ],
        "technical_design": [
            ("Approach", f"Build {name} to address: {problem}"),
            ("Technologies", technologies),
            ("Requirements", scope),
            ("Constraints", bullets(answers.get("constraints", []))),
        ],
        "architecture": [
            ("System context", f"{name}\n{problem}\nUsers:\n{users}"),
            ("Components", technologies),
            (
                "Boundaries",
                "Separate presentation, domain rules and persistence. "
                "TODO: assign component ownership.",
            ),
            ("Integrations", bullets(answers.get("integrations", []))),
        ],
        "adr": [
            ("Status", "Proposed — human review required"),
            ("Context", f"{name}: {problem}"),
            (
                "Decision",
                f"Evaluate the deterministic recommendations:\n{technologies}",
            ),
            (
                "Consequences",
                "Verify operational burden, free-tier limits "
                "and data portability before adoption.",
            ),
            (
                "Alternatives",
                "TODO: compare catalogue alternatives and document rejected options.",
            ),
        ],
        "data_model": [
            ("Domain scope", scope),
            (
                "Entities and relationships",
                f"For {name}, derive entities from the requirements above. "
                "TODO: define identifiers, fields, cardinality and ownership.",
            ),
            (
                "Integrity and retention",
                "TODO: specify uniqueness, foreign keys, retention and deletion rules.",
            ),
        ],
        "api_contract": [
            ("Operations", scope),
            (
                "Contract",
                "TODO: define methods, paths, request/response schemas "
                f"and pagination for {name}.",
            ),
            (
                "Errors and access",
                "Use explicit validation errors; authenticate callers and enforce "
                "resource ownership. TODO: document status codes and idempotency.",
            ),
        ],
        "user_stories": [("Stories", stories), ("Acceptance criteria", criteria)],
        "acceptance_criteria": [
            ("Requirement checks", criteria),
            ("Review", "TODO: agree measurable examples for missing criteria."),
        ],
        "non_functional_requirements": [
            ("Quality attributes", nfr),
            ("Constraints", bullets(answers.get("constraints", []))),
        ],
        "security": [
            ("Protected context", f"{name}\n{users}"),
            (
                "Controls",
                "Authenticate, authorize per resource, validate inputs, encrypt "
                "transport, redact secrets and minimize personal data.",
            ),
            ("Risks", bullets(answers.get("risks", []))),
            (
                "Review",
                "TODO: threat model trust boundaries, abuse cases and recovery.",
            ),
        ],
        "test_strategy": [
            ("Acceptance coverage", criteria),
            ("Quality checks", nfr),
            (
                "Test levels",
                "Unit-test domain rules; integration-test persistence and "
                "authorization; exercise critical user journeys end to end.",
            ),
            (
                "Exit criteria",
                "TODO: agree coverage, performance budgets and release sign-off.",
            ),
        ],
    }
    return [
        {"key": heading.lower().replace(" ", "_"), "heading": heading, "body": body}
        for heading, body in layouts[kind]
    ]


def generate(
    session: Session,
    project: Project,
    catalogue: Catalogue,
    kinds: list[Kind] | None = None,
    overwrite_edited: bool = False,
    generated: list[Artefact] | None = None,
) -> list[Artefact]:
    context = snapshot(session, project, catalogue)
    existing = list(
        session.scalars(
            select(Artefact)
            .where(Artefact.project_id == project.id)
            .order_by(Artefact.created_at, Artefact.id)
        )
    )
    for kind in dict.fromkeys(kinds or KINDS):
        matches = [a for a in existing if a.kind == kind]
        if not matches:
            item = Artefact(project_id=project.id, kind=kind)
            session.add(item)
            matches = [item]
        for item in matches:
            if item.edited and not overwrite_edited:
                continue
            item.title = TITLES[kind]
            item.sections = template(kind, context)
            item.context = context
            item.edited = False
            if generated is not None:
                generated.append(item)
    session.flush()
    return ordered(session, project.id)


def ordered(session: Session, project_id: object) -> list[Artefact]:
    items = list(
        session.scalars(select(Artefact).where(Artefact.project_id == project_id))
    )
    positions = {str(kind): index for index, kind in enumerate(KINDS)}
    return sorted(items, key=lambda a: (positions[a.kind], a.created_at, str(a.id)))


def markdown(item: Artefact) -> str:
    return (
        f"# {item.title}\n\n"
        + "\n\n".join(f"## {s['heading']}\n\n{s['body']}" for s in item.sections)
        + "\n"
    )


def export(project: Project, items: list[Artefact]) -> str:
    header = f"# {project.name} — Specifications\n\n{project.description}\n\n"
    toc = "## Table of contents\n\n" + "\n".join(
        f"- [{item.title}](#artefact-{item.id})" for item in items
    )
    contents = "\n\n".join(
        f'<a id="artefact-{item.id}"></a>\n\n{markdown(item)}\n'
        "### Generation context\n\n```json\n"
        + json.dumps(item.context, indent=2, ensure_ascii=False)
        + "\n```"
        for item in items
    )
    return header + toc + "\n\n" + (contents or "TODO: generate artefacts.") + "\n"

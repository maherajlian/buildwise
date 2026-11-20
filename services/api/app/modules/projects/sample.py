from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.modules.discovery.schemas import DiscoveryAnswers
from app.modules.operations.service import generate as generate_operations
from app.modules.planning.service import generate as generate_plan
from app.modules.projects.access import SAMPLE_PROJECT_ID
from app.modules.projects.models import Discovery, Project, Requirement
from app.modules.recommendations.catalogue_loader import load_catalogue
from app.modules.specifications.generator import generate as generate_artefacts

NAME = "Restaurant Booking & Customer Engagement SaaS (illustrative sample)"
DESCRIPTION = (
    "Illustrative, read-only sample project. It shows what a completed BuildWise "
    "discovery looks like for a fictional multi-tenant restaurant booking product. "
    "It is not real customer data and does not describe a real business."
)
ANSWERS = DiscoveryAnswers(
    problem_statement=(
        "Independent restaurants lose revenue to no-shows and phone-only bookings, "
        "and have no simple way to re-engage past guests."
    ),
    target_users=["Restaurant owners", "Front-of-house managers", "Diners"],
    user_needs=[
        "Diners book a table online in under a minute",
        "Managers see tonight's covers and adjust table plans",
        "Owners send opt-in offers to returning guests",
    ],
    goals=["Reduce no-shows", "Increase online bookings", "Grow repeat visits"],
    success_metrics=[
        "No-show rate below 5% within three months",
        "60% of bookings made online",
        "15% of guests return within 90 days",
    ],
    in_scope=["Online booking widget", "Table management", "Reminder messages"],
    out_of_scope=["Point-of-sale integration", "Food delivery"],
    constraints=[
        "Small team of three engineers",
        "Must comply with UK GDPR for guest data",
        "Launch MVP within four months",
    ],
    integrations=["Email provider", "SMS provider", "Calendar export"],
    assumptions=[
        "Restaurants have a stable internet connection",
        "Diners accept email or SMS reminders",
    ],
    risks=["Low adoption by staff during busy service", "SMS costs at scale"],
    open_questions=[
        "Should deposits be taken for large groups?",
        "Which regions are in scope after the UK?",
    ],
)
REQUIREMENTS = [
    (
        "functional",
        "Diner books a table online",
        "A diner selects date, time and party size and receives a confirmation.",
        "P0",
        "confirmed",
        [
            "Given an available slot, when the diner submits the form, then a booking "
            "is created and a confirmation email is sent",
            "Unavailable slots cannot be selected",
        ],
    ),
    (
        "functional",
        "Automatic booking reminders",
        "Guests receive a reminder 24 hours before the booking with a cancel link.",
        "P0",
        "confirmed",
        ["Reminder is sent 24 hours before the booking time"],
    ),
    (
        "functional",
        "Manager views tonight's covers",
        "Managers see a list of bookings for the current service by table.",
        "P1",
        "proposed",
        ["Bookings are grouped by service and table"],
    ),
    (
        "functional",
        "Opt-in guest offers",
        "Owners send offers only to guests who opted in to marketing.",
        "P2",
        "deferred",
        ["Guests without consent never receive offers"],
    ),
    (
        "non_functional",
        "Booking page performance",
        "The booking widget loads quickly on mobile networks.",
        "P1",
        "confirmed",
        ["Largest contentful paint under 2.5 s on a mid-range phone over 4G"],
    ),
    (
        "non_functional",
        "Tenant data isolation",
        "One restaurant can never read another restaurant's guests or bookings.",
        "P0",
        "confirmed",
        ["Automated tests prove cross-tenant reads return 404"],
    ),
]


def seed_sample(session: Session) -> Project:
    project = session.get(Project, SAMPLE_PROJECT_ID) or Project(id=SAMPLE_PROJECT_ID)
    project.owner_hash = None
    project.is_sample = True
    project.name = NAME
    project.description = DESCRIPTION
    project.status = "active"
    session.add(project)
    session.flush()
    discovery = session.get(Discovery, SAMPLE_PROJECT_ID) or Discovery(
        project_id=SAMPLE_PROJECT_ID
    )
    discovery.answers = ANSWERS.model_dump()
    discovery.current_step = "review"
    session.add(discovery)
    session.execute(
        delete(Requirement).where(Requirement.project_id == SAMPLE_PROJECT_ID)
    )
    for kind, title, description, priority, status, criteria in REQUIREMENTS:
        session.add(
            Requirement(
                project_id=SAMPLE_PROJECT_ID,
                type=kind,
                title=title,
                description=description,
                priority=priority,
                status=status,
                acceptance_criteria=criteria,
            )
        )
    session.flush()
    catalogue = load_catalogue()
    generate_artefacts(session, project, catalogue, overwrite_edited=True)
    generate_plan(session, project, catalogue, overwrite=True)
    generate_operations(session, project, catalogue, replace_edited=True)
    session.commit()
    return project

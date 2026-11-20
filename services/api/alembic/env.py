from sqlalchemy import create_engine, pool

from alembic import context
from app.core.settings import Settings, database_url
from app.db.base import Base
from app.modules.planning.models import Epic, PlanTask  # noqa: F401
from app.modules.projects.models import Project  # noqa: F401
from app.modules.recommendations.models import RecommendationInputs  # noqa: F401
from app.modules.specifications.models import Artefact  # noqa: F401

engine = create_engine(database_url(Settings().database_url), poolclass=pool.NullPool)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.settings import Settings, database_url
from app.modules.projects.sample import seed_sample


def main() -> None:
    engine = create_engine(database_url(Settings().database_url))
    with Session(engine) as session:
        seed_sample(session)
    engine.dispose()


if __name__ == "__main__":
    main()

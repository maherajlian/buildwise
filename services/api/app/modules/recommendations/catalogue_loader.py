from pathlib import Path

from app.modules.recommendations.schemas import Catalogue


def load_catalogue() -> Catalogue:
    path = Path(__file__).parent / "catalogue" / "catalogue.json"
    return Catalogue.model_validate_json(path.read_text())

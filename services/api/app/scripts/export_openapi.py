import json
from pathlib import Path

from app.core.settings import Settings
from app.main import create_app


def main() -> None:
    app = create_app(Settings(otel_exporter_otlp_endpoint=""))
    target = Path(__file__).resolve().parents[5] / "packages/shared-types/openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    app.state.engine.dispose()


if __name__ == "__main__":
    main()

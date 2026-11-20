import secrets
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.main import create_app
from app.modules.projects.access import SAMPLE_PROJECT_ID
from app.modules.projects.sample import seed_sample
from app.modules.recommendations.models import RecommendationInputs


def test_recommendation_endpoints(migrated_url: str) -> None:
    owner = {"X-Project-Token": secrets.token_urlsafe(32)}
    other = {"X-Project-Token": secrets.token_urlsafe(32)}
    with TestClient(
        create_app(Settings(database_url=migrated_url, otel_exporter_otlp_endpoint=""))
    ) as client:
        catalogue = client.get("/api/v1/catalogue")
        assert catalogue.status_code == 200
        assert len(catalogue.json()["entries"]) == 30
        project_id = client.post(
            "/api/v1/projects", headers=owner, json={"name": "Recommendations"}
        ).json()["id"]
        base = f"/api/v1/projects/{project_id}"
        for suffix in ("recommendations", "recommendation-inputs"):
            assert client.get(f"{base}/{suffix}").status_code == 404
            assert client.get(f"{base}/{suffix}", headers=other).status_code == 404
            assert (
                client.get(
                    f"/api/v1/projects/{uuid4()}/{suffix}", headers=owner
                ).status_code
                == 404
            )
        before = client.get(base + "/recommendations", headers=owner)
        assert before.status_code == 200
        assert (
            before.content
            == client.get(base + "/recommendations", headers=owner).content
        )
        assert (
            client.get(base + "/recommendation-inputs", headers=owner).json()[
                "overrides"
            ]
            == {}
        )
        body = {
            "overrides": {
                "scale": "large",
                "ops_capability": "high",
                "ai_layer": "required",
            }
        }
        assert (
            client.put(
                base + "/recommendation-inputs", headers=other, json=body
            ).status_code
            == 404
        )
        assert (
            client.put(
                base + "/recommendation-inputs", headers=owner, json=body
            ).status_code
            == 200
        )
        after = client.get(base + "/recommendations", headers=owner).json()
        assert after["input_fingerprint"] != before.json()["input_fingerprint"]
        hosting = next(
            r for r in after["recommendations"] if r["category"] == "hosting"
        )
        assert hosting["recommendation"]["id"] == "kubernetes"
        assert after["recommendations"][-1]["recommendation"]["optional"]
        assert (
            client.get(base + "/recommendation-inputs", headers=owner).json()[
                "overrides"
            ]
            == body["overrides"]
        )
        for invalid in ({"scale": "huge"}, {"unknown": "yes"}, {"budget": None}):
            assert (
                client.put(
                    base + "/recommendation-inputs",
                    headers=owner,
                    json={"overrides": invalid},
                ).status_code
                == 422
            )
        assert (
            client.put(
                base + "/recommendation-inputs", headers=owner, json={"overrides": {}}
            ).status_code
            == 200
        )
        assert (
            client.get(base + "/recommendations", headers=owner).content
            == before.content
        )
        engine = create_engine(migrated_url)
        with Session(engine) as session:
            seed_sample(session)
        sample = f"/api/v1/projects/{SAMPLE_PROJECT_ID}"
        assert client.get(sample + "/recommendations").status_code == 200
        assert client.get(sample + "/recommendation-inputs").json()["overrides"] == {}
        assert (
            client.put(
                sample + "/recommendation-inputs", headers=owner, json=body
            ).status_code
            == 403
        )
        assert client.delete(base, headers=owner).status_code == 204
        with Session(engine) as session:
            assert session.get(RecommendationInputs, UUID(project_id)) is None
        engine.dispose()

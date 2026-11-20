import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError

from grafana_provision import (
    FOLDER_UID,
    ROOT,
    Grafana,
    alert_payload,
    dashboard_payload,
    datasource_map,
    provision,
)


class ProvisionTests(unittest.TestCase):
    def test_error_queries_have_zero_defaults_and_keep_traffic_guards(self):
        dashboard = json.loads(
            (ROOT / "infra/grafana/dashboards/service-overview.json").read_text()
        )
        for panel_id in (2, 6):
            panel = next(p for p in dashboard["panels"] if p["id"] == panel_id)
            query = panel["targets"][0]["expr"]
            self.assertEqual(query.count("or vector(0)"), 2)
            self.assertIn("clamp_min", query)
        rules = json.loads((ROOT / "infra/grafana/alerts/buildwise.yaml").read_text())[
            "groups"
        ][0]["rules"]
        for rule in rules:
            query = rule["data"][0]["model"]["expr"]
            self.assertTrue(query.endswith("or vector(0)"))
            self.assertIn(
                ">= bool 5"
                if rule["uid"] == "buildwise-db-unavailable"
                else ">= bool 20",
                query,
            )

    def setUp(self):
        self.sources = [
            {"type": kind, "name": "Cloud " + kind, "uid": "cloud-" + kind}
            for kind in ("prometheus", "loki", "tempo")
        ]

    def test_maps_datasources_without_changing_template_references(self):
        sources = datasource_map(self.sources)
        for path in (ROOT / "infra/grafana/dashboards").glob("*.json"):
            dashboard = json.loads(path.read_text())
            payload = dashboard_payload(dashboard, sources)
            self.assertTrue(payload["overwrite"])
            self.assertEqual(payload["folderUid"], FOLDER_UID)
            self.assertEqual(payload["dashboard"]["uid"], dashboard["uid"])
            for variable in payload["dashboard"]["templating"]["list"][:3]:
                self.assertEqual(
                    variable["current"]["value"], "cloud-" + variable["query"]
                )
        group = json.loads((ROOT / "infra/grafana/alerts/buildwise.yaml").read_text())[
            "groups"
        ][0]
        rules = alert_payload(group, sources)["rules"]
        self.assertEqual(len(rules), 5)
        self.assertTrue(
            all(r["data"][0]["datasourceUid"] == "cloud-prometheus" for r in rules)
        )
        self.assertEqual(group["rules"][0]["data"][0]["datasourceUid"], "prometheus")

    def test_empty_and_ambiguous_sources_fail(self):
        with self.assertRaises(ValueError):
            datasource_map([])
        with self.assertRaises(ValueError):
            datasource_map(self.sources + [self.sources[0]])
        self.sources[0]["isDefault"] = True
        alternative = {"type": "prometheus", "name": "other", "uid": "other"}
        self.assertEqual(
            datasource_map(self.sources + [alternative])["prometheus"]["uid"],
            "cloud-prometheus",
        )

    def test_creates_folder_and_is_idempotent(self):
        client = Mock()

        def response(method, path, payload=None):
            if path == "/api/datasources":
                return self.sources
            if method == "GET":
                raise HTTPError(path, 404, "Not found", {}, None)
            return {}

        client.request.side_effect = response
        provision(client)
        self.assertEqual(
            sum(
                c.args[1] == "/api/dashboards/db" for c in client.request.call_args_list
            ),
            4,
        )
        client.request.reset_mock()
        client.request.side_effect = lambda method, path, payload=None: (
            self.sources if path == "/api/datasources" else {}
        )
        provision(client)
        self.assertFalse(
            any(
                c.args[0] == "POST" and c.args[1] == "/api/folders"
                for c in client.request.call_args_list
            )
        )

    def test_insecure_remote_url_rejected(self):
        with self.assertRaises(ValueError):
            Grafana("http://example.com", "not-a-real-token")


if __name__ == "__main__":
    unittest.main()

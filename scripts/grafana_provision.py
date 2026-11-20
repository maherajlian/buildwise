#!/usr/bin/env python3
"""Provision repository dashboards and alerts using only the Python stdlib."""

import copy
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FOLDER_UID = "buildwise-observability"


def datasource_map(sources: list[dict]) -> dict[str, dict]:
    selected = {}
    for kind in ("prometheus", "loki", "tempo"):
        matches = [source for source in sources if source["type"] == kind]
        defaults = [source for source in matches if source.get("isDefault")]
        if len(matches) == 1:
            selected[kind] = matches[0]
        elif len(defaults) == 1:
            selected[kind] = defaults[0]
        else:
            raise ValueError(f"Expected one {kind} datasource (or one default)")
    return selected


def dashboard_payload(dashboard: dict, sources: dict[str, dict]) -> dict:
    dashboard = copy.deepcopy(dashboard)
    dashboard.pop("id", None)
    for variable in dashboard["templating"]["list"]:
        if variable["type"] == "datasource":
            source = sources[variable["query"]]
            variable["current"] = {"text": source["name"], "value": source["uid"]}
            variable["options"] = []
    return {"dashboard": dashboard, "folderUid": FOLDER_UID, "overwrite": True}


def alert_payload(group: dict, sources: dict[str, dict]) -> dict:
    rules = copy.deepcopy(group["rules"])
    for rule in rules:
        rule["folderUID"] = FOLDER_UID
        rule["ruleGroup"] = group["name"]
        for query in rule["data"]:
            if query["datasourceUid"] == "prometheus":
                query["datasourceUid"] = sources["prometheus"]["uid"]
                query["model"]["datasource"]["uid"] = sources["prometheus"]["uid"]
    return {
        "title": group["name"],
        "folderUid": FOLDER_UID,
        "interval": 60,
        "rules": rules,
    }


class Grafana:
    def __init__(self, url: str, token: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
        ):
            raise ValueError("GRAFANA_URL must be an HTTP(S) URL without credentials")
        if parsed.scheme != "https" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Use HTTPS for non-loopback Grafana instances")
        self.url = url.rstrip("/")
        self.token = token

    def request(
        self, method: str, path: str, payload: dict | None = None
    ) -> dict | list:
        request = Request(
            self.url + path,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "X-Disable-Provenance": "true",
            },
            data=json.dumps(payload).encode() if payload is not None else None,
        )
        with urlopen(request, timeout=15) as response:
            return json.load(response)


def provision(client: Grafana) -> None:
    sources = datasource_map(client.request("GET", "/api/datasources"))
    try:
        client.request("GET", "/api/folders/" + FOLDER_UID)
    except HTTPError as exc:
        if exc.code != 404:
            raise
        client.request(
            "POST", "/api/folders", {"uid": FOLDER_UID, "title": "BuildWise"}
        )
    for path in sorted((ROOT / "infra/grafana/dashboards").glob("*.json")):
        client.request(
            "POST",
            "/api/dashboards/db",
            dashboard_payload(json.loads(path.read_text()), sources),
        )
        print("Provisioned dashboard:", path.stem)
    # JSON is a YAML subset, so this needs no YAML dependency.
    config = json.loads((ROOT / "infra/grafana/alerts/buildwise.yaml").read_text())
    for group in config["groups"]:
        client.request(
            "PUT",
            f"/api/v1/provisioning/folder/{FOLDER_UID}/rule-groups/{quote(group['name'], safe='')}",
            alert_payload(group, sources),
        )
        print("Provisioned alert group:", group["name"])


def main() -> int:
    try:
        provision(Grafana(os.environ["GRAFANA_URL"], os.environ["GRAFANA_SA_TOKEN"]))
    except KeyError:
        print("Set GRAFANA_URL and GRAFANA_SA_TOKEN", file=sys.stderr)
        return 1
    except HTTPError as exc:
        print(f"Grafana provisioning failed: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (ValueError, URLError, TimeoutError) as exc:
        # Do not echo response bodies, tokens or URLs supplied by the caller.
        print(f"Grafana provisioning failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

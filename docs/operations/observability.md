# Backend observability

## Architecture and privacy

The API owns OpenTelemetry trace, metric and log providers. A privacy-bounded
ASGI server span surrounds business spans and SQLAlchemy cursor spans; only the
SQL verb is retained, never SQL text or bind parameters. Rule evaluation is a
child of recommendation generation (also used by document/task generation).
SDK batches export OTLP/HTTP directly to Grafana Cloud or the local LGTM
Collector, which routes to Prometheus, Loki and Tempo. Grafana queries those
three backends. No paid AI SDK or model is involved.

Span attributes are limited to `buildwise.operation`, `buildwise.artifact.type`,
`buildwise.recommendation.category`, `buildwise.catalogue.version`, standard
`http.*`, and `error.type` on failure. Names are static; HTTP routes are templates
or `unmatched`. No project/user IDs, names, discovery text, SQL, headers, tokens,
emails or exception messages are exported. Errors carry class names and error
status, not exception events/stack traces. Logs contain static event names and
bounded request metadata; trace/span IDs are correlation fields, never metric
labels or Loki index labels. Do not promote structured metadata into index labels.

Resource attributes include `service.name`, `service.version` (`APP_VERSION`,
otherwise the first seven characters of `RENDER_GIT_COMMIT`, otherwise `dev`),
and `deployment.environment`. W3C `traceparent`/`tracestate` cross CORS; no baggage
is propagated. Incoming sampled parents are honored by the parent-based sampler.

## Configuration (environment only)

| Variable | Default / purpose |
| --- | --- |
| `APP_ENV` | `development`; `production` disables faults with a warning |
| `APP_VERSION` / `RENDER_GIT_COMMIT` | Deployment version fallback above |
| `OTEL_SERVICE_NAME` | `buildwise-api` (dashboard service variable; alerts target this service) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Empty disables network export; base URL without `/v1/traces` |
| `OTEL_EXPORTER_OTLP_HEADERS` | Empty; cloud gateway auth, URL-encoded comma-separated key/value pairs |
| `OTEL_TRACES_SAMPLER_ARG` | `0.1`; use `1` for a short local demonstration |
| `OTEL_TRACES_SAMPLER` | `parentbased_traceidratio` |
| `FAULT_INJECTION` | Empty; `recommendations:slow` sleeps 3s, `recommendations:fail` raises; `exports:*` also supported |
| `GRAFANA_URL`, `GRAFANA_SA_TOKEN` | Provisioning script only; Grafana API URL and service-account token, not OTLP gateway credentials |

Metrics export every 60 seconds. Allow **two export intervals** after first
traffic for rates/increases; counters first appearing after an event have no
earlier zero sample, so the first burst alone cannot produce an increase. Keep
generating traffic across intervals. Histogram bounds are 5/10/25/50/100/250/500ms,
1/3/5s plus infinity. Span/log queues are bounded at 512, batches 128, HTTP exporter
timeouts 1s; export failure is nonfatal and logged once. Telemetry can be dropped.

## Local profile

```sh
OTEL_EXPORTER_OTLP_ENDPOINT=http://lgtm:4318 OTEL_TRACES_SAMPLER_ARG=1 \
  docker compose --profile observability up -d --build
```

Grafana: <http://localhost:3001> (local anonymous Admin; default `admin/admin`).
OTLP/HTTP: `http://localhost:4318` for a host-run API. Docker API uses
`http://lgtm:4318`. Ports bind **127.0.0.1 only**; never expose this development
image publicly. Port 3000 remains available to Next.js. Image is pinned to
`grafana/otel-lgtm:0.11.0`. Dashboards/alerts mount read-only into Grafana's
provisioning directories. Open **Dashboards → BuildWise**. Local datasources are
Prometheus/Loki/Tempo; the datasource variables can be changed independently.
LGTM data is ephemeral (container recreation clears demo history).

Run `/health` and `/ready` probes at least once a minute while demonstrating
health/DB alerting, e.g. an external monitor or a shell loop with curl. No probe is
started by the application. Missing probes and a stopped exporter cannot be
distinguished from a stopped API using application telemetry alone.

### Metric translation

Dashboards use Prometheus classic histogram `_bucket`, `_sum`, `_count` series.
The OTel instruments deliberately include the target seconds / total suffixes;
Prometheus OTLP ingestion must not add a second suffix. Label dots become
underscores: `http.request.method` → `http_request_method`, `http.route` →
`http_route`, `http.response.status_code` → `http_response_status_code`,
`buildwise.artifact.type` → `buildwise_artifact_type`, `buildwise.operation` →
`buildwise_operation`, `error.type` → `error_type`, `statement.verb` →
`statement_verb`. OTel `service.name` maps to Prometheus `job` and Loki
`service_name`. The checked local series are listed in the verification section.

## Grafana Cloud Free provisioning

```sh
# Supply these in your shell/secret manager, never a committed file.
export GRAFANA_URL=https://YOUR-STACK.grafana.net
export GRAFANA_SA_TOKEN=... # service-account API token, not OTLP credentials
python3 scripts/grafana_provision.py
unset GRAFANA_SA_TOKEN
```

Stdlib only, 15s HTTP timeouts, stable folder/dashboard/rule UIDs and overwrite /
rule-group PUT make repeated runs idempotent. Creates a **BuildWise** folder and
looks up datasources by `prometheus`, `loki`, `tempo` type; selects the sole
matching datasource or its sole default. Without a default, standard Grafana Cloud
UIDs (`grafanacloud-prom`, `grafanacloud-logs`, `grafanacloud-traces`) disambiguate
the application stores from internal usage and alert-history stores. Other
ambiguous mappings fail rather than guessing.
Dashboard variables retain portability; their selected UIDs and alert datasource
UIDs are mapped to the destination. Token needs datasource-read, folder/dashboard
write and alert-rule provisioning permissions (Grafana Admin service account is
sufficient for initial provisioning; restrict permissions afterward).
Do not run this against the local file-provisioned dashboards: Grafana disallows
API overwriting file-managed resources. The YAML alert document is JSON syntax
(a valid YAML subset), allowing the same source to be loaded without PyYAML.

Cloud Loki should have a derived field: name/matcher `trace_id`, matcher type
**Label**, internal link to the selected Tempo datasource, URL `${__value.raw}`.
Tempo's traces-to-logs should map `service.name` to `service_name`, target Loki,
and use `{${__tags}} | trace_id = "${__trace.traceId}"`. Local LGTM already
provisions both. The script does not overwrite shared datasource configuration.
Use the Logs and Traces dashboard to expand a log's structured metadata and
follow its trace link; alternatively paste the trace ID into Tempo Explore.

### Free-tier budget

Verified against [Grafana pricing](https://grafana.com/pricing/) and
[Free tier](https://grafana.com/products/cloud/free-tier/) on 2026-11-20:
**10,000 active metric series**, **50 GB/month logs ingested**, **50 GB/month traces
ingested**, **14-day retention** for metrics, logs and traces. Terms can change;
check the stack Usage page and pricing before deployment. Stay on Free; never
enable a paid plan/payment method to bypass limits.

Keep route/operation/type/verb labels bounded. Each classic histogram costs one
series per bucket plus count/sum per label combination, so avoid adding dimensions
casually. A 60s metric interval reduces samples (not active-series count). Default
10% root-trace sampling limits trace volume but does not reduce metric/log volume;
upstream sampled parents can exceed that ratio. Request logging is one compact
event per request, with no bodies. At 1 req/s and ~1KB/log, logs are ~2.6GB/month;
10% sampling of ~10KB traces is ~2.6GB/month. These are estimates, not quota
guarantees. Review actual ingestion and cardinality before increasing traffic;
revert sampler to 0.1 after demos. Free API sleep, quota exhaustion, exporter
failure or collector loss can cause gaps.

## Alerts (Grafana-managed, evaluated every minute)

All rules are warning severity. Configure contact points/notification policies
in the destination Grafana; the repository deliberately provisions no recipients.
NoData is OK to avoid false alarms on a new/unused demo; datasource execution
errors produce Error state. Missing telemetry is not an independent uptime SLA.

| Rule | Threshold and guard | Pending |
| --- | --- | --- |
| Elevated 5xx | >5% of requests over 5m; >=20 requests/5m | 5m |
| High latency | Request P95 >1s over 5m; >=20 requests/5m | 5m |
| Health missing/failing | No successful `/health` increments for 10m, or absent series; >=20 requests in preceding 1h | 5m |
| DB unavailable | >=3 `/ready` 503s/5m; >=5 ready probes/5m | 2m |
| Operation errors | >=5 operation errors/5m; >=20 requests/5m | 2m |

Availability is **non-5xx request percentage**, not wall-clock uptime. Availability
and error ratios use zero defaults for missing outcome series. With no observed
requests the dashboard reports 0% availability (not evidence of downtime); all-5xx
traffic also reports 0%. Healthy traffic without any 5xx reports a 0% error ratio.
Alert queries return zero when inputs are absent, retaining their traffic guards.
Health alerting requires regular probes and a prior traffic baseline; long-total outages
eventually age out of the 1h guard. Use an external uptime monitor for production
black-box coverage. Low traffic deliberately suppresses these demo alerts.

## Failure demonstration / recovery

1. Start the profile with sampler 1. Create a project with a browser token; submit
   discovery, request recommendations, generate artefacts/tasks and export Markdown.
   Repeat across at least two 60s exports. Health/ready probes should return 200.
2. Recreate only the API (do not restart LGTM and lose telemetry history):
   ```sh
   OTEL_EXPORTER_OTLP_ENDPOINT=http://lgtm:4318 OTEL_TRACES_SAMPLER_ARG=1 \
     FAULT_INJECTION=recommendations:slow docker compose up -d api
   ```
   GET `/api/v1/projects/00000000-0000-4000-8000-000000000001/recommendations`
   (read-only seeded sample, no token). It takes ~3s. Repeat and open **Service
   Overview** P95 / **Backend and Dependencies** slow operations. In **Logs and
   Traces**, open the slow request trace and inspect its rule/DB children.
3. Switch `FAULT_INJECTION=recommendations:fail` in the same command. The same
   GET returns 500. Repeat traffic/probes; **Service Overview** shows 5xx and
   **Backend** shows `recommendations`/`RuntimeError`. **Logs and Traces** shows
   `operation_failed` with `error_type=RuntimeError`; expand details, click
   `trace_id` to Tempo. The failed span has error status but no exception message.
   To see an alert actually fire, sustain the documented minimum traffic and
   pending period; a single fault does not meet the alert guard.
4. Disable the fault, retaining the endpoint:
   ```sh
   OTEL_EXPORTER_OTLP_ENDPOINT=http://lgtm:4318 OTEL_TRACES_SAMPLER_ARG=1 \
     FAULT_INJECTION= docker compose up -d api
   ```
   Confirm recommendations and `/ready` are 200, latency recovers, and no new
   operation errors appear. Alert recovery follows its rolling evaluation window.
   Then restart with `OTEL_TRACES_SAMPLER_ARG=0.1` for normal usage.
5. To demonstrate nonfatal exporter failure, recreate the API with
   `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:1` (inside the container) and call
   `/health`, `/ready`, recommendations. They still serve; a sanitized
   `telemetry_export_failed` warning appears. Restore the LGTM endpoint afterward.

## Verification

Use Grafana's datasource proxy to inspect the actual local storage, not only SDK
instrument names:

```sh
curl -s http://localhost:3001/api/datasources/proxy/uid/prometheus/api/v1/label/__name__/values
curl -sG http://localhost:3001/api/datasources/proxy/uid/prometheus/api/v1/query \
  --data-urlencode 'query=http_server_requests_total{job="buildwise-api"}'
```

The four dashboards are Service Overview, Product Operations, Backend and
Dependencies, and Logs and Traces. Screenshots from verification are kept outside
the repository in `~/screens/`.

Local Prometheus API verification found **no double suffixes**:
`http_server_requests_total`, `buildwise_projects_created_total`,
`buildwise_discovery_submissions_total`, `buildwise_recommendation_runs_total`,
`buildwise_artifact_generation_total`, `buildwise_task_generation_total`,
`buildwise_export_total`, `buildwise_operation_errors_total`, `db_pool_connections`;
and `_bucket`, `_sum`, `_count` for `http_server_request_duration_seconds`,
`buildwise_operation_duration_seconds`, `buildwise_rule_evaluation_duration_seconds`,
`db_query_duration_seconds`. The dot-to-underscore labels and `job="buildwise-api"`
selector above were verified in stored series, not inferred from SDK names.

Backend checks:

```sh
(cd services/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app)
python3 scripts/no_paid_ai.py
python3 -m unittest discover -s scripts -p 'test_*.py'
docker compose up -d postgres
(cd services/api && DATABASE_URL=postgresql+psycopg://buildwise:buildwise@localhost:5432/buildwise uv run pytest -q)
```

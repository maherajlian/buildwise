import { ApiStatus } from "@/components/api-status";
export default function Page() {
  return (
    <div className="observability-practices">
      <header>
        <div className="eyebrow">BUILDWISE · SERVICE OPERATIONS</div>
        <div className="page-heading">
          <div>
            <h1>Observability</h1>
            <p>
              How BuildWise monitors its own API, diagnoses incidents and sets
              reliability objectives.
            </p>
          </div>
        </div>
      </header>
      <section aria-label="Live BuildWise status">
        <ApiStatus />
        <p className="mt-3 text-sm text-slate-600">
          Live probes: <code>/health</code> checks API liveness;{" "}
          <code>/ready</code> checks database connectivity with SELECT 1.
          Readiness is not a migration or end-to-end check.
        </p>
      </section>
      <section className="panel tech-panel">
        <h2>BuildWise service objectives</h2>
        <p>
          Targets for review, not measured achievements. The live status above
          is a current probe, not a 28-day compliance report.
        </p>
        <dl className="operations-summary">
          <div>
            <dt>Availability · /health</dt>
            <dd>
              99.5%
              <p className="text-sm font-normal">
                Successful health probes over 28 days.
              </p>
            </dd>
          </div>
          <div>
            <dt>API read latency</dt>
            <dd>
              &lt; 500 ms
              <p className="text-sm font-normal">
                p95 duration of API reads over 28 days.
              </p>
            </dd>
          </div>
          <div>
            <dt>API error rate</dt>
            <dd>
              &lt; 1%
              <p className="text-sm font-normal">
                5xx responses / eligible requests over 28 days.
              </p>
            </dd>
          </div>
        </dl>
        <h3>Recommended alerts</h3>
        <p>
          Use multi-window error-budget burn rates: page at 14.4× over both 1
          hour and 5 minutes; ticket at 6× over both 6 hours and 30 minutes.
          Alert on sustained readiness failures and latency above the read
          budget. Assign an owner and verify signal quality before enabling
          notifications; these are recommendations, not configured alerts.
        </p>
      </section>
      <section className="panel tech-panel">
        <h2>Signals we emit</h2>
        <ul>
          <li>
            <strong>Structured logs:</strong> timestamp, severity, service,
            environment, event, trace ID and span ID. Request completion/failure
            events support debugging; API responses include an X-Correlation-ID.
          </li>
          <li>
            <strong>Traces:</strong> FastAPI request spans and SQLAlchemy
            database spans, using parent-based trace-ID-ratio sampling (default
            10%).
          </li>
          <li>
            <strong>Metrics:</strong> FastAPI/OpenTelemetry HTTP instrumentation
            records request duration and active-request metrics. No inbound
            /metrics endpoint is exposed.
          </li>
          <li>
            <strong>Export:</strong> when configured, traces, logs and metrics
            go directly over OTLP HTTP to /v1/traces, /v1/logs and /v1/metrics.
            Metrics export every 60 seconds; trace/log queues are bounded. JSON
            console logs remain available without an OTLP endpoint.
          </li>
          <li>
            <strong>Safe diagnostics:</strong> export failures are sanitized as
            telemetry_export_failed. Never include tokens, credentials or
            personal data in diagnostic notes or logs.
          </li>
        </ul>
      </section>
      <section className="panel tech-panel">
        <h2>Incident &amp; debugging runbook</h2>
        <ol>
          <li>
            <strong>Render cold start:</strong> a sleeping free API can take
            time to wake. Let the bounded status retries finish, then use Retry.
            Check /health before investigating database readiness.
          </li>
          <li>
            <strong>Neon unreachable:</strong> /health may be OK while /ready
            returns 503. Check database availability, connection settings and
            provider status in authorized dashboards. Do not expose connection
            strings in reports.
          </li>
          <li>
            <strong>CORS or browser-only failure:</strong> verify the exact
            browser origin is in CORS_ORIGINS, including scheme and port.
            Locally use http://localhost:3000, not 127.0.0.1. Confirm
            NEXT_PUBLIC_API_BASE_URL and rebuild after changing it.
          </li>
          <li>
            <strong>Lost token / project not found:</strong> project access
            belongs to the token in this browser&apos;s localStorage. Clearing
            storage or switching browsers loses access; there is no account
            recovery. Do not paste the token into logs. Create a new project if
            the original owning browser is unavailable.
          </li>
          <li>
            <strong>Escalation:</strong> record time, affected endpoint,
            response status and correlation ID; inspect service logs and sampled
            traces. Verify /health and /ready after recovery and record the
            incident outcome separately from proposed test plans.
          </li>
        </ol>
      </section>
    </div>
  );
}

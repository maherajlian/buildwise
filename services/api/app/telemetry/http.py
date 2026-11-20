import logging
from time import perf_counter

from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind, StatusCode
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.telemetry.setup import Telemetry


class RequestTelemetry:
    def __init__(self, app: ASGIApp, telemetry: Telemetry) -> None:
        self.app = app
        self.telemetry = telemetry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        status = 500
        method = scope["method"]
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
            method = "OTHER"
        headers = {k.decode("latin1"): v.decode("latin1") for k, v in scope["headers"]}
        with self.telemetry.traces.get_tracer("buildwise").start_as_current_span(
            "http.request",
            context=extract(headers),
            kind=SpanKind.SERVER,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:

            async def wrapped(message: Message) -> None:
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                await send(message)

            try:
                await self.app(scope, receive, wrapped)
            except Exception as exc:
                span.set_status(StatusCode.ERROR)
                span.set_attribute("error.type", type(exc).__name__)
                raise
            finally:
                route = getattr(scope.get("route"), "path", "unmatched")
                attrs = {
                    "http.request.method": method,
                    "http.route": route,
                    "http.response.status_code": status,
                }
                span.set_attributes(attrs)
                span.update_name(f"{method} {route}")
                if status >= 500:
                    span.set_status(StatusCode.ERROR)
                elapsed = perf_counter() - started
                meter = self.telemetry.metrics.get_meter("buildwise")
                meter.create_counter("http_server_requests_total").add(1, attrs)
                meter.create_histogram(
                    "http_server_request_duration_seconds", unit="s"
                ).record(elapsed, attrs)
                logging.getLogger("buildwise").info(
                    "request_completed",
                    extra={
                        "method": method,
                        "route": route,
                        "status_code": status,
                        "duration_ms": round(elapsed * 1000, 3),
                    },
                )

from time import perf_counter
from typing import Any

from opentelemetry.metrics import Observation
from opentelemetry.trace import StatusCode, use_span
from sqlalchemy import Engine, event

from app.telemetry.setup import Telemetry


def instrument_database(engine: Engine, telemetry: Telemetry) -> None:
    meter = telemetry.metrics.get_meter("buildwise")
    duration = meter.create_histogram("db_query_duration_seconds", unit="s")

    def pool_connections(options: Any) -> list[Observation]:
        pool = engine.pool
        return [
            Observation(getattr(pool, method)(), {"state": state})
            for state, method in (("idle", "checkedin"), ("used", "checkedout"))
        ]

    meter.create_observable_gauge("db_pool_connections", callbacks=[pool_connections])

    @event.listens_for(engine, "before_cursor_execute")
    def before(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        first = statement.split(None, 1)[0].upper() if statement.strip() else "OTHER"
        verb = (
            first
            if first
            in {"SELECT", "INSERT", "UPDATE", "DELETE", "BEGIN", "COMMIT", "ROLLBACK"}
            else "OTHER"
        )
        span = telemetry.traces.get_tracer("buildwise").start_span("db." + verb)
        active = use_span(
            span,
            end_on_exit=True,
            record_exception=False,
            set_status_on_exception=False,
        )
        active.__enter__()
        context.buildwise_query = (perf_counter(), verb, span, active)

    def finish(context: Any, error: Exception | None = None) -> None:
        state = getattr(context, "buildwise_query", None)
        if state is None:
            return
        context.buildwise_query = None
        started, verb, span, active = state
        if error:
            span.set_status(StatusCode.ERROR)
            span.set_attribute("error.type", type(error).__name__)
        duration.record(perf_counter() - started, {"statement.verb": verb})
        active.__exit__(None, None, None)

    @event.listens_for(engine, "after_cursor_execute")
    def after(
        conn: Any,
        cursor: Any,
        statement: Any,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        finish(context)

    @event.listens_for(engine, "handle_error")
    def failed(context: Any) -> None:
        finish(context.execution_context, context.original_exception)

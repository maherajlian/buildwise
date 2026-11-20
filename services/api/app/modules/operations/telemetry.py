from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from opentelemetry.trace import StatusCode

from app.telemetry.setup import Telemetry


@contextmanager
def generation(telemetry: Telemetry) -> Iterator[None]:
    tracer = telemetry.traces.get_tracer("buildwise.operations")
    meter = telemetry.metrics.get_meter("buildwise.operations")
    counter = meter.create_counter("operations_generation_total")
    duration = meter.create_histogram(
        "operations_generation_duration_seconds", unit="s"
    )
    started = perf_counter()
    outcome = "success"
    with tracer.start_as_current_span(
        "operations.generate", record_exception=False, set_status_on_exception=False
    ) as span:
        try:
            yield
        except Exception:
            outcome = "error"
            span.set_status(StatusCode.ERROR)
            raise
        finally:
            attributes = {"outcome": outcome}
            span.set_attribute("outcome", outcome)
            counter.add(1, attributes)
            duration.record(perf_counter() - started, attributes)

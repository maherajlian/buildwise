from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from opentelemetry.trace import StatusCode

from app.telemetry.setup import Telemetry


@contextmanager
def generation(telemetry: Telemetry) -> Iterator[None]:
    tracer = telemetry.traces.get_tracer("buildwise")
    meter = telemetry.metrics.get_meter("buildwise.operations")
    counter = meter.create_counter("operations_generation_total")
    duration = meter.create_histogram(
        "operations_generation_duration_seconds", unit="s"
    )
    started = perf_counter()
    outcome = "success"
    with tracer.start_as_current_span(
        "operations.generate",
        attributes={"buildwise.operation": "operations.generate"},
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            yield
        except Exception as exc:
            outcome = "error"
            span.set_status(StatusCode.ERROR)
            span.set_attribute("error.type", type(exc).__name__)
            meter.create_counter("buildwise_operation_errors_total").add(
                1,
                {
                    "buildwise.operation": "operations.generate",
                    "error.type": type(exc).__name__,
                },
            )
            raise
        finally:
            attributes = {"outcome": outcome}
            counter.add(1, attributes)
            duration.record(perf_counter() - started, attributes)

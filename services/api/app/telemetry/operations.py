import logging
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from time import perf_counter, sleep
from typing import Any, TypeVar

from fastapi import Request
from opentelemetry.trace import StatusCode

from app.telemetry.setup import Telemetry

current: ContextVar[Telemetry | None] = ContextVar("telemetry", default=None)
F = TypeVar("F", bound=Callable[..., Any])
COUNTERS = {
    "projects.create": "buildwise_projects_created_total",
    "recommendations": "buildwise_recommendation_runs_total",
    "artifacts": "buildwise_artifact_generation_total",
    "tasks": "buildwise_task_generation_total",
    "exports": "buildwise_export_total",
}


@contextmanager
def operation(telemetry: Telemetry, name: str) -> Iterator[None]:
    meter = telemetry.metrics.get_meter("buildwise")
    attrs = {"buildwise.operation": name}
    started = perf_counter()
    with telemetry.traces.get_tracer("buildwise").start_as_current_span(
        name, attributes=attrs, record_exception=False, set_status_on_exception=False
    ) as span:
        try:
            yield
        except Exception as exc:
            span.set_status(StatusCode.ERROR)
            span.set_attribute("error.type", type(exc).__name__)
            meter.create_counter("buildwise_operation_errors_total").add(
                1, {**attrs, "error.type": type(exc).__name__}
            )
            logging.getLogger("buildwise").error(
                "operation_failed", extra={"error_type": type(exc).__name__}
            )
            raise
        else:
            if name in COUNTERS and name != "artifacts":
                meter.create_counter(COUNTERS[name]).add(1)
        finally:
            if name == "rules":
                meter.create_histogram(
                    "buildwise_rule_evaluation_duration_seconds", unit="s"
                ).record(perf_counter() - started)


def observed(name: str) -> Callable[[F], F]:
    def decorate(fn: F) -> F:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            request = next(
                (v for v in (*args, *kwargs.values()) if isinstance(v, Request)), None
            )
            telemetry = request.app.state.telemetry if request else current.get()
            if telemetry is None:
                return fn(*args, **kwargs)
            token = current.set(telemetry)
            try:
                with operation(telemetry, name):
                    if request and request.app.state.settings.app_env != "production":
                        fault = os.getenv("FAULT_INJECTION", "")
                        if fault == name + ":slow":
                            sleep(3)
                        elif fault == name + ":fail":
                            raise RuntimeError("Injected failure")
                    result = fn(*args, **kwargs)
                    if name == "artifacts":
                        for item in result:
                            telemetry.metrics.get_meter("buildwise").create_counter(
                                COUNTERS[name]
                            ).add(1, {"buildwise.artifact.type": item.kind})
                    return result
            finally:
                current.reset(token)

        return wrapped  # type: ignore[return-value]

    return decorate

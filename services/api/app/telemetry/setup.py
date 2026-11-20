import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import unquote

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import Histogram, MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.core.settings import Settings


class JsonFormatter(logging.Formatter):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def format(self, record: logging.LogRecord) -> str:
        context = trace.get_current_span().get_span_context()
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "service": self.settings.otel_service_name,
            "environment": self.settings.app_env,
            "event": record.getMessage(),
            "trace_id": format(context.trace_id, "032x"),
            "span_id": format(context.span_id, "016x"),
        }
        for key in ("method", "route", "status_code", "duration_ms", "error_type"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info and record.exc_info[0]:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload)


class ExportFailureFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self.reported = False

    def filter(self, record: logging.LogRecord) -> bool:
        if self.reported:
            return False
        self.reported = True
        record.msg = "telemetry_export_failed"
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        return True


@dataclass
class Telemetry:
    traces: TracerProvider
    metrics: MeterProvider
    logs: LoggerProvider
    handler: logging.Handler | None

    def shutdown(self) -> None:
        if self.handler:
            logging.getLogger("buildwise").removeHandler(self.handler)
        self.traces.shutdown()
        self.metrics.shutdown()
        self.logs.shutdown()


def configure_telemetry(
    settings: Settings,
    span_exporter: SpanExporter | None = None,
    metric_reader: MetricReader | None = None,
) -> Telemetry:
    set_global_textmap(TraceContextTextMapPropagator())
    export_logger = logging.getLogger("opentelemetry")
    export_logger.handlers.clear()
    export_logger.propagate = False
    export_stream = logging.StreamHandler()
    export_stream.setFormatter(JsonFormatter(settings))
    export_stream.addFilter(ExportFailureFilter())
    export_logger.addHandler(export_stream)
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": os.getenv("APP_VERSION")
            or os.getenv("RENDER_GIT_COMMIT", "")[:7]
            or "dev",
            "deployment.environment": settings.app_env,
        }
    )
    traces = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.otel_traces_sampler_arg)),
    )
    logs = LoggerProvider(resource=resource)
    if span_exporter:
        traces.add_span_processor(SimpleSpanProcessor(span_exporter))
    readers = [metric_reader] if metric_reader else []
    handler = LoggingHandler(logger_provider=logs)
    if settings.otel_exporter_otlp_endpoint:
        endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
        headers = dict(
            (key.strip(), unquote(value.strip()))
            for entry in settings.otel_exporter_otlp_headers.split(",")
            if "=" in entry
            for key, value in [entry.split("=", 1)]
        )
        traces.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=endpoint + "/v1/traces", headers=headers, timeout=1
                ),
                max_queue_size=512,
                max_export_batch_size=128,
            )
        )
        logs.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=endpoint + "/v1/logs", headers=headers, timeout=1
                ),
                max_queue_size=512,
                max_export_batch_size=128,
            )
        )
        readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=endpoint + "/v1/metrics", headers=headers, timeout=1
                ),
                export_interval_millis=60000,
            )
        )
        handler = LoggingHandler(logger_provider=logs)
    metrics = MeterProvider(
        resource=resource,
        metric_readers=readers,
        views=[
            View(
                instrument_type=Histogram,
                aggregation=ExplicitBucketHistogramAggregation(
                    [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 3, 5]
                ),
            )
        ],
    )
    logger = logging.getLogger("buildwise")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for old in list(logger.handlers):
        logger.removeHandler(old)
    stream = logging.StreamHandler()
    stream.setFormatter(JsonFormatter(settings))
    logger.addHandler(stream)
    if handler:
        logger.addHandler(handler)
    if settings.app_env == "production" and os.getenv("FAULT_INJECTION"):
        logger.warning("fault_injection_ignored")
    return Telemetry(traces, metrics, logs, handler)

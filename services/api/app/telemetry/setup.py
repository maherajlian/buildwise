import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import unquote

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.core.settings import Settings


class JsonFormatter(logging.Formatter):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def format(self, record: logging.LogRecord) -> str:
        context = trace.get_current_span().get_span_context()
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "severity": record.levelname,
                "service": self.settings.otel_service_name,
                "environment": self.settings.app_env,
                "event": record.getMessage(),
                "trace_id": format(context.trace_id, "032x"),
                "span_id": format(context.span_id, "016x"),
            }
        )


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


def configure_telemetry(settings: Settings) -> Telemetry:
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env,
        }
    )
    traces = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.otel_traces_sampler_arg)),
    )
    logs = LoggerProvider(resource=resource)
    readers = []
    handler = None
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
    metrics = MeterProvider(resource=resource, metric_readers=readers)
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
    return Telemetry(traces, metrics, logs, handler)

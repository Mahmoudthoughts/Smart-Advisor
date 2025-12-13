from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.semconv.resource import ResourceAttributes

logger = logging.getLogger("ibkr_service.telemetry")


def _get_env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def setup_telemetry(app: FastAPI) -> None:
    """Configure OTLP tracing/logging/metrics if TELEMETRY_ENABLED=true."""

    if not _get_env_bool("TELEMETRY_ENABLED", False):
        logger.info("Telemetry disabled for ibkr_service")
        return

    service_name = os.getenv("TELEMETRY_SERVICE_NAME", "ibkr-service")
    otlp_endpoint = os.getenv("TELEMETRY_OTLP_ENDPOINT", "http://otel-collector:4317")
    insecure = _get_env_bool("TELEMETRY_OTLP_INSECURE", True)
    sample_ratio = float(os.getenv("TELEMETRY_SAMPLE_RATIO", "1.0"))
    traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", otlp_endpoint)
    metrics_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", otlp_endpoint)
    logs_endpoint = os.getenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", otlp_endpoint)

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "dev"),
        }
    )

    trace_provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(sample_ratio)),
    )
    span_exporter = OTLPSpanExporter(endpoint=traces_endpoint, insecure=insecure)
    trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=metrics_endpoint, insecure=insecure)
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint=logs_endpoint, insecure=insecure)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    LoggingInstrumentor().instrument(set_logging_format=True, log_hook=_attach_trace_ids)
    SystemMetricsInstrumentor().instrument()
    FastAPIInstrumentor.instrument_app(app, tracer_provider=trace_provider)
    logger.info("Telemetry enabled for ibkr_service, endpoint=%s, insecure=%s", otlp_endpoint, insecure)


def _attach_trace_ids(record: logging.LogRecord, _: Any) -> None:
    span = trace.get_current_span()
    span_ctx = span.get_span_context()
    if span_ctx is None or not span_ctx.is_valid:
        return
    record.trace_id = format(span_ctx.trace_id, "032x")
    record.span_id = format(span_ctx.span_id, "016x")

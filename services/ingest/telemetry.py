"""OpenTelemetry setup for the ingest service."""

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
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
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
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

_INIT = False
_METRIC_EXPORT_INTERVAL_MS = 10000


def _enabled() -> bool:
    # Enable when exporter endpoint or exporter name is provided
    return bool(
        os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or os.getenv("OTEL_TRACES_EXPORTER")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )


def _build_resource() -> Resource:
    service_name = os.getenv("OTEL_SERVICE_NAME", "smart-advisor-ingest")
    attributes: dict[str, Any] = {
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_NAMESPACE: "smart-advisor",
    }
    return Resource.create(attributes)


def _build_exporter_options() -> dict[str, Any]:
    options: dict[str, Any] = {"insecure": True}
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        options["endpoint"] = endpoint
    return options


def setup_telemetry(app: FastAPI, engine: AsyncEngine | None = None) -> None:
    global _INIT
    if _INIT:
        return
    if not _enabled():
        logger.info("Telemetry disabled for ingest (no OTEL exporter configured)")
        return

    resource = _build_resource()
    sampler = ParentBased(TraceIdRatioBased(1.0))

    exporter_options = _build_exporter_options()

    tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(**exporter_options)))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://otel-collector:4317"), insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=_METRIC_EXPORT_INTERVAL_MS)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", "http://otel-collector:4317"), insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)
    LoggingInstrumentor().instrument(set_logging_format=False)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider, meter_provider=meter_provider)
    # Instrument httpx so outbound Alpha Vantage calls are traced and context propagates
    HTTPXClientInstrumentor().instrument()
    SystemMetricsInstrumentor().instrument(meter_provider=meter_provider)

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=tracer_provider)

    _INIT = True
    logger.info("Ingest telemetry initialised")


__all__ = ["setup_telemetry"]

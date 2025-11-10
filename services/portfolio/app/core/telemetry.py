"""OpenTelemetry helpers for the portfolio microservice."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
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

from .config import PortfolioSettings

logger = logging.getLogger(__name__)

_TELEMETRY_INITIALISED = False
_METRIC_EXPORT_INTERVAL_MS = 10000


def _build_resource(settings: PortfolioSettings) -> Resource:
    attributes: dict[str, Any] = {
        ResourceAttributes.SERVICE_NAME: settings.telemetry_service_name or settings.app_name,
        ResourceAttributes.SERVICE_NAMESPACE: "smart-advisor",
    }
    return Resource.create(attributes)


def setup_telemetry(app: FastAPI, settings: PortfolioSettings, engine: AsyncEngine | None = None) -> None:
    """Configure tracing, metrics and logging exporters once for the process."""

    global _TELEMETRY_INITIALISED  # noqa: PLW0603

    if _TELEMETRY_INITIALISED:
        return

    if not settings.telemetry_enabled:
        logger.info("Telemetry disabled via configuration")
        return

    resource = _build_resource(settings)
    sampler = ParentBased(TraceIdRatioBased(settings.telemetry_sample_ratio))

    tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    span_processor = BatchSpanProcessor(OTLPSpanExporter(**_exporter_options(settings)))
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(**_exporter_options(settings)),
                export_interval_millis=_METRIC_EXPORT_INTERVAL_MS,
            )
        ],
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(**_exporter_options(settings)))
    )
    set_logger_provider(logger_provider)
    LoggingInstrumentor().instrument(set_logging_format=False)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )
    SystemMetricsInstrumentor().instrument(meter_provider=meter_provider)

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,
            tracer_provider=tracer_provider,
        )

    _TELEMETRY_INITIALISED = True
    logger.info("Telemetry initialised")


def _exporter_options(settings: PortfolioSettings) -> dict[str, Any]:
    options: dict[str, Any] = {"insecure": settings.telemetry_otlp_insecure}
    if settings.telemetry_otlp_endpoint:
        options["endpoint"] = settings.telemetry_otlp_endpoint
    return options


__all__ = ["setup_telemetry"]

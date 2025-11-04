"""OpenTelemetry configuration helpers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.semconv.resource import ResourceAttributes
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import AppSettings

logger = logging.getLogger(__name__)

_TELEMETRY_INITIALISED = False


def _build_resource(settings: AppSettings) -> Resource:
    attributes: dict[str, Any] = {
        ResourceAttributes.SERVICE_NAME: settings.telemetry_service_name or settings.app_name,
        ResourceAttributes.SERVICE_NAMESPACE: "smart-advisor",
    }
    return Resource.create(attributes)


def setup_telemetry(app: FastAPI, settings: AppSettings, engine: AsyncEngine | None = None) -> None:
    """Configure tracing exporters and instrument FastAPI plus SQLAlchemy."""

    global _TELEMETRY_INITIALISED  # noqa: PLW0603 - single initialisation guard

    if _TELEMETRY_INITIALISED:
        return

    if not settings.telemetry_enabled:
        logger.info("Telemetry disabled via configuration")
        return

    resource = _build_resource(settings)
    sampler = ParentBased(TraceIdRatioBased(settings.telemetry_sample_ratio))
    provider = TracerProvider(resource=resource, sampler=sampler)

    exporter_options: dict[str, Any] = {"insecure": settings.telemetry_otlp_insecure}
    if settings.telemetry_otlp_endpoint:
        exporter_options["endpoint"] = settings.telemetry_otlp_endpoint

    span_processor = BatchSpanProcessor(OTLPSpanExporter(**exporter_options))
    provider.add_span_processor(span_processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

    _TELEMETRY_INITIALISED = True
    logger.info("Telemetry initialised and instrumentation enabled")


__all__ = ["setup_telemetry"]

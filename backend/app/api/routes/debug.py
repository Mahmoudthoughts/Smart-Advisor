"""Debug endpoints for CORS and tracing header propagation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from opentelemetry import trace
from opentelemetry.propagate import inject

router = APIRouter()


@router.get("/cors-test")
async def cors_trace_test(request: Request, response: Response) -> dict[str, Any]:
    """Echo incoming trace headers and inject current context into response headers.

    Use this to validate that browsers can read trace headers (via CORS expose) and
    that trace context is flowing from frontend → backend.
    """

    # Capture incoming headers of interest
    received_traceparent = request.headers.get("traceparent")
    received_tracestate = request.headers.get("tracestate")
    received_baggage = request.headers.get("baggage")

    # Inject current context into headers to send back
    injected: dict[str, str] = {}
    try:
        inject(injected)
        for key, val in injected.items():
            response.headers[key] = val
    except Exception:
        # Best-effort; keep running even if injection fails
        pass

    # Include an easy-to-read trace ID in response headers
    span = trace.get_current_span()
    ctx = span.get_span_context()
    trace_id_hex = f"{ctx.trace_id:032x}" if ctx and ctx.is_valid else None
    if trace_id_hex:
        response.headers["x-trace-id"] = trace_id_hex

    return {
        "status": "ok",
        "received": {
            "traceparent": received_traceparent,
            "tracestate": received_tracestate,
            "baggage": received_baggage,
        },
        "injected": injected,
        "active_trace_id": trace_id_hex,
    }


__all__ = ["router"]

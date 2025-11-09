from __future__ import annotations

from typing import Any

import httpx
from opentelemetry.propagate import inject


class IngestServiceError(RuntimeError):
    pass


async def trigger_price_ingest(symbol: str, base_url: str, run_sync: bool = True) -> dict[str, Any]:
    """
    Call the ingest microservice to ingest prices for a symbol.
    When run_sync=True, the service runs the job inline and returns rows ingested.
    """
    url = f"{base_url.rstrip('/')}/jobs/prices"
    params = {"run_sync": "true" if run_sync else "false"}
    headers: dict[str, str] = {}
    # Inject current trace context so ingest service links to backend span
    try:
        inject(headers)
    except Exception:
        # Best-effort; tracing injection is optional
        pass
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json={"symbol": symbol}, params=params, headers=headers)
    if resp.status_code >= 400:
        try:
            payload = resp.json()
            detail = payload.get("detail", payload)
        except Exception:
            detail = resp.text
        raise IngestServiceError(f"Ingest service error {resp.status_code}: {detail}")
    return resp.json()

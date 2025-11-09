# Smart Advisor – Operations and Developer Guide

This document describes how the Smart Advisor services run together, how to operate them in Docker Compose, and how developers should integrate with the ingest microservice.

## Overview

- Services:
  - `backend` (FastAPI): API, auth, portfolio logic, snapshot recompute, proxies ingest health.
  - `frontend` (Angular + NGINX): UI served on port 4200 (mapped to container port 80).
  - `db` (PostgreSQL): primary datastore.
  - `ingest` (FastAPI): microservice that fetches Alpha Vantage data and writes to DB.
  - Optional: `otel-collector` (not included in this repo) for OpenTelemetry export.

## Quick Start

- Build and run all services:
  - `docker compose up --build`
- Frontend: `http://localhost:4200`
- Backend: `http://localhost:8000`
  - Health: `GET /health`
  - Ingest health proxy: `GET /ingest/health`
- Ingest service: `http://localhost:8100`
  - Health: `GET /health`

## Networking

- Compose network DNS names map to service names (`backend`, `ingest`, `db`).
- Backend calls ingest via `http://ingest:8100` inside the Compose network. Externally you can reach ingest via `http://localhost:8100`.

## Environment Variables

### Backend (service: `backend`)

- `DATABASE_URL` – `postgresql+asyncpg://smart_advisor:smart_advisor@db:5432/smart_advisor`
- `ALPHAVANTAGE_API_KEY` – API key for provider calls (search, etc.).
- `INGEST_BASE_URL` – base URL for ingest service (default set in Compose to `http://ingest:8100`).
- Telemetry (optional):
  - `TELEMETRY_ENABLED`: `true|false`
  - `TELEMETRY_SERVICE_NAME`: `smart-advisor`
  - `OTEL_*` envs for OTLP exporters (see `docker-compose.yml`).

### Ingest (service: `ingest`)

- `DATABASE_URL` – same DSN used by backend.
- `ALPHAVANTAGE_API_KEY` – provider key.
- `ALPHAVANTAGE_REQUESTS_PER_MINUTE` – throttle (default 5).
- `BASE_CURRENCY` – fallback currency for rows when provider omits it (default `USD`).
- OpenTelemetry:
  - `OTEL_SERVICE_NAME`: `smart-advisor-ingest`.
  - `OTEL_RESOURCE_ATTRIBUTES`: e.g., `deployment.environment=dev,service.version=1.0.0`.
  - `OTEL_TRACES_EXPORTER`: `otlp` with `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` set to collector, protocol `grpc`.
  - `OTEL_LOGS_EXPORTER`, `OTEL_METRICS_EXPORTER` and corresponding `OTEL_EXPORTER_OTLP_*_ENDPOINT`.

## Ingest Architecture and API

### Backend integration

- Backend does not ingest in-process. It always calls ingest microservice.
- Endpoints triggering ingest:
  - `POST /portfolio/watchlist` – when adding a symbol, backend calls `POST {INGEST_BASE_URL}/jobs/prices?run_sync=true`.
  - `POST /symbols/{symbol}/refresh` – refresh endpoint calls the same ingest job synchronously.
- After ingest completes, backend recomputes snapshots and returns counts.
- Health proxy:
  - `GET /ingest/health` → backend calls `GET {INGEST_BASE_URL}/health` and returns `{ status: ok, upstream: ... }`, or `{ status: disabled }` if not configured.

### Ingest microservice API

- `GET /health` → `{ status, rate_limit, base_currency }`
- `POST /jobs/prices?run_sync=true|false` body `{ "symbol": "AAPL" }`
  - `run_sync=true` (used by backend): runs job inline and returns `{ symbol, rows }`.
  - `run_sync=false`: schedules job in background and returns `{ status: "scheduled", symbol }`.
- `POST /jobs/fx?run_sync=true|false` body `{ from_ccy, to_ccy }`

### Incremental ingest behavior

- On initial load (no rows for symbol): uses `outputsize=full` and upserts all data.
- On subsequent runs: uses `outputsize=compact` (last ~100 days) and only upserts rows whose `date >= last_ingested_date - 5 days`.
- Large gaps: if `today - last_ingested_date > 90 days`, service switches to a one-time `full` fetch to catch up.
- All writes are idempotent via `ON CONFLICT DO UPDATE` on `(symbol, date)`.

## Telemetry

### Backend

- Controlled by settings in `backend/app/config/settings.py` and enabled in `backend/app/main.py`.
- Exports traces, metrics, and logs to the configured OTLP collectors.

### Ingest service

- `services/ingest/telemetry.py` instruments FastAPI, SQLAlchemy, logging, and system metrics.
- Enabled when `OTEL_*` exporter envs are present (Compose provides defaults pointing to `otel-collector:4317`).
- Service name: `smart-advisor-ingest`.

## Operations

### Health checks

- Backend: `GET /health` → readiness metadata.
- Ingest (direct): `GET http://localhost:8100/health`.
- Ingest via backend proxy: `GET http://localhost:8000/ingest/health`.

### Common tasks

- Refresh data for a symbol (via UI): use the Symbol Detail page “Refresh data” button.
- Add a symbol to watchlist: triggers ingest for that symbol and updates dashboards.

### Troubleshooting

- Backend returns 503 on refresh/add:
  - Verify ingest is running: `curl http://localhost:8100/health`.
  - Verify backend can reach ingest: `curl http://backend:8000/ingest/health` from inside the Compose network or `curl http://localhost:8000/ingest/health` externally.
  - Check `INGEST_BASE_URL` is set in backend environment.
- Rate limits from Alpha Vantage:
  - Increase `ALPHAVANTAGE_REQUESTS_PER_MINUTE` conservatively; watch provider terms.
- Telemetry not visible:
  - Ensure `otel-collector` is reachable at the configured endpoints and exporters are enabled.

## Developer Notes

- Ingest code lives under `services/ingest`. Main entrypoint: `services/ingest/main.py`.
- Incremental logic: `services/ingest/prices.py` (see comments at the top for the algorithm).
- Backend-to-ingest client is in `backend/app/ingest/client.py`.
- To change backfill window or gap threshold, update `services/ingest/prices.py` or promote them to env-config in `services/ingest/config.py` (and document in this file).

## Security

- Do not commit real provider keys; use env vars and `.env` files not checked into VCS.
- CORS in backend allows local dev origins only.

## Versioning

- Compose pins images with tags for frontend/backend; rebuild when code changes.


# Smart Advisor – Operations and Developer Guide

This document describes how the Smart Advisor services run together, how to operate them in Docker Compose, and how developers should integrate with the ingest microservice.

## Overview

- Services:
  - `backend` (FastAPI): API + auth gateway that proxies portfolio endpoints and orchestrates ingest jobs.
  - `portfolio` (FastAPI): owns portfolio/watchlist/account CRUD, snapshot recompute, and emits outbox events.
  - `frontend` (Angular + NGINX): UI served on port 4200 (mapped to container port 80).
  - `db` (PostgreSQL): primary datastore shared across services.
  - `ingest` (FastAPI): microservice that fetches price data (Alpha Vantage or IBKR) and writes to DB.
  - `ibkr` (FastAPI): bridge over the IB Gateway/TWS session that delivers historical bars and symbol search.
  - Optional: `otel-collector` (not included in this repo) for OpenTelemetry export.

## Quick Start

- Build and run all services:
  - `docker compose up --build`
- Frontend: `http://localhost:4200`
- Backend: `http://localhost:8000`
  - Health: `GET /health`
  - Ingest health proxy: `GET /ingest/health`
- Portfolio service: `http://localhost:8200`
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
- `PORTFOLIO_SERVICE_URL` – base URL for the portfolio service (Compose points to `http://portfolio:8200/portfolio`).
- `PORTFOLIO_SERVICE_TOKEN` – shared secret sent via `X-Internal-Token` when proxying to the portfolio service.
- `IBKR_SERVICE_URL` – base URL for the IBKR bridge (`http://ibkr:8110` in Compose) used by `/symbols/search`.
- `AUTHORIZATION` / `X-User-Id` headers – every application request now carries a bearer token; the backend uses it to resolve the current user and forwards their ID to the portfolio service via `X-User-Id` so each account sees only its own trades.
- Telemetry (optional):
  - `TELEMETRY_ENABLED`: `true|false`
  - `TELEMETRY_SERVICE_NAME`: `smart-advisor`
  - `OTEL_*` envs for OTLP exporters (see `docker-compose.yml`).

### Portfolio (service: `portfolio`)

- `DATABASE_URL` – async SQLAlchemy DSN pointed at the shared Postgres database.
- `INGEST_SERVICE_URL` – ingest base URL used when watchlist changes require price history.
- `INTERNAL_AUTH_TOKEN` – optional shared secret that must match the backend `PORTFOLIO_SERVICE_TOKEN` value.
- `X-User-Id` header – required on all proxied calls; identifies the requesting user’s portfolio.
- Telemetry:
  - `TELEMETRY_ENABLED`
  - `TELEMETRY_SERVICE_NAME` (defaults to `portfolio-service`).
  - `TELEMETRY_OTLP_ENDPOINT`, `TELEMETRY_OTLP_INSECURE`, `TELEMETRY_SAMPLE_RATIO` – configure OTLP exporters similar to backend/ingest.

### Ingest (service: `ingest`)

- `DATABASE_URL` – same DSN used by backend.
- `PRICE_PROVIDER` – `alpha_vantage` (default) or `ibkr` to switch sources without changing callers.
- `ALPHAVANTAGE_API_KEY` – provider key (required when `PRICE_PROVIDER=alpha_vantage`).
- `ALPHAVANTAGE_REQUESTS_PER_MINUTE` – throttle (default 5 for Alpha Vantage).
- `BASE_CURRENCY` – fallback currency for rows when provider omits it (default `USD`).
- IBKR provider tuning (used when `PRICE_PROVIDER=ibkr`):
  - `IBKR_HOST` (default `host.docker.internal`) and `IBKR_PORT` (default `4001`) to reach a local Gateway/TWS.
  - `IBKR_CLIENT_ID` – stable client ID (default `1`).
  - `IBKR_MARKET_DATA_TYPE` – `1` real-time, `3` delayed (default `3`).
  - `IBKR_USE_RTH` – use regular trading hours (default `true`).
  - `IBKR_DURATION_DAYS`, `IBKR_BAR_SIZE`, `IBKR_WHAT_TO_SHOW` – historical window and bar settings.
- OpenTelemetry:
  - `OTEL_SERVICE_NAME`: `smart-advisor-ingest`.
  - `OTEL_RESOURCE_ATTRIBUTES`: e.g., `deployment.environment=dev,service.version=1.0.0`.
  - `OTEL_TRACES_EXPORTER`: `otlp` with `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` set to collector, protocol `grpc`.
  - `OTEL_LOGS_EXPORTER`, `OTEL_METRICS_EXPORTER` and corresponding `OTEL_EXPORTER_OTLP_*_ENDPOINT`.

## Ingest Architecture and API

### Backend integration

- Backend does not ingest in-process. It always calls ingest microservice.
- Endpoints triggering ingest:
  - `POST /portfolio/watchlist` – backend proxies to the portfolio service which, after persisting the symbol, calls `POST {INGEST_SERVICE_URL}/jobs/prices?run_sync=true`.
  - `POST /symbols/{symbol}/refresh` – refresh endpoint calls the same ingest job synchronously.
- After ingest completes, the portfolio service recomputes snapshots and returns counts via the backend proxy.
- Requests hitting `/portfolio/*`, `/accounts/*`, and `/symbols/*` (timeline/refresh/missed-days) must include a valid bearer token; the backend uses it to look up the current user and forwards that identity via `X-User-Id` when calling the portfolio service so data stays tenant-scoped.
- Health proxy:
  - `GET /ingest/health` → backend calls `GET {INGEST_BASE_URL}/health` and returns `{ status: ok, upstream: ... }`, or `{ status: disabled }` if not configured.

### Ingest microservice API

- `GET /health` → `{ status, price_provider, rate_limit, base_currency }`
- `POST /jobs/prices?run_sync=true|false` body `{ "symbol": "AAPL" }`
  - `run_sync=true` (used by backend): runs job inline and returns `{ symbol, rows }`.
  - `run_sync=false`: schedules job in background and returns `{ status: "scheduled", symbol }`.
- `POST /jobs/fx?run_sync=true|false` body `{ from_ccy, to_ccy }`

### Incremental ingest behavior

- On initial load (no rows for symbol): uses `outputsize=full` and upserts all data.
- On subsequent runs: uses `outputsize=compact` (last ~100 days) and only upserts rows whose `date >= last_ingested_date - 5 days`.
- Large gaps: if `today - last_ingested_date > 90 days`, service switches to a one-time `full` fetch to catch up.
- All writes are idempotent via `ON CONFLICT DO UPDATE` on `(symbol, date)`.
- Setting `PRICE_PROVIDER=ibkr` routes `/jobs/prices` to the IBKR client, which connects once to the configured Gateway/TWS host, pulls historical bars, and upserts to `DailyBar` with the same schema.

## Telemetry

### Backend

- Controlled by settings in `backend/app/config/settings.py` and enabled in `backend/app/main.py`.
- Exports traces, metrics, and logs to the configured OTLP collectors.

### Portfolio service

- `services/portfolio/app/core/telemetry.py` instruments FastAPI, SQLAlchemy, logging, and system metrics.
- Enabled when `TELEMETRY_ENABLED=true` and OTLP exporter options are provided (Compose wires defaults pointing to `otel-collector:4317`).
- Emits spans for portfolio CRUD, ingest client calls, and snapshot recomputes using the service name `portfolio-service`.

### Ingest service

- `services/ingest/telemetry.py` instruments FastAPI, SQLAlchemy, logging, and system metrics.
- Enabled when `OTEL_*` exporter envs are present (Compose provides defaults pointing to `otel-collector:4317`).
- Service name: `smart-advisor-ingest`.

### End-user identity propagation (frontend → backend → ingest)

- Frontend:
  - Use `setUserTelemetry({ id, email?, role? })` from `frontend/src/app/telemetry-user.ts` after login and on user changes.
  - The interceptor `frontend/src/app/http-baggage.interceptor.ts` adds a W3C `baggage` header on every request with `enduser.*` entries.
  - Existing fetch/XMLHttpRequest instrumentations propagate `traceparent` headers for tracing.
- Backend:
  - Middleware in `backend/app/main.py` reads baggage (`enduser.id`, `enduser.email`, `enduser.role`) and sets these as span attributes.
  - httpx instrumentation + explicit propagation ties backend → ingest spans in the same trace.
- Ingest:
  - Middleware in `services/ingest/main.py` mirrors the same baggage → span attribute mapping.
- Privacy and PII:
  - Prefer stable internal user IDs over emails when possible.
  - Do not include sensitive data (names, phone numbers) in baggage.
  - Ensure telemetry stores and dashboards are access-controlled.

## Operations

### Health checks

- Backend: `GET /health` → readiness metadata.
- Portfolio: `GET http://localhost:8200/health`.
- Ingest (direct): `GET http://localhost:8100/health`.
- Ingest via backend proxy: `GET http://localhost:8000/ingest/health`.

### Common tasks

- Refresh data for a symbol (via UI): use the Symbol Detail page “Refresh data” button.
- Add a symbol to watchlist: triggers ingest for that symbol and updates dashboards.

### Troubleshooting

- Backend returns 503 on refresh/add:
  - Verify the portfolio service is healthy: `curl http://localhost:8200/health`.
  - Verify ingest is running: `curl http://localhost:8100/health`.
  - Verify backend can reach ingest: `curl http://backend:8000/ingest/health` from inside the Compose network or `curl http://localhost:8000/ingest/health` externally.
  - Check `PORTFOLIO_SERVICE_URL`, `PORTFOLIO_SERVICE_TOKEN`, and `INGEST_BASE_URL` are set in backend environment.
- Rate limits from Alpha Vantage:
  - Increase `ALPHAVANTAGE_REQUESTS_PER_MINUTE` conservatively; watch provider terms.
- Telemetry not visible:
  - Ensure `otel-collector` is reachable at the configured endpoints and exporters are enabled.

## IBKR bridge service

- Location: `services/ibkr_service` (FastAPI app served on port 8110 by Compose).
- Endpoints:
  - `POST /prices` – fetch historical bars for a symbol through the Gateway/TWS session (ingest service consumes this when `PRICE_PROVIDER=ibkr`).
  - `GET /symbols/search?query=...` – lightweight wrapper around IBKR’s `reqMatchingSymbols`; backend `/symbols/search` uses this when `IBKR_SERVICE_URL` is set so watchlist search/add/refresh all share the same data provider.
- Configure the backend with `IBKR_SERVICE_URL` (default `http://ibkr:8110` in Compose) so symbol search requests can reach the bridge. For local development outside Compose, run `uvicorn services.ibkr_service.main:app --reload --port 8110` (requires a reachable IB Gateway/TWS host).

## Developer Notes

- Portfolio domain logic lives in `services/portfolio/app`. The FastAPI router under `app/api/routes/portfolio.py` exposes the REST contract consumed by the backend proxy and persists domain events to the `portfolio_outbox` table.
- Ingest code lives under `services/ingest`. Main entrypoint: `services/ingest/main.py`.
- Incremental logic: `services/ingest/prices.py` (see comments at the top for the algorithm).
- Backend-to-ingest client is in `backend/app/ingest/client.py`.
- To change backfill window or gap threshold, update `services/ingest/prices.py` or promote them to env-config in `services/ingest/config.py` (and document in this file).

## Security

- Do not commit real provider keys; use env vars and `.env` files not checked into VCS.
- CORS in backend allows local dev origins only.

## Versioning

- Compose pins images with tags for frontend/backend; rebuild when code changes.

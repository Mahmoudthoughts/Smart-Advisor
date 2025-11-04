# Smart Advisor Platform

This repository now ships with a Python analytics backend, a PostgreSQL schema, and an Angular frontend that together deliver the Smart Advisor experience.

- `backend/` — Python package that rebuilds positions, computes hypothetical liquidation metrics, and now exposes FastAPI endpoints for multi-user authentication. Includes a Dockerfile for containerized execution and pytest coverage.
- `frontend/` — Angular workspace with login/registration flows, responsive advisor dashboards, and ngx-echarts visualisations (auto-resize aware navigation + chart layouts). Served through NGINX with SPA routing configured in `frontend/nginx.conf`.
- `backend/sql/schema.sql` — DDL for the PostgreSQL schema used by the authentication system and shared portfolios.

## Running with Docker Compose

The repository includes a `docker-compose.yml` file that orchestrates the backend API, PostgreSQL, and the Angular build served through NGINX.

```bash
docker compose up --build
```

Services exposed locally:

- **Backend API:** http://localhost:8000 (FastAPI with `/auth/register`, `/auth/login`, `/health`)
- **Angular Frontend:** http://localhost:4200 (served from the production build)
- **PostgreSQL:** localhost:5432 (credentials `smart_advisor`/`smart_advisor`)

The backend container now exposes the `ALPHAVANTAGE_API_KEY` environment variable so market data integrations can authenticate
against Alpha Vantage out of the box.

> **Note:** After updating frontend assets or `frontend/nginx.conf`, rebuild the frontend image so the single-page app fallback (deep-link support) picks up the changes:
> ```bash
> docker compose build frontend
> docker compose up -d frontend
> ```

When the compose stack starts, PostgreSQL loads `backend/sql/schema.sql` automatically to provision the required tables. The frontend communicates with the backend using the `environment.apiBaseUrl` value defined under `frontend/src/environments/`.

## Backend service layout

The `/backend/app` package now provides the Missed Opportunity Analyzer + Smart Advisor service skeleton described in `AGENT.md`:

- `app/main.py` — FastAPI app wiring and `/health` route.
- `app/config/settings.py` — Centralised configuration (Asia/Dubai timezone, USD base currency, Alpha Vantage API key + rate limits).
- `app/db/` — Declarative base and async session helpers.
- `app/models/` — SQLAlchemy models for Portfolio, Transaction, Lot, DailyBar, FXRate, DailyPortfolioSnapshot, SignalEvent, TickerSentimentDaily, AnalystSnapshot, ForecastDaily, MacroEvent, and DashboardKPI with required indexes.
- `app/providers/alpha_vantage.py` — Throttled Alpha Vantage client exposing `daily_adjusted` (TIME_SERIES_DAILY), `fx_daily`, `tech_indicator`, `news_sentiment`, and `econ_indicator` helpers.
- `app/ingest/` — Idempotent upsert jobs for TIME_SERIES_DAILY and FX_DAILY responses.
- `app/indicators/compute.py` — Pandas-powered SMA/EMA/RSI/MACD/ATR/volume-multiple indicators with caching.
- `app/rules/engine.py` — Boolean expression evaluation with cooldown tracking per rule.
- `app/services/snapshots.py` — FIFO/LIFO lot builder and daily P&L metrics per §3–§4 of the spec.
- `app/api/routes/` — Endpoints for timelines, top missed days, signal definitions/events, sentiment series, forecast stub, and simulator stub.
- `app/migrations/` — Alembic environment plus initial revision (see `app/migrations/versions/0001_initial.py` for SQL operations).

Utility scripts under `/backend/scripts` support ingestion, indicator recompute, snapshot rebuilds, and seed loading. Common workflows are wrapped in the backend `Makefile`:

```bash
cd backend
make dev              # Uvicorn with reload
make migrate          # Alembic upgrade head
make ingest SYMBOL=AAPL
make indicators SYMBOL=AAPL
make recompute SYMBOL=AAPL
make test
```

### OpenTelemetry

Tracing can be enabled without further code changes by exporting the following environment variables before launching the backend (e.g. `make dev`):

- `TELEMETRY_ENABLED=true`
- `TELEMETRY_SERVICE_NAME=smart-advisor-api` (optional; defaults to the logical service name)
- `TELEMETRY_OTLP_ENDPOINT=http://otel-collector:4317` (optional; default follows OpenTelemetry SDK conventions)
- `TELEMETRY_OTLP_INSECURE=true` when targeting an unsecured collector endpoint
- `TELEMETRY_SAMPLE_RATIO=1.0` for probabilistic sampling (0.0–1.0)

When enabled the FastAPI router and SQLAlchemy ORM emit spans through the OTLP gRPC exporter, so traces appear automatically in any standards-compliant collector.

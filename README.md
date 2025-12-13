# Smart Advisor Platform

This repository now ships with a Python analytics backend, a PostgreSQL schema, and an Angular frontend that together deliver the Smart Advisor experience.

For contributor/agent guidelines, see `AGENTS.md`.

- `backend/` — Python package that rebuilds positions, computes hypothetical liquidation metrics, and now exposes FastAPI endpoints for multi-user authentication. Includes a Dockerfile for containerized execution and pytest coverage.
- `frontend/` — Angular workspace with login/registration flows, responsive advisor dashboards, and ngx-echarts visualisations (auto-resize aware navigation + chart layouts). Served through NGINX with SPA routing configured in `frontend/nginx.conf`.
- `backend/sql/schema.sql` — DDL for the PostgreSQL schema used by the authentication system and shared portfolios.
- `services/ingest/` — Standalone Alpha Vantage ingest service that can run independently to populate the shared PostgreSQL schema or feed downstream consumers.
- `services/portfolio/` — Dedicated FastAPI portfolio service that owns transactions, watchlists, accounts, and snapshot recompute logic plus an outbox for domain events.

## Running with Docker Compose

The repository includes a `docker-compose.yml` file that orchestrates the backend API, PostgreSQL, and the Angular build served through NGINX.

```bash
docker compose up --build
```

Services exposed locally:

- **Backend API:** http://localhost:8000 (FastAPI with `/auth/register`, `/auth/login`, `/health`)
- **Angular Frontend:** http://localhost:4200 (served from the production build)
- **Ingest Service:** http://localhost:8100 (FastAPI `/health`, `/jobs/prices`, `/jobs/fx`)
- **IBKR Bridge:** http://localhost:8110 (FastAPI `/prices`, `/symbols/search` — talks to your IB Gateway/TWS session)
- **Portfolio Service:** http://localhost:8200 (FastAPI `/health`, `/portfolio/*` proxied internally by the backend)
- **PostgreSQL:** localhost:5432 (credentials `smart_advisor`/`smart_advisor`)

The backend and ingest containers expose the `ALPHAVANTAGE_API_KEY` environment variable so market data integrations can authenticate
against Alpha Vantage out of the box.

> **Note:** After updating frontend assets or `frontend/nginx.conf`, rebuild the frontend image so the single-page app fallback (deep-link support) picks up the changes:
> ```bash
> docker compose build frontend
> docker compose up -d frontend
> ```

When the compose stack starts, PostgreSQL loads `backend/sql/schema.sql` automatically to provision the required tables. The frontend communicates with the backend using the `environment.apiBaseUrl` value defined under `frontend/src/environments/`.

## Portfolio service

The portfolio microservice under `services/portfolio` now owns the portfolio domain models. It exposes the REST contract that the backend previously served and persists domain events into a Postgres-backed outbox table for downstream processing.

### Configuration

Compose wires the following environment variables (override as needed):

- `DATABASE_URL` — Async SQLAlchemy URL pointing at the shared PostgreSQL instance.
- `INGEST_SERVICE_URL` — Base URL for the ingest service so watchlist additions can request historical prices.
- `INTERNAL_AUTH_TOKEN` — Optional shared secret the backend must supply via the `X-Internal-Token` header.
- `X-User-Id` header — required on every request; identifies the authenticated user so the service can map calls to the correct portfolio.
- `TELEMETRY_*` — Mirrors the backend configuration to enable OTLP tracing/logging/metrics.

To run locally:

```bash
export DATABASE_URL=postgresql+asyncpg://smart_advisor:smart_advisor@localhost:5432/smart_advisor
export INGEST_SERVICE_URL=http://localhost:8100
uvicorn services.portfolio.app.main:app --reload --port 8200
```

The backend now proxies its `/portfolio` and `/accounts` endpoints to this service using the `PORTFOLIO_SERVICE_URL` and `PORTFOLIO_SERVICE_TOKEN` configuration keys. Set `IBKR_SERVICE_URL` (Compose defaults to `http://ibkr:8110`) so `/symbols/search` and watchlist actions fetch data through the IBKR bridge instead of Alpha Vantage. Every proxied call includes a bearer token plus `X-User-Id`; requests missing that identity are rejected to keep each user’s trades isolated.

## Ingest service

The ingest worker under `services/ingest` wraps the Alpha Vantage client and the idempotent price/FX upsert jobs so they can run as a dedicated service.

### Configuration

Set the following environment variables before starting the service (Compose wires sensible defaults):

- `DATABASE_URL` — Async SQLAlchemy URL pointing at the shared PostgreSQL instance (e.g. `postgresql+asyncpg://smart_advisor:smart_advisor@localhost:5432/smart_advisor`).
- `ALPHAVANTAGE_API_KEY` — Alpha Vantage API key.
- `ALPHAVANTAGE_REQUESTS_PER_MINUTE` — Optional throttle override (defaults to 5 req/min).
- `BASE_CURRENCY` — Fallback currency code applied when Alpha Vantage omits one (defaults to `USD`).

### Running standalone

```bash
export DATABASE_URL=postgresql+asyncpg://smart_advisor:smart_advisor@localhost:5432/smart_advisor
export ALPHAVANTAGE_API_KEY=demo
uvicorn services.ingest.main:app --reload --port 8100
```

The service exposes:

- `GET /health` — lightweight probe with rate-limit metadata.
- `POST /jobs/prices` — schedule or synchronously run an equity/ETF ingest (set `run_sync=true` to await completion). Body: `{ "symbol": "AAPL" }`.
- `POST /jobs/fx` — schedule or synchronously run an FX ingest. Body: `{ "from_ccy": "USD", "to_ccy": "AED" }`.

Jobs persist normalized rows into the existing schema:

- `daily_bar` (`symbol`, `date`, `adj_close`, `volume`, `currency`, `dividend_amount`, `split_coefficient`) via an upsert keyed on `(symbol, date)`.
- `fx_rate` (`date`, `from_ccy`, `to_ccy`, `rate_close`) via an upsert keyed on `(date, from_ccy, to_ccy)`.

Downstream processors can either read directly from these tables or plug into the job helpers (`services.ingest.prices.ingest_prices` / `services.ingest.fx.ingest_fx_pair`) to reroute records to a message broker.

## Recent UI changes and usage

- Collapsible sidebar (left)
  - Menu button moved to the left of the top bar next to the brand.
  - Drawer opens from the left, overlays content, and closes on backdrop click, Esc, or navigation.
  - Sidebar is scrollable to access all items and contains the user chip and a Sign out button.
  - Navigation customization (choose pages) now lives inside the drawer.
  - Files: `frontend/src/app/app.component.html|scss|ts`.

- Timeline date presets
  - Quick ranges: Week to date, Month to date, Last week, Last month, Last 3 months.
  - Presets update From/To and auto-refresh data (chart, table, transactions).
  - Manual editing of dates clears the active preset.
  - Files: `frontend/src/app/timeline/timeline.component.{html,ts,scss}`.

- Symbol detail ranges and enriched header
  - Range presets: 1D, 1W, 1M, 3M, 6M, 1Y, 5Y.
  - Header shows actual data: SYMBOL · Company Name · Region [· Currency] with higher contrast.
  - Region/currency are sourced via `searchSymbols()` best match when available.
  - Files: `frontend/src/app/symbol-detail/symbol-detail.component.{html,ts,scss}`.

- Theme toggle (light/dark)
  - Sun/Moon icon in the top bar toggles theme, persisted in `localStorage`.
  - Theming driven by CSS variables; dark mode applies `theme-dark` class to `<body>`.
  - Files: `frontend/src/styles.scss`, `frontend/src/app/app.component.{html,ts,scss}`.

- Global background
  - Default background switched to white for all pages; top bar now uses theme variables.
  - Files: `frontend/src/styles.scss`, `frontend/src/app/app.component.scss`.

- Decision log
  - Log per-investor planned moves, filter by symbol or status, and resolve items with outcome prices and notes.
  - Files: `frontend/src/app/decisions/decisions.component.{html,ts,scss}`.
- Transactions ledger
  - Inline editing plus delete actions keep the manual trade history clean; ledger recomputes portfolio metrics after each change.
  - Files: `frontend/src/app/transactions/transactions.component.{html,ts,scss}`, backend proxy `backend/app/api/routes/portfolio.py`, portfolio service routes/services.
- Administration dashboard
  - Manage Smart Advisor users (create, promote to admin, reset passwords) and configure stock list data providers with API keys/default selection.
  - Files: `frontend/src/app/admin/admin.component.{html,ts,scss}`, `frontend/src/app/admin.service.ts`, backend admin routes in `backend/smart_advisor/api/admin.py`.

- CORS and API proxy
  - Backend CORS expanded to allow `http://localhost[:4200]` and `http://127.0.0.1[:4200]` (fixes preflight 400 for auth).
  - Frontend NGINX proxies `/api/` → `backend:8000` to simplify production deployments.
  - Files: `backend/app/main.py`, `frontend/nginx.conf`.

### Tips

- Development login/register issues: if preflight fails, ensure backend is restarted after CORS changes: `docker compose restart backend`.
- For production, consider setting `environment.prod.ts` `apiBaseUrl` to `/api` to use the NGINX proxy and avoid CORS.
- The sidebar can be made light-themed by adjusting its background and text colors to theme variables if desired.

## Backend service layout

The `/backend/app` package now provides the Missed Opportunity Analyzer + Smart Advisor service skeleton described in `AGENT.md`:

- `app/main.py` — FastAPI app wiring and `/health` route.
- `app/config/settings.py` — Centralised configuration (Asia/Dubai timezone, USD base currency, Alpha Vantage API key + rate limits).
- `app/db/` — Declarative base and async session helpers.
- `app/models/` — SQLAlchemy models for Portfolio, Transaction, Lot, DailyBar, FXRate, DailyPortfolioSnapshot, SignalEvent, TickerSentimentDaily, AnalystSnapshot, ForecastDaily, MacroEvent, and DashboardKPI with required indexes.
- `app/providers/alpha_vantage.py` — Re-export of the shared Alpha Vantage client housed in `services/ingest/alpha_vantage.py`.
- `app/ingest/` — Backwards-compatible shims that point to the standalone ingest jobs under `services/ingest/`.
- `app/indicators/compute.py` — Pandas-powered SMA/EMA/RSI/MACD/ATR/volume-multiple indicators with caching.
- `app/rules/engine.py` — Boolean expression evaluation with cooldown tracking per rule.
- `app/services/snapshots.py` — FIFO/LIFO lot builder and daily P&L metrics per §3–§4 of the spec.
- `app/services/unrealized.py` — Unrealized gain/loss module with FIFO/LIFO/average cost aggregation, price-source abstraction, caching wrapper, and profit-target helper.
- `app/api/routes/` — Endpoints for timelines, top missed days, signal definitions/events, sentiment series, forecast stub, simulator stub, and the new `/decisions` log for investor choices and outcomes.
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

When enabled the FastAPI router and SQLAlchemy ORM emit spans through the OTLP gRPC exporter, **and** the runtime forwards structured application logs plus CPU/memory metrics (via the System Metrics instrumentation) to the same collector endpoint. Make sure your collector exposes OTLP gRPC on `otel-collector:4317` (or override `TELEMETRY_OTLP_ENDPOINT`) so spans, logs, and metrics land in the same pipeline.

The Angular frontend now boots with OpenTelemetry Web instrumentation as well. During local development (`ng serve`) it pushes document-load + fetch/XMLHttpRequest spans to `http://localhost:4318/v1/traces`; production builds (Docker) default to `http://otel-collector:4318/v1/traces`. Update the endpoints in `frontend/src/environments/` if your collector lives elsewhere, then rebuild the frontend image.

The IBKR bridge service (`services/ibkr_service`) now emits OTLP traces/logs/metrics when `TELEMETRY_ENABLED=true`. Configure it via:

- `TELEMETRY_SERVICE_NAME` (default `ibkr-service`)
- `TELEMETRY_OTLP_ENDPOINT` (default `http://otel-collector:4317`)
- `TELEMETRY_OTLP_INSECURE` (default `true`)
- `TELEMETRY_SAMPLE_RATIO` (default `1.0`)
- Connection parameters are read directly from `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`, `IBKR_MARKET_DATA_TYPE`, `IBKR_DURATION_DAYS`, `IBKR_BAR_SIZE`, `IBKR_WHAT_TO_SHOW`, `IBKR_USE_RTH`, and `IBKR_BASE_CURRENCY` (no extra prefix).

## Unrealized gain and profit-target module

`backend/app/services/unrealized.py` implements real + hypothetical lot tracking, unrealized P/L series generation, and profit-first target conversion with a swappable price provider.

- Configure a price provider: plug in `CachingPriceSource` around any provider that implements `get_price_series()`/`get_latest_price()`. The included `InMemoryPriceSource` is useful for fixtures; wire your own adapter to Alpha Vantage/IBKR and surface `price_field` plus `non_trading_day_policy` (snap prev/next or skip) as needed.
- Add lots:

```python
from decimal import Decimal
from datetime import date
from app.services.unrealized import LotStore, LotInput, LotType

store = LotStore()
store.add_lot(LotInput(lot_id="real-1", ticker="AAPL", buy_date=date(2024, 1, 2), shares=Decimal("10"), buy_price=Decimal("100"), type=LotType.REAL))
store.add_lot(LotInput(lot_id="hypo-1", ticker="AAPL", buy_date=date(2024, 2, 1), shares=Decimal("5"), buy_price=Decimal("90"), type=LotType.HYPOTHETICAL))
```

- Generate a report (date range, last N trading days, or explicit dates):

```python
from app.services.unrealized import InMemoryPriceSource, SimulationRequest, simulate_unrealized_series

prices = InMemoryPriceSource({"AAPL": {date(2024, 1, 2): {"close": "100"}, date(2024, 1, 3): {"close": "110"}}})
series = simulate_unrealized_series(
    prices,
    store,
    SimulationRequest(
        ticker="AAPL",
        last_n_trading_days=30,
        cost_mode="FIFO",
        price_field="close",
        non_trading_day_policy="SNAP_PREV_TRADING_DAY",
    ),
)
```

- Select a chart point and derive the equivalent target price:

```python
from decimal import Decimal
from app.services.unrealized import compute_target_from_point

target = compute_target_from_point(store, "AAPL", Decimal("500"))
```

Fees/tax controls live on `SimulationRequest` (`buy_fee`, `sell_fee`, `tax_rate`) and are applied uniformly across the series. To run the module tests locally:

```bash
pytest backend/tests/test_unrealized.py
```

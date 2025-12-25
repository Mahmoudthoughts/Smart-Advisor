# AGENTS.md — Smart Advisor Repo Guide for Agents

Purpose
- This file guides coding agents (Codex CLI, etc.) working in this repository.
- It defines project structure, conventions, and do/don’t practices to keep changes safe, minimal, and consistent.
- Scope: the entire repository unless a more specific AGENTS.md appears deeper in a directory.

Tech Stack
- Frontend: Angular (standalone components, Signals API), ngx-echarts, SCSS, served via NGINX.
- Backend: FastAPI (Python 3.11), SQLAlchemy (async), PostgreSQL, Alembic, OpenTelemetry optional.
- Orchestration: Docker Compose (db, backend, frontend).
  - Ingest microservice: FastAPI service under `services/ingest` (Alpha Vantage data fetcher), now the only path for price ingest.

Run & Build
- Compose: `docker compose up --build`
- Backend: http://localhost:8000 (health: `/health`, auth: `/auth/*`)
- Frontend: http://localhost:4200 (served by NGINX from production build)
- DB: `postgres://smart_advisor:smart_advisor@localhost:5432/smart_advisor`

API Base URL
- Dev: `frontend/src/environments/environment.ts` → `apiBaseUrl` (default `http://localhost:8000`).
- Prod: Prefer same-origin proxy via NGINX (`/api` → backend:8000). If you adopt this, set `environment.prod.ts` `apiBaseUrl` to `/api`.

CORS & Proxy
- Backend CORS allows `http://localhost[:4200]` and `http://127.0.0.1[:4200]` (preflight OPTIONS now succeeds for auth).
- Frontend NGINX proxies `/api/` to the backend container for production deployments.

Frontend Conventions
- Components are standalone. Import Angular features directly in the `imports: []` array of each component.
- State uses Angular Signals (`signal`, `computed`, `effect`). Prefer signals over RxJS component state where feasible.
- HTTP via `HttpClient` and `environment.apiBaseUrl`. Do not hardcode URLs.
- Charts via `ngx-echarts`. Keep `EChartsOption` immutable; update via `.set()` or `.update()` on a signal.
- Styling: SCSS with CSS variables in `frontend/src/styles.scss`. Use `var(--color-*)` tokens for theme-aware colors.
- Theming: body gets `.theme-dark` class for dark mode. Toggle with a button in the header (sun/moon icons). Persist to `localStorage` key `smart-advisor.theme`.
- Navigation: left-side collapsible drawer (scrollable). The menu button is on the left of the top bar.
- Timeline page: quick presets WTD/MTD/Last week/Last month/Last 3M; manual date changes clear preset and allow refresh.
- Symbol detail page: range presets 1D/1W/1M/3M/6M/1Y/5Y; header shows actual data (symbol · company · region [· currency]).
- Symbol detail trade plan: quick trade plan card uses intraday bars from `/symbols/{symbol}/intraday` to summarize midday dips and late-day recoveries.

Backend Conventions
- FastAPI app at `backend/app/main.py`. Routers in `backend/app/api/routes/`.
- Auth endpoints under `/auth`: `POST /auth/register`, `POST /auth/login`. See `backend/smart_advisor/api/auth.py` for token generation.
- DB sessions via async dependencies (`Depends(get_db)` or legacy `.get_session`).
- Migrations under `backend/app/migrations`.
- Portfolio data is user-scoped: attach `Depends(get_current_user)` to routes touching watchlists/transactions/timelines and pass `str(current_user.id)` into `app/services/portfolio` helpers so the `X-User-Id` header is forwarded downstream.
- Symbol search (`GET /symbols/search`) uses the IBKR bridge (`services/ibkr_service`) whenever `IBKR_SERVICE_URL` is configured so watchlist search/add flows share the same provider as refresh.
 - Ingest flow:
   - All price ingests are routed via the ingest microservice (no in-process fallback).
   - Backend endpoints that trigger ingest:
     - `POST /portfolio/watchlist` (on add) → calls ingest `POST /jobs/prices?run_sync=true`
     - `POST /symbols/{symbol}/refresh` → calls ingest `POST /jobs/prices?run_sync=true`
   - Ingest health proxy: `GET /ingest/health` forwards to the microservice `/health`.
   - Configure backend with `INGEST_BASE_URL` (Compose sets `http://ingest:8100`).

Ingest Microservice
- Location: `services/ingest` (FastAPI app, separate container `ingest`).
- Endpoints:
  - `GET /health` – lightweight health/status.
  - `POST /jobs/prices` – body `{ symbol }`, query `run_sync`: `true|false`.
  - `POST /jobs/fx` – body `{ from_ccy, to_ccy }`, query `run_sync`: `true|false`.
- Incremental ingest:
  - Initial run: `outputsize=full` and upsert all days.
  - Subsequent runs: `outputsize=compact`; only upsert days ≥ (last_ingested_date − 5 days).
  - If last ingested is older than 90 days, microservice uses a one-time `full` fetch to catch up.
- OpenTelemetry: enabled via OTLP envs (see Compose). Service name `smart-advisor-ingest`.
- IBKR bridge: FastAPI app under `services/ibkr_service` exposes `/prices` (ingest uses this when `PRICE_PROVIDER=ibkr`) and `/symbols/search` (backend search calls this when `IBKR_SERVICE_URL` is set).

User Telemetry Propagation
- Frontend attaches user identity to requests via a baggage-aware HTTP interceptor.
  - Set the user after login using `setUserTelemetry({ id, email?, role? })` exported from `frontend/src/app/telemetry-user.ts`.
  - The interceptor `frontend/src/app/http-baggage.interceptor.ts` injects a W3C `baggage` header (keys: `enduser.id`, `enduser.email`, `enduser.role`).
- Backend and ingest read baggage and annotate server spans with the same keys.
  - Middleware in `backend/app/main.py` and `services/ingest/main.py` sets span attributes when present.
- Privacy: avoid placing sensitive PII into baggage; prefer stable, non-guessable IDs.

Do
- Make minimal, surgical changes; keep existing structure and naming.
- Prefer CSS variables for color changes; avoid hardcoded colors where a token exists.
- Keep accessibility in mind: aria labels, keyboard support (Esc to close drawer), adequate color contrast.
- Update docs when adding visible features (README and this AGENTS.md).
  - When changing ingest behavior or env vars, also update `docs/operations-and-developer-guide.md`.
- When adding components: use standalone components, co-locate `.html/.ts/.scss`.

Don’t
- Don’t refactor unrelated modules or reformat entire files without need.
- Don’t hardcode API hosts; always use `environment.apiBaseUrl`.
- Don’t remove or bypass auth flows.
- Don’t rely on Angular’s generated `_ngcontent-*` attributes for styling (they change per build).

Testing & Validation
- Prefer verifying specific pages/components you change rather than running all tests (unless backend changes require it).
- For auth issues in dev, restart backend after CORS changes: `docker compose restart backend`.

Common Tasks
- Add a new nav item: update `allNavLinks` in `app.component.ts`, ensure route exists, and theme colors use CSS variables.
- Add a date preset: follow Timeline or Symbol Detail patterns; compute ISO `YYYY-MM-DD` strings and reload data.
- Extend symbol header data: enrich via `PortfolioDataService.searchSymbols()`; avoid blocking UI if provider data is missing.
- Manage transactions: inline edit/delete live in `frontend/src/app/transactions/transactions.component.*`; backend proxies (`/portfolio/transactions/{id}`) to the portfolio service, which now implements `DELETE` alongside POST/PUT.

File Map (UI features)
 - Header, sidebar, theme toggle, top tabs + mega dropdown: `frontend/src/app/app.component.{html,ts,scss}`
- Timeline presets: `frontend/src/app/timeline/timeline.component.{html,ts,scss}`
- Symbol ranges + header + trade plan: `frontend/src/app/symbol-detail/symbol-detail.component.{html,ts,scss}`
- Monte Carlo + AI Simulator: `frontend/src/app/montecarlo/montecarlo.component.{html,ts,scss}` (route `/app/montecarlo`, API `POST /risk/montecarlo/run`)
- Global styles + theme variables: `frontend/src/styles.scss`
- NGINX SPA + API proxy: `frontend/nginx.conf`
- Backend CORS: `backend/app/main.py`

Notes for Agents
- If a change affects multiple files, group related patches and keep context hunks minimal.
- Prefer additive patches; avoid file deletes unless replacing the full content (and only when necessary).
- If you must introduce new env vars or tokens, document them in README and here.
 - Ingest-related env vars to keep in sync:
   - Backend: `INGEST_BASE_URL`, `IBKR_SERVICE_URL`.
   - Ingest: `DATABASE_URL`, `ALPHAVANTAGE_API_KEY`, `ALPHAVANTAGE_REQUESTS_PER_MINUTE`, `BASE_CURRENCY`, OTEL envs.
- Portfolio service calls must include both `X-Internal-Token` (when configured) and `X-User-Id`; reuse the helpers under `app/services/portfolio.py` rather than issuing ad-hoc httpx requests.

This document applies to all subdirectories unless overridden by a deeper AGENTS.md.

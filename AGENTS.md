# AGENTS.md — Smart Advisor Repo Guide for Agents

Purpose
- This file guides coding agents (Codex CLI, etc.) working in this repository.
- It defines project structure, conventions, and do/don’t practices to keep changes safe, minimal, and consistent.
- Scope: the entire repository unless a more specific AGENTS.md appears deeper in a directory.

Tech Stack
- Frontend: Angular (standalone components, Signals API), ngx-echarts, SCSS, served via NGINX.
- Backend: FastAPI (Python 3.11), SQLAlchemy (async), PostgreSQL, Alembic, OpenTelemetry optional.
- Orchestration: Docker Compose (db, backend, frontend).

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

Backend Conventions
- FastAPI app at `backend/app/main.py`. Routers in `backend/app/api/routes/`.
- Auth endpoints under `/auth`: `POST /auth/register`, `POST /auth/login`. See `backend/smart_advisor/api/auth.py` for token generation.
- DB sessions via async dependencies (`Depends(get_db)` or legacy `.get_session`).
- Migrations under `backend/app/migrations`.

Do
- Make minimal, surgical changes; keep existing structure and naming.
- Prefer CSS variables for color changes; avoid hardcoded colors where a token exists.
- Keep accessibility in mind: aria labels, keyboard support (Esc to close drawer), adequate color contrast.
- Update docs when adding visible features (README and this AGENTS.md).
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

File Map (UI features)
- Header, sidebar, theme toggle: `frontend/src/app/app.component.{html,ts,scss}`
- Timeline presets: `frontend/src/app/timeline/timeline.component.{html,ts,scss}`
- Symbol ranges + header: `frontend/src/app/symbol-detail/symbol-detail.component.{html,ts,scss}`
- Global styles + theme variables: `frontend/src/styles.scss`
- NGINX SPA + API proxy: `frontend/nginx.conf`
- Backend CORS: `backend/app/main.py`

Notes for Agents
- If a change affects multiple files, group related patches and keep context hunks minimal.
- Prefer additive patches; avoid file deletes unless replacing the full content (and only when necessary).
- If you must introduce new env vars or tokens, document them in README and here.

This document applies to all subdirectories unless overridden by a deeper AGENTS.md.

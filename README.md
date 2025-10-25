# Smart Advisor Platform

This repository now ships with a Python analytics backend, a PostgreSQL schema, and an Angular frontend that together deliver the Smart Advisor experience.

- `backend/` — Python package that rebuilds positions, computes hypothetical liquidation metrics, and now exposes FastAPI endpoints for multi-user authentication. Includes a Dockerfile for containerized execution and pytest coverage.
- `frontend/` — Angular workspace with login/registration flows, guarded advisor dashboards, and ngx-echarts visualisations.
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

When the compose stack starts, PostgreSQL loads `backend/sql/schema.sql` automatically to provision the required tables. The frontend communicates with the backend using the `environment.apiBaseUrl` value defined under `frontend/src/environments/`.

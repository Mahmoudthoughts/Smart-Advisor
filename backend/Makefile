APP_MODULE=app.main:app
ENV_FILE?=.env

.PHONY: dev migrate ingest indicators recompute test

.ONESHELL:

dev:
	uvicorn $(APP_MODULE) --reload

migrate:
	alembic -c app/migrations/alembic.ini upgrade head

ingest:
	python scripts/ingest_prices.py --symbol $(SYMBOL)

indicators:
	python scripts/compute_indicators.py --symbol $(SYMBOL)

recompute:
	python scripts/recompute_snapshots.py --symbol $(SYMBOL)

test:
	pytest

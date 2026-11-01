# DRISHTI Ganjam — common tasks. Run `make help`.
API := services/api
WEB := apps/web
UV  := cd $(API) && uv run

.PHONY: help up down logs demo seed seed-reset migrate api web worker test test-api test-web lint fmt \
        backtest scenarios tokens build-web ci

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

up: ## Start the full stack with Docker Compose (db, redis, minio, api, worker, beat, web)
	docker compose up --build -d
	@echo "Web: http://localhost:8080   API: http://localhost:8000/api/v1/docs"

down: ## Stop the stack
	docker compose down

logs: ## Tail API logs
	docker compose logs -f api

demo: up ## Start the stack and reset demo data
	docker compose exec api python -m app.seed.loader --runtime

migrate: ## Apply DB migrations (local)
	$(UV) alembic upgrade head

seed: ## Load seed data if the DB is empty (local)
	$(UV) python -m app.seed.loader

seed-reset: ## Wipe and reload all seed data (local)
	$(UV) python -m app.seed.loader --reset

api: ## Run the API locally with reload
	$(UV) uvicorn app.main:app --reload --port 8000

web: ## Run the web dev server (proxies /api to :8000)
	cd $(WEB) && npm run dev

worker: ## Run a Celery worker locally
	$(UV) celery -A app.worker.celery_app worker -l info

test: test-api test-web ## Run all tests

test-api: ## Python tests (DB tests need PostGIS at TEST_DATABASE_URL)
	$(UV) pytest -q

test-web: ## Web unit tests
	cd $(WEB) && npm test

lint: ## Lint + typecheck everything
	$(UV) ruff check app tests alembic ../../scripts ../../ml
	$(UV) ruff format --check app tests alembic ../../scripts ../../ml
	cd $(WEB) && npm run -s lint && npm run -s typecheck && npm run -s format:check

fmt: ## Auto-format
	$(UV) ruff check --fix app tests alembic ../../scripts ../../ml
	$(UV) ruff format app tests alembic ../../scripts ../../ml
	cd $(WEB) && npm run -s format

backtest: ## Replay Titli + Phailin and write reports/backtest_*.md
	$(UV) python ../../ml/backtest/run.py

scenarios: ## Regenerate seed/scenarios/*.json (illustrative)
	$(UV) python ../../scripts/gen_scenarios.py

tokens: ## Regenerate CSS variables from packages/design-tokens/tokens.json
	node packages/design-tokens/build.mjs

build-web: ## Production build of the web app
	cd $(WEB) && npm run build

ci: lint test build-web ## What CI runs

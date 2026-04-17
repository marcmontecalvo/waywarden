SHELL := /bin/bash

.PHONY: bootstrap dev lint format test db-up db-down migrate run worker backup

bootstrap:
	uv sync --extra dev

dev:
	uv run uvicorn waywarden.app:app --app-dir src --reload --host 0.0.0.0 --port 8000

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest

db-up:
	docker compose -f infra/docker-compose.sidecars.yaml up -d postgres

db-down:
	docker compose -f infra/docker-compose.sidecars.yaml down

migrate:
	uv run alembic upgrade head

run:
	uv run uvicorn waywarden.app:app --app-dir src --host 0.0.0.0 --port 8000

worker:
	uv run python -m waywarden.todo.ea_profile.workers.scheduler

backup:
	uv run python scripts/backup_now.py

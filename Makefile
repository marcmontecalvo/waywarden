SHELL := /bin/bash

.PHONY: bootstrap dev lint format secret-scan test run migrate migrate-down

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

secret-scan:
	uv run pre-commit run gitleaks --all-files

test:
	uv run pytest

run:
	uv run uvicorn waywarden.app:app --app-dir src --host 0.0.0.0 --port 8000

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

.PHONY: install test lint format typecheck check up down

install:
	python -m pip install -e '.[dev]'

test:
	pytest --cov=creova --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

check: lint typecheck test

up:
	docker compose up -d postgres minio minio-init

down:
	docker compose down

UV ?= uv

.PHONY: venv install install-dev hooks-install lint typecheck format test check

venv:
	$(UV) venv .venv

install:
	$(UV) pip install -r requirements.txt

install-dev: venv
	$(UV) pip install -r requirements-dev.txt

hooks-install:
	$(UV) run pre-commit install
	$(UV) run pre-commit install --hook-type pre-push

lint:
	$(UV) run ruff check app tests

type-check:
	$(UV) run mypy app

format:
	$(UV) run ruff format app tests

test:
	$(UV) run pytest

check: lint type-check test

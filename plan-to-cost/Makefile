.PHONY: setup test lint format check
PY ?= python3

setup:
	$(PY) -m pip install -e ".[dev]"
test:
	$(PY) -m pytest
lint:
	ruff check src tests
	ruff format --check src tests
format:
	ruff format src tests
	ruff check --fix src tests
check: lint test

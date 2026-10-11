.PHONY: setup test lint format sample fetch heights build run serve check clean

PY ?= python3

setup:            ## create venv-free dev install (use a venv if you prefer)
	$(PY) -m pip install -e ".[dev]"

test:             ## run the test suite
	$(PY) -m pytest

lint:             ## static checks
	ruff check src tests
	ruff format --check src tests

format:           ## auto-format
	ruff format src tests
	ruff check --fix src tests

check: lint test  ## everything CI runs

sample:           ## synthetic end-to-end run -> web/data (works offline)
	$(PY) -m blm sample

fetch:            ## Catastro WFS -> data/interim/<area>/parts.parquet
	$(PY) -m blm fetch

heights:          ## PNOA LiDAR (data/raw/lidar/*.laz) -> heights per building part
	$(PY) -m blm heights

build:            ## parcels + buildable gap + validation -> web/data
	$(PY) -m blm build

run:              ## fetch -> heights (if .laz present) -> build
	$(PY) -m blm run

serve:            ## open http://localhost:8000
	cd web && $(PY) -m http.server 8000

clean:            ## remove generated data (keeps raw downloads)
	rm -rf data/interim/* data/processed/*
	touch data/interim/.gitkeep data/processed/.gitkeep

help:
	@grep -E '^[a-z]+:.*## ' Makefile | sed 's/:.*## /\t/'

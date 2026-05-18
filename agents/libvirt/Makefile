.PHONY: install dev test lint openapi run

VENV := .venv
PY := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
PIP := $(PY) -m pip

install:
	$(PIP) install -e ".[dev,libvirt]"

dev:
	$(PIP) install -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests

openapi:
	$(PY) scripts/export_openapi.py

run:
	$(PY) -m huy_libvirt_agent.main

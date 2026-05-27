.PHONY: compose-up compose-down compose-logs compose-ps test test-unit test-integration test-deps venv \
	test-huy-events test-iam test-registry test-inventory test-projects test-web

VENV ?= $(CURDIR)/.venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f --tail=100

compose-ps:
	docker compose ps

venv: $(VENV)/bin/python

$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(PIP) install -q -U pip setuptools wheel

test: test-unit

test-unit: venv test-deps test-huy-events test-iam test-registry test-inventory test-projects test-web

test-deps: venv
	$(PIP) install -q -e shared/huy_auth
	$(PIP) install -q -e "shared/huy_events[dev]"

test-huy-events: venv
	$(PIP) install -q -e "shared/huy_events[dev]"
	cd shared/huy_events && $(PYTEST) -q

test-iam: venv
	$(PIP) install -q -e "services/iam[dev]"
	cd services/iam && $(PYTEST) -q

test-registry: venv test-deps
	$(PIP) install -q -e "services/registry[dev]"
	cd services/registry && $(PYTEST) -q

test-inventory: venv test-deps
	$(PIP) install -q -e "services/inventory[dev]"
	cd services/inventory && $(PYTEST) -q

test-projects: venv test-deps
	$(PIP) install -q -e "services/projects[dev]"
	cd services/projects && $(PYTEST) -q

test-web:
	cd web && npm install && npm test

# Cross-service tests against docker compose (not part of default `make test`).
test-integration: venv test-deps
	$(PIP) install -q httpx pytest pytest-asyncio
	HUY_E2E=1 PYTHONPATH=tests/integration $(PYTEST) -q tests/integration

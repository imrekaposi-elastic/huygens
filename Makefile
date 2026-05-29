.PHONY: compose-up compose-down compose-logs compose-ps test test-unit test-integration test-ci test-deps venv \
	test-huy-auth test-huy-events test-huy-telemetry test-iam test-registry test-inventory test-projects test-compliance \
	test-agent-libvirt test-breakout-controller test-ssh-gateway test-web wait-stack \
	test-integration-stack test-integration-iam test-integration-registry test-integration-inventory \
	test-integration-projects test-integration-web

VENV ?= $(CURDIR)/.venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
INTEGRATION_DIR := tests/integration
PYTEST_INTEGRATION = HUY_E2E=1 PYTHONPATH=$(INTEGRATION_DIR) $(PYTEST) -q $(INTEGRATION_DIR)

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

# Matches default GitHub Actions CI (unit + integration).
test-ci: test-unit test-integration

test-unit: venv test-deps test-huy-auth test-huy-events test-huy-telemetry test-iam test-registry test-inventory test-projects test-compliance test-agent-libvirt test-breakout-controller test-ssh-gateway test-web

wait-stack:
	bash scripts/wait-for-stack.sh

test-deps: venv
	$(PIP) install -q -e shared/huy_auth
	$(PIP) install -q -e "shared/huy_events[dev]"
	$(PIP) install -q -e "shared/huy_telemetry[dev]"

test-huy-auth: venv
	$(PIP) install -q -e "shared/huy_auth[dev]"
	cd shared/huy_auth && $(PYTEST) -q

test-huy-events: venv
	$(PIP) install -q -e "shared/huy_events[dev]"
	cd shared/huy_events && $(PYTEST) -q

test-huy-telemetry: venv
	$(PIP) install -q -e "shared/huy_telemetry[dev]"
	cd shared/huy_telemetry && $(PYTEST) -q

test-iam: venv test-deps
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

test-compliance: venv test-deps
	$(PIP) install -q -e "services/compliance[dev]"
	cd services/compliance && $(PYTEST) -q

test-agent-libvirt: venv test-deps
	$(PIP) install -q -e "agents/libvirt[dev]"
	cd agents/libvirt && $(PYTEST) -q

test-breakout-controller:
	docker run --rm -v "$(CURDIR)/services/breakout-controller:/src" -w /src golang:1.25-bookworm go test ./...

test-ssh-gateway:
	docker run --rm -v "$(CURDIR)/services/ssh-gateway:/src" -w /src golang:1.25-bookworm go test ./...

test-web:
	cd web && npm install && npm test

# Cross-service tests against docker compose (not part of default `make test`).
test-integration: venv test-deps test-integration-deps \
	test-integration-stack test-integration-iam test-integration-registry \
	test-integration-inventory test-integration-projects test-integration-web

test-integration-deps: venv
	$(PIP) install -q httpx pytest pytest-asyncio

test-integration-stack: venv test-integration-deps
	$(PYTEST_INTEGRATION)/stack

test-integration-iam: venv test-integration-deps
	$(PYTEST_INTEGRATION)/iam

test-integration-registry: venv test-integration-deps
	$(PYTEST_INTEGRATION)/registry

test-integration-inventory: venv test-integration-deps
	$(PYTEST_INTEGRATION)/inventory

test-integration-projects: venv test-integration-deps
	$(PYTEST_INTEGRATION)/projects

test-integration-web: venv test-integration-deps
	$(PYTEST_INTEGRATION)/web

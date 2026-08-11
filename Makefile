PYTHON := uv run --project backend
PYTHONPATH := backend/src
TEST_DATABASE_URL ?= postgresql://postgres:postgres@127.0.0.1:55432/postgres
export NEXT_TELEMETRY_DISABLED := 1

.PHONY: clean-install lint typecheck test test-rls openapi-check web-build e2e-f001 docs-check architecture-check migration-authority-check

clean-install:
	uv sync --project backend --frozen --all-groups
	npm ci

lint: architecture-check migration-authority-check
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) ruff check backend scripts tests
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) ruff format --check backend scripts tests
	npm run lint

typecheck:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) mypy --config-file backend/pyproject.toml backend/src scripts
	npm run typecheck

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) pytest backend/tests tests -m "not rls"

test-rls:
	docker compose up -d --wait db
	cd backend && PYTHONPATH=src TEST_DATABASE_URL=$(TEST_DATABASE_URL) uv run python manage.py migrate --noinput
	PYTHONPATH=$(PYTHONPATH) TEST_DATABASE_URL=$(TEST_DATABASE_URL) $(PYTHON) pytest backend/tests -m rls

openapi-check:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) python scripts/generate_openapi.py --check
	./scripts/check_openapi_client.sh

web-build:
	npm run build --workspace @ai-lms/web

e2e-f001: web-build
	npm run test:e2e --workspace @ai-lms/e2e

docs-check:
	python3 scripts/docs_check.py

architecture-check:
	python3 scripts/check_architecture.py

migration-authority-check:
	python3 scripts/check_migration_authority.py

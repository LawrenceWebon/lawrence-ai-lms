COMPOSE := docker compose
BACKEND_EXEC := $(COMPOSE) exec -T backend
WEB_EXEC := $(COMPOSE) exec -T web
PYTHONPATH := backend/src

.PHONY: compose-up clean-install lint typecheck test test-rls openapi-check web-build e2e-f001 e2e-f002 e2e-f003 docs-check architecture-check migration-authority-check

compose-up:
	$(COMPOSE) up -d --build --wait

clean-install:
	$(COMPOSE) build --no-cache backend web

lint: architecture-check migration-authority-check
	$(BACKEND_EXEC) ruff check backend scripts tests
	$(BACKEND_EXEC) ruff format --check backend scripts tests
	$(WEB_EXEC) npm run lint

typecheck:
	$(BACKEND_EXEC) mypy --config-file backend/pyproject.toml backend/src scripts
	$(WEB_EXEC) npm run typecheck

test:
	$(BACKEND_EXEC) pytest backend/tests tests -m "not rls"

test-rls:
	$(BACKEND_EXEC) python backend/manage.py migrate --noinput
	$(BACKEND_EXEC) pytest backend/tests -m rls

openapi-check:
	$(BACKEND_EXEC) python scripts/generate_openapi.py --check
	$(WEB_EXEC) ./scripts/check_openapi_client.sh

web-build:
	$(WEB_EXEC) npm run build --workspace @ai-lms/web

e2e-f001: web-build
	$(WEB_EXEC) npm run test:e2e --workspace @ai-lms/e2e -- f001-foundation.spec.ts f001-integration.spec.ts f001-lane-d.spec.ts

e2e-f002: web-build
	$(WEB_EXEC) npm run test:e2e --workspace @ai-lms/e2e -- f002-course-editor.spec.ts

e2e-f003: web-build
	$(WEB_EXEC) npm run test:e2e --workspace @ai-lms/e2e -- f003-source-admission.spec.ts

docs-check:
	$(BACKEND_EXEC) python scripts/docs_check.py

architecture-check:
	$(BACKEND_EXEC) python scripts/check_architecture.py

migration-authority-check:
	$(BACKEND_EXEC) python scripts/check_migration_authority.py

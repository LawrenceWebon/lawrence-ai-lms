from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class DockerWorkflowContractTests(unittest.TestCase):
    def test_exact_tooling_images_and_frozen_installs_are_declared(self) -> None:
        backend = (REPO_ROOT / "docker/backend.Dockerfile").read_text(encoding="utf-8")
        web = (REPO_ROOT / "docker/web.Dockerfile").read_text(encoding="utf-8")

        self.assertIn(
            "python:3.14.7-slim-bookworm@sha256:"
            "23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52",
            backend,
        )
        self.assertIn("uv sync --project backend --frozen --all-groups", backend)
        self.assertIn(
            "node:24.19.0-bookworm-slim@sha256:"
            "3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03",
            web,
        )
        self.assertIn(
            "mcr.microsoft.com/playwright:v1.62.1-noble@sha256:"
            "dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e",
            web,
        )
        self.assertIn("npm ci", web)
        self.assertIn("PLAYWRIGHT_BROWSERS_PATH=/ms-playwright", web)

    def test_compose_exposes_reusable_tooling_services(self) -> None:
        compose = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")

        for service in ("db", "backend", "web"):
            self.assertRegex(compose, rf"(?m)^  {service}:$")
        self.assertIn("COMPOSE_PROJECT_NAME", compose)
        self.assertNotIn("- .:/workspace", compose)
        self.assertIn("./backend:/workspace/backend", compose)
        self.assertIn("./apps:/workspace/apps", compose)
        self.assertNotIn("/workspace/node_modules", compose)
        self.assertEqual(
            2,
            compose.count('user: "${AI_LMS_UID:-1000}:${AI_LMS_GID:-1000}"'),
        )
        self.assertIn("RUFF_CACHE_DIR: /tmp/ruff-cache", compose)
        self.assertIn("PYTEST_ADDOPTS: -o cache_dir=/tmp/pytest-cache", compose)
        self.assertIn("XDG_CACHE_HOME: /tmp/xdg-cache", compose)

    def test_make_targets_execute_project_tools_in_compose(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("COMPOSE := docker compose", makefile)
        self.assertIn("BACKEND_EXEC := $(COMPOSE) exec -T backend", makefile)
        self.assertIn("WEB_EXEC := $(COMPOSE) exec -T web", makefile)
        targets = (
            "lint",
            "typecheck",
            "test",
            "test-rls",
            "openapi-check",
            "web-build",
            "e2e-f001",
            "docs-check",
        )

        for target in targets:
            recipe_match = re.search(
                rf"(?ms)^{re.escape(target)}(?:\s*:[^\n]*)?\n(?P<recipe>(?:\t[^\n]*\n)+)",
                makefile,
            )
            self.assertIsNotNone(recipe_match, f"missing Make recipe for {target}")
            assert recipe_match is not None
            self.assertRegex(
                recipe_match.group("recipe"),
                r"\$\((?:BACKEND|WEB)_EXEC\)",
                f"{target} must execute project tools through a Compose service",
            )

        prohibited = ("uv sync", "uv run", "npm ci", "npm run", "python3 scripts/")
        for command in prohibited:
            self.assertNotIn(f"\t{command}", makefile)

    def test_worktree_and_dependency_directories_are_not_host_artifacts(self) -> None:
        dockerignore = (
            (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        )
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn(
            "/home/lawrence/Project Neo/worktrees/ai-lms/",
            agents,
        )
        for ignored in (".venv", "node_modules"):
            self.assertIn(ignored, dockerignore)

    def test_ci_starts_the_same_compose_contract(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertGreaterEqual(
            workflow.count("docker compose up -d --build --wait"), 3
        )
        self.assertNotIn("make clean-install", workflow)
        self.assertNotIn("npm ci", workflow)
        self.assertNotIn("uv sync", workflow)


if __name__ == "__main__":
    unittest.main()

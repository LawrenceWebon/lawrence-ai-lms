from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class StepZeroScaffoldContractTests(unittest.TestCase):
    def test_required_foundation_files_exist(self) -> None:
        required = {
            ".github/workflows/ci.yml",
            ".gitignore",
            ".node-version",
            ".python-version",
            "Makefile",
            "backend/manage.py",
            "backend/pyproject.toml",
            "backend/src/lms/api/main.py",
            "backend/src/lms/config/settings/base.py",
            "backend/src/lms/platform_database/migrations/0001_platform_baseline.py",
            "compose.yaml",
            "contracts/f001/auth-context.v1.schema.json",
            "contracts/f001/membership-administration.v1.schema.json",
            "contracts/openapi/openapi.json",
            "database/generated/data-dictionary.json",
            "database/security/role-catalog.json",
            "docs/evidence/f001-step-0/toolchain.md",
            "package-lock.json",
            "package.json",
            "packages/api-client/src/generated/schema.d.ts",
            "packages/test-data/src/f001.ts",
            "scripts/check_architecture.py",
            "scripts/check_migration_authority.py",
            "scripts/generate_openapi.py",
        }
        missing = sorted(path for path in required if not (REPO_ROOT / path).is_file())
        self.assertEqual([], missing, f"missing Step 0 files: {missing}")

    def test_makefile_exposes_stable_issue_commands(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        targets = {
            "lint",
            "typecheck",
            "test",
            "test-rls",
            "openapi-check",
            "web-build",
            "e2e-f001",
            "docs-check",
        }
        missing = sorted(
            target
            for target in targets
            if re.search(rf"(?m)^{re.escape(target)}\s*:", makefile) is None
        )
        self.assertEqual([], missing, f"missing Make targets: {missing}")

    def test_next_generated_types_are_reproducible(self) -> None:
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        web_package = json.loads(
            (REPO_ROOT / "apps/web/package.json").read_text(encoding="utf-8")
        )

        self.assertIn("next-env.d.ts", gitignore)
        self.assertEqual(
            "next typegen && tsc --noEmit",
            web_package["scripts"]["typecheck"],
        )

    def test_e2e_uses_the_production_web_surface(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        playwright_config = (REPO_ROOT / "apps/e2e/playwright.config.ts").read_text(
            encoding="utf-8"
        )

        self.assertRegex(makefile, r"(?m)^e2e-f001:\s+web-build$")
        self.assertIn("npm run start --workspace @ai-lms/web", playwright_config)
        self.assertNotIn("npm run dev --workspace @ai-lms/web", playwright_config)

    def test_deferred_capabilities_are_not_scaffolded(self) -> None:
        prohibited = {
            "backend/src/lms/modules/ai_companion",
            "backend/src/lms/modules/assessments",
            "backend/src/lms/modules/commerce",
            "backend/src/lms/modules/payments",
            "backend/src/lms/workers",
            "apps/worker",
            "infra/pinecone",
            "infra/qstash",
        }
        present = sorted(path for path in prohibited if (REPO_ROOT / path).exists())
        self.assertEqual([], present, f"deferred capability paths exist: {present}")

    def test_django_is_the_only_application_migration_authority(self) -> None:
        prohibited = {
            "database/migrations",
            "infra/supabase/migrations",
            "supabase/migrations",
        }
        present = sorted(path for path in prohibited if (REPO_ROOT / path).exists())
        self.assertEqual([], present, f"alternate migration histories exist: {present}")

        django_root = REPO_ROOT / "backend" / "src" / "lms"
        migration_files = list(django_root.glob("**/migrations/*.py"))
        self.assertTrue(migration_files, "Django migration baseline is missing")

    def test_frozen_contract_examples_validate_against_their_schemas(self) -> None:
        contract_dir = REPO_ROOT / "contracts" / "f001"
        pairs = (
            ("auth-context.v1.schema.json", "auth-context.v1.example.json"),
            (
                "membership-administration.v1.schema.json",
                "membership-administration.v1.example.json",
            ),
        )
        for schema_name, example_name in pairs:
            schema = json.loads(
                (contract_dir / schema_name).read_text(encoding="utf-8")
            )
            example = json.loads(
                (contract_dir / example_name).read_text(encoding="utf-8")
            )
            self.assertEqual(
                schema["$id"],
                example["$schema"],
                f"{example_name} must identify its exact schema",
            )

    def test_generated_artifacts_have_do_not_edit_headers(self) -> None:
        generated = (
            "contracts/openapi/openapi.json",
            "packages/api-client/src/generated/schema.d.ts",
            "database/generated/data-dictionary.json",
        )
        missing_markers = []
        for relative_path in generated:
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            if "GENERATED" not in content[:300] or "DO NOT EDIT" not in content[:300]:
                missing_markers.append(relative_path)
        self.assertEqual([], missing_markers)


if __name__ == "__main__":
    unittest.main()

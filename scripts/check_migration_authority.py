#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DJANGO_ROOT = REPO_ROOT / "backend" / "src" / "lms"


def main() -> int:
    violations: list[str] = []
    prohibited = (
        REPO_ROOT / "database" / "migrations",
        REPO_ROOT / "infra" / "supabase" / "migrations",
        REPO_ROOT / "supabase" / "migrations",
    )
    for path in prohibited:
        if path.exists():
            violations.append(
                f"alternate application migration history: {path.relative_to(REPO_ROOT)}"
            )

    migrations = sorted(DJANGO_ROOT.glob("**/migrations/*.py"))
    if not migrations:
        violations.append("no Django migration baseline exists")
    compose_path = REPO_ROOT / "compose.yaml"
    if compose_path.exists() and "docker-entrypoint-initdb.d" in compose_path.read_text(
        encoding="utf-8"
    ):
        violations.append("Compose mounts an alternate database initialization history")

    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1

    print(f"Migration authority check passed: {len(migrations)} Django files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

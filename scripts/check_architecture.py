#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend" / "src" / "lms"


def module_name(path: Path) -> str:
    return ".".join(
        path.relative_to(REPO_ROOT / "backend" / "src").with_suffix("").parts
    )


def imported_modules(tree: ast.AST) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def main() -> int:
    violations: list[str] = []
    for path in sorted(BACKEND_ROOT.rglob("*.py")):
        if "migrations" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = imported_modules(tree)
        relative = path.relative_to(REPO_ROOT)
        module = module_name(path)

        if module.startswith("lms.api"):
            forbidden = sorted(name for name in imports if ".models" in name)
            if forbidden:
                violations.append(
                    f"{relative}: API adapter imports models: {forbidden}"
                )
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "objects":
                    violations.append(
                        f"{relative}: API adapter accesses ORM manager directly"
                    )

        if ".admin" in module:
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in {
                    "save",
                    "delete",
                    "objects",
                }:
                    violations.append(
                        f"{relative}: Admin adapter mutates models directly"
                    )

        if module.startswith("lms.modules"):
            forbidden = sorted(
                name
                for name in imports
                if name == "fastapi"
                or name.startswith(("fastapi.", "lms.integrations"))
            )
            if forbidden:
                violations.append(
                    f"{relative}: domain imports adapter/provider: {forbidden}"
                )

    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1

    print("Architecture boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

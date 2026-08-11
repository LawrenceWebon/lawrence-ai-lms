#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"!?(?:\[[^\]]*\])\((?P<target>[^)]+)\)")


def document_paths() -> list[Path]:
    paths = [REPO_ROOT / "README.md", *REPO_ROOT.joinpath("docs").rglob("*.md")]
    return sorted(
        paths, key=lambda path: path.relative_to(REPO_ROOT).as_posix().casefold()
    )


def validate_links(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(content):
            target = match.group("target").strip().strip("<>")
            if (
                not target
                or target.startswith("#")
                or re.match(r"(?i)^(https?|mailto|tel|data):", target)
            ):
                continue
            path_only = unquote(target.split("#", 1)[0])
            if path_only and not (path.parent / path_only).exists():
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: missing local link '{target}'"
                )
    return errors


def expected_manifest(paths: list[Path]) -> dict[str, object]:
    documents: list[dict[str, object]] = []
    for path in paths:
        data = path.read_bytes()
        documents.append(
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    aggregate_input = "\n".join(
        f"{item['path']}:{item['bytes']}:{item['sha256']}" for item in documents
    )
    return {
        "schema_version": 2,
        "name": "LMS SaaS Master Architecture and Delivery Plan",
        "plan_approval_date": "2026-08-02",
        "generated_by": "scripts/generate-document-manifest.ps1",
        "checksum_algorithm": "SHA-256",
        "document_count": len(documents),
        "aggregate_sha256": hashlib.sha256(aggregate_input.encode()).hexdigest(),
        "documents": documents,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    paths = document_paths()
    expected = expected_manifest(paths)
    if args.write_manifest:
        rendered = (
            json.dumps(expected, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        (REPO_ROOT / "manifest.json").write_text(rendered, encoding="utf-8")
        print(f"Generated manifest.json for {len(paths)} files.")
        return 0

    errors = validate_links(paths)
    current_manifest = json.loads(
        (REPO_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    if current_manifest != expected:
        errors.append("manifest.json has drifted")
    if errors:
        print("\n".join(sorted(errors)), file=sys.stderr)
        return 1
    print(f"Documentation checks passed for {len(paths)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

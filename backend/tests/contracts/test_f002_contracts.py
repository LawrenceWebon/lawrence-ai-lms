from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contracts/f002/canonical-course.v1.schema.json"
EXAMPLE_PATH = REPO_ROOT / "contracts/f002/canonical-course.v1.example.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def content_projection(example: dict[str, Any]) -> dict[str, Any]:
    version = example["version"]
    return {
        "primary_locale": version["primary_locale"],
        "title": version["title"],
        "description": version["description"],
        "sections": [
            {
                "title": section["title"],
                "position": section["position"],
                "lessons": [
                    {
                        "title": lesson["title"],
                        "position": lesson["position"],
                        "is_required": lesson["is_required"],
                        "content_blocks": [
                            {
                                "kind": block["kind"],
                                "position": block["position"],
                                "document": block["document"],
                            }
                            for block in lesson["content_blocks"]
                        ],
                    }
                    for lesson in section["lessons"]
                ],
            }
            for section in example["sections"]
        ],
    }


def test_f002_example_matches_frozen_canonical_course_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(load_json(EXAMPLE_PATH))


def test_f002_example_has_matching_tenant_edges_and_canonical_content_hash() -> None:
    example = load_json(EXAMPLE_PATH)
    tenant_id = example["course"]["tenant_id"]
    course_id = example["course"]["id"]
    version_id = example["version"]["id"]
    assert example["version"]["tenant_id"] == tenant_id
    assert example["version"]["course_id"] == course_id

    for section in example["sections"]:
        assert section["tenant_id"] == tenant_id
        assert section["course_version_id"] == version_id
        for lesson in section["lessons"]:
            assert lesson["tenant_id"] == tenant_id
            assert lesson["course_version_id"] == version_id
            assert lesson["section_id"] == section["id"]
            for block in lesson["content_blocks"]:
                assert block["tenant_id"] == tenant_id
                assert block["course_version_id"] == version_id
                assert block["lesson_id"] == lesson["id"]

    canonical_bytes = json.dumps(
        content_projection(example),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    expected_hash = f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"
    assert example["version"]["content_hash"] == expected_hash


@pytest.mark.parametrize("forbidden_type", ["raw_html", "link", "image", "embed"])
def test_f002_contract_rejects_unapproved_content_nodes(forbidden_type: str) -> None:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)
    document = example["sections"][0]["lessons"][0]["content_blocks"][0]["document"]  # type: ignore[index]
    document["content"] = [{"type": forbidden_type}]  # type: ignore[index]

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(example)


def test_f002_contract_rejects_unknown_fields() -> None:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)
    example["provider_payload"] = {"unsafe": True}

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(example)

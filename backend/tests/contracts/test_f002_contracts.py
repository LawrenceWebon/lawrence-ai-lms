from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_SCHEMA_PATH = REPO_ROOT / "contracts/f002/canonical-course.v1.schema.json"
SNAPSHOT_EXAMPLE_PATH = REPO_ROOT / "contracts/f002/canonical-course.v1.example.json"
LIFECYCLE_SCHEMA_PATH = REPO_ROOT / "contracts/f002/course-lifecycle.v1.schema.json"
LIFECYCLE_EXAMPLES_PATH = REPO_ROOT / "contracts/f002/course-lifecycle.v1.examples.json"
EXPECTED_CONTENT_HASH = "sha256:f4e7e98f5fe8199a25ba5293d4a7a58e1f45b649941de8c0935282ae5845ec31"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_registry() -> Registry[Any]:
    schemas = [load_json(SNAPSHOT_SCHEMA_PATH), load_json(LIFECYCLE_SCHEMA_PATH)]
    return Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )


def validator_for(dto_name: str) -> Draft202012Validator:
    lifecycle_schema = load_json(LIFECYCLE_SCHEMA_PATH)
    return Draft202012Validator(
        {"$ref": f"{lifecycle_schema['$id']}#/$defs/{dto_name}"},
        registry=contract_registry(),
        format_checker=FormatChecker(),
    )


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


def canonical_content_hash(example: dict[str, Any]) -> str:
    canonical_bytes = json.dumps(
        content_projection(example),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode()
    return f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"


def require_unique_positions(items: Iterable[dict[str, Any]], path: str) -> None:
    positions = [item["position"] for item in items]
    if len(positions) != len(set(positions)):
        raise ValueError(f"duplicate position at {path}")


def validate_curriculum_semantics(sections: list[dict[str, Any]]) -> None:
    require_unique_positions(sections, "sections")
    for section in sections:
        require_unique_positions(section["lessons"], f"section:{section.get('id', 'new')}")
        for lesson in section["lessons"]:
            require_unique_positions(lesson["content_blocks"], f"lesson:{lesson.get('id', 'new')}")


def validate_snapshot_semantics(example: dict[str, Any]) -> None:
    tenant_id = example["course"]["tenant_id"]
    course_id = example["course"]["id"]
    version_id = example["version"]["id"]
    if example["version"]["tenant_id"] != tenant_id:
        raise ValueError("version tenant edge mismatch")
    if example["version"]["course_id"] != course_id:
        raise ValueError("version course edge mismatch")

    validate_curriculum_semantics(example["sections"])
    for section in example["sections"]:
        if section["tenant_id"] != tenant_id:
            raise ValueError("section tenant edge mismatch")
        if section["course_version_id"] != version_id:
            raise ValueError("section version edge mismatch")
        for lesson in section["lessons"]:
            if lesson["tenant_id"] != tenant_id:
                raise ValueError("lesson tenant edge mismatch")
            if lesson["course_version_id"] != version_id:
                raise ValueError("lesson version edge mismatch")
            if lesson["section_id"] != section["id"]:
                raise ValueError("lesson section edge mismatch")
            for block in lesson["content_blocks"]:
                if block["tenant_id"] != tenant_id:
                    raise ValueError("block tenant edge mismatch")
                if block["course_version_id"] != version_id:
                    raise ValueError("block version edge mismatch")
                if block["lesson_id"] != lesson["id"]:
                    raise ValueError("block lesson edge mismatch")

    if example["version"]["content_hash"] != canonical_content_hash(example):
        raise ValueError("content hash mismatch")


def test_f002_schemas_and_all_named_examples_are_executable() -> None:
    snapshot_schema = load_json(SNAPSHOT_SCHEMA_PATH)
    lifecycle_schema = load_json(LIFECYCLE_SCHEMA_PATH)
    examples = load_json(LIFECYCLE_EXAMPLES_PATH)
    Draft202012Validator.check_schema(snapshot_schema)
    Draft202012Validator.check_schema(lifecycle_schema)
    Draft202012Validator(
        lifecycle_schema,
        registry=contract_registry(),
        format_checker=FormatChecker(),
    ).validate(examples)

    for dto_name, example in examples.items():
        validator_for(dto_name).validate(example)


def test_f002_snapshot_example_matches_suite_and_exact_checksum() -> None:
    snapshot = load_json(SNAPSHOT_EXAMPLE_PATH)
    examples = load_json(LIFECYCLE_EXAMPLES_PATH)
    Draft202012Validator(load_json(SNAPSHOT_SCHEMA_PATH), format_checker=FormatChecker()).validate(
        snapshot
    )
    assert examples["CourseSnapshotV1"] == snapshot
    assert canonical_content_hash(snapshot) == EXPECTED_CONTENT_HASH
    assert snapshot["version"]["content_hash"] == EXPECTED_CONTENT_HASH
    validate_snapshot_semantics(snapshot)


@pytest.mark.parametrize("forbidden_type", ["raw_html", "link", "image", "embed"])
def test_f002_contract_rejects_unapproved_content_nodes(forbidden_type: str) -> None:
    schema = load_json(SNAPSHOT_SCHEMA_PATH)
    example = load_json(SNAPSHOT_EXAMPLE_PATH)
    document = example["sections"][0]["lessons"][0]["content_blocks"][0]["document"]
    document["content"] = [{"type": forbidden_type}]

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(example)


def test_f002_contract_rejects_unknown_fields() -> None:
    schema = load_json(SNAPSHOT_SCHEMA_PATH)
    example = load_json(SNAPSHOT_EXAMPLE_PATH)
    example["provider_payload"] = {"unsafe": True}

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(example)


def test_f002_semantics_reject_cross_tenant_edges() -> None:
    example = load_json(SNAPSHOT_EXAMPLE_PATH)
    example["sections"][0]["lessons"][0]["tenant_id"] = "00000000-0000-4000-8000-0000000000b2"

    with pytest.raises(ValueError, match="lesson tenant edge mismatch"):
        validate_snapshot_semantics(example)


def test_f002_semantics_reject_duplicate_positions() -> None:
    command = load_json(LIFECYCLE_EXAMPLES_PATH)["ReplaceCurriculumV1"]
    duplicate = copy.deepcopy(command["sections"][0])
    duplicate["id"] = "00000000-0000-4000-8000-00000000c202"
    command["sections"].append(duplicate)

    with pytest.raises(ValueError, match="duplicate position at sections"):
        validate_curriculum_semantics(command["sections"])


def test_f002_curriculum_identity_pair_allows_server_assigned_new_nodes() -> None:
    command = load_json(LIFECYCLE_EXAMPLES_PATH)["ReplaceCurriculumV1"]
    section = command["sections"][0]
    lesson = section["lessons"][0]
    block = lesson["content_blocks"][0]
    for node in (section, lesson, block):
        node.pop("id")
        node.pop("expected_row_version")

    validator_for("ReplaceCurriculumV1").validate(command)


def test_f002_semantics_reject_content_hash_mismatch() -> None:
    example = load_json(SNAPSHOT_EXAMPLE_PATH)
    example["version"]["content_hash"] = f"sha256:{'0' * 64}"

    with pytest.raises(ValueError, match="content hash mismatch"):
        validate_snapshot_semantics(example)


@pytest.mark.parametrize(
    ("dto_name", "mutation"),
    [
        ("UpdateCourseVersionV1", lambda body: body.clear()),
        ("UpdateCourseVersionV1", lambda body: body.update(title=None)),
        (
            "ReplaceCurriculumV1",
            lambda body: body["sections"][0].pop("expected_row_version"),
        ),
        (
            "TransitionCourseVersionV1",
            lambda body: body.update(transition="request_changes"),
        ),
        (
            "TransitionCourseVersionV1",
            lambda body: body.update(transition="publish"),
        ),
        (
            "TransitionCourseVersionV1",
            lambda body: body.update(reason_code="NOT_ALLOWED"),
        ),
        (
            "TransitionCourseVersionV1",
            lambda body: body.update(idempotency_key="must-be-a-header"),
        ),
    ],
)
def test_f002_contract_rejects_invalid_request_shapes(dto_name: str, mutation: Any) -> None:
    example = copy.deepcopy(load_json(LIFECYCLE_EXAMPLES_PATH)[dto_name])
    mutation(example)

    with pytest.raises(ValidationError):
        validator_for(dto_name).validate(example)


@pytest.mark.parametrize(
    "transition",
    [
        {"transition": "submit_review"},
        {"transition": "request_changes", "reason_codes": ["CONTENT_GAP"]},
        {"transition": "approve"},
        {"transition": "publish", "expected_course_row_version": 4},
        {
            "transition": "withdraw",
            "expected_course_row_version": 5,
            "reason_code": "AUTHOR_WITHDRAWAL",
        },
        {"transition": "archive", "reason_code": "RETENTION_APPROVED"},
    ],
)
def test_f002_transition_discriminators_are_executable(
    transition: dict[str, Any],
) -> None:
    command = {
        "expected_version_row_version": 3,
        "expected_content_hash": EXPECTED_CONTENT_HASH,
        **transition,
    }
    validator_for("TransitionCourseVersionV1").validate(command)


def test_f002_history_and_successor_examples_preserve_scope_and_identity() -> None:
    examples = load_json(LIFECYCLE_EXAMPLES_PATH)
    history = examples["CourseVersionHistoryV1"]
    versions = history["versions"]
    assert [version["version_number"] for version in versions] == [2, 1]
    assert all(version["tenant_id"] == history["tenant_id"] for version in versions)
    assert all(version["course_id"] == history["course_id"] for version in versions)
    assert [version["id"] for version in versions if version["is_current_published"]] == [
        history["current_published_version_id"]
    ]

    result = examples["SuccessorDraftResultV1"]
    snapshot = result["snapshot"]
    assert result["successor_version_id"] == snapshot["version"]["id"]
    assert result["source_version_id"] == snapshot["version"]["predecessor_version_id"]
    assert snapshot["version"]["status"] == "draft"
    validate_snapshot_semantics(snapshot)

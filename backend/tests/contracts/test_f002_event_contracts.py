from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_TYPES = (
    "course.version.submitted",
    "course.version.changes_requested",
    "course.version.approved",
    "course.version.published",
    "course.version.withdrawn",
    "course.version.archived",
    "course.version.successor_created",
)
FORBIDDEN_PAYLOAD_KEYS = {
    "title",
    "description",
    "lesson_text",
    "review_notes",
    "token",
    "provider_payload",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_f002_event_schemas_and_examples_are_executable_and_minimized() -> None:
    for event_type in EVENT_TYPES:
        root = REPO_ROOT / "contracts" / "events" / event_type
        schema = load(root / "v1.schema.json")
        example = load(root / "v1.example.json")

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)
        assert schema["properties"]["event_type"]["const"] == f"{event_type}.v1"
        assert example["event_type"] == f"{event_type}.v1"
        assert example["producer"] == "courses"
        assert example["privacy_class"] == "internal"
        assert FORBIDDEN_PAYLOAD_KEYS.isdisjoint(example["payload"])

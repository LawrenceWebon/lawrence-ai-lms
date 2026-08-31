from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_TYPES = (
    "document.ingestion.requested",
    "document.ingestion.ready",
    "document.ingestion.failed",
)
FORBIDDEN_KEYS = {
    "body",
    "bytes",
    "content",
    "declared_filename",
    "element_text",
    "evidence_reference",
    "lesson_text",
    "markdown",
    "object_key",
    "opaque_token",
    "private_locator",
    "prompt",
    "source_text",
    "target_url",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _nested_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _nested_keys(child)}
    return set()


def test_f004_ingestion_events_are_executable_scoped_and_content_minimized() -> None:
    for event_type in EVENT_TYPES:
        root = REPO_ROOT / "contracts" / "events" / event_type
        schema = _load(root / "v1.schema.json")
        example = _load(root / "v1.example.json")

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)
        assert schema["properties"]["event_type"]["const"] == f"{event_type}.v1"
        assert example["event_type"] == f"{event_type}.v1"
        assert example["producer"] == "documents"
        assert example["aggregate_type"] == "document_ingestion_run"
        assert example["aggregate_id"] == example["ingestion_run_id"]
        assert example["privacy_class"] == "internal"
        assert FORBIDDEN_KEYS.isdisjoint(_nested_keys(example))


def test_f004_failed_event_rejects_unbounded_reason_and_payload_content() -> None:
    root = REPO_ROOT / "contracts/events/document.ingestion.failed"
    schema = _load(root / "v1.schema.json")
    example = _load(root / "v1.example.json")

    invalid_reason = copy.deepcopy(example)
    invalid_reason["payload"]["reason_code"] = "PRIVATE_PROVIDER_MESSAGE"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(invalid_reason)

    leaked = copy.deepcopy(example)
    leaked["payload"]["source_text"] = "untrusted source content"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(leaked)

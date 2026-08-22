from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_TYPES = (
    "source.rights.declared",
    "source.store_authorization.activated",
    "source.version.quarantined",
    "source.admission.validation_requested",
    "source.version.admitted",
    "source.version.rejected",
    "source.version.cancelled",
    "source.rights.revoked",
    "source.removal.completed",
)
FORBIDDEN_KEYS = {
    "body",
    "bytes",
    "content",
    "declared_filename",
    "evidence_reference",
    "object_key",
    "opaque_token",
    "private_locator",
    "rights_holder_name",
    "signed_url",
    "target_url",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in nested_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in nested_keys(child)}
    return set()


def test_f003_event_schemas_are_concrete_executable_and_content_minimized() -> None:
    for event_type in EVENT_TYPES:
        root = REPO_ROOT / "contracts" / "events" / event_type
        schema = load(root / "v1.schema.json")
        example = load(root / "v1.example.json")

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)
        assert schema["properties"]["event_type"]["const"] == f"{event_type}.v1"
        assert example["event_type"] == f"{event_type}.v1"
        assert example["producer"] == "documents"
        assert example["aggregate_id"] == example["source_version_id"]
        assert example["privacy_class"] == "internal"
        assert FORBIDDEN_KEYS.isdisjoint(nested_keys(example))


def test_event_reason_families_reject_cross_event_values() -> None:
    cancelled_root = REPO_ROOT / "contracts/events/source.version.cancelled"
    cancelled_schema = load(cancelled_root / "v1.schema.json")
    invalid = load(cancelled_root / "v1.example.json")
    invalid["payload"]["reason_code"] = "RIGHTS_REVOKED"

    errors = list(Draft202012Validator(cancelled_schema).iter_errors(invalid))

    assert errors

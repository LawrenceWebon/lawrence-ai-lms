from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_f001_examples_match_frozen_json_schemas() -> None:
    pairs = (
        (
            "contracts/f001/auth-context.v1.schema.json",
            "contracts/f001/auth-context.v1.example.json",
        ),
        (
            "contracts/f001/membership-administration.v1.schema.json",
            "contracts/f001/membership-administration.v1.example.json",
        ),
    )

    for schema_path, example_path in pairs:
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(load_json(example_path))


def test_event_examples_match_frozen_event_schemas() -> None:
    event_types = (
        "tenant.invitation.created",
        "tenant.membership.activated",
        "tenant.membership.roles_changed",
        "tenant.membership.deactivated",
    )

    for event_type in event_types:
        schema = load_json(f"contracts/events/{event_type}/v1.schema.json")
        example = load_json(f"contracts/events/{event_type}/v1.example.json")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(example)
        assert example["event_type"] == f"{event_type}.v1"


def test_four_lane_fixture_suites_share_the_frozen_synthetic_dataset() -> None:
    schema = load_json("contracts/f001/synthetic-fixtures.v1.schema.json")
    Draft202012Validator.check_schema(schema)

    fixture_paths = sorted((REPO_ROOT / "contracts" / "f001" / "fixtures").glob("lane-*.v1.json"))
    assert [path.stem for path in fixture_paths] == [
        "lane-a-identity.v1",
        "lane-b-tenancy.v1",
        "lane-c-adapters.v1",
        "lane-d-web.v1",
    ]
    for path in fixture_paths:
        Draft202012Validator(schema).validate(json.loads(path.read_text(encoding="utf-8")))

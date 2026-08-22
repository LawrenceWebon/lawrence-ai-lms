from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[3]
FROZEN_SCHEMA = REPO_ROOT / "contracts/f007/learner-events.v1.schema.json"
FROZEN_EXAMPLES = REPO_ROOT / "contracts/f007/learner-events.v1.examples.json"
EVENTS = {
    "learning.enrollment.created": "EnrollmentCreatedV1",
    "learning.enrollment.revoked": "EnrollmentRevokedV1",
    "learning.lesson.progressed": "LessonProgressedV1",
    "learning.course.completed": "CourseCompletedV1",
    "learning.course.reopened": "CourseReopenedV1",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_learning_event_registry_paths_resolve_to_the_frozen_contract() -> None:
    frozen_schema = load(FROZEN_SCHEMA)
    frozen_examples = load(FROZEN_EXAMPLES)
    registry = Registry().with_resource(frozen_schema["$id"], Resource.from_contents(frozen_schema))

    for event_type, definition in EVENTS.items():
        root = REPO_ROOT / "contracts/events" / event_type
        schema = load(root / "v1.schema.json")
        example = load(root / "v1.example.json")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).validate(example)
        assert schema["$ref"].endswith(f"#/$defs/{definition}")
        assert example == frozen_examples[definition]
        assert example["event_type"] == f"{event_type}.v1"

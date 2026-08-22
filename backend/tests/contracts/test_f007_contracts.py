from __future__ import annotations

import copy
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[3]
F002_SCHEMA_PATH = REPO_ROOT / "contracts/f002/canonical-course.v1.schema.json"
PLAYBACK_SCHEMA_PATH = REPO_ROOT / "contracts/f007/learner-playback.v1.schema.json"
PLAYBACK_EXAMPLES_PATH = REPO_ROOT / "contracts/f007/learner-playback.v1.examples.json"
EVENT_SCHEMA_PATH = REPO_ROOT / "contracts/f007/learner-events.v1.schema.json"
EVENT_EXAMPLES_PATH = REPO_ROOT / "contracts/f007/learner-events.v1.examples.json"
FIXTURE_PATH = REPO_ROOT / "contracts/f007/fixtures/playback-fixtures.v1.json"
TECHNICAL_DECISIONS_PATH = (
    REPO_ROOT / "docs/features/07-learner-course-playback/technical-decisions.md"
)
READINESS_AUDIT_PATH = REPO_ROOT / "docs/features/07-learner-course-playback/readiness-audit.md"
PRODUCT_DECISIONS_PATH = REPO_ROOT / "docs/product/decisions.md"
LOCALE_PLAN_PATH = REPO_ROOT / "docs/plan/18-localization-accessibility.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_registry() -> Registry[Any]:
    schemas = [
        load_json(F002_SCHEMA_PATH),
        load_json(PLAYBACK_SCHEMA_PATH),
        load_json(EVENT_SCHEMA_PATH),
    ]
    return Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )


def validator_for(schema_path: Path, definition: str) -> Draft202012Validator:
    schema = load_json(schema_path)
    return Draft202012Validator(
        {"$ref": f"{schema['$id']}#/$defs/{definition}"},
        registry=contract_registry(),
        format_checker=FormatChecker(),
    )


def iter_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from iter_keys(nested)
    elif isinstance(value, list):
        for item in value:
            yield from iter_keys(item)


def test_f007_schemas_and_all_named_examples_are_executable() -> None:
    playback_schema = load_json(PLAYBACK_SCHEMA_PATH)
    event_schema = load_json(EVENT_SCHEMA_PATH)
    playback_examples = load_json(PLAYBACK_EXAMPLES_PATH)
    event_examples = load_json(EVENT_EXAMPLES_PATH)

    Draft202012Validator.check_schema(playback_schema)
    Draft202012Validator.check_schema(event_schema)
    Draft202012Validator(
        playback_schema,
        registry=contract_registry(),
        format_checker=FormatChecker(),
    ).validate(playback_examples)
    Draft202012Validator(
        event_schema,
        registry=contract_registry(),
        format_checker=FormatChecker(),
    ).validate(event_examples)

    for dto_name, example in playback_examples.items():
        validator_for(PLAYBACK_SCHEMA_PATH, dto_name).validate(example)
    for event_name, example in event_examples.items():
        validator_for(EVENT_SCHEMA_PATH, event_name).validate(example)


def test_f007_lesson_reuses_f002_rich_text_and_rejects_unsafe_content() -> None:
    lesson = load_json(PLAYBACK_EXAMPLES_PATH)["LessonPlaybackV1"]
    validator = validator_for(PLAYBACK_SCHEMA_PATH, "LessonPlaybackV1")
    validator.validate(lesson)

    unsafe = copy.deepcopy(lesson)
    document = unsafe["lesson"]["content_blocks"][0]["document"]
    document["content"] = [{"type": "raw_html", "html": "<script>unsafe()</script>"}]

    with pytest.raises(ValidationError):
        validator.validate(unsafe)


@pytest.mark.parametrize(
    ("dto_name", "forbidden_field", "forbidden_value"),
    [
        ("CreateEnrollmentV1", "tenant_id", "00000000-0000-4000-8000-0000000000a1"),
        ("CreateEnrollmentV1", "course_version_id", "00000000-0000-4000-8000-00000000c101"),
        ("RevokeEnrollmentV1", "actor_id", "00000000-0000-4000-8000-000000000301"),
        ("ProgressCommandV1", "idempotency_key", "body-key-is-not-authority"),
    ],
)
def test_f007_requests_reject_browser_authority_fields(
    dto_name: str, forbidden_field: str, forbidden_value: str
) -> None:
    example = load_json(PLAYBACK_EXAMPLES_PATH)[dto_name]
    example[forbidden_field] = forbidden_value

    with pytest.raises(ValidationError):
        validator_for(PLAYBACK_SCHEMA_PATH, dto_name).validate(example)


def test_f007_enrollment_status_and_revocation_time_are_consistent() -> None:
    enrollment = load_json(PLAYBACK_EXAMPLES_PATH)["EnrollmentV1"]
    validator = validator_for(PLAYBACK_SCHEMA_PATH, "EnrollmentV1")

    enrollment["revoked_at"] = "2026-08-21T00:10:00Z"
    with pytest.raises(ValidationError):
        validator.validate(enrollment)

    enrollment["status"] = "revoked"
    enrollment["revoked_at"] = None
    with pytest.raises(ValidationError):
        validator.validate(enrollment)


def test_f007_progress_contract_rejects_implicit_or_stale_shape() -> None:
    command = load_json(PLAYBACK_EXAMPLES_PATH)["ProgressCommandV1"]
    validator = validator_for(PLAYBACK_SCHEMA_PATH, "ProgressCommandV1")

    command["command"] = "scroll_observed"
    with pytest.raises(ValidationError):
        validator.validate(command)

    command = load_json(PLAYBACK_EXAMPLES_PATH)["ProgressCommandV1"]
    command["expected_progress_row_version"] = -1
    with pytest.raises(ValidationError):
        validator.validate(command)


def test_f007_events_are_version_consistent_and_content_minimized() -> None:
    events = load_json(EVENT_EXAMPLES_PATH)
    forbidden_keys = {
        "title",
        "description",
        "content",
        "document",
        "lesson_text",
        "source_document_id",
        "source_content",
        "provider_payload",
        "review_notes",
        "actor_email",
    }

    for event_name, event in events.items():
        validator_for(EVENT_SCHEMA_PATH, event_name).validate(event)
        assert event["aggregate_version"] == event["payload"]["aggregate_version"]
        assert forbidden_keys.isdisjoint(set(iter_keys(event["payload"])))


def test_f007_event_contract_rejects_unapproved_payload_fields() -> None:
    event = load_json(EVENT_EXAMPLES_PATH)["LessonProgressedV1"]
    event["payload"]["lesson_text"] = "must never enter an event"

    with pytest.raises(ValidationError):
        validator_for(EVENT_SCHEMA_PATH, "LessonProgressedV1").validate(event)


def test_f007_fixtures_freeze_version_pin_and_negative_cases() -> None:
    fixture = load_json(FIXTURE_PATH)
    decisions = fixture["approved_decisions"]
    course = fixture["courses"]["pointer_advanced"]
    active = fixture["enrollments"]["active_pin_v1"]
    pinned = course["versions"]["v1"]
    current = course["versions"]["v2"]
    scenarios = {scenario["id"]: scenario for scenario in fixture["scenarios"]}

    assert fixture["classification"] == "synthetic"
    assert decisions == {
        "private_enrollment": {
            "admission_source": "manual_assignment",
            "self_enrollment": False,
            "revocation_terminal": True,
            "reenrollment_creates_new_record": True,
            "reenrollment_pins_current_published_version": True,
            "copy_historical_progress": False,
        },
        "unavailable_pinned_version": {
            "states": ["withdrawn", "archived"],
            "http_status": 404,
            "problem_code": "LEARNING_RESOURCE_NOT_FOUND",
            "auto_migrate": False,
            "learner_history_readable": False,
        },
        "progress": {
            "commands": ["open_lesson", "complete_lesson", "reopen_lesson"],
            "get_or_telemetry_mutates": False,
            "course_completion_rule": "all_required_lessons_complete",
            "required_lesson_reopen_reopens_course": True,
        },
        "locale": {
            "initial_pilot": "en",
            "preserve_unicode_and_fallback_metadata": True,
            "rtl_ready": True,
        },
    }
    assert active["status"] == "active"
    assert active["admission_source"] == "manual_assignment"
    assert active["course_version_id"] == pinned["id"]
    assert course["current_published_version_id"] == current["id"]
    assert active["course_version_id"] != course["current_published_version_id"]
    assert (
        scenarios["active_pin_survives_pointer_advance"]["requested_lesson_id"]
        in pinned["lesson_ids"]
    )
    assert scenarios["guessed_lesson_denied"]["requested_lesson_id"] in current["lesson_ids"]
    assert scenarios["guessed_lesson_denied"]["requested_lesson_id"] not in pinned["lesson_ids"]
    assert fixture["enrollments"]["revoked"]["status"] == "revoked"
    assert fixture["memberships"]["alpha_learner_revoked"]["status"] == "revoked"
    assert scenarios["wrong_tenant_denied"]["expected_result"] == "learning_resource_not_found"
    active_enrollment_keys = [
        (
            enrollment["tenant_id"],
            enrollment["learner_membership_id"],
            enrollment["course_id"],
        )
        for enrollment in fixture["enrollments"].values()
        if enrollment["status"] == "active"
    ]
    assert len(active_enrollment_keys) == len(set(active_enrollment_keys))

    old_enrollment = fixture["enrollments"]["reenrollment_revoked_v1"]
    new_enrollment = fixture["enrollments"]["reenrollment_active_v2"]
    assert old_enrollment["id"] != new_enrollment["id"]
    assert old_enrollment["status"] == "revoked"
    assert new_enrollment["status"] == "active"
    assert old_enrollment["learner_membership_id"] == new_enrollment["learner_membership_id"]
    assert new_enrollment["learner_membership_id"] != active["learner_membership_id"]
    assert old_enrollment["course_id"] == new_enrollment["course_id"] == course["id"]
    assert old_enrollment["course_version_id"] == pinned["id"]
    assert new_enrollment["course_version_id"] == course["current_published_version_id"]
    assert fixture["progress_records"]["reenrollment_revoked_v1"] == [
        {
            "lesson_id": "00000000-0000-4000-8000-00000000c301",
            "state": "completed",
        }
    ]
    assert fixture["progress_records"]["reenrollment_active_v2"] == []

    for state in ("withdrawn", "archived"):
        unavailable_course = fixture["courses"][state]
        unavailable_pin = fixture["enrollments"][f"{state}_pin"]
        scenario = scenarios[f"{state}_pin_denied"]
        assert unavailable_course["versions"]["v1"]["status"] == state
        assert unavailable_pin["course_version_id"] == unavailable_course["versions"]["v1"]["id"]
        assert scenario["expected_result"] == "learning_resource_not_found"
        assert scenario["expected_course_version_id"] is None


def test_f007_progress_commands_and_initial_locale_are_frozen() -> None:
    playback_schema = load_json(PLAYBACK_SCHEMA_PATH)
    playback_examples = load_json(PLAYBACK_EXAMPLES_PATH)

    assert playback_schema["$defs"]["ProgressCommandV1"]["properties"]["command"]["enum"] == [
        "open_lesson",
        "complete_lesson",
        "reopen_lesson",
    ]
    assert playback_schema["$defs"]["EnrollmentV1"]["properties"]["admission_source"] == {
        "const": "manual_assignment"
    }
    assert {
        example["primary_locale"]
        for example in playback_examples.values()
        if isinstance(example, dict) and "primary_locale" in example
    } == {"en"}


def test_f007_decisions_are_owner_approved_and_contract_ready() -> None:
    technical_decisions = TECHNICAL_DECISIONS_PATH.read_text(encoding="utf-8")
    readiness = READINESS_AUDIT_PATH.read_text(encoding="utf-8")
    product_decisions = PRODUCT_DECISIONS_PATH.read_text(encoding="utf-8")
    locale_plan = LOCALE_PLAN_PATH.read_text(encoding="utf-8")

    for decision_id in ("F007-Q01", "F007-Q02", "F007-Q03", "F007-Q04"):
        assert decision_id in technical_decisions
        assert decision_id in readiness

    assert "P-014" in product_decisions
    assert "Status: **owner-approved and frozen" in technical_decisions
    assert "READY FOR IMPLEMENTATION" in readiness
    assert "- [ ] F007-Q" not in readiness
    assert "NOT READY FOR IMPLEMENTATION" not in readiness
    assert "Initial focused-pilot locale under P-014" in locale_plan
    assert "\nen\n" in locale_plan

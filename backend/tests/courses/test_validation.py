from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from lms.modules.courses.errors import CourseLifecycleError
from lms.modules.courses.types import (
    CreateCourseCommand,
    CreateSuccessorDraftCommand,
    CurriculumSectionInput,
    ReplaceCurriculumCommand,
    Transition,
    TransitionCourseVersionCommand,
    UpdateCourseVersionCommand,
)
from lms.modules.courses.validation import (
    validate_complete_course,
    validate_create_course,
    validate_idempotency_key,
    validate_replace_curriculum,
    validate_rich_text_document,
    validate_successor,
    validate_transition,
    validate_update_course,
)
from tests.contract_fakes.f002_courses import (
    new_curriculum_command,
    snapshot_from_contract,
)


def _assert_validation_error(
    call: object, code: str = "COURSE_VALIDATION_FAILED"
) -> CourseLifecycleError:
    with pytest.raises(CourseLifecycleError) as caught:
        call()
    assert caught.value.code == code
    assert 1 <= len(caught.value.field_errors) <= 100
    return caught.value


@pytest.mark.parametrize("node_type", ["raw_html", "embed", "image", "link", "provider_payload"])
def test_unknown_or_executable_rich_text_nodes_are_rejected(node_type: str) -> None:
    document = {"type": "document", "content": [{"type": node_type, "html": "<script>"}]}
    error = _assert_validation_error(lambda: validate_rich_text_document(document))
    assert "<script>" not in str(error.field_errors)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda node: node.update(url="https://example.invalid"),
        lambda node: node.update(provider_payload={"secret": "value"}),
        lambda node: node.update(text=""),
        lambda node: node.update(text="   "),
        lambda node: node.update(marks=["strong", "strong"]),
        lambda node: node.update(marks=["unknown"]),
    ],
)
def test_unknown_attributes_empty_text_and_invalid_marks_are_rejected(mutation: object) -> None:
    document = deepcopy(snapshot_from_contract().sections[0].lessons[0].content_blocks[0].document)
    text_node = document["content"][0]["content"][0]
    mutation(text_node)

    _assert_validation_error(lambda: validate_rich_text_document(document))


@pytest.mark.parametrize("level", [1, 5, True, "2"])
def test_heading_level_is_strictly_bounded_integer(level: object) -> None:
    document = deepcopy(snapshot_from_contract().sections[0].lessons[0].content_blocks[0].document)
    document["content"][0]["level"] = level

    _assert_validation_error(lambda: validate_rich_text_document(document))


def test_duplicate_positions_and_partial_identity_pairs_are_rejected() -> None:
    command = new_curriculum_command()
    duplicate = replace(command.sections[0], title="Second", position=command.sections[0].position)
    duplicate_command = replace(command, sections=(command.sections[0], duplicate))
    _assert_validation_error(lambda: validate_replace_curriculum(duplicate_command))

    partial = replace(command.sections[0], id=snapshot_from_contract().sections[0].id)
    partial_command = replace(command, sections=(partial,))
    _assert_validation_error(lambda: validate_replace_curriculum(partial_command))


def test_duplicate_preserved_ids_are_rejected_even_under_different_positions() -> None:
    existing = snapshot_from_contract().sections[0]
    first = CurriculumSectionInput(
        id=existing.id,
        expected_row_version=existing.row_version,
        title=existing.title,
        position=1,
        lessons=(),
    )
    command = ReplaceCurriculumCommand(
        expected_version_row_version=1,
        sections=(first, replace(first, position=2)),
    )

    _assert_validation_error(lambda: validate_replace_curriculum(command))


def test_metadata_commands_require_strict_nonempty_values() -> None:
    validate_create_course(CreateCourseCommand("safe-course", "en", "Safe", "Synthetic"))

    _assert_validation_error(
        lambda: validate_create_course(CreateCourseCommand("Unsafe Slug", "en", "Safe", "Text"))
    )
    _assert_validation_error(
        lambda: validate_update_course(UpdateCourseVersionCommand(expected_version_row_version=1))
    )
    _assert_validation_error(
        lambda: validate_update_course(
            UpdateCourseVersionCommand(expected_version_row_version=1, title="   ")
        )
    )


def test_transition_fields_are_bound_to_the_selected_operation() -> None:
    content_hash = snapshot_from_contract().version.content_hash
    validate_transition(
        TransitionCourseVersionCommand(
            transition=Transition.REQUEST_CHANGES,
            expected_version_row_version=2,
            expected_content_hash=content_hash,
            reason_codes=("CONTENT_GAP",),
        )
    )
    validate_transition(
        TransitionCourseVersionCommand(
            transition=Transition.WITHDRAW,
            expected_version_row_version=5,
            expected_content_hash=content_hash,
            expected_course_row_version=2,
            reason_code="CONTENT_RETIRED",
        )
    )

    invalid_commands = (
        TransitionCourseVersionCommand(Transition.REQUEST_CHANGES, 2, content_hash),
        TransitionCourseVersionCommand(Transition.PUBLISH, 4, content_hash),
        TransitionCourseVersionCommand(Transition.ARCHIVE, 6, content_hash),
        TransitionCourseVersionCommand(
            Transition.SUBMIT_REVIEW,
            2,
            content_hash,
            expected_course_row_version=1,
        ),
    )
    for command in invalid_commands:
        _assert_validation_error(lambda command=command: validate_transition(command))


def test_successor_and_idempotency_expectations_are_strict() -> None:
    content_hash = snapshot_from_contract().version.content_hash
    validate_successor(CreateSuccessorDraftCommand(1, 1, content_hash))
    validate_idempotency_key("valid-key-0001")

    _assert_validation_error(
        lambda: validate_successor(CreateSuccessorDraftCommand(0, 1, content_hash))
    )
    _assert_validation_error(lambda: validate_idempotency_key(" short "))


def test_complete_course_requires_nonempty_metadata_and_a_required_lesson() -> None:
    snapshot = snapshot_from_contract()
    validate_complete_course(snapshot)

    no_required_lesson = replace(
        snapshot,
        sections=(
            replace(
                snapshot.sections[0],
                lessons=(replace(snapshot.sections[0].lessons[0], is_required=False),),
            ),
        ),
    )
    _assert_validation_error(lambda: validate_complete_course(no_required_lesson))
    _assert_validation_error(
        lambda: validate_complete_course(
            replace(snapshot, version=replace(snapshot.version, description="   "))
        )
    )


def test_validation_errors_are_bounded_and_never_echo_lesson_content() -> None:
    unsafe_text = "private-lesson-body-never-echo"
    command = new_curriculum_command(section_count=110, text=unsafe_text)

    error = _assert_validation_error(lambda: validate_replace_curriculum(command))
    assert len(error.field_errors) <= 100
    assert unsafe_text not in str(error)
    assert unsafe_text not in str(error.field_errors)


def test_unknown_attribute_names_are_not_reflected_in_safe_errors() -> None:
    unsafe_key = "private-lesson-body-never-echo"
    document = deepcopy(snapshot_from_contract().sections[0].lessons[0].content_blocks[0].document)
    document["content"][0]["content"][0][unsafe_key] = True

    error = _assert_validation_error(lambda: validate_rich_text_document(document))

    assert unsafe_key not in str(error)
    assert unsafe_key not in str(error.field_errors)

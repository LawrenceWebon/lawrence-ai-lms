from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

from .errors import FieldError, validation_failed
from .types import (
    ContentBlockInput,
    CourseSnapshot,
    CreateCourseCommand,
    CreateSuccessorDraftCommand,
    CurriculumSectionInput,
    LessonInput,
    ReplaceCurriculumCommand,
    Transition,
    TransitionCourseVersionCommand,
    UpdateCourseVersionCommand,
)

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LOCALE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_ALLOWED_MARKS = frozenset({"strong", "emphasis", "code"})
_MAX_ERRORS = 100


@dataclass(slots=True)
class _Collector:
    errors: list[FieldError] = field(default_factory=list)

    def add(self, path: str, code: str, detail: str) -> None:
        if len(self.errors) < _MAX_ERRORS:
            self.errors.append(FieldError(path=path, code=code, detail=detail))

    def raise_if_any(self) -> None:
        if self.errors:
            raise validation_failed(tuple(self.errors))


def _mapping(value: object, path: str, errors: _Collector) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        errors.add(path, "invalid_type", "A structured object is required.")
        return None
    return cast(Mapping[str, object], value)


def _array(value: object, path: str, errors: _Collector) -> list[object] | None:
    if not isinstance(value, list):
        errors.add(path, "invalid_type", "An array is required.")
        return None
    return cast(list[object], value)


def _exact_keys(
    value: Mapping[str, object], required: frozenset[str], path: str, errors: _Collector
) -> None:
    for key in sorted(required):
        if key not in value:
            errors.add(f"{path}.{key}", "required", "A required field is missing.")
    if any(key not in required for key in value):
        # Unknown keys are untrusted input too. Do not reflect them in a public path.
        errors.add(f"{path}.*", "unknown", "One or more fields are not supported.")


def _positive_integer(value: object, path: str, errors: _Collector) -> bool:
    if type(value) is not int or value < 1:
        errors.add(path, "invalid_integer", "A positive integer is required.")
        return False
    return True


def _bounded_text(value: object, path: str, maximum: int, errors: _Collector) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        errors.add(path, "invalid_text", "Non-empty bounded text is required.")
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        errors.add(path, "invalid_text", "Valid UTF-8 text is required.")
        return False
    return True


def _validate_text_node(value: object, path: str, errors: _Collector) -> None:
    node = _mapping(value, path, errors)
    if node is None:
        return
    _exact_keys(node, frozenset({"type", "text", "marks"}), path, errors)
    if node.get("type") != "text":
        errors.add(f"{path}.type", "unsupported", "Only text nodes are supported here.")
    _bounded_text(node.get("text"), f"{path}.text", 10_000, errors)
    marks = _array(node.get("marks"), f"{path}.marks", errors)
    if marks is None:
        return
    if len(marks) > 3:
        errors.add(f"{path}.marks", "too_many", "At most three marks are allowed.")
    if any(not isinstance(mark, str) or mark not in _ALLOWED_MARKS for mark in marks):
        errors.add(f"{path}.marks", "unsupported", "One or more marks are unsupported.")
    string_marks = [mark for mark in marks if isinstance(mark, str)]
    if len(string_marks) != len(set(string_marks)):
        errors.add(f"{path}.marks", "duplicate", "Marks must be unique.")


def _validate_inline_content(value: object, path: str, maximum: int, errors: _Collector) -> None:
    content = _array(value, path, errors)
    if content is None:
        return
    if not content or len(content) > maximum:
        errors.add(path, "invalid_length", "The text node count is outside the allowed range.")
    for index, item in enumerate(content[: maximum + 1]):
        _validate_text_node(item, f"{path}[{index}]", errors)


def _validate_paragraph(value: object, path: str, errors: _Collector) -> None:
    node = _mapping(value, path, errors)
    if node is None:
        return
    _exact_keys(node, frozenset({"type", "content"}), path, errors)
    if node.get("type") != "paragraph":
        errors.add(f"{path}.type", "unsupported", "A paragraph is required.")
    _validate_inline_content(node.get("content"), f"{path}.content", 500, errors)


def _validate_heading(value: object, path: str, errors: _Collector) -> None:
    node = _mapping(value, path, errors)
    if node is None:
        return
    _exact_keys(node, frozenset({"type", "level", "content"}), path, errors)
    if node.get("type") != "heading":
        errors.add(f"{path}.type", "unsupported", "A heading is required.")
    level = node.get("level")
    if type(level) is not int or not 2 <= level <= 4:
        errors.add(f"{path}.level", "invalid_heading", "Heading level must be 2, 3, or 4.")
    _validate_inline_content(node.get("content"), f"{path}.content", 100, errors)


def _validate_list_item(value: object, path: str, errors: _Collector) -> None:
    node = _mapping(value, path, errors)
    if node is None:
        return
    _exact_keys(node, frozenset({"type", "content"}), path, errors)
    if node.get("type") != "list_item":
        errors.add(f"{path}.type", "unsupported", "A list item is required.")
    content = _array(node.get("content"), f"{path}.content", errors)
    if content is None:
        return
    if not content or len(content) > 20:
        errors.add(f"{path}.content", "invalid_length", "A list item requires 1 to 20 paragraphs.")
    for index, paragraph in enumerate(content[:21]):
        _validate_paragraph(paragraph, f"{path}.content[{index}]", errors)


def _validate_list(value: object, path: str, list_type: str, errors: _Collector) -> None:
    node = _mapping(value, path, errors)
    if node is None:
        return
    _exact_keys(node, frozenset({"type", "items"}), path, errors)
    if node.get("type") != list_type:
        errors.add(f"{path}.type", "unsupported", "The list type is unsupported.")
    items = _array(node.get("items"), f"{path}.items", errors)
    if items is None:
        return
    if not items or len(items) > 100:
        errors.add(f"{path}.items", "invalid_length", "A list requires 1 to 100 items.")
    for index, item in enumerate(items[:101]):
        _validate_list_item(item, f"{path}.items[{index}]", errors)


def _validate_rich_text_document(value: object, path: str, errors: _Collector) -> None:
    document = _mapping(value, path, errors)
    if document is None:
        return
    _exact_keys(document, frozenset({"type", "content"}), path, errors)
    if document.get("type") != "document":
        errors.add(f"{path}.type", "unsupported", "A rich-text document is required.")
    content = _array(document.get("content"), f"{path}.content", errors)
    if content is None:
        return
    if not content or len(content) > 500:
        errors.add(f"{path}.content", "invalid_length", "A document requires 1 to 500 nodes.")
    for index, item in enumerate(content[:501]):
        node = _mapping(item, f"{path}.content[{index}]", errors)
        if node is None:
            continue
        node_type = node.get("type")
        node_path = f"{path}.content[{index}]"
        if node_type == "paragraph":
            _validate_paragraph(item, node_path, errors)
        elif node_type == "heading":
            _validate_heading(item, node_path, errors)
        elif node_type in {"bullet_list", "ordered_list"}:
            _validate_list(item, node_path, node_type, errors)
        else:
            errors.add(f"{node_path}.type", "unsupported", "This document node is unsupported.")


def validate_rich_text_document(value: object) -> None:
    errors = _Collector()
    _validate_rich_text_document(value, "document", errors)
    errors.raise_if_any()


def _identity_pair(
    identifier: object, expected_row_version: object, path: str, errors: _Collector
) -> None:
    if (identifier is None) != (expected_row_version is None):
        errors.add(
            path, "partial_identity", "Identity and expected row version must appear together."
        )
    if expected_row_version is not None:
        _positive_integer(expected_row_version, f"{path}.expected_row_version", errors)


def _unique_positions(
    items: tuple[object, ...], path: str, maximum: int, errors: _Collector
) -> None:
    positions = [getattr(item, "position", None) for item in items[: maximum + 1]]
    for index, position in enumerate(positions):
        _positive_integer(position, f"{path}[{index}].position", errors)
    integer_positions = [position for position in positions if type(position) is int]
    if len(integer_positions) != len(set(integer_positions)):
        errors.add(path, "duplicate_position", "Positions must be unique within their parent.")


def _validate_block(block: ContentBlockInput, path: str, errors: _Collector) -> None:
    _identity_pair(block.id, block.expected_row_version, path, errors)
    if block.kind != "rich_text":
        errors.add(f"{path}.kind", "unsupported", "Only rich_text blocks are supported.")
    _positive_integer(block.position, f"{path}.position", errors)
    _validate_rich_text_document(block.document, f"{path}.document", errors)


def _validate_lesson(lesson: LessonInput, path: str, errors: _Collector) -> None:
    _identity_pair(lesson.id, lesson.expected_row_version, path, errors)
    _bounded_text(lesson.title, f"{path}.title", 160, errors)
    _positive_integer(lesson.position, f"{path}.position", errors)
    if type(lesson.is_required) is not bool:
        errors.add(f"{path}.is_required", "invalid_type", "A boolean is required.")
    if not lesson.content_blocks or len(lesson.content_blocks) > 100:
        errors.add(
            f"{path}.content_blocks",
            "invalid_length",
            "A lesson requires 1 to 100 content blocks.",
        )
    _unique_positions(
        cast(tuple[object, ...], lesson.content_blocks),
        f"{path}.content_blocks",
        100,
        errors,
    )
    for index, block in enumerate(lesson.content_blocks[:101]):
        _validate_block(block, f"{path}.content_blocks[{index}]", errors)


def _validate_section(section: CurriculumSectionInput, path: str, errors: _Collector) -> None:
    _identity_pair(section.id, section.expected_row_version, path, errors)
    _bounded_text(section.title, f"{path}.title", 160, errors)
    _positive_integer(section.position, f"{path}.position", errors)
    if not section.lessons or len(section.lessons) > 200:
        errors.add(f"{path}.lessons", "invalid_length", "A section requires 1 to 200 lessons.")
    _unique_positions(cast(tuple[object, ...], section.lessons), f"{path}.lessons", 200, errors)
    for index, lesson in enumerate(section.lessons[:201]):
        _validate_lesson(lesson, f"{path}.lessons[{index}]", errors)


def validate_create_course(command: CreateCourseCommand) -> None:
    errors = _Collector()
    if not _SLUG.fullmatch(command.slug) or len(command.slug) > 63:
        errors.add("slug", "invalid_slug", "The slug format is invalid.")
    if not _LOCALE.fullmatch(command.primary_locale) or len(command.primary_locale) > 10:
        errors.add("primary_locale", "invalid_locale", "The locale format is invalid.")
    _bounded_text(command.title, "title", 160, errors)
    _bounded_text(command.description, "description", 2_000, errors)
    errors.raise_if_any()


def validate_update_course(command: UpdateCourseVersionCommand) -> None:
    errors = _Collector()
    _positive_integer(command.expected_version_row_version, "expected_version_row_version", errors)
    if command.primary_locale is None and command.title is None and command.description is None:
        errors.add("$", "empty_patch", "At least one metadata field is required.")
    if command.primary_locale is not None and (
        not _LOCALE.fullmatch(command.primary_locale) or len(command.primary_locale) > 10
    ):
        errors.add("primary_locale", "invalid_locale", "The locale format is invalid.")
    if command.title is not None:
        _bounded_text(command.title, "title", 160, errors)
    if command.description is not None:
        _bounded_text(command.description, "description", 2_000, errors)
    errors.raise_if_any()


def validate_replace_curriculum(command: ReplaceCurriculumCommand) -> None:
    errors = _Collector()
    _positive_integer(command.expected_version_row_version, "expected_version_row_version", errors)
    if len(command.sections) > 100:
        errors.add("sections", "too_many", "At most 100 sections are allowed.")
    _unique_positions(cast(tuple[object, ...], command.sections), "sections", 100, errors)
    section_ids: set[object] = set()
    lesson_ids: set[object] = set()
    block_ids: set[object] = set()
    for section_index, section in enumerate(command.sections[:101]):
        path = f"sections[{section_index}]"
        _validate_section(section, path, errors)
        if section.id is not None and section.id in section_ids:
            errors.add(f"{path}.id", "duplicate_id", "A curriculum ID may appear only once.")
        section_ids.add(section.id)
        for lesson_index, lesson in enumerate(section.lessons[:201]):
            lesson_path = f"{path}.lessons[{lesson_index}]"
            if lesson.id is not None and lesson.id in lesson_ids:
                errors.add(
                    f"{lesson_path}.id", "duplicate_id", "A curriculum ID may appear only once."
                )
            lesson_ids.add(lesson.id)
            for block_index, block in enumerate(lesson.content_blocks[:101]):
                block_path = f"{lesson_path}.content_blocks[{block_index}]"
                if block.id is not None and block.id in block_ids:
                    errors.add(
                        f"{block_path}.id", "duplicate_id", "A curriculum ID may appear only once."
                    )
                block_ids.add(block.id)
    errors.raise_if_any()


def _validate_hash(value: object, path: str, errors: _Collector) -> None:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        errors.add(path, "invalid_hash", "A canonical sha256 hash is required.")


def _validate_reason(value: object, path: str, errors: _Collector) -> None:
    if not isinstance(value, str) or not _REASON.fullmatch(value):
        errors.add(path, "invalid_reason", "The reason code format is invalid.")


def validate_transition(command: TransitionCourseVersionCommand) -> None:
    errors = _Collector()
    _positive_integer(command.expected_version_row_version, "expected_version_row_version", errors)
    _validate_hash(command.expected_content_hash, "expected_content_hash", errors)
    needs_course = command.transition in {Transition.PUBLISH, Transition.WITHDRAW}
    if needs_course:
        _positive_integer(
            command.expected_course_row_version, "expected_course_row_version", errors
        )
    elif command.expected_course_row_version is not None:
        errors.add(
            "expected_course_row_version",
            "unexpected",
            "This transition does not change the course pointer.",
        )
    if command.transition is Transition.REQUEST_CHANGES:
        if not command.reason_codes or len(command.reason_codes) > 20:
            errors.add("reason_codes", "invalid_length", "One to twenty reason codes are required.")
        if len(command.reason_codes) != len(set(command.reason_codes)):
            errors.add("reason_codes", "duplicate", "Reason codes must be unique.")
        for index, reason in enumerate(command.reason_codes):
            _validate_reason(reason, f"reason_codes[{index}]", errors)
        if command.reason_code is not None:
            errors.add("reason_code", "unexpected", "A singular reason code is not allowed here.")
    else:
        if command.reason_codes:
            errors.add("reason_codes", "unexpected", "Reason codes are not allowed here.")
        if command.transition in {Transition.WITHDRAW, Transition.ARCHIVE}:
            if command.reason_code is None:
                errors.add("reason_code", "required", "A reason code is required.")
            else:
                _validate_reason(command.reason_code, "reason_code", errors)
        elif command.reason_code is not None:
            errors.add("reason_code", "unexpected", "A reason code is not allowed here.")
    errors.raise_if_any()


def validate_successor(command: CreateSuccessorDraftCommand) -> None:
    errors = _Collector()
    _positive_integer(command.expected_course_row_version, "expected_course_row_version", errors)
    _positive_integer(
        command.expected_source_version_row_version,
        "expected_source_version_row_version",
        errors,
    )
    _validate_hash(command.expected_source_content_hash, "expected_source_content_hash", errors)
    errors.raise_if_any()


def validate_idempotency_key(value: str) -> None:
    if (
        not 8 <= len(value) <= 128
        or value.strip() != value
        or any(ord(char) < 33 for char in value)
    ):
        raise validation_failed(
            (FieldError("idempotency_key", "invalid", "A valid idempotency key is required."),)
        )


def validate_complete_course(snapshot: CourseSnapshot) -> None:
    errors = _Collector()
    version = snapshot.version
    if not _LOCALE.fullmatch(version.primary_locale) or len(version.primary_locale) > 10:
        errors.add("version.primary_locale", "invalid_locale", "The locale format is invalid.")
    _bounded_text(version.title, "version.title", 160, errors)
    _bounded_text(version.description, "version.description", 2_000, errors)
    _validate_hash(version.content_hash, "version.content_hash", errors)
    if not snapshot.sections:
        errors.add("sections", "required", "At least one section is required for review.")
    if len(snapshot.sections) > 100:
        errors.add("sections", "too_many", "At most 100 sections are allowed.")
    _unique_positions(cast(tuple[object, ...], snapshot.sections), "sections", 100, errors)
    required_lessons = 0
    for section_index, section in enumerate(snapshot.sections[:101]):
        section_path = f"sections[{section_index}]"
        if (
            section.tenant_id != snapshot.course.tenant_id
            or section.course_version_id != version.id
        ):
            errors.add(section_path, "invalid_edge", "The curriculum edge is invalid.")
        _bounded_text(section.title, f"{section_path}.title", 160, errors)
        if not section.lessons:
            errors.add(f"{section_path}.lessons", "required", "At least one lesson is required.")
        if len(section.lessons) > 200:
            errors.add(f"{section_path}.lessons", "too_many", "At most 200 lessons are allowed.")
        _unique_positions(
            cast(tuple[object, ...], section.lessons),
            f"{section_path}.lessons",
            200,
            errors,
        )
        for lesson_index, lesson in enumerate(section.lessons[:201]):
            lesson_path = f"{section_path}.lessons[{lesson_index}]"
            if (
                lesson.tenant_id != snapshot.course.tenant_id
                or lesson.course_version_id != version.id
                or lesson.section_id != section.id
            ):
                errors.add(lesson_path, "invalid_edge", "The curriculum edge is invalid.")
            _bounded_text(lesson.title, f"{lesson_path}.title", 160, errors)
            required_lessons += int(lesson.is_required)
            if not lesson.content_blocks:
                errors.add(
                    f"{lesson_path}.content_blocks",
                    "required",
                    "At least one content block is required.",
                )
            if len(lesson.content_blocks) > 100:
                errors.add(
                    f"{lesson_path}.content_blocks",
                    "too_many",
                    "At most 100 content blocks are allowed.",
                )
            _unique_positions(
                cast(tuple[object, ...], lesson.content_blocks),
                f"{lesson_path}.content_blocks",
                100,
                errors,
            )
            for block_index, block in enumerate(lesson.content_blocks[:101]):
                block_path = f"{lesson_path}.content_blocks[{block_index}]"
                if (
                    block.tenant_id != snapshot.course.tenant_id
                    or block.course_version_id != version.id
                    or block.lesson_id != lesson.id
                ):
                    errors.add(block_path, "invalid_edge", "The curriculum edge is invalid.")
                if block.kind != "rich_text":
                    errors.add(f"{block_path}.kind", "unsupported", "Only rich_text is supported.")
                _validate_rich_text_document(block.document, f"{block_path}.document", errors)
    if required_lessons == 0:
        errors.add("sections", "required_lesson", "At least one required lesson is needed.")
    errors.raise_if_any()

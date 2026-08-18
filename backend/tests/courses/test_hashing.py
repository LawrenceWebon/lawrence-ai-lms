from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from uuid import UUID

import pytest

from lms.modules.courses.hashing import canonical_content_hash, canonical_json_bytes
from lms.modules.courses.types import CourseStatus, OriginType
from tests.contract_fakes.f002_courses import snapshot_from_contract

EXPECTED_HASH = "sha256:f4e7e98f5fe8199a25ba5293d4a7a58e1f45b649941de8c0935282ae5845ec31"


def _with_block_document(snapshot: object, document: dict[str, object]) -> object:
    block = snapshot.sections[0].lessons[0].content_blocks[0]
    lesson = snapshot.sections[0].lessons[0]
    section = snapshot.sections[0]
    changed_block = replace(block, document=document)
    changed_lesson = replace(lesson, content_blocks=(changed_block,))
    changed_section = replace(section, lessons=(changed_lesson,))
    return replace(snapshot, sections=(changed_section,))


def test_contract_fixture_has_exact_rfc8785_sha256_hash() -> None:
    assert canonical_content_hash(snapshot_from_contract()) == EXPECTED_HASH


def test_canonical_json_is_stable_for_key_order_and_unicode() -> None:
    left = {"z": "课程", "a": {"strong": True, "position": 1}}
    right = {"a": {"position": 1, "strong": True}, "z": "课程"}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_bytes(left).decode("utf-8") == (
        '{"a":{"position":1,"strong":true},"z":"课程"}'
    )
    with pytest.raises(ValueError, match="outside the canonical F-002 JSON subset"):
        canonical_json_bytes({"unsupported_float": 1.5})


def test_hash_ignores_identity_workflow_and_audit_metadata() -> None:
    original = snapshot_from_contract()
    changed = replace(
        original,
        course=replace(
            original.course,
            id=UUID("ffffffff-ffff-4fff-8fff-ffffffffffff"),
            slug="ignored-slug",
            current_published_version_id=original.version.id,
            row_version=99,
        ),
        version=replace(
            original.version,
            id=UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
            predecessor_version_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            version_number=27,
            status=CourseStatus.PUBLISHED,
            origin_type=OriginType.AI_ASSISTED,
            submitted_hash=EXPECTED_HASH,
            approved_hash=EXPECTED_HASH,
            row_version=42,
        ),
        latest_review=None,
    )
    section = changed.sections[0]
    lesson = section.lessons[0]
    block = lesson.content_blocks[0]
    changed = replace(
        changed,
        sections=(
            replace(
                section,
                id=UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
                row_version=91,
                lessons=(
                    replace(
                        lesson,
                        id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
                        row_version=92,
                        content_blocks=(
                            replace(
                                block,
                                id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
                                row_version=93,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    assert canonical_content_hash(changed) == canonical_content_hash(original)


def test_hash_changes_for_every_product_content_field() -> None:
    original = snapshot_from_contract()
    section = original.sections[0]
    lesson = section.lessons[0]
    block = lesson.content_blocks[0]
    document = deepcopy(block.document)
    document["content"][1]["content"][0]["text"] = "Changed synthetic text."

    changes = (
        replace(original, version=replace(original.version, primary_locale="zh-CN")),
        replace(original, version=replace(original.version, title="Changed title")),
        replace(original, version=replace(original.version, description="Changed description")),
        replace(original, sections=(replace(section, title="Changed section"),)),
        replace(original, sections=(replace(section, position=2),)),
        replace(
            original,
            sections=(replace(section, lessons=(replace(lesson, title="Changed lesson"),)),),
        ),
        replace(original, sections=(replace(section, lessons=(replace(lesson, position=2),)),)),
        replace(
            original, sections=(replace(section, lessons=(replace(lesson, is_required=False),)),)
        ),
        replace(
            original,
            sections=(
                replace(
                    section,
                    lessons=(replace(lesson, content_blocks=(replace(block, position=2),)),),
                ),
            ),
        ),
        replace(
            original,
            sections=(
                replace(
                    section,
                    lessons=(
                        replace(lesson, content_blocks=(replace(block, kind="changed_kind"),)),
                    ),
                ),
            ),
        ),
        _with_block_document(original, document),
    )

    baseline = canonical_content_hash(original)
    assert all(canonical_content_hash(change) != baseline for change in changes)

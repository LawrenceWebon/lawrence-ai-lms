from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from django.db import transaction
from jsonschema import Draft202012Validator, FormatChecker

from lms.modules.courses.repositories import CoursePersistenceConflictError, CourseRepository
from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact
from tests.courses.test_models import CONTENT_HASH, DOCUMENT
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

UPDATED_HASH = "sha256:" + "2" * 64
REPLACED_HASH = "sha256:" + "3" * 64


def curriculum(title: str = "Synthetic section") -> list[dict[str, object]]:
    return [
        {
            "title": title,
            "position": 1,
            "lessons": [
                {
                    "title": "Synthetic lesson",
                    "position": 1,
                    "is_required": True,
                    "content_blocks": [
                        {
                            "kind": "rich_text",
                            "position": 1,
                            "document": DOCUMENT,
                        }
                    ],
                }
            ],
        }
    ]


@pytest.mark.django_db
def test_repository_inserts_course_v1_and_reads_exact_snapshot_and_history(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = CourseRepository()
    snapshot = repository.insert_course_with_v1(
        tenant_id=tenancy_seed["alpha"].id,
        slug="repository-course",
        primary_locale="en",
        title="Repository course",
        description="Synthetic repository fixture.",
        content_hash=CONTENT_HASH,
        instructor_membership_ids=(tenancy_seed["memberships"]["instructor_alpha"].id,),
    )

    course_id = snapshot["course"]["id"]
    version_id = snapshot["version"]["id"]
    assert snapshot["version"]["status"] == "draft"
    assert snapshot["sections"] == []
    schema = json.loads(
        Path("contracts/f002/canonical-course.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(snapshot)
    assert repository.load_snapshot(tenancy_seed["alpha"].id, course_id, version_id) == snapshot
    page, next_position = repository.list_version_summaries(
        tenancy_seed["alpha"].id, course_id, limit=10
    )
    assert [item["id"] for item in page] == [version_id]
    assert next_position is None


@pytest.mark.django_db
def test_repository_compares_rows_and_replaces_curriculum_atomically(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = CourseRepository()
    created = repository.insert_course_with_v1(
        tenant_id=tenancy_seed["alpha"].id,
        slug="editable-course",
        primary_locale="en",
        title="Editable course",
        description="Synthetic repository fixture.",
        content_hash=CONTENT_HASH,
        instructor_membership_ids=(tenancy_seed["memberships"]["instructor_alpha"].id,),
    )
    tenant_id = tenancy_seed["alpha"].id
    course_id = created["course"]["id"]
    version_id = created["version"]["id"]

    updated = repository.compare_and_update_version(
        tenant_id=tenant_id,
        course_id=course_id,
        version_id=version_id,
        expected_row_version=1,
        updates={"title": "Updated course"},
        content_hash=UPDATED_HASH,
    )
    assert updated["version"]["row_version"] == 2
    with pytest.raises(CoursePersistenceConflictError):
        repository.compare_and_update_version(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
            expected_row_version=1,
            updates={"title": "Stale write"},
            content_hash=UPDATED_HASH,
        )

    replaced = repository.replace_curriculum(
        tenant_id=tenant_id,
        course_id=course_id,
        version_id=version_id,
        expected_row_version=2,
        sections=curriculum(),
        content_hash=REPLACED_HASH,
    )
    section = replaced["sections"][0]
    lesson = section["lessons"][0]
    block = lesson["content_blocks"][0]
    assert replaced["version"]["row_version"] == 3

    preserved = curriculum("Renamed section")
    preserved[0]["id"] = section["id"]
    preserved[0]["expected_row_version"] = section["row_version"]
    preserved_lesson = preserved[0]["lessons"][0]  # type: ignore[index]
    preserved_lesson["id"] = lesson["id"]  # type: ignore[index]
    preserved_lesson["expected_row_version"] = lesson["row_version"]  # type: ignore[index]
    preserved_block = preserved_lesson["content_blocks"][0]  # type: ignore[index]
    preserved_block["id"] = block["id"]  # type: ignore[index]
    preserved_block["expected_row_version"] = block["row_version"]  # type: ignore[index]
    again = repository.replace_curriculum(
        tenant_id=tenant_id,
        course_id=course_id,
        version_id=version_id,
        expected_row_version=3,
        sections=preserved,
        content_hash=REPLACED_HASH,
    )
    assert again["sections"][0]["id"] == section["id"]
    assert again["sections"][0]["row_version"] == 2
    assert again["version"]["row_version"] == 4


@pytest.mark.django_db
def test_repository_transitions_pointer_and_deep_copies_successor(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = CourseRepository()
    created = repository.insert_course_with_v1(
        tenant_id=tenancy_seed["alpha"].id,
        slug="published-course",
        primary_locale="en",
        title="Published course",
        description="Synthetic repository fixture.",
        content_hash=CONTENT_HASH,
        instructor_membership_ids=(tenancy_seed["memberships"]["instructor_alpha"].id,),
    )
    tenant_id = tenancy_seed["alpha"].id
    course_id = created["course"]["id"]
    version_id = created["version"]["id"]
    with_curriculum = repository.replace_curriculum(
        tenant_id=tenant_id,
        course_id=course_id,
        version_id=version_id,
        expected_row_version=1,
        sections=curriculum(),
        content_hash=CONTENT_HASH,
    )
    reviewed = repository.append_review(
        tenant_id=tenant_id,
        course_id=course_id,
        version_id=version_id,
        decision="approved",
        reviewed_hash=CONTENT_HASH,
        reviewer_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        self_review=True,
        reason_codes=(),
    )
    assert reviewed["latest_review"]["decision"] == "approved"
    published = repository.compare_and_transition_version(
        tenant_id=tenant_id,
        course_id=course_id,
        version_id=version_id,
        expected_row_version=2,
        expected_status="draft",
        expected_content_hash=CONTENT_HASH,
        next_status="published",
        hash_updates={"submitted_hash": CONTENT_HASH, "approved_hash": CONTENT_HASH},
        publication_pointer=(1, None, version_id),
    )
    assert published["course"]["current_published_version_id"] == version_id

    successor = repository.create_successor_draft(
        tenant_id=tenant_id,
        course_id=course_id,
        source_version_id=version_id,
        expected_course_row_version=2,
        expected_source_row_version=3,
        expected_source_content_hash=CONTENT_HASH,
    )
    assert successor["version"]["predecessor_version_id"] == version_id
    assert successor["version"]["status"] == "draft"
    assert successor["sections"][0]["id"] != with_curriculum["sections"][0]["id"]
    assert successor["sections"][0]["row_version"] == 1
    assert successor["latest_review"] is None
    replayed = repository.create_successor_draft(
        tenant_id=tenant_id,
        course_id=course_id,
        source_version_id=version_id,
        expected_course_row_version=2,
        expected_source_row_version=3,
        expected_source_content_hash=CONTENT_HASH,
    )
    assert replayed["version"]["id"] == successor["version"]["id"]
    first_page, cursor = repository.list_version_summaries(tenant_id, course_id, limit=1)
    assert [item["id"] for item in first_page] == [successor["version"]["id"]]
    assert cursor is not None
    second_page, final_cursor = repository.list_version_summaries(
        tenant_id, course_id, limit=1, before=cursor
    )
    assert [item["id"] for item in second_page] == [version_id]
    assert final_cursor is None
    original = repository.load_snapshot(tenant_id, course_id, version_id)
    assert original is not None
    assert original["version"]["status"] == "published"


@pytest.mark.django_db(transaction=True)
def test_idempotency_and_facts_require_and_share_the_calling_transaction(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = CourseRepository()
    actor_id = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    with pytest.raises(RuntimeError, match="atomic"):
        repository.reserve_idempotency(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation="courses.create",
            key_digest="a" * 64,
            request_hash="b" * 64,
        )

    with transaction.atomic():
        reservation, replay = repository.reserve_idempotency(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation="courses.create",
            key_digest="a" * 64,
            request_hash="b" * 64,
        )
        assert replay is False
        repository.complete_idempotency(reservation.id, {"status": 201})
        repository.append_atomic_facts(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type="course.version.published.v1",
            subject_type="course_version",
            subject_id=reservation.id,
            aggregate_type="course",
            aggregate_id=reservation.id,
            payload={"course_version_id": str(reservation.id)},
        )

    assert IdempotencyReservation.objects.get(id=reservation.id).status == "completed"
    assert AuditFact.objects.filter(subject_id=reservation.id).count() == 1
    assert OutboxFact.objects.filter(aggregate_id=reservation.id).count() == 1

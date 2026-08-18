from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping, Sequence
from typing import Any, cast
from uuid import UUID

from django.db import connection, transaction
from django.db.models import F, Max, Q
from django.utils import timezone

from lms.modules.tenancy.models import (
    AuditFact,
    IdempotencyReservation,
    OutboxFact,
    Tenant,
    TenantMembership,
)

from .models import (
    Course,
    CourseInstructor,
    CoursePublicationReview,
    CourseVersion,
    CurriculumSection,
    Lesson,
    LessonContentBlock,
)

Identifier = UUID | str
Snapshot = dict[str, Any]
POSITION_OFFSET = 1_000_000
SNAPSHOT_SCHEMA = "https://contracts.ai-lms.local/f002/canonical-course.v1.schema.json"


class CoursePersistenceConflictError(Exception):
    """A tenant scope, parent edge, or optimistic expectation did not match."""


def _as_uuid(value: Identifier) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _require_atomic_transaction() -> None:
    if not connection.in_atomic_block:
        raise RuntimeError("This persistence operation requires the calling atomic transaction.")


def _identity(node: Mapping[str, Any]) -> tuple[UUID | None, int | None]:
    raw_id = node.get("id")
    raw_version = node.get("expected_row_version")
    if (raw_id is None) != (raw_version is None):
        raise CoursePersistenceConflictError("Curriculum identities require matching row versions.")
    if raw_id is None:
        return None, None
    if not isinstance(raw_version, int) or raw_version < 1:
        raise CoursePersistenceConflictError("Curriculum row version is invalid.")
    return _as_uuid(cast(Identifier, raw_id)), raw_version


def _nodes(value: object, field: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CoursePersistenceConflictError(f"{field} must be an ordered sequence.")
    if not all(isinstance(item, Mapping) for item in value):
        raise CoursePersistenceConflictError(f"{field} contains an invalid node.")
    return cast(Sequence[Mapping[str, Any]], value)


class CourseRepository:
    """Tenant-scoped storage mechanics; lifecycle policy remains in the service lane."""

    def load_snapshot(
        self,
        tenant_id: Identifier,
        course_id: Identifier,
        version_id: Identifier,
    ) -> Snapshot | None:
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = _as_uuid(course_id)
        version_uuid = _as_uuid(version_id)
        course = Course.objects.filter(tenant_id=tenant_uuid, id=course_uuid).first()
        version = CourseVersion.objects.filter(
            tenant_id=tenant_uuid,
            course_id=course_uuid,
            id=version_uuid,
        ).first()
        if course is None or version is None:
            return None

        sections = list(
            CurriculumSection.objects.filter(
                tenant_id=tenant_uuid,
                course_version_id=version_uuid,
            ).order_by("position", "id")
        )
        lessons = list(
            Lesson.objects.filter(
                tenant_id=tenant_uuid,
                course_version_id=version_uuid,
            ).order_by("section_id", "position", "id")
        )
        blocks = list(
            LessonContentBlock.objects.filter(
                tenant_id=tenant_uuid,
                course_version_id=version_uuid,
            ).order_by("lesson_id", "position", "id")
        )
        lesson_rows: dict[UUID, list[Lesson]] = {}
        for lesson in lessons:
            lesson_rows.setdefault(lesson.section_id, []).append(lesson)
        block_rows: dict[UUID, list[LessonContentBlock]] = {}
        for block in blocks:
            block_rows.setdefault(block.lesson_id, []).append(block)

        latest_review = (
            CoursePublicationReview.objects.filter(
                tenant_id=tenant_uuid,
                course_version_id=version_uuid,
            )
            .order_by("-decided_at", "-id")
            .first()
        )
        review_payload: dict[str, object] | None = None
        if latest_review is not None:
            review_payload = {
                "id": str(latest_review.id),
                "tenant_id": str(latest_review.tenant_id),
                "course_version_id": str(latest_review.course_version_id),
                "decision": latest_review.decision,
                "reviewed_hash": latest_review.reviewed_hash,
                "reviewer_id": str(latest_review.reviewer_id),
                "self_review": latest_review.self_review,
                "reason_codes": list(latest_review.reason_codes),
                "decided_at": latest_review.decided_at.isoformat(),
            }

        section_payloads: list[dict[str, object]] = []
        for section in sections:
            lesson_payloads: list[dict[str, object]] = []
            for lesson in lesson_rows.get(section.id, []):
                block_payloads = [
                    {
                        "id": str(block.id),
                        "tenant_id": str(block.tenant_id),
                        "course_version_id": str(block.course_version_id),
                        "lesson_id": str(block.lesson_id),
                        "kind": block.kind,
                        "position": block.position,
                        "row_version": block.row_version,
                        "document": copy.deepcopy(block.document),
                    }
                    for block in block_rows.get(lesson.id, [])
                ]
                lesson_payloads.append(
                    {
                        "id": str(lesson.id),
                        "tenant_id": str(lesson.tenant_id),
                        "course_version_id": str(lesson.course_version_id),
                        "section_id": str(lesson.section_id),
                        "title": lesson.title,
                        "position": lesson.position,
                        "is_required": lesson.is_required,
                        "row_version": lesson.row_version,
                        "content_blocks": block_payloads,
                    }
                )
            section_payloads.append(
                {
                    "id": str(section.id),
                    "tenant_id": str(section.tenant_id),
                    "course_version_id": str(section.course_version_id),
                    "title": section.title,
                    "position": section.position,
                    "row_version": section.row_version,
                    "lessons": lesson_payloads,
                }
            )

        instructors = [
            str(value)
            for value in CourseInstructor.objects.filter(
                tenant_id=tenant_uuid,
                course_id=course_uuid,
            )
            .order_by("membership_id")
            .values_list("membership_id", flat=True)
        ]
        return {
            "$schema": SNAPSHOT_SCHEMA,
            "course": {
                "id": str(course.id),
                "tenant_id": str(course.tenant_id),
                "slug": course.slug,
                "reviewer_policy": course.reviewer_policy,
                "current_published_version_id": (
                    None
                    if course.current_published_version_id is None
                    else str(course.current_published_version_id)
                ),
                "instructor_membership_ids": instructors,
                "row_version": course.row_version,
            },
            "version": {
                "id": str(version.id),
                "tenant_id": str(version.tenant_id),
                "course_id": str(version.course_id),
                "predecessor_version_id": (
                    None
                    if version.predecessor_version_id is None
                    else str(version.predecessor_version_id)
                ),
                "version_number": version.version_number,
                "status": version.status,
                "origin_type": version.origin_type,
                "primary_locale": version.primary_locale,
                "title": version.title,
                "description": version.description,
                "content_hash": version.content_hash,
                "submitted_hash": version.submitted_hash,
                "approved_hash": version.approved_hash,
                "row_version": version.row_version,
            },
            "sections": section_payloads,
            "latest_review": review_payload,
        }

    def _required_snapshot(
        self, tenant_id: Identifier, course_id: Identifier, version_id: Identifier
    ) -> Snapshot:
        snapshot = self.load_snapshot(tenant_id, course_id, version_id)
        if snapshot is None:
            raise CoursePersistenceConflictError("Course version is unavailable in this tenant.")
        return snapshot

    def list_version_summaries(
        self,
        tenant_id: Identifier,
        course_id: Identifier,
        *,
        limit: int,
        before: tuple[int, Identifier] | None = None,
    ) -> tuple[list[dict[str, object]], tuple[int, str] | None]:
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = _as_uuid(course_id)
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        course = Course.objects.filter(tenant_id=tenant_uuid, id=course_uuid).first()
        if course is None:
            raise CoursePersistenceConflictError("Course is unavailable in this tenant.")
        query = CourseVersion.objects.filter(tenant_id=tenant_uuid, course_id=course_uuid)
        if before is not None:
            version_number, version_id = before
            before_id = _as_uuid(version_id)
            query = query.filter(
                Q(version_number__lt=version_number)
                | Q(version_number=version_number, id__lt=before_id)
            )
        versions = list(query.order_by("-version_number", "-id")[: limit + 1])
        has_more = len(versions) > limit
        page = versions[:limit]
        summaries: list[dict[str, object]] = [
            {
                "id": str(version.id),
                "tenant_id": str(version.tenant_id),
                "course_id": str(version.course_id),
                "predecessor_version_id": (
                    None
                    if version.predecessor_version_id is None
                    else str(version.predecessor_version_id)
                ),
                "version_number": version.version_number,
                "status": version.status,
                "title": version.title,
                "content_hash": version.content_hash,
                "row_version": version.row_version,
                "is_current_published": course.current_published_version_id == version.id,
            }
            for version in page
        ]
        next_position = None
        if has_more and page:
            tail = page[-1]
            next_position = (tail.version_number, str(tail.id))
        return summaries, next_position

    def insert_course_with_v1(
        self,
        *,
        tenant_id: Identifier,
        slug: str,
        primary_locale: str,
        title: str,
        description: str,
        content_hash: str,
        instructor_membership_ids: Sequence[Identifier],
        course_id: Identifier | None = None,
        version_id: Identifier | None = None,
        reviewer_policy: str = "self_review_allowed",
        origin_type: str = "manual",
    ) -> Snapshot:
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = uuid.uuid4() if course_id is None else _as_uuid(course_id)
        version_uuid = uuid.uuid4() if version_id is None else _as_uuid(version_id)
        membership_ids = tuple(_as_uuid(value) for value in instructor_membership_ids)
        with transaction.atomic():
            tenant = Tenant.objects.get(id=tenant_uuid)
            memberships = {
                membership.id: membership
                for membership in TenantMembership.objects.filter(
                    tenant_id=tenant_uuid,
                    id__in=membership_ids,
                )
            }
            if len(memberships) != len(set(membership_ids)) or not memberships:
                raise CoursePersistenceConflictError("Instructor membership scope did not match.")
            course = Course.objects.create(
                id=course_uuid,
                tenant=tenant,
                slug=slug,
                reviewer_policy=reviewer_policy,
            )
            version = CourseVersion.objects.create(
                id=version_uuid,
                tenant=tenant,
                course=course,
                version_number=1,
                status="draft",
                origin_type=origin_type,
                primary_locale=primary_locale,
                title=title,
                description=description,
                content_hash=content_hash,
            )
            CourseInstructor.objects.bulk_create(
                [
                    CourseInstructor(
                        tenant=tenant,
                        course=course,
                        membership=memberships[membership_id],
                    )
                    for membership_id in membership_ids
                ]
            )
            return self._required_snapshot(tenant_uuid, course.id, version.id)

    def compare_and_update_version(
        self,
        *,
        tenant_id: Identifier,
        course_id: Identifier,
        version_id: Identifier,
        expected_row_version: int,
        updates: Mapping[str, str],
        content_hash: str,
    ) -> Snapshot:
        allowed_fields = {"primary_locale", "title", "description"}
        if not updates or not set(updates) <= allowed_fields:
            raise ValueError("Only non-empty course metadata updates are accepted.")
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = _as_uuid(course_id)
        version_uuid = _as_uuid(version_id)
        with transaction.atomic():
            version = (
                CourseVersion.objects.select_for_update()
                .filter(tenant_id=tenant_uuid, course_id=course_uuid, id=version_uuid)
                .first()
            )
            if version is None or version.row_version != expected_row_version:
                raise CoursePersistenceConflictError("Course version row changed.")
            for field, value in updates.items():
                setattr(version, field, value)
            version.content_hash = content_hash
            version.row_version += 1
            version.save(update_fields=(*updates, "content_hash", "row_version", "updated_at"))
            return self._required_snapshot(tenant_uuid, course_uuid, version_uuid)

    def replace_curriculum(
        self,
        *,
        tenant_id: Identifier,
        course_id: Identifier,
        version_id: Identifier,
        expected_row_version: int,
        sections: Sequence[Mapping[str, Any]],
        content_hash: str,
    ) -> Snapshot:
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = _as_uuid(course_id)
        version_uuid = _as_uuid(version_id)
        with transaction.atomic():
            version = (
                CourseVersion.objects.select_for_update()
                .filter(tenant_id=tenant_uuid, course_id=course_uuid, id=version_uuid)
                .first()
            )
            if version is None or version.row_version != expected_row_version:
                raise CoursePersistenceConflictError("Course version row changed.")
            self._replace_curriculum_rows(tenant_uuid, version, sections)
            version.content_hash = content_hash
            version.row_version += 1
            version.save(update_fields=("content_hash", "row_version", "updated_at"))
            return self._required_snapshot(tenant_uuid, course_uuid, version_uuid)

    def _replace_curriculum_rows(
        self,
        tenant_id: UUID,
        version: CourseVersion,
        sections: Sequence[Mapping[str, Any]],
    ) -> None:
        existing_sections = list(
            CurriculumSection.objects.select_for_update().filter(
                tenant_id=tenant_id, course_version_id=version.id
            )
        )
        existing_lessons = list(
            Lesson.objects.select_for_update().filter(
                tenant_id=tenant_id, course_version_id=version.id
            )
        )
        existing_blocks = list(
            LessonContentBlock.objects.select_for_update().filter(
                tenant_id=tenant_id, course_version_id=version.id
            )
        )
        section_map = {item.id: item for item in existing_sections}
        lesson_map = {item.id: item for item in existing_lessons}
        block_map = {item.id: item for item in existing_blocks}

        LessonContentBlock.objects.filter(tenant_id=tenant_id, course_version_id=version.id).update(
            position=F("position") + POSITION_OFFSET
        )
        Lesson.objects.filter(tenant_id=tenant_id, course_version_id=version.id).update(
            position=F("position") + POSITION_OFFSET
        )
        CurriculumSection.objects.filter(tenant_id=tenant_id, course_version_id=version.id).update(
            position=F("position") + POSITION_OFFSET
        )

        kept_sections: set[UUID] = set()
        kept_lessons: set[UUID] = set()
        kept_blocks: set[UUID] = set()
        for section_node in sections:
            section_id, expected_section_row = _identity(section_node)
            section_title = cast(str, section_node["title"])
            section_position = cast(int, section_node["position"])
            if section_id is None:
                section = CurriculumSection.objects.create(
                    tenant_id=tenant_id,
                    course_version=version,
                    title=section_title,
                    position=section_position,
                )
            else:
                original_section = section_map.get(section_id)
                if original_section is None or original_section.row_version != expected_section_row:
                    raise CoursePersistenceConflictError("Section identity or row changed.")
                changed = (
                    original_section.title != section_title
                    or original_section.position != section_position
                )
                CurriculumSection.objects.filter(id=section_id).update(
                    title=section_title,
                    position=section_position,
                    row_version=original_section.row_version + int(changed),
                )
                section = original_section
            kept_sections.add(section.id)

            for lesson_node in _nodes(section_node.get("lessons"), "lessons"):
                lesson_id, expected_lesson_row = _identity(lesson_node)
                lesson_title = cast(str, lesson_node["title"])
                lesson_position = cast(int, lesson_node["position"])
                is_required = cast(bool, lesson_node["is_required"])
                if lesson_id is None:
                    lesson = Lesson.objects.create(
                        tenant_id=tenant_id,
                        course_version=version,
                        section_id=section.id,
                        title=lesson_title,
                        position=lesson_position,
                        is_required=is_required,
                    )
                else:
                    original_lesson = lesson_map.get(lesson_id)
                    if (
                        original_lesson is None
                        or original_lesson.section_id != section.id
                        or original_lesson.row_version != expected_lesson_row
                    ):
                        raise CoursePersistenceConflictError(
                            "Lesson identity, parent, or row changed."
                        )
                    changed = (
                        original_lesson.title != lesson_title
                        or original_lesson.position != lesson_position
                        or original_lesson.is_required != is_required
                    )
                    Lesson.objects.filter(id=lesson_id).update(
                        title=lesson_title,
                        position=lesson_position,
                        is_required=is_required,
                        row_version=original_lesson.row_version + int(changed),
                    )
                    lesson = original_lesson
                kept_lessons.add(lesson.id)

                for block_node in _nodes(lesson_node.get("content_blocks"), "content_blocks"):
                    block_id, expected_block_row = _identity(block_node)
                    kind = cast(str, block_node["kind"])
                    block_position = cast(int, block_node["position"])
                    document = copy.deepcopy(block_node["document"])
                    if block_id is None:
                        block = LessonContentBlock.objects.create(
                            tenant_id=tenant_id,
                            course_version=version,
                            lesson_id=lesson.id,
                            kind=kind,
                            position=block_position,
                            document=document,
                        )
                    else:
                        original_block = block_map.get(block_id)
                        if (
                            original_block is None
                            or original_block.lesson_id != lesson.id
                            or original_block.row_version != expected_block_row
                        ):
                            raise CoursePersistenceConflictError(
                                "Content-block identity, parent, or row changed."
                            )
                        changed = (
                            original_block.kind != kind
                            or original_block.position != block_position
                            or original_block.document != document
                        )
                        LessonContentBlock.objects.filter(id=block_id).update(
                            kind=kind,
                            position=block_position,
                            document=document,
                            row_version=original_block.row_version + int(changed),
                        )
                        block = original_block
                    kept_blocks.add(block.id)

        LessonContentBlock.objects.filter(
            tenant_id=tenant_id, course_version_id=version.id
        ).exclude(id__in=kept_blocks).delete()
        Lesson.objects.filter(tenant_id=tenant_id, course_version_id=version.id).exclude(
            id__in=kept_lessons
        ).delete()
        CurriculumSection.objects.filter(tenant_id=tenant_id, course_version_id=version.id).exclude(
            id__in=kept_sections
        ).delete()

    def append_review(
        self,
        *,
        tenant_id: Identifier,
        course_id: Identifier,
        version_id: Identifier,
        decision: str,
        reviewed_hash: str,
        reviewer_id: Identifier,
        self_review: bool,
        reason_codes: Sequence[str],
    ) -> Snapshot:
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = _as_uuid(course_id)
        version_uuid = _as_uuid(version_id)
        with transaction.atomic():
            if not CourseVersion.objects.filter(
                tenant_id=tenant_uuid, course_id=course_uuid, id=version_uuid
            ).exists():
                raise CoursePersistenceConflictError(
                    "Course version is unavailable in this tenant."
                )
            CoursePublicationReview.objects.create(
                tenant_id=tenant_uuid,
                course_version_id=version_uuid,
                decision=decision,
                reviewed_hash=reviewed_hash,
                reviewer_id=_as_uuid(reviewer_id),
                self_review=self_review,
                reason_codes=list(reason_codes),
                decided_at=timezone.now(),
            )
            return self._required_snapshot(tenant_uuid, course_uuid, version_uuid)

    def compare_and_transition_version(
        self,
        *,
        tenant_id: Identifier,
        course_id: Identifier,
        version_id: Identifier,
        expected_row_version: int,
        expected_status: str,
        expected_content_hash: str,
        next_status: str,
        hash_updates: Mapping[str, str | None],
        publication_pointer: tuple[int, Identifier | None, Identifier | None] | None = None,
    ) -> Snapshot:
        if not set(hash_updates) <= {"submitted_hash", "approved_hash"}:
            raise ValueError("Only review-binding hashes may transition here.")
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = _as_uuid(course_id)
        version_uuid = _as_uuid(version_id)
        with transaction.atomic():
            course = (
                Course.objects.select_for_update()
                .filter(tenant_id=tenant_uuid, id=course_uuid)
                .first()
            )
            version = (
                CourseVersion.objects.select_for_update()
                .filter(tenant_id=tenant_uuid, course_id=course_uuid, id=version_uuid)
                .first()
            )
            if (
                course is None
                or version is None
                or version.row_version != expected_row_version
                or version.status != expected_status
                or version.content_hash != expected_content_hash
            ):
                raise CoursePersistenceConflictError("Course transition expectation changed.")

            pointer_target: UUID | None = None
            if publication_pointer is not None:
                expected_course_row, expected_pointer, new_pointer = publication_pointer
                expected_pointer_uuid = (
                    None if expected_pointer is None else _as_uuid(expected_pointer)
                )
                pointer_target = None if new_pointer is None else _as_uuid(new_pointer)
                if (
                    course.row_version != expected_course_row
                    or course.current_published_version_id != expected_pointer_uuid
                    or (pointer_target is not None and pointer_target != version.id)
                ):
                    raise CoursePersistenceConflictError("Course publication pointer changed.")
                if pointer_target is None:
                    course.current_published_version_id = None
                    course.row_version += 1
                    course.save(
                        update_fields=(
                            "current_published_version",
                            "row_version",
                            "updated_at",
                        )
                    )

            version.status = next_status
            for field, value in hash_updates.items():
                setattr(version, field, value)
            version.row_version += 1
            version.save(
                update_fields=("status", *hash_updates.keys(), "row_version", "updated_at")
            )

            if publication_pointer is not None and pointer_target is not None:
                course.current_published_version_id = pointer_target
                course.row_version += 1
                course.save(
                    update_fields=("current_published_version", "row_version", "updated_at")
                )
            return self._required_snapshot(tenant_uuid, course_uuid, version_uuid)

    def create_successor_draft(
        self,
        *,
        tenant_id: Identifier,
        course_id: Identifier,
        source_version_id: Identifier,
        expected_course_row_version: int,
        expected_source_row_version: int,
        expected_source_content_hash: str,
    ) -> Snapshot:
        tenant_uuid = _as_uuid(tenant_id)
        course_uuid = _as_uuid(course_id)
        source_uuid = _as_uuid(source_version_id)
        with transaction.atomic():
            course = (
                Course.objects.select_for_update()
                .filter(tenant_id=tenant_uuid, id=course_uuid)
                .first()
            )
            source = (
                CourseVersion.objects.select_for_update()
                .filter(tenant_id=tenant_uuid, course_id=course_uuid, id=source_uuid)
                .first()
            )
            if (
                course is None
                or source is None
                or source.row_version != expected_source_row_version
                or source.content_hash != expected_source_content_hash
            ):
                raise CoursePersistenceConflictError("Successor source expectation changed.")
            existing = (
                CourseVersion.objects.filter(
                    tenant_id=tenant_uuid,
                    course_id=course_uuid,
                    predecessor_version_id=source.id,
                )
                .order_by("version_number", "id")
                .first()
            )
            if existing is not None:
                if (
                    existing.status in {"draft", "changes_requested"}
                    and course.row_version == expected_course_row_version + 1
                ):
                    return self._required_snapshot(tenant_uuid, course_uuid, existing.id)
                raise CoursePersistenceConflictError("A non-mutable successor already exists.")
            if course.row_version != expected_course_row_version:
                raise CoursePersistenceConflictError(
                    "Course row changed before successor creation."
                )

            maximum = CourseVersion.objects.filter(
                tenant_id=tenant_uuid, course_id=course_uuid
            ).aggregate(value=Max("version_number"))["value"]
            successor = CourseVersion.objects.create(
                tenant_id=tenant_uuid,
                course_id=course_uuid,
                predecessor_version=source,
                version_number=cast(int, maximum) + 1,
                status="draft",
                origin_type=source.origin_type,
                primary_locale=source.primary_locale,
                title=source.title,
                description=source.description,
                content_hash=source.content_hash,
                submitted_hash=None,
                approved_hash=None,
                row_version=1,
            )
            section_ids: dict[UUID, UUID] = {}
            lesson_ids: dict[UUID, UUID] = {}
            for section in CurriculumSection.objects.filter(
                tenant_id=tenant_uuid, course_version_id=source.id
            ).order_by("position", "id"):
                section_clone = CurriculumSection.objects.create(
                    tenant_id=tenant_uuid,
                    course_version=successor,
                    title=section.title,
                    position=section.position,
                    row_version=1,
                )
                section_ids[section.id] = section_clone.id
            for lesson in Lesson.objects.filter(
                tenant_id=tenant_uuid, course_version_id=source.id
            ).order_by("section_id", "position", "id"):
                lesson_clone = Lesson.objects.create(
                    tenant_id=tenant_uuid,
                    course_version=successor,
                    section_id=section_ids[lesson.section_id],
                    title=lesson.title,
                    position=lesson.position,
                    is_required=lesson.is_required,
                    row_version=1,
                )
                lesson_ids[lesson.id] = lesson_clone.id
            for block in LessonContentBlock.objects.filter(
                tenant_id=tenant_uuid, course_version_id=source.id
            ).order_by("lesson_id", "position", "id"):
                LessonContentBlock.objects.create(
                    tenant_id=tenant_uuid,
                    course_version=successor,
                    lesson_id=lesson_ids[block.lesson_id],
                    kind=block.kind,
                    position=block.position,
                    document=copy.deepcopy(block.document),
                    row_version=1,
                )
            course.row_version += 1
            course.save(update_fields=("row_version", "updated_at"))
            return self._required_snapshot(tenant_uuid, course_uuid, successor.id)

    def reserve_idempotency(
        self,
        *,
        tenant_id: Identifier,
        actor_id: Identifier,
        operation: str,
        key_digest: str,
        request_hash: str,
    ) -> tuple[IdempotencyReservation, bool]:
        _require_atomic_transaction()
        reservation, created = IdempotencyReservation.objects.get_or_create(
            tenant_id=_as_uuid(tenant_id),
            actor_id=_as_uuid(actor_id),
            operation=operation,
            key_digest=key_digest,
            defaults={"request_hash": request_hash},
        )
        if reservation.request_hash != request_hash:
            raise CoursePersistenceConflictError("Idempotency key request changed.")
        return reservation, not created

    def complete_idempotency(
        self, reservation_id: Identifier, response_payload: Mapping[str, object]
    ) -> None:
        _require_atomic_transaction()
        reservation = IdempotencyReservation.objects.select_for_update().get(
            id=_as_uuid(reservation_id)
        )
        reservation.status = "completed"
        reservation.response_payload = dict(response_payload)
        reservation.save(update_fields=("status", "response_payload", "updated_at"))

    def append_atomic_facts(
        self,
        *,
        tenant_id: Identifier,
        actor_id: Identifier,
        event_type: str,
        subject_type: str,
        subject_id: Identifier,
        aggregate_type: str,
        aggregate_id: Identifier,
        payload: Mapping[str, object],
    ) -> tuple[UUID, UUID]:
        _require_atomic_transaction()
        request_id = uuid.uuid4()
        audit = AuditFact.objects.create(
            tenant_id=_as_uuid(tenant_id),
            event_type=event_type,
            actor_id=_as_uuid(actor_id),
            subject_type=subject_type,
            subject_id=_as_uuid(subject_id),
            request_id=request_id,
            payload=dict(payload),
        )
        outbox = OutboxFact.objects.create(
            tenant_id=_as_uuid(tenant_id),
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=_as_uuid(aggregate_id),
            actor_id=_as_uuid(actor_id),
            request_id=request_id,
            payload=dict(payload),
        )
        return audit.id, outbox.id

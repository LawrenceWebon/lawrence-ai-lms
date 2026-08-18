from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from lms.api.schemas.courses import (
    CourseAdministrationError,
    CourseAdministrationServiceV1,
    CourseSnapshotV1,
    CourseVersionHistoryV1,
    CreateCourseV1,
    CreateSuccessorDraftV1,
    ReplaceCurriculumV1,
    SuccessorDraftResultV1,
    TransitionCourseVersionV1,
    UpdateCourseVersionV1,
)

COURSE_LIFECYCLE_READONLY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "tenant_id",
        "reviewer_policy",
        "current_published_version_id",
        "instructor_membership_ids",
        "predecessor_version_id",
        "version_number",
        "status",
        "origin_type",
        "content_hash",
        "submitted_hash",
        "approved_hash",
        "row_version",
        "latest_review",
    }
)


@dataclass(frozen=True, slots=True)
class AdminActorContext:
    """Trusted actor and explicit tenant selector established by Django Admin."""

    actor_id: UUID
    tenant_id: UUID | None
    privileged_access_grant_id: UUID | None = None


class CourseAdminActions:
    """Trusted Admin actions that delegate every read and mutation to the service."""

    readonly_fields = COURSE_LIFECYCLE_READONLY_FIELDS

    def __init__(self, *, service: CourseAdministrationServiceV1) -> None:
        self._service = service

    @staticmethod
    def _tenant_id(context: AdminActorContext) -> UUID:
        if context.tenant_id is None:
            raise CourseAdministrationError(code="TENANT_CONTEXT_REQUIRED")
        return context.tenant_id

    @staticmethod
    def _idempotency_key(value: str) -> str:
        if not 16 <= len(value) <= 128:
            raise CourseAdministrationError(code="COURSE_VALIDATION_FAILED")
        return value

    def create_course(
        self,
        *,
        context: AdminActorContext,
        request: CreateCourseV1,
        idempotency_key: str,
    ) -> CourseSnapshotV1:
        result = self._service.create_course(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return CourseSnapshotV1.model_validate(result, from_attributes=True)

    def get_course_version(
        self,
        *,
        context: AdminActorContext,
        course_id: UUID,
        version_id: UUID,
    ) -> CourseSnapshotV1:
        result = self._service.get_course_version(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            course_id=course_id,
            version_id=version_id,
        )
        return CourseSnapshotV1.model_validate(result, from_attributes=True)

    def list_course_versions(
        self,
        *,
        context: AdminActorContext,
        course_id: UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> CourseVersionHistoryV1:
        tenant_id = self._tenant_id(context)
        if not 1 <= limit <= 100 or (cursor is not None and not 1 <= len(cursor) <= 2048):
            raise CourseAdministrationError(code="COURSE_VALIDATION_FAILED")
        result = self._service.list_course_versions(
            actor_id=context.actor_id,
            tenant_id=tenant_id,
            course_id=course_id,
            cursor=cursor,
            limit=limit,
        )
        return CourseVersionHistoryV1.model_validate(result, from_attributes=True)

    def update_version(
        self,
        *,
        context: AdminActorContext,
        course_id: UUID,
        version_id: UUID,
        request: UpdateCourseVersionV1,
    ) -> CourseSnapshotV1:
        result = self._service.update_version(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            course_id=course_id,
            version_id=version_id,
            command=request,
        )
        return CourseSnapshotV1.model_validate(result, from_attributes=True)

    def replace_curriculum(
        self,
        *,
        context: AdminActorContext,
        course_id: UUID,
        version_id: UUID,
        request: ReplaceCurriculumV1,
    ) -> CourseSnapshotV1:
        result = self._service.replace_curriculum(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            course_id=course_id,
            version_id=version_id,
            command=request,
        )
        return CourseSnapshotV1.model_validate(result, from_attributes=True)

    def transition_version(
        self,
        *,
        context: AdminActorContext,
        course_id: UUID,
        version_id: UUID,
        request: TransitionCourseVersionV1,
        idempotency_key: str,
    ) -> CourseSnapshotV1:
        result = self._service.transition_version(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            course_id=course_id,
            version_id=version_id,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return CourseSnapshotV1.model_validate(result, from_attributes=True)

    def create_successor_draft(
        self,
        *,
        context: AdminActorContext,
        course_id: UUID,
        source_version_id: UUID,
        request: CreateSuccessorDraftV1,
        idempotency_key: str,
    ) -> SuccessorDraftResultV1:
        result = self._service.create_successor_draft(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            course_id=course_id,
            source_version_id=source_version_id,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return SuccessorDraftResultV1.model_validate(result, from_attributes=True)

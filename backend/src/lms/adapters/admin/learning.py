from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from lms.api.schemas.learning import (
    CreateEnrollmentV1,
    EnrollmentV1,
    LearningAdministrationError,
    LearningServiceV1,
    RevokeEnrollmentV1,
)

LEARNING_READONLY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "tenant_id",
        "learner_membership_id",
        "course_id",
        "course_version_id",
        "admission_source",
        "status",
        "enrolled_at",
        "revoked_at",
        "revocation_reason_code",
        "assigned_by_actor_id",
        "row_version",
        "course_progress",
        "lesson_progress",
    }
)


@dataclass(frozen=True, slots=True)
class LearningAdminActorContext:
    actor_id: UUID
    tenant_id: UUID | None


class LearningAdminActions:
    """Trusted Admin commands; generic editing is deliberately unavailable."""

    readonly_fields = LEARNING_READONLY_FIELDS

    def __init__(self, *, service: LearningServiceV1) -> None:
        self._service = service

    @staticmethod
    def _tenant_id(context: LearningAdminActorContext) -> UUID:
        if context.tenant_id is None:
            raise LearningAdministrationError(code="TENANT_CONTEXT_REQUIRED", status=400)
        return context.tenant_id

    @staticmethod
    def _idempotency_key(value: str) -> str:
        if not 16 <= len(value) <= 128:
            raise LearningAdministrationError(code="ENROLLMENT_VALIDATION_FAILED", status=422)
        return value

    def create_enrollment(
        self,
        *,
        context: LearningAdminActorContext,
        request: CreateEnrollmentV1,
        idempotency_key: str,
    ) -> EnrollmentV1:
        return EnrollmentV1.model_validate(
            self._service.create_enrollment(
                actor_id=context.actor_id,
                tenant_id=self._tenant_id(context),
                command=request,
                idempotency_key=self._idempotency_key(idempotency_key),
            ),
            from_attributes=True,
        )

    def revoke_enrollment(
        self,
        *,
        context: LearningAdminActorContext,
        enrollment_id: UUID,
        request: RevokeEnrollmentV1,
        idempotency_key: str,
    ) -> EnrollmentV1:
        return EnrollmentV1.model_validate(
            self._service.revoke_enrollment(
                actor_id=context.actor_id,
                tenant_id=self._tenant_id(context),
                enrollment_id=enrollment_id,
                command=request,
                idempotency_key=self._idempotency_key(idempotency_key),
            ),
            from_attributes=True,
        )

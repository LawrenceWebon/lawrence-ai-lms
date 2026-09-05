from __future__ import annotations

from typing import Final
from uuid import UUID

from lms.adapters.admin.documents import AdminActorContext
from lms.api.schemas.course_generation import (
    ApproveGenerationBlueprintV1,
    CanonicalizeCourseGenerationV1,
    CourseGenerationReviewPackageV1,
    CourseGenerationRunV1,
    CourseGenerationServiceV1,
    GenerationCanonicalizationV1,
    GenerationContractError,
    RejectCourseGenerationV1,
    StartCourseGenerationV1,
)

COURSE_GENERATION_READONLY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "tenant_id",
        "source_document_id",
        "source_version_id",
        "ingestion_run_id",
        "supersedes_run_id",
        "status",
        "adapter",
        "provider",
        "model",
        "input_manifest_sha256",
        "blueprint_content_sha256",
        "output_manifest_sha256",
        "attempt_count",
        "max_attempts",
        "checkpoint",
        "reason_code",
        "row_version",
        "created_at",
        "updated_at",
        "blueprint",
        "lessons",
        "source_edges",
    }
)


class CourseGenerationAdminActions:
    """Trusted Admin actions use the same human-review service boundary as FastAPI."""

    readonly_fields = COURSE_GENERATION_READONLY_FIELDS

    def __init__(self, *, service: CourseGenerationServiceV1) -> None:
        self._service = service

    @staticmethod
    def _tenant_id(context: AdminActorContext) -> UUID:
        if context.tenant_id is None:
            raise GenerationContractError(code="TENANT_CONTEXT_REQUIRED")
        return context.tenant_id

    @staticmethod
    def _idempotency_key(value: str) -> str:
        if not 16 <= len(value) <= 128 or value != value.strip():
            raise GenerationContractError(code="GENERATION_VALIDATION_FAILED")
        return value

    def start_generation(
        self,
        *,
        context: AdminActorContext,
        request: StartCourseGenerationV1,
        idempotency_key: str,
    ) -> CourseGenerationRunV1:
        result = self._service.start_generation(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return CourseGenerationRunV1.model_validate(result, from_attributes=True)

    def get_generation(
        self,
        *,
        context: AdminActorContext,
        run_id: UUID,
    ) -> CourseGenerationReviewPackageV1:
        result = self._service.get_generation(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            run_id=run_id,
        )
        return CourseGenerationReviewPackageV1.model_validate(result, from_attributes=True)

    def approve_blueprint(
        self,
        *,
        context: AdminActorContext,
        run_id: UUID,
        request: ApproveGenerationBlueprintV1,
        idempotency_key: str,
    ) -> CourseGenerationRunV1:
        result = self._service.approve_blueprint(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            run_id=run_id,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return CourseGenerationRunV1.model_validate(result, from_attributes=True)

    def reject_generation(
        self,
        *,
        context: AdminActorContext,
        run_id: UUID,
        request: RejectCourseGenerationV1,
        idempotency_key: str,
    ) -> CourseGenerationRunV1:
        result = self._service.reject_generation(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            run_id=run_id,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return CourseGenerationRunV1.model_validate(result, from_attributes=True)

    def canonicalize_generation(
        self,
        *,
        context: AdminActorContext,
        run_id: UUID,
        request: CanonicalizeCourseGenerationV1,
        idempotency_key: str,
    ) -> GenerationCanonicalizationV1:
        result = self._service.canonicalize_generation(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            run_id=run_id,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return GenerationCanonicalizationV1.model_validate(result, from_attributes=True)

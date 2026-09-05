from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from django.db import close_old_connections

from lms.api.course_composition import DjangoCourseAdministrationService
from lms.api.schemas.course_generation import (
    ApproveGenerationBlueprintV1,
    CanonicalizeCourseGenerationV1,
    GenerationContractError,
    RejectCourseGenerationV1,
    StartCourseGenerationV1,
)
from lms.modules.course_generation.errors import CourseGenerationError
from lms.modules.course_generation.services import CourseGenerationService
from lms.modules.course_generation.types import (
    ApproveBlueprintCommand,
    CanonicalizeGenerationCommand,
    GenerationIntent,
    RejectGenerationCommand,
)


def _translate[Result](call: Callable[[], Result]) -> Result:
    try:
        return call()
    except CourseGenerationError as error:
        raise GenerationContractError(
            code=error.code,
            errors=tuple(
                {
                    "location": ("body", *field.path.split(".")),
                    "code": field.code,
                }
                for field in error.field_errors
            ),
        ) from error
    finally:
        close_old_connections()


class DjangoCourseGenerationService:
    """Compose F005 behind the API/Admin structural port."""

    def __init__(self, *, service: CourseGenerationService | None = None) -> None:
        self._service = service or CourseGenerationService(
            course_drafts=DjangoCourseAdministrationService()
        )

    def start_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: StartCourseGenerationV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.start_generation(
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_document_id=command.source_document_id,
                source_version_id=command.source_version_id,
                ingestion_run_id=command.ingestion_run_id,
                intent=GenerationIntent(
                    target_level=command.target_level,
                    target_duration_minutes=command.target_duration_minutes,
                    intended_audience=command.intended_audience,
                    teaching_style=command.teaching_style,
                    locale=command.locale,
                    supersedes_run_id=command.supersedes_run_id,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def get_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
    ) -> object:
        return _translate(
            lambda: self._service.get_generation(
                actor_id=actor_id,
                tenant_id=tenant_id,
                run_id=run_id,
            )
        )

    def approve_blueprint(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: ApproveGenerationBlueprintV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.approve_blueprint(
                actor_id=actor_id,
                tenant_id=tenant_id,
                run_id=run_id,
                command=ApproveBlueprintCommand(
                    expected_run_row_version=command.expected_run_row_version,
                    blueprint_id=command.blueprint_id,
                    blueprint_revision=command.blueprint_revision,
                    expected_blueprint_content_sha256=(command.expected_blueprint_content_sha256),
                ),
                idempotency_key=idempotency_key,
            )
        )

    def reject_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: RejectCourseGenerationV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.reject_generation(
                actor_id=actor_id,
                tenant_id=tenant_id,
                run_id=run_id,
                command=RejectGenerationCommand(
                    expected_run_row_version=command.expected_run_row_version,
                    expected_review_content_sha256=(command.expected_review_content_sha256),
                    reason_code=command.reason_code,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def canonicalize_generation(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        command: CanonicalizeCourseGenerationV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.canonicalize_generation(
                actor_id=actor_id,
                tenant_id=tenant_id,
                run_id=run_id,
                command=CanonicalizeGenerationCommand(
                    expected_run_row_version=command.expected_run_row_version,
                    expected_output_manifest_sha256=(command.expected_output_manifest_sha256),
                    course_slug=command.course_slug,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def run_generation(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
    ) -> object:
        return _translate(
            lambda: self._service.run_generation(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
            )
        )

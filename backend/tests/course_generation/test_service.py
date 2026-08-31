from __future__ import annotations

from typing import Any

import pytest

from lms.modules.course_generation.errors import CourseGenerationError
from lms.modules.course_generation.models import (
    BlueprintReviewDecision,
    CourseBlueprintItem,
    CourseGenerationAttempt,
    CourseGenerationRejection,
    GeneratedLessonArtifact,
    GenerationRunSnapshot,
    GenerationSourceEdge,
)
from lms.modules.course_generation.types import (
    ApproveBlueprintCommand,
    GenerationIntent,
    RejectGenerationCommand,
)
from lms.modules.courses.validation import validate_rich_text_document
from lms.modules.documents.types import ReviewAuthorizationCommand
from tests.documents.test_ingestion_service import _activate_operation, _admit


def _intent(*, supersedes_run_id: Any = None) -> GenerationIntent:
    return GenerationIntent(
        target_level="beginner",
        target_duration_minutes=45,
        intended_audience="Adult learners using a synthetic source",
        teaching_style="guided",
        locale="en",
        supersedes_run_id=supersedes_run_id,
    )


def _ready_source(
    *,
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    valid_pdf_bytes: bytes,
    suffix: str,
) -> Any:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted = _admit(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        body=valid_pdf_bytes,
        key_suffix=f"generation-{suffix}",
    )
    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="extract",
        key_suffix=f"generation-{suffix}",
    )
    ingestion = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key=f"generation-ingestion-start-{suffix}",
    )
    result = ingestion_service.run_ingestion(
        tenant_id=tenant_id,
        run_id=ingestion.id,
        worker_id=f"generation-source-worker-{suffix}",
    )
    assert result.run.status == "ready_for_generation"
    return admitted, result.run


@pytest.mark.django_db
def test_generation_requires_independent_rights_and_exact_human_approval(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    generation_service: Any,
    valid_pdf_bytes: bytes,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted, ingestion = _ready_source(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        ingestion_service=ingestion_service,
        valid_pdf_bytes=valid_pdf_bytes,
        suffix="happy-0001",
    )

    with pytest.raises(CourseGenerationError, match="GENERATION_RIGHTS_REQUIRED"):
        generation_service.start_generation(
            actor_id=instructor,
            tenant_id=tenant_id,
            source_document_id=admitted.source_document.id,
            source_version_id=admitted.source_version.id,
            ingestion_run_id=ingestion.id,
            intent=_intent(),
            idempotency_key="generation-start-without-rights-0001",
        )

    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="generate",
        key_suffix="generation-happy-0001",
    )
    run = generation_service.start_generation(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        ingestion_run_id=ingestion.id,
        intent=_intent(),
        idempotency_key="generation-start-happy-0001",
    )
    replay = generation_service.start_generation(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        ingestion_run_id=ingestion.id,
        intent=_intent(),
        idempotency_key="generation-start-happy-0001",
    )
    assert replay.id == run.id
    snapshot = GenerationRunSnapshot.objects.get(generation_run_id=run.id)
    assert snapshot.metadata["provider"] == "local_deterministic"
    assert snapshot.metadata["model"] == "none"
    assert snapshot.metadata["input_token_count"] == 0
    assert snapshot.metadata["output_token_count"] == 0
    assert snapshot.metadata["cost_minor_units"] == 0
    assert "prompt" not in snapshot.metadata

    planned = generation_service.run_generation(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="generation-worker-happy",
    )
    assert planned.claimed is True
    assert planned.run.status == "blueprint_review"
    package = generation_service.get_generation(
        actor_id=admin,
        tenant_id=tenant_id,
        run_id=run.id,
    )
    assert package.blueprint is not None
    assert package.lessons == ()
    assert CourseBlueprintItem.objects.filter(generation_run_id=run.id).count() == 2
    assert (
        GenerationSourceEdge.objects.filter(
            generation_run_id=run.id, edge_kind="blueprint_item"
        ).count()
        == 2
    )

    with pytest.raises(CourseGenerationError, match="GENERATION_VERSION_CONFLICT"):
        generation_service.approve_blueprint(
            actor_id=admin,
            tenant_id=tenant_id,
            run_id=run.id,
            command=ApproveBlueprintCommand(
                expected_run_row_version=planned.run.row_version,
                blueprint_id=package.blueprint.id,
                blueprint_revision=1,
                expected_blueprint_content_sha256="sha256:" + "0" * 64,
            ),
        )

    approved = generation_service.approve_blueprint(
        actor_id=admin,
        tenant_id=tenant_id,
        run_id=run.id,
        command=ApproveBlueprintCommand(
            expected_run_row_version=planned.run.row_version,
            blueprint_id=package.blueprint.id,
            blueprint_revision=1,
            expected_blueprint_content_sha256=package.blueprint.content_sha256,
        ),
    )
    assert approved.status == "generation_queued"
    assert BlueprintReviewDecision.objects.get(generation_run_id=run.id).decision == "approve"

    generated = generation_service.run_generation(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="generation-worker-happy",
    )
    assert generated.run.status == "review_ready"
    assert generated.run.output_manifest_sha256 is not None
    final_package = generation_service.get_generation(
        actor_id=admin,
        tenant_id=tenant_id,
        run_id=run.id,
    )
    assert len(final_package.lessons) == 1
    validate_rich_text_document(final_package.lessons[0].document)
    assert GeneratedLessonArtifact.objects.filter(generation_run_id=run.id).count() == 1
    assert (
        GenerationSourceEdge.objects.filter(
            generation_run_id=run.id, edge_kind="generated_lesson"
        ).count()
        == 1
    )
    assert (
        CourseGenerationAttempt.objects.filter(
            generation_run_id=run.id, outcome="completed"
        ).count()
        == 2
    )

    rejected = generation_service.reject_generation(
        actor_id=admin,
        tenant_id=tenant_id,
        run_id=run.id,
        command=RejectGenerationCommand(
            expected_run_row_version=generated.run.row_version,
            expected_review_content_sha256=generated.run.output_manifest_sha256,
            reason_code="GENERATION_CONTENT_REJECTED",
        ),
    )
    assert rejected.status == "rejected"
    assert CourseGenerationRejection.objects.filter(generation_run_id=run.id).exists()

    successor = generation_service.start_generation(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        ingestion_run_id=ingestion.id,
        intent=_intent(supersedes_run_id=run.id),
        idempotency_key="generation-start-successor-0002",
    )
    assert successor.id != run.id
    assert successor.supersedes_run_id == run.id


@pytest.mark.django_db
def test_revoked_generate_rights_block_worker_before_source_processing(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    generation_service: Any,
    valid_pdf_bytes: bytes,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted, ingestion = _ready_source(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        ingestion_service=ingestion_service,
        valid_pdf_bytes=valid_pdf_bytes,
        suffix="revoked-0001",
    )
    generate = _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="generate",
        key_suffix="generation-revoked-0001",
    )
    run = generation_service.start_generation(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        ingestion_run_id=ingestion.id,
        intent=_intent(),
        idempotency_key="generation-start-before-revoke-0001",
    )
    documents_service.review_operation_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        operation="generate",
        command=ReviewAuthorizationCommand(
            decision="revoke",
            expected_authorization_row_version=generate.row_version,
            decision_code="RIGHTS_REVOKED",
        ),
        idempotency_key="generation-revoke-operation-0001",
    )

    result = generation_service.run_generation(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="generation-worker-revoked",
    )
    assert result.claimed is False
    assert result.run.status == "rights_blocked"
    assert result.run.reason_code == "GENERATION_RIGHTS_INACTIVE"
    assert CourseGenerationAttempt.objects.filter(generation_run_id=run.id).count() == 0

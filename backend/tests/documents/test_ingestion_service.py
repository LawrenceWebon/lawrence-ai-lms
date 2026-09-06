from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from typing import Any

import pytest
from django.utils import timezone
from pypdf import PdfWriter

from lms.modules.documents.errors import SourceAdmissionError
from lms.modules.documents.models import (
    DocumentElement,
    DocumentIngestionAttempt,
    DocumentIngestionRun,
    DocumentPage,
    DocumentSection,
    SourceArtifact,
    SourceUseAuthorization,
)
from lms.modules.documents.types import (
    CreateAdmissionCommand,
    ReviewAuthorizationCommand,
    RightsDeclarationInput,
)


def _create_command() -> CreateAdmissionCommand:
    return CreateAdmissionCommand(
        display_name="Synthetic ingestion source",
        declared_filename="synthetic-ingestion-source.pdf",
        rights_declaration=RightsDeclarationInput(
            basis="owned",
            attestation_version="f003-source-rights-attestation-v1",
            attested=True,
        ),
    )


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    body = BytesIO()
    writer.write(body)
    return body.getvalue()


def _admit(
    *,
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    body: bytes,
    key_suffix: str,
) -> Any:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = documents_service.create_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        command=_create_command(),
        idempotency_key=f"ingestion-create-{key_suffix}",
    )
    documents_service.review_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=ReviewAuthorizationCommand(
            decision="activate",
            expected_authorization_row_version=1,
            decision_code="RIGHTS_EVIDENCE_ACCEPTED",
        ),
        idempotency_key=f"ingestion-store-review-{key_suffix}",
    )
    intent = documents_service.create_upload_intent(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key=f"ingestion-upload-intent-{key_suffix}",
    )
    return documents_service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=body,
    )


def _activate_operation(
    *,
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    admitted: Any,
    operation: str,
    key_suffix: str,
) -> Any:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    requested = documents_service.request_operation_authorization(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        operation=operation,
        idempotency_key=f"ingestion-operation-request-{operation}-{key_suffix}",
    )
    return documents_service.review_operation_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        operation=operation,
        command=ReviewAuthorizationCommand(
            decision="activate",
            expected_authorization_row_version=requested.row_version,
            decision_code="RIGHTS_EVIDENCE_ACCEPTED",
        ),
        idempotency_key=f"ingestion-operation-review-{operation}-{key_suffix}",
    )


@pytest.mark.django_db
def test_ingestion_requires_independent_extract_rights_and_persists_stable_output(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    valid_pdf_bytes: bytes,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted = _admit(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        body=valid_pdf_bytes,
        key_suffix="happy-0001",
    )

    with pytest.raises(
        SourceAdmissionError,
        match="SOURCE_OPERATION_AUTHORIZATION_REQUIRED",
    ):
        ingestion_service.start_ingestion(
            actor_id=instructor,
            tenant_id=tenant_id,
            source_document_id=admitted.source_document.id,
            source_version_id=admitted.source_version.id,
            idempotency_key="ingestion-start-without-extract-0001",
        )

    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="extract",
        key_suffix="happy-0001",
    )
    run = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key="ingestion-start-happy-0001",
    )
    replay = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key="ingestion-start-happy-0001",
    )
    assert replay.id == run.id

    result = ingestion_service.run_ingestion(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="documents-worker-1",
    )
    assert result.claimed is True
    assert result.run.status == "ready_for_generation"
    assert result.run.output_manifest_sha256 is not None
    assert result.run.quality_summary["page_count"] == 1
    assert DocumentPage.objects.filter(source_version_id=run.source_version_id).count() == 1
    assert DocumentElement.objects.filter(source_version_id=run.source_version_id).count() >= 2
    assert DocumentSection.objects.filter(source_version_id=run.source_version_id).count() == 1
    assert SourceArtifact.objects.filter(source_version_id=run.source_version_id).count() == 2
    first_page_ids = tuple(
        DocumentPage.objects.filter(source_version_id=run.source_version_id)
        .order_by("page_number")
        .values_list("id", flat=True)
    )

    reprocess = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key="ingestion-start-happy-reprocess-0002",
    )
    assert reprocess.id != run.id
    repeated = ingestion_service.run_ingestion(
        tenant_id=tenant_id,
        run_id=reprocess.id,
        worker_id="documents-worker-1",
    )
    assert repeated.run.status == "ready_for_generation"
    assert repeated.run.output_manifest_sha256 == result.run.output_manifest_sha256
    assert (
        tuple(
            DocumentPage.objects.filter(source_version_id=run.source_version_id)
            .order_by("page_number")
            .values_list("id", flat=True)
        )
        == first_page_ids
    )
    assert DocumentIngestionRun.objects.filter(source_version_id=run.source_version_id).count() == 2


@pytest.mark.django_db
def test_empty_page_requests_ocr_but_unapproved_adapter_cannot_run(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted = _admit(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        body=_blank_pdf(),
        key_suffix="ocr-0001",
    )
    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="extract",
        key_suffix="ocr-0001",
    )
    run = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key="ingestion-start-ocr-0001",
    )

    first = ingestion_service.run_ingestion(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="documents-worker-ocr",
    )
    assert first.run.status == "retryable"
    assert first.run.reason_code == "OCR_REQUIRED"
    ocr = SourceUseAuthorization.objects.get(
        tenant_id=tenant_id,
        source_version_id=run.source_version_id,
        operation="ocr",
    )
    assert ocr.status == "requested"
    assert DocumentIngestionAttempt.objects.get(
        ingestion_run_id=run.id,
        attempt_number=1,
    ).observation == {"ocr_page_numbers": [1]}

    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="ocr",
        key_suffix="ocr-activation-0002",
    )
    second = ingestion_service.run_ingestion(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="documents-worker-ocr",
    )
    assert second.run.status == "retryable"
    assert second.run.reason_code == "OCR_ADAPTER_UNAVAILABLE"
    assert DocumentPage.objects.filter(source_version_id=run.source_version_id).count() == 0


@pytest.mark.django_db
def test_revoked_extract_rights_block_a_queued_run_before_reading_source(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    valid_pdf_bytes: bytes,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted = _admit(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        body=valid_pdf_bytes,
        key_suffix="revoke-0001",
    )
    extract = _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="extract",
        key_suffix="revoke-0001",
    )
    run = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key="ingestion-start-before-revoke-0001",
    )
    documents_service.review_operation_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        operation="extract",
        command=ReviewAuthorizationCommand(
            decision="revoke",
            expected_authorization_row_version=extract.row_version,
            decision_code="RIGHTS_REVOKED",
        ),
        idempotency_key="ingestion-revoke-extract-0001",
    )

    result = ingestion_service.run_ingestion(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="documents-worker-revoked",
    )
    assert result.claimed is False
    assert result.run.status == "rights_blocked"
    assert result.run.reason_code == "SOURCE_OPERATION_AUTHORIZATION_INACTIVE"
    assert DocumentIngestionAttempt.objects.filter(ingestion_run_id=run.id).count() == 0


@pytest.mark.django_db
def test_expired_mid_stage_lease_resumes_from_a_new_bounded_attempt(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    valid_pdf_bytes: bytes,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted = _admit(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        body=valid_pdf_bytes,
        key_suffix="lease-0001",
    )
    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="extract",
        key_suffix="lease-0001",
    )
    run = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key="ingestion-start-lease-0001",
    )
    _claimed_run, _attempt, claimed = ingestion_service._claim(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="documents-worker-stalled",
    )
    assert claimed is True
    ingestion_service._advance(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="documents-worker-stalled",
        expected_status="claimed",
        status="extracting",
        checkpoint="extracting_text",
    )
    DocumentIngestionRun.objects.filter(id=run.id).update(
        lease_expires_at=timezone.now() - timedelta(seconds=1)
    )

    resumed = ingestion_service.run_ingestion(
        tenant_id=tenant_id,
        run_id=run.id,
        worker_id="documents-worker-resumed",
    )
    assert resumed.run.status == "ready_for_generation"
    assert resumed.run.attempt_count == 2
    assert list(
        DocumentIngestionAttempt.objects.filter(ingestion_run_id=run.id)
        .order_by("attempt_number")
        .values_list("outcome", flat=True)
    ) == ["retryable", "completed"]


@pytest.mark.django_db
def test_ingestion_read_uses_tenant_scoped_neutral_not_found(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    valid_pdf_bytes: bytes,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admitted = _admit(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        body=valid_pdf_bytes,
        key_suffix="neutral-0001",
    )
    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="extract",
        key_suffix="neutral-0001",
    )
    run = ingestion_service.start_ingestion(
        actor_id=instructor,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=admitted.source_document.id,
        source_version_id=admitted.source_version.id,
        idempotency_key="ingestion-start-neutral-0001",
    )

    with pytest.raises(SourceAdmissionError, match="INGESTION_RESOURCE_NOT_FOUND"):
        ingestion_service.get_ingestion(
            actor_id=instructor,
            tenant_id=tenancy_seed["beta"].id,
            source_document_id=admitted.source_document.id,
            source_version_id=admitted.source_version.id,
            run_id=run.id,
        )

from __future__ import annotations

from typing import Any

import pytest

from lms.modules.documents.errors import SourceAdmissionError
from lms.modules.documents.models import DocumentJob, StorageObject, UploadIntent
from lms.modules.documents.types import (
    CancelAdmissionCommand,
    CreateAdmissionCommand,
    ReviewAuthorizationCommand,
    RightsDeclarationInput,
)
from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact


def create_command(*, display_name: str = "Synthetic civic source") -> CreateAdmissionCommand:
    return CreateAdmissionCommand(
        display_name=display_name,
        declared_filename="synthetic-civic-source.pdf",
        rights_declaration=RightsDeclarationInput(
            basis="owned",
            attestation_version="f003-source-rights-attestation-v1",
            attested=True,
        ),
    )


@pytest.mark.django_db
def test_create_records_declaration_but_does_not_authorize_upload(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    snapshot = documents_service.create_admission(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        command=create_command(),
        idempotency_key="create-source-admission-0001",
    )

    assert snapshot.source_version.admission_status == "rights_pending"
    assert snapshot.store_authorization.status == "requested"
    assert snapshot.store_authorization.operation == "store"
    assert snapshot.upload_intent is None
    assert AuditFact.objects.filter(event_type="source.rights.declared.v1").count() == 1
    assert OutboxFact.objects.filter(event_type="source.rights.declared.v1").count() == 1


@pytest.mark.django_db
def test_same_human_cannot_review_own_declaration(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    actor_id = tenancy_seed["profiles"]["instructor"].provider_subject
    created = documents_service.create_admission(
        actor_id=actor_id,
        tenant_id=tenancy_seed["alpha"].id,
        command=create_command(),
        idempotency_key="create-source-admission-0002",
    )

    with pytest.raises(
        SourceAdmissionError,
        match="SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED",
    ):
        documents_service.review_authorization(
            actor_id=actor_id,
            tenant_id=tenancy_seed["alpha"].id,
            source_document_id=created.source_document.id,
            source_version_id=created.source_version.id,
            authorization_id=created.store_authorization.id,
            command=ReviewAuthorizationCommand(
                decision="activate",
                expected_authorization_row_version=1,
                decision_code="RIGHTS_EVIDENCE_ACCEPTED",
            ),
            idempotency_key="review-source-admission-0001",
        )

    unchanged = documents_service.get_admission(
        actor_id=actor_id,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
    )
    assert unchanged.store_authorization.status == "requested"


@pytest.mark.django_db
def test_distinct_reviewer_upload_and_validation_admit_byte_derived_pdf(
    tenancy_seed: dict[str, Any], documents_service: Any, valid_pdf_bytes: bytes
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = documents_service.create_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        command=create_command(),
        idempotency_key="create-source-admission-0003",
    )
    approved = documents_service.review_authorization(
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
        idempotency_key="review-source-admission-0002",
    )
    assert approved.source_version.admission_status == "upload_pending"

    intent = documents_service.create_upload_intent(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="create-upload-intent-0001",
    )
    persisted_intent = UploadIntent.objects.get(id=intent.id)
    assert intent.opaque_token not in persisted_intent.token_digest
    assert "source_quarantine" not in intent.target_url

    admitted = documents_service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )
    assert admitted.source_version.admission_status == "admitted"
    assert admitted.source_version.content_sha256 is not None
    assert admitted.source_version.derived_file_size_bytes == len(valid_pdf_bytes)
    assert admitted.source_version.derived_page_count == 1
    assert StorageObject.objects.filter(tenant_id=tenant_id, status="present").count() == 1
    assert DocumentJob.objects.get(stage="validate_admission").status == "completed"


@pytest.mark.django_db
def test_create_idempotency_replays_equivalent_input_and_conflicts_on_change(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    first = documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenant_id,
        command=create_command(),
        idempotency_key="create-source-admission-replay",
    )
    replay = documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenant_id,
        command=create_command(),
        idempotency_key="create-source-admission-replay",
    )
    assert replay.source_document.id == first.source_document.id
    assert IdempotencyReservation.objects.count() == 1

    with pytest.raises(SourceAdmissionError, match="IDEMPOTENCY_CONFLICT"):
        documents_service.create_admission(
            actor_id=actor,
            tenant_id=tenant_id,
            command=create_command(display_name="Changed synthetic source"),
            idempotency_key="create-source-admission-replay",
        )


@pytest.mark.django_db
def test_cancel_blocks_target_and_never_reports_removal_without_observation(
    tenancy_seed: dict[str, Any], documents_service: Any, valid_pdf_bytes: bytes
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = documents_service.create_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        command=create_command(),
        idempotency_key="create-source-admission-cancel",
    )
    approved = documents_service.review_authorization(
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
        idempotency_key="review-source-admission-cancel",
    )
    intent = documents_service.create_upload_intent(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="create-upload-intent-cancel",
    )
    cancelled = documents_service.cancel_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        command=CancelAdmissionCommand(
            expected_source_version_row_version=approved.source_version.row_version,
            reason_code="USER_CANCELLED",
        ),
        idempotency_key="cancel-source-admission-0001",
    )
    assert cancelled.source_version.admission_status == "cancelled"
    assert cancelled.removal.status == "not_required"

    with pytest.raises(SourceAdmissionError, match="RESOURCE_NOT_FOUND"):
        documents_service.upload_to_intent(
            opaque_token=intent.opaque_token,
            content_type="application/pdf",
            body=valid_pdf_bytes,
        )


@pytest.mark.django_db
def test_wrong_tenant_source_selector_is_neutral(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    created = documents_service.create_admission(
        actor_id=instructor,
        tenant_id=tenancy_seed["alpha"].id,
        command=create_command(),
        idempotency_key="create-source-admission-neutral",
    )

    with pytest.raises(SourceAdmissionError, match="RESOURCE_NOT_FOUND"):
        documents_service.get_admission(
            actor_id=instructor,
            tenant_id=tenancy_seed["beta"].id,
            source_document_id=created.source_document.id,
            source_version_id=created.source_version.id,
        )

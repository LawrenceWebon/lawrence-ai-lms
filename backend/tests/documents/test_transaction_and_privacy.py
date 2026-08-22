from __future__ import annotations

import json
from typing import Any

import pytest

from lms.modules.documents.errors import SourceAdmissionError
from lms.modules.documents.models import (
    SourceDocument,
    SourceRightsDeclaration,
    SourceUseAuthorization,
    SourceVersion,
    StorageObject,
    UploadIntent,
)
from lms.modules.documents.services import SourceAdmissionService
from lms.modules.documents.types import (
    CancelAdmissionCommand,
    CreateAdmissionCommand,
    ReviewAuthorizationCommand,
    RightsDeclarationInput,
)
from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact


def command(suffix: str) -> CreateAdmissionCommand:
    return CreateAdmissionCommand(
        display_name=f"Synthetic {suffix} source",
        declared_filename=f"synthetic-{suffix}.pdf",
        rights_declaration=RightsDeclarationInput(
            basis="owned",
            attestation_version="f003-source-rights-attestation-v1",
            attested=True,
        ),
    )


@pytest.mark.django_db
def test_create_rolls_back_state_idempotency_audit_and_outbox_together(
    tenancy_seed: dict[str, Any],
    documents_service: SourceAdmissionService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_fact(**_kwargs: object) -> None:
        raise RuntimeError("synthetic outbox failure")

    monkeypatch.setattr(documents_service, "_record_fact", fail_fact)
    with pytest.raises(RuntimeError, match="synthetic outbox failure"):
        documents_service.create_admission(
            actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
            tenant_id=tenancy_seed["alpha"].id,
            command=command("rollback"),
            idempotency_key="create-transaction-rollback-0001",
        )

    assert SourceDocument.objects.count() == 0
    assert SourceVersion.objects.count() == 0
    assert SourceRightsDeclaration.objects.count() == 0
    assert SourceUseAuthorization.objects.count() == 0
    assert IdempotencyReservation.objects.count() == 0
    assert AuditFact.objects.count() == 0
    assert OutboxFact.objects.count() == 0


@pytest.mark.django_db
def test_review_and_cancel_are_idempotent_and_stale_commands_leave_no_partial_fact(
    tenancy_seed: dict[str, Any], documents_service: SourceAdmissionService
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = documents_service.create_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        command=command("idempotent-review"),
        idempotency_key="create-idempotent-review-0001",
    )
    review_command = ReviewAuthorizationCommand(
        decision="activate",
        expected_authorization_row_version=1,
        decision_code="RIGHTS_EVIDENCE_ACCEPTED",
    )
    first = documents_service.review_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=review_command,
        idempotency_key="review-idempotent-replay-0001",
    )
    replay = documents_service.review_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=review_command,
        idempotency_key="review-idempotent-replay-0001",
    )
    assert replay.store_authorization.row_version == first.store_authorization.row_version
    assert (
        OutboxFact.objects.filter(event_type="source.store_authorization.activated.v1").count() == 1
    )

    with pytest.raises(SourceAdmissionError, match="SOURCE_ADMISSION_VERSION_CONFLICT"):
        documents_service.cancel_admission(
            actor_id=instructor,
            tenant_id=tenant_id,
            source_document_id=created.source_document.id,
            source_version_id=created.source_version.id,
            command=CancelAdmissionCommand(
                expected_source_version_row_version=1,
                reason_code="USER_CANCELLED",
            ),
            idempotency_key="cancel-stale-version-0001",
        )
    assert OutboxFact.objects.filter(event_type="source.version.cancelled.v1").count() == 0

    cancel_command = CancelAdmissionCommand(
        expected_source_version_row_version=first.source_version.row_version,
        reason_code="USER_CANCELLED",
    )
    cancelled = documents_service.cancel_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        command=cancel_command,
        idempotency_key="cancel-idempotent-replay-0001",
    )
    cancel_replay = documents_service.cancel_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        command=cancel_command,
        idempotency_key="cancel-idempotent-replay-0001",
    )
    assert cancel_replay.source_version.row_version == cancelled.source_version.row_version
    assert OutboxFact.objects.filter(event_type="source.version.cancelled.v1").count() == 1


@pytest.mark.django_db
def test_events_and_audit_facts_exclude_source_bytes_tokens_paths_and_names(
    tenancy_seed: dict[str, Any],
    documents_service: SourceAdmissionService,
    valid_pdf_bytes: bytes,
    caplog: pytest.LogCaptureFixture,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    declared_filename = "synthetic-private-filename.pdf"
    created = documents_service.create_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        command=CreateAdmissionCommand(
            display_name="Synthetic private display name",
            declared_filename=declared_filename,
            rights_declaration=RightsDeclarationInput(
                basis="owned",
                attestation_version="f003-source-rights-attestation-v1",
                attested=True,
            ),
        ),
        idempotency_key="create-private-facts-0001",
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
        idempotency_key="review-private-facts-0001",
    )
    intent = documents_service.create_upload_intent(
        actor_id=instructor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="intent-private-facts-0001",
    )
    admitted = documents_service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )
    locator = StorageObject.objects.get().private_locator
    documents_service.review_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=ReviewAuthorizationCommand(
            decision="revoke",
            expected_authorization_row_version=admitted.store_authorization.row_version,
            decision_code="RIGHTS_REVOKED",
        ),
        idempotency_key="review-private-facts-revoke-0001",
    )

    serialized_facts = json.dumps(
        list(AuditFact.objects.values("event_type", "payload"))
        + list(OutboxFact.objects.values("event_type", "payload")),
        sort_keys=True,
    )
    forbidden = (
        declared_filename,
        "Synthetic private display name",
        intent.opaque_token,
        intent.target_url,
        locator,
        valid_pdf_bytes.decode(),
    )
    assert all(value not in serialized_facts for value in forbidden)
    assert all(value not in caplog.text for value in forbidden)
    persisted_intent = UploadIntent.objects.get(id=intent.id)
    assert persisted_intent.token_digest != intent.opaque_token
    assert approved.store_authorization.operation == "store"

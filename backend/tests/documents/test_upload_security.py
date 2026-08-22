from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from lms.modules.documents import services as services_module
from lms.modules.documents.errors import SourceAdmissionError
from lms.modules.documents.inspector import LocalPdfInspector
from lms.modules.documents.models import StorageObject, UploadIntent
from lms.modules.documents.policy import ADMISSION_POLICY
from lms.modules.documents.services import SourceAdmissionService
from lms.modules.documents.storage import LocalQuarantineStorage
from lms.modules.documents.types import (
    CreateAdmissionCommand,
    ReviewAuthorizationCommand,
    RightsDeclarationInput,
)


def create_command(suffix: str) -> CreateAdmissionCommand:
    return CreateAdmissionCommand(
        display_name=f"Synthetic {suffix} source",
        declared_filename=f"synthetic-{suffix}.pdf",
        rights_declaration=RightsDeclarationInput(
            basis="owned",
            attestation_version="f003-source-rights-attestation-v1",
            attested=True,
        ),
    )


def approve_source(
    service: SourceAdmissionService,
    tenancy_seed: dict[str, Any],
    suffix: str,
) -> tuple[Any, Any]:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = service.create_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        command=create_command(suffix),
        idempotency_key=f"create-security-{suffix}-0001",
    )
    approved = service.review_authorization(
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
        idempotency_key=f"review-security-{suffix}-0001",
    )
    return created, approved


def issue_intent(
    service: SourceAdmissionService,
    tenancy_seed: dict[str, Any],
    created: Any,
    suffix: str,
) -> Any:
    return service.create_upload_intent(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key=f"intent-security-{suffix}-0001",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("content_type", "body_factory", "expected_code"),
    [
        (
            "text/plain",
            lambda valid: valid,
            "PDF_MEDIA_TYPE_INVALID",
        ),
        (
            "application/pdf",
            lambda _valid: b"",
            "PDF_SIGNATURE_MISMATCH",
        ),
        (
            "application/pdf",
            lambda _valid: b"%PDF-1.4\n" + b"x" * ADMISSION_POLICY.max_pdf_bytes,
            "PDF_SIZE_LIMIT_EXCEEDED",
        ),
    ],
)
def test_pre_storage_upload_rejections_are_bounded_and_create_no_object(
    tenancy_seed: dict[str, Any],
    documents_service: SourceAdmissionService,
    valid_pdf_bytes: bytes,
    content_type: str,
    body_factory: Any,
    expected_code: str,
) -> None:
    created, _approved = approve_source(documents_service, tenancy_seed, expected_code)
    intent = issue_intent(documents_service, tenancy_seed, created, expected_code)

    rejected = documents_service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type=content_type,
        body=body_factory(valid_pdf_bytes),
    )

    assert rejected.source_version.admission_status == "rejected"
    assert rejected.source_version.rejection_code == expected_code
    assert StorageObject.objects.count() == 0
    assert UploadIntent.objects.get(id=intent.id).status == "consumed"


@pytest.mark.django_db
def test_upload_target_is_opaque_tamper_safe_and_expiry_is_terminal(
    tenancy_seed: dict[str, Any],
    documents_service: SourceAdmissionService,
    valid_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created, _approved = approve_source(documents_service, tenancy_seed, "opaque")
    intent = issue_intent(documents_service, tenancy_seed, created, "opaque")

    with pytest.raises(SourceAdmissionError, match="RESOURCE_NOT_FOUND"):
        documents_service.upload_to_intent(
            opaque_token=f"{intent.opaque_token[:-1]}x",
            content_type="application/pdf",
            body=valid_pdf_bytes,
        )
    assert StorageObject.objects.count() == 0

    monkeypatch.setattr(
        services_module.timezone,
        "now",
        lambda: intent.expires_at + timedelta(seconds=1),
    )
    with pytest.raises(SourceAdmissionError, match="UPLOAD_INTENT_EXPIRED"):
        documents_service.upload_to_intent(
            opaque_token=intent.opaque_token,
            content_type="application/pdf",
            body=valid_pdf_bytes,
        )
    assert UploadIntent.objects.get(id=intent.id).status == "expired"
    assert StorageObject.objects.count() == 0
    replacement = issue_intent(documents_service, tenancy_seed, created, "opaque-replacement")
    assert replacement.id != intent.id


@pytest.mark.django_db
def test_consumed_target_replays_same_bytes_and_conflicts_on_different_bytes(
    tenancy_seed: dict[str, Any],
    documents_service: SourceAdmissionService,
    valid_pdf_bytes: bytes,
) -> None:
    created, _approved = approve_source(documents_service, tenancy_seed, "replay")
    intent = issue_intent(documents_service, tenancy_seed, created, "replay")
    first = documents_service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )
    replay = documents_service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )

    assert replay.source_version.id == first.source_version.id
    assert StorageObject.objects.count() == 1
    with pytest.raises(SourceAdmissionError, match="SOURCE_ADMISSION_STATE_CONFLICT"):
        documents_service.upload_to_intent(
            opaque_token=intent.opaque_token,
            content_type="application/pdf",
            body=valid_pdf_bytes + b"changed",
        )
    assert StorageObject.objects.count() == 1


@pytest.mark.django_db
def test_one_active_target_per_version_and_tenant_active_quota(
    tenancy_seed: dict[str, Any], tmp_path: Path
) -> None:
    service = SourceAdmissionService(
        storage=LocalQuarantineStorage(tmp_path / "quota"),
        inspector=LocalPdfInspector(),
        policy=replace(ADMISSION_POLICY, max_active_upload_intents_per_tenant=1),
    )
    first, _approved = approve_source(service, tenancy_seed, "quota-first")
    issue_intent(service, tenancy_seed, first, "quota-first")

    with pytest.raises(SourceAdmissionError, match="SOURCE_ADMISSION_STATE_CONFLICT"):
        issue_intent(service, tenancy_seed, first, "quota-same-version")

    second, _approved = approve_source(service, tenancy_seed, "quota-second")
    with pytest.raises(SourceAdmissionError, match="UPLOAD_QUOTA_EXCEEDED"):
        issue_intent(service, tenancy_seed, second, "quota-second")
    assert UploadIntent.objects.count() == 1


@pytest.mark.django_db
def test_rolling_intent_count_quota_is_enforced(
    tenancy_seed: dict[str, Any], tmp_path: Path
) -> None:
    count_service = SourceAdmissionService(
        storage=LocalQuarantineStorage(tmp_path / "count-quota"),
        inspector=LocalPdfInspector(),
        policy=replace(ADMISSION_POLICY, max_upload_intents_per_tenant_24h=1),
    )
    first, _approved = approve_source(count_service, tenancy_seed, "count-quota-first")
    first_intent = issue_intent(count_service, tenancy_seed, first, "count-quota-first")
    count_service.upload_to_intent(
        opaque_token=first_intent.opaque_token,
        content_type="application/pdf",
        body=b"x",
    )
    second, _approved = approve_source(count_service, tenancy_seed, "count-quota-second")
    with pytest.raises(SourceAdmissionError, match="UPLOAD_QUOTA_EXCEEDED"):
        issue_intent(count_service, tenancy_seed, second, "count-quota-second")


@pytest.mark.django_db
def test_rolling_attempt_byte_quota_is_enforced(
    tenancy_seed: dict[str, Any], tmp_path: Path
) -> None:
    byte_service = SourceAdmissionService(
        storage=LocalQuarantineStorage(tmp_path / "byte-quota"),
        inspector=LocalPdfInspector(),
        policy=replace(ADMISSION_POLICY, max_upload_attempt_bytes_per_tenant_24h=1),
    )
    third, _approved = approve_source(byte_service, tenancy_seed, "byte-quota-first")
    third_intent = issue_intent(byte_service, tenancy_seed, third, "byte-quota-first")
    byte_service.upload_to_intent(
        opaque_token=third_intent.opaque_token,
        content_type="application/pdf",
        body=b"x",
    )
    fourth, _approved = approve_source(byte_service, tenancy_seed, "byte-quota-second")
    with pytest.raises(SourceAdmissionError, match="UPLOAD_QUOTA_EXCEEDED"):
        issue_intent(byte_service, tenancy_seed, fourth, "byte-quota-second")


@pytest.mark.django_db
@pytest.mark.parametrize("quota_field", ["objects", "bytes"])
def test_quarantine_inventory_count_and_byte_quotas_are_enforced(
    tenancy_seed: dict[str, Any],
    tmp_path: Path,
    valid_pdf_bytes: bytes,
    quota_field: str,
) -> None:
    policy = replace(
        ADMISSION_POLICY,
        max_quarantine_objects_per_tenant=(
            1 if quota_field == "objects" else ADMISSION_POLICY.max_quarantine_objects_per_tenant
        ),
        max_quarantine_bytes_per_tenant=(
            1 if quota_field == "bytes" else ADMISSION_POLICY.max_quarantine_bytes_per_tenant
        ),
    )
    service = SourceAdmissionService(
        storage=LocalQuarantineStorage(tmp_path / f"inventory-{quota_field}"),
        inspector=LocalPdfInspector(),
        policy=policy,
    )
    first, _approved = approve_source(service, tenancy_seed, f"inventory-{quota_field}-first")
    first_intent = issue_intent(
        service,
        tenancy_seed,
        first,
        f"inventory-{quota_field}-first",
    )
    admitted = service.upload_to_intent(
        opaque_token=first_intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )
    assert admitted.source_version.admission_status == "admitted"

    second, _approved = approve_source(
        service,
        tenancy_seed,
        f"inventory-{quota_field}-second",
    )
    with pytest.raises(SourceAdmissionError, match="UPLOAD_QUOTA_EXCEEDED"):
        issue_intent(
            service,
            tenancy_seed,
            second,
            f"inventory-{quota_field}-second",
        )


@pytest.mark.django_db
def test_learner_and_inactive_members_cannot_admit_sources(
    tenancy_seed: dict[str, Any], documents_service: SourceAdmissionService
) -> None:
    tenant_id = tenancy_seed["alpha"].id
    learner = tenancy_seed["profiles"]["learner"].provider_subject
    inactive = tenancy_seed["profiles"]["inactive"].provider_subject

    with pytest.raises(SourceAdmissionError, match="SOURCE_PERMISSION_DENIED"):
        documents_service.create_admission(
            actor_id=learner,
            tenant_id=tenant_id,
            command=create_command("learner-denied"),
            idempotency_key="create-learner-denied-0001",
        )
    with pytest.raises(SourceAdmissionError, match="TENANT_ACCESS_INACTIVE"):
        documents_service.create_admission(
            actor_id=inactive,
            tenant_id=tenant_id,
            command=create_command("inactive-denied"),
            idempotency_key="create-inactive-denied-0001",
        )

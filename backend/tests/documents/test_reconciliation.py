from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from django.db import connection
from django.utils import timezone

from lms.modules.documents import services as services_module
from lms.modules.documents.errors import SourceAdmissionError
from lms.modules.documents.inspector import LocalPdfInspector
from lms.modules.documents.models import (
    DocumentJob,
    DocumentJobAttempt,
    SourceVersion,
    StorageObject,
    UploadIntent,
)
from lms.modules.documents.services import SourceAdmissionService
from lms.modules.documents.storage import LocalQuarantineStorage, StoredObjectObservation
from lms.modules.documents.types import (
    CancelAdmissionCommand,
    CreateAdmissionCommand,
    ReviewAuthorizationCommand,
    RightsDeclarationInput,
    TrustedAuthorizationBlockCommand,
)
from lms.modules.tenancy.models import AuditFact, OutboxFact


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.read_mode = "normal"
        self.delete_failures = 0
        self.read_callback: Callable[[], None] | None = None
        self.operations: list[str] = []

    def _outside_transaction(self, operation: str) -> None:
        assert not connection.in_atomic_block
        self.operations.append(operation)

    def put(self, *, intent_id: UUID, body: bytes) -> StoredObjectObservation:
        self._outside_transaction("put")
        locator = f"{intent_id.hex}.pdf"
        self.objects[locator] = body
        return StoredObjectObservation(locator=locator, byte_count=len(body))

    def read(self, locator: str) -> bytes:
        self._outside_transaction("read")
        if self.read_callback is not None:
            callback = self.read_callback
            self.read_callback = None
            callback()
        if self.read_mode == "missing":
            raise FileNotFoundError(locator)
        if self.read_mode == "unavailable":
            raise OSError("synthetic read outage")
        body = self.objects[locator]
        if self.read_mode == "checksum_mismatch":
            return b"X" + body[1:]
        return body

    def delete(self, locator: str) -> None:
        self._outside_transaction("delete")
        if self.delete_failures > 0:
            self.delete_failures -= 1
            raise OSError("synthetic delete outage")
        self.objects.pop(locator, None)

    def exists(self, locator: str) -> bool:
        self._outside_transaction("exists")
        return locator in self.objects

    def locators(self) -> tuple[str, ...]:
        return tuple(sorted(self.objects))


def command(suffix: str, *, valid_until: Any = None) -> CreateAdmissionCommand:
    return CreateAdmissionCommand(
        display_name=f"Synthetic {suffix} source",
        declared_filename=f"synthetic-{suffix}.pdf",
        rights_declaration=RightsDeclarationInput(
            basis="owned",
            attestation_version="f003-source-rights-attestation-v1",
            attested=True,
            valid_until=valid_until,
        ),
    )


def approved_source(
    service: SourceAdmissionService,
    tenancy_seed: dict[str, Any],
    suffix: str,
    *,
    valid_until: Any = None,
) -> tuple[Any, Any]:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = service.create_admission(
        actor_id=instructor,
        tenant_id=tenant_id,
        command=command(suffix, valid_until=valid_until),
        idempotency_key=f"create-reconcile-{suffix}-0001",
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
        idempotency_key=f"review-reconcile-{suffix}-0001",
    )
    return created, approved


def upload(
    service: SourceAdmissionService,
    tenancy_seed: dict[str, Any],
    created: Any,
    valid_pdf_bytes: bytes,
    suffix: str,
) -> Any:
    intent = service.create_upload_intent(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key=f"intent-reconcile-{suffix}-0001",
    )
    return service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )


@pytest.mark.django_db(transaction=True)
def test_validation_unavailable_retries_to_a_bounded_terminal_job(
    tenancy_seed: dict[str, Any], valid_pdf_bytes: bytes
) -> None:
    storage = MemoryStorage()
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector(available=False))
    created, _approved = approved_source(service, tenancy_seed, "validator-outage")

    first = upload(service, tenancy_seed, created, valid_pdf_bytes, "validator-outage")
    job = DocumentJob.objects.get(stage="validate_admission")
    assert first.source_version.admission_status == "quarantined"
    assert (job.status, job.attempt_count, job.checkpoint) == (
        "retryable",
        1,
        "validation_unavailable",
    )

    service.run_validation_job(job_id=job.id)
    third = service.run_validation_job(job_id=job.id)
    job.refresh_from_db()
    assert third.source_version.admission_status == "quarantined"
    assert (job.status, job.attempt_count) == ("failed", 3)
    assert DocumentJobAttempt.objects.filter(job=job).count() == 3
    with pytest.raises(SourceAdmissionError, match="SOURCE_ADMISSION_STATE_CONFLICT"):
        service.run_validation_job(job_id=job.id)
    job.refresh_from_db()
    assert job.attempt_count == 3


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("read_mode", "expected_code", "object_status"),
    [
        ("missing", "OBJECT_MISSING", "missing"),
        ("checksum_mismatch", "OBJECT_CHECKSUM_MISMATCH", "present"),
    ],
)
def test_object_inventory_mismatch_fails_closed(
    tenancy_seed: dict[str, Any],
    valid_pdf_bytes: bytes,
    read_mode: str,
    expected_code: str,
    object_status: str,
) -> None:
    storage = MemoryStorage()
    storage.read_mode = read_mode
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector())
    created, _approved = approved_source(service, tenancy_seed, read_mode)

    rejected = upload(service, tenancy_seed, created, valid_pdf_bytes, read_mode)

    assert rejected.source_version.admission_status == "rejected"
    assert rejected.source_version.rejection_code == expected_code
    assert StorageObject.objects.get(source_version_id=created.source_version.id).status == (
        object_status
    )
    assert DocumentJob.objects.get(stage="validate_admission").status == "completed"


@pytest.mark.django_db(transaction=True)
def test_storage_inspection_and_removal_io_never_spans_a_database_transaction(
    tenancy_seed: dict[str, Any], valid_pdf_bytes: bytes
) -> None:
    storage = MemoryStorage()
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector())
    created, admitted = approved_source(service, tenancy_seed, "transaction-boundary")
    admitted = upload(service, tenancy_seed, created, valid_pdf_bytes, "transaction-boundary")
    assert admitted.source_version.admission_status == "admitted"

    blocked = service.review_authorization(
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=ReviewAuthorizationCommand(
            decision="revoke",
            expected_authorization_row_version=admitted.store_authorization.row_version,
            decision_code="RIGHTS_REVOKED",
        ),
        idempotency_key="review-reconcile-revoke-0001",
    )
    assert blocked.removal.status == "pending"
    removal_job = DocumentJob.objects.get(stage="remove_quarantine_object")
    removed = service.run_removal_job(job_id=removal_job.id)

    assert removed.removal.status == "completed"
    assert StorageObject.objects.get().status == "deleted"
    assert storage.operations == ["put", "read", "delete", "exists"]


@pytest.mark.django_db(transaction=True)
def test_failed_delete_retries_are_bounded_and_never_report_false_completion(
    tenancy_seed: dict[str, Any], valid_pdf_bytes: bytes
) -> None:
    storage = MemoryStorage()
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector())
    created, _approved = approved_source(service, tenancy_seed, "delete-outage")
    admitted = upload(service, tenancy_seed, created, valid_pdf_bytes, "delete-outage")
    service.review_authorization(
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=ReviewAuthorizationCommand(
            decision="revoke",
            expected_authorization_row_version=admitted.store_authorization.row_version,
            decision_code="RIGHTS_REVOKED",
        ),
        idempotency_key="review-delete-outage-revoke-0001",
    )
    storage.delete_failures = 3
    job = DocumentJob.objects.get(stage="remove_quarantine_object")

    service.run_removal_job(job_id=job.id)
    service.run_removal_job(job_id=job.id)
    failed = service.run_removal_job(job_id=job.id)
    job.refresh_from_db()
    assert failed.removal.status == "failed"
    assert (job.status, job.attempt_count) == ("failed", 3)
    assert StorageObject.objects.get().status == "present"
    assert service.reconcile_pending() == ()
    with pytest.raises(SourceAdmissionError, match="SOURCE_ADMISSION_STATE_CONFLICT"):
        service.run_removal_job(job_id=job.id)


@pytest.mark.django_db(transaction=True)
def test_trusted_expiry_blocks_admitted_source_and_reconciles_removal(
    tenancy_seed: dict[str, Any],
    valid_pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = MemoryStorage()
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector())
    valid_until = timezone.now() + timedelta(minutes=5)
    created, _approved = approved_source(
        service,
        tenancy_seed,
        "expired-rights",
        valid_until=valid_until,
    )
    admitted = upload(service, tenancy_seed, created, valid_pdf_bytes, "expired-rights")
    monkeypatch.setattr(
        services_module.timezone,
        "now",
        lambda: valid_until + timedelta(seconds=1),
    )

    blocked = service.block_authorization(
        policy_actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=TrustedAuthorizationBlockCommand(
            status="expired",
            expected_authorization_row_version=admitted.store_authorization.row_version,
            decision_code="RIGHTS_EXPIRED",
        ),
    )
    assert blocked.source_version.admission_status == "blocked"
    assert blocked.store_authorization.status == "expired"
    assert blocked.removal.status == "pending"
    assert AuditFact.objects.filter(event_type="source.rights.expired.v1").count() == 1

    removal_job = DocumentJob.objects.get(stage="remove_quarantine_object")
    removed = service.run_removal_job(job_id=removal_job.id)
    assert removed.removal.status == "completed"
    assert (
        OutboxFact.objects.filter(
            event_type="source.removal.completed.v1",
            payload__reason_code="RIGHTS_EXPIRED",
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_trusted_dispute_cancels_active_target_without_browser_authority(
    tenancy_seed: dict[str, Any],
) -> None:
    storage = MemoryStorage()
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector())
    created, approved = approved_source(service, tenancy_seed, "disputed-rights")
    intent = service.create_upload_intent(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="intent-disputed-rights-0001",
    )

    blocked = service.block_authorization(
        policy_actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=TrustedAuthorizationBlockCommand(
            status="disputed",
            expected_authorization_row_version=approved.store_authorization.row_version,
            decision_code="RIGHTS_DISPUTED",
        ),
    )

    assert blocked.source_version.admission_status == "blocked"
    assert blocked.store_authorization.status == "disputed"
    assert blocked.removal.status == "not_required"
    assert UploadIntent.objects.get(id=intent.id).status == "cancelled"


@pytest.mark.django_db(transaction=True)
def test_cancel_during_validation_discards_result_and_preserves_durable_removal(
    tenancy_seed: dict[str, Any], valid_pdf_bytes: bytes
) -> None:
    storage = MemoryStorage()
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector())
    created, _approved = approved_source(service, tenancy_seed, "cancel-race")
    intent = service.create_upload_intent(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="intent-cancel-race-0001",
    )

    def cancel_after_claim() -> None:
        version = SourceVersion.objects.get(id=created.source_version.id)
        service.cancel_admission(
            actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
            tenant_id=tenancy_seed["alpha"].id,
            source_document_id=created.source_document.id,
            source_version_id=created.source_version.id,
            command=CancelAdmissionCommand(
                expected_source_version_row_version=version.row_version,
                reason_code="USER_CANCELLED",
            ),
            idempotency_key="cancel-during-validation-0001",
        )

    storage.read_callback = cancel_after_claim
    cancelled = service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )

    validation_job = DocumentJob.objects.get(stage="validate_admission")
    attempt = DocumentJobAttempt.objects.get(job=validation_job)
    assert cancelled.source_version.admission_status == "cancelled"
    assert cancelled.removal.status == "pending"
    assert validation_job.status == "cancelled"
    assert attempt.outcome == "cancelled"
    assert attempt.observation == {"result_discarded": True}
    assert OutboxFact.objects.filter(event_type="source.version.admitted.v1").count() == 0

    removal_job = DocumentJob.objects.get(stage="remove_quarantine_object")
    removed = service.run_removal_job(job_id=removal_job.id)
    assert removed.removal.status == "completed"


@pytest.mark.django_db(transaction=True)
def test_expired_validation_lease_records_crash_and_recovers_without_duplicate_job(
    tenancy_seed: dict[str, Any], valid_pdf_bytes: bytes
) -> None:
    storage = MemoryStorage()
    unavailable = SourceAdmissionService(
        storage=storage,
        inspector=LocalPdfInspector(available=False),
    )
    created, _approved = approved_source(unavailable, tenancy_seed, "expired-lease")
    first = upload(unavailable, tenancy_seed, created, valid_pdf_bytes, "expired-lease")
    assert first.source_version.admission_status == "quarantined"
    job = DocumentJob.objects.get(stage="validate_admission")
    job.status = "claimed"
    job.attempt_count += 1
    job.lease_owner = "crashed-worker"
    job.lease_expires_at = timezone.now() - timedelta(seconds=1)
    job.checkpoint = "object_read_requested"
    job.row_version += 1
    job.save(
        update_fields=(
            "status",
            "attempt_count",
            "lease_owner",
            "lease_expires_at",
            "checkpoint",
            "row_version",
            "updated_at",
        )
    )
    DocumentJobAttempt.objects.create(
        tenant_id=job.tenant_id,
        job=job,
        attempt_number=2,
        outcome="running",
        input_manifest_sha256=job.input_manifest_sha256,
        started_at=timezone.now() - timedelta(minutes=3),
    )

    recovered_service = SourceAdmissionService(
        storage=storage,
        inspector=LocalPdfInspector(),
    )
    recovered = recovered_service.run_validation_job(job_id=job.id)
    job.refresh_from_db()
    attempts = list(
        DocumentJobAttempt.objects.filter(job=job)
        .order_by("attempt_number")
        .values_list("attempt_number", "outcome", "retry_class", "reason_code")
    )

    assert recovered.source_version.admission_status == "admitted"
    assert (job.status, job.attempt_count) == ("completed", 3)
    assert DocumentJob.objects.filter(stage="validate_admission").count() == 1
    assert attempts == [
        (1, "retryable", "bounded_retry", "SOURCE_ADMISSION_VALIDATION_UNAVAILABLE"),
        (2, "retryable", "lease_expired", "WORKER_LEASE_EXPIRED"),
        (3, "completed", "none", None),
    ]


@pytest.mark.django_db(transaction=True)
def test_orphan_local_object_is_removed_and_upload_claim_is_released(
    tenancy_seed: dict[str, Any],
    valid_pdf_bytes: bytes,
    tmp_path: Path,
) -> None:
    storage = LocalQuarantineStorage(tmp_path / "orphan-quarantine")
    service = SourceAdmissionService(storage=storage, inspector=LocalPdfInspector())
    created, _approved = approved_source(service, tenancy_seed, "orphan-object")
    intent = service.create_upload_intent(
        actor_id=tenancy_seed["profiles"]["instructor"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="intent-orphan-object-0001",
    )
    observation = storage.put(intent_id=intent.id, body=valid_pdf_bytes)
    persisted = UploadIntent.objects.get(id=intent.id)
    persisted.upload_claim_digest = hashlib.sha256(valid_pdf_bytes).hexdigest()
    persisted.upload_claim_expires_at = timezone.now() + timedelta(seconds=60)
    persisted.row_version += 1
    persisted.save(
        update_fields=(
            "upload_claim_digest",
            "upload_claim_expires_at",
            "row_version",
            "updated_at",
        )
    )
    assert storage.exists(observation.locator)
    assert StorageObject.objects.count() == 0

    assert service.reconcile_pending() == ()

    persisted.refresh_from_db()
    assert not storage.exists(observation.locator)
    assert persisted.status == "active"
    assert persisted.upload_claim_digest is None
    assert persisted.upload_claim_expires_at is None
    assert AuditFact.objects.filter(event_type="source.orphan_object.removed.v1").count() == 1

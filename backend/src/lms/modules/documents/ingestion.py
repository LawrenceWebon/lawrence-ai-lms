from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from lms.modules.tenancy.errors import TenancyError
from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact
from lms.modules.tenancy.services import authorize_tenant_permission

from .errors import SourceAdmissionError
from .extraction import (
    EXTRACTION_CONFIGURATION_VERSION,
    LocalPdfTextExtractor,
    NormalizationError,
    NormalizedSource,
    normalize_extracted_pages,
)
from .inspector import INSPECTOR_VERSION
from .models import (
    DocumentElement,
    DocumentIngestionAttempt,
    DocumentIngestionRun,
    DocumentPage,
    DocumentSection,
    DocumentSectionElement,
    SourceArtifact,
    SourceDocument,
    SourceRightsDeclaration,
    SourceUseAuthorization,
    SourceVersion,
    StorageObject,
)
from .policy import PERMISSION_INGESTION_READ, PERMISSION_INGESTION_START
from .storage import LocalQuarantineStorage
from .types import IngestionRunRecord, IngestionWorkerResult

_LEASE_SECONDS = 300
_WORKER_ACTOR_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-lms:service:document-ingestion")
_ACTIVE_WORKER_STATES = frozenset({"claimed", "extracting", "normalizing", "quality_check"})
_TERMINAL_STATES = frozenset({"ready_for_generation", "failed", "cancelled", "rights_blocked"})


class _RightsBlockedError(Exception):
    pass


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode("utf-8")


def _manifest_hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _request_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _secret_digest(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _stable_id(*parts: object) -> UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, "ai-lms:" + ":".join(str(part) for part in parts))


def _set_worker_context(*, tenant_id: UUID, run_id: UUID, stage: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT set_config('app.current_actor_id', %s, true),
                   set_config('app.current_tenant_id', %s, true),
                   set_config('app.current_job_id', %s, true),
                   set_config('app.current_job_stage', %s, true)
            """,
            [str(_WORKER_ACTOR_ID), str(tenant_id), str(run_id), f"ingestion_{stage}"],
        )


def _translate_tenancy(error: TenancyError) -> SourceAdmissionError:
    if error.code == "TENANT_ACCESS_INACTIVE":
        return SourceAdmissionError("TENANT_ACCESS_INACTIVE")
    if error.code == "TENANT_PERMISSION_DENIED":
        return SourceAdmissionError("SOURCE_PERMISSION_DENIED")
    return SourceAdmissionError("INGESTION_RESOURCE_NOT_FOUND")


class DocumentIngestionService:
    """Durable local extraction boundary shared by API, Admin, and the worker."""

    def __init__(
        self,
        *,
        storage: LocalQuarantineStorage,
        extractor: LocalPdfTextExtractor | None = None,
    ) -> None:
        self._storage = storage
        self._extractor = extractor or LocalPdfTextExtractor()

    @staticmethod
    def _authorize(*, actor_id: UUID, tenant_id: UUID, permission: str) -> None:
        try:
            authorize_tenant_permission(actor_id, tenant_id, permission)
        except TenancyError as error:
            raise _translate_tenancy(error) from error

    @staticmethod
    def _validate_idempotency_key(key: str) -> None:
        if not 16 <= len(key) <= 128 or key != key.strip():
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_FAILED")

    @classmethod
    def _reserve_idempotency(
        cls,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        key: str,
        request: object,
    ) -> tuple[IdempotencyReservation, dict[str, object] | None]:
        cls._validate_idempotency_key(key)
        reservation, created = IdempotencyReservation.objects.select_for_update().get_or_create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation="documents.ingestion.start",
            key_digest=_secret_digest(key),
            defaults={"request_hash": _request_hash(request)},
        )
        if reservation.request_hash != _request_hash(request):
            raise SourceAdmissionError("IDEMPOTENCY_CONFLICT")
        if not created and reservation.status == "completed":
            if not isinstance(reservation.response_payload, dict):
                raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")
            return reservation, reservation.response_payload
        if not created:
            raise SourceAdmissionError("INGESTION_STATE_CONFLICT")
        return reservation, None

    @staticmethod
    def _complete_idempotency(
        reservation: IdempotencyReservation,
        *,
        run: DocumentIngestionRun,
    ) -> None:
        reservation.status = "completed"
        reservation.response_payload = {
            "resource_id": str(run.id),
            "source_document_id": str(run.source_document_id),
            "source_version_id": str(run.source_version_id),
        }
        reservation.save(update_fields=("status", "response_payload", "updated_at"))

    @staticmethod
    def _authorization_is_active(authorization: SourceUseAuthorization) -> bool:
        now = timezone.now()
        return (
            authorization.status == "active"
            and authorization.valid_from is not None
            and authorization.valid_from <= now
            and (authorization.valid_until is None or authorization.valid_until > now)
        )

    @staticmethod
    def _record(run: DocumentIngestionRun) -> IngestionRunRecord:
        if not isinstance(run.quality_summary, dict):
            raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")
        return IngestionRunRecord(
            id=run.id,
            tenant_id=run.tenant_id,
            source_document_id=run.source_document_id,
            source_version_id=run.source_version_id,
            status=run.status,
            parser_version=run.parser_version,
            configuration_version=run.configuration_version,
            locale=run.locale,
            attempt_count=run.attempt_count,
            max_attempts=run.max_attempts,
            checkpoint=run.checkpoint,
            input_manifest_sha256=run.input_manifest_sha256,
            output_manifest_sha256=run.output_manifest_sha256,
            reason_code=run.reason_code,
            quality_summary=run.quality_summary,
            row_version=run.row_version,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _record_fact(
        *,
        actor_id: UUID,
        run: DocumentIngestionRun,
        event_type: str,
    ) -> None:
        request_id = uuid.uuid4()
        now = timezone.now()
        safe_payload = {
            "source_document_id": str(run.source_document_id),
            "source_version_id": str(run.source_version_id),
            "ingestion_run_id": str(run.id),
            "status": run.status,
            "checkpoint": run.checkpoint,
            "reason_code": run.reason_code,
            "input_manifest_sha256": run.input_manifest_sha256,
            "output_manifest_sha256": run.output_manifest_sha256,
            "attempt_count": run.attempt_count,
            "row_version": run.row_version,
        }
        AuditFact.objects.create(
            tenant_id=run.tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            subject_type="document_ingestion_run",
            subject_id=run.id,
            request_id=request_id,
            payload=safe_payload,
        )
        OutboxFact.objects.create(
            tenant_id=run.tenant_id,
            event_type=event_type,
            aggregate_type="document_ingestion_run",
            aggregate_id=run.id,
            actor_id=actor_id,
            request_id=request_id,
            payload={
                "event_version": 1,
                "producer": "documents",
                "recorded_at": now.isoformat(),
                "privacy_class": "internal",
                **safe_payload,
            },
        )

    def start_ingestion(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> IngestionRunRecord:
        request = {
            "source_document_id": source_document_id,
            "source_version_id": source_version_id,
            "parser_version": INSPECTOR_VERSION,
            "configuration_version": EXTRACTION_CONFIGURATION_VERSION,
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_INGESTION_START,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                try:
                    replayed = DocumentIngestionRun.objects.get(
                        tenant_id=tenant_id,
                        source_document_id=source_document_id,
                        source_version_id=source_version_id,
                        id=UUID(str(replay["resource_id"])),
                    )
                except (KeyError, ValueError, DocumentIngestionRun.DoesNotExist) as error:
                    raise SourceAdmissionError("SERVICE_CONTRACT_ERROR") from error
                return self._record(replayed)
            try:
                document = SourceDocument.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    id=source_document_id,
                    current_version_id=source_version_id,
                )
                version = SourceVersion.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    id=source_version_id,
                    admission_status="admitted",
                )
                storage_object = StorageObject.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    source_version_id=source_version_id,
                    status="present",
                )
            except (
                SourceDocument.DoesNotExist,
                SourceVersion.DoesNotExist,
                StorageObject.DoesNotExist,
            ) as error:
                raise SourceAdmissionError("INGESTION_RESOURCE_NOT_FOUND") from error
            try:
                authorization = SourceUseAuthorization.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    source_version_id=source_version_id,
                    operation="extract",
                )
            except SourceUseAuthorization.DoesNotExist as error:
                raise SourceAdmissionError("SOURCE_OPERATION_AUTHORIZATION_REQUIRED") from error
            if not self._authorization_is_active(authorization):
                raise SourceAdmissionError("SOURCE_OPERATION_AUTHORIZATION_INACTIVE")
            if version.content_sha256 is None:
                raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")

            active = (
                DocumentIngestionRun.objects.filter(
                    tenant_id=tenant_id,
                    source_version_id=source_version_id,
                    parser_version=INSPECTOR_VERSION,
                    configuration_version=EXTRACTION_CONFIGURATION_VERSION,
                    status__in=(
                        "queued",
                        "claimed",
                        "extracting",
                        "normalizing",
                        "quality_check",
                        "retryable",
                    ),
                )
                .order_by("created_at", "id")
                .first()
            )
            if active is not None:
                self._complete_idempotency(reservation, run=active)
                return self._record(active)

            input_manifest_sha256 = _manifest_hash(
                {
                    "source_document_id": str(document.id),
                    "source_version_id": str(version.id),
                    "source_content_sha256": version.content_sha256,
                    "storage_object_id": str(storage_object.id),
                    "storage_content_sha256": storage_object.content_sha256,
                    "extract_authorization_id": str(authorization.id),
                    "extract_authorization_row_version": authorization.row_version,
                    "parser_version": INSPECTOR_VERSION,
                    "configuration_version": EXTRACTION_CONFIGURATION_VERSION,
                }
            )
            run = DocumentIngestionRun.objects.create(
                tenant_id=tenant_id,
                source_document=document,
                source_version=version,
                storage_object=storage_object,
                extract_authorization=authorization,
                requested_by_actor_id=actor_id,
                parser_version=INSPECTOR_VERSION,
                configuration_version=EXTRACTION_CONFIGURATION_VERSION,
                input_manifest_sha256=input_manifest_sha256,
            )
            self._record_fact(
                actor_id=actor_id,
                run=run,
                event_type="document.ingestion.requested.v1",
            )
            self._complete_idempotency(reservation, run=run)
            return self._record(run)

    def get_ingestion(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        run_id: UUID,
    ) -> IngestionRunRecord:
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_INGESTION_READ,
            )
            try:
                run = DocumentIngestionRun.objects.get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    source_version_id=source_version_id,
                    id=run_id,
                )
            except DocumentIngestionRun.DoesNotExist as error:
                raise SourceAdmissionError("INGESTION_RESOURCE_NOT_FOUND") from error
            return self._record(run)

    @staticmethod
    def _active_extract_authorization(run: DocumentIngestionRun) -> bool:
        try:
            authorization = SourceUseAuthorization.objects.get(
                tenant_id=run.tenant_id,
                source_version_id=run.source_version_id,
                id=run.extract_authorization_id,
                operation="extract",
            )
            version = SourceVersion.objects.get(
                tenant_id=run.tenant_id,
                id=run.source_version_id,
                source_document_id=run.source_document_id,
                admission_status="admitted",
            )
        except SourceUseAuthorization.DoesNotExist, SourceVersion.DoesNotExist:
            return False
        del version
        return DocumentIngestionService._authorization_is_active(authorization)

    def _claim(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
    ) -> tuple[DocumentIngestionRun, DocumentIngestionAttempt | None, bool]:
        if not 1 <= len(worker_id.strip()) <= 80:
            raise SourceAdmissionError("INGESTION_LEASE_CONFLICT")
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="claim")
            try:
                run = (
                    DocumentIngestionRun.objects.select_for_update()
                    .select_related("storage_object")
                    .get(
                        tenant_id=tenant_id,
                        id=run_id,
                    )
                )
            except DocumentIngestionRun.DoesNotExist as error:
                raise SourceAdmissionError("INGESTION_RESOURCE_NOT_FOUND") from error
            if run.status in _TERMINAL_STATES:
                return run, None, False
            now = timezone.now()
            if run.status in _ACTIVE_WORKER_STATES:
                if run.lease_expires_at is None:
                    raise SourceAdmissionError("INGESTION_STATE_CONFLICT")
                if run.lease_expires_at > now:
                    raise SourceAdmissionError("INGESTION_LEASE_CONFLICT")
                DocumentIngestionAttempt.objects.filter(
                    tenant_id=tenant_id,
                    ingestion_run_id=run.id,
                    outcome="running",
                ).update(
                    outcome="retryable",
                    reason_code="INGESTION_LEASE_CONFLICT",
                    checkpoint="lease_expired",
                    completed_at=now,
                )
                run.status = "retryable"
                run.reason_code = "INGESTION_LEASE_CONFLICT"
                run.checkpoint = "lease_expired"
                run.lease_owner = None
                run.lease_expires_at = None
                run.heartbeat_at = now
                run.row_version += 1
                run.save(
                    update_fields=(
                        "status",
                        "reason_code",
                        "checkpoint",
                        "lease_owner",
                        "lease_expires_at",
                        "heartbeat_at",
                        "row_version",
                        "updated_at",
                    )
                )
            elif run.status not in {"queued", "retryable"}:
                raise SourceAdmissionError("INGESTION_STATE_CONFLICT")
            if run.attempt_count >= run.max_attempts:
                if run.status == "retryable":
                    run.status = "failed"
                    run.reason_code = "INGESTION_RETRY_EXHAUSTED"
                    run.checkpoint = "retry_exhausted"
                    run.row_version += 1
                    run.save(
                        update_fields=(
                            "status",
                            "reason_code",
                            "checkpoint",
                            "row_version",
                            "updated_at",
                        )
                    )
                    self._record_fact(
                        actor_id=_WORKER_ACTOR_ID,
                        run=run,
                        event_type="document.ingestion.failed.v1",
                    )
                    return run, None, False
                raise SourceAdmissionError("INGESTION_RETRY_EXHAUSTED")
            if not self._active_extract_authorization(run):
                run.status = "rights_blocked"
                run.reason_code = "SOURCE_OPERATION_AUTHORIZATION_INACTIVE"
                run.checkpoint = "rights_blocked"
                run.lease_owner = None
                run.lease_expires_at = None
                run.row_version += 1
                run.save(
                    update_fields=(
                        "status",
                        "reason_code",
                        "checkpoint",
                        "lease_owner",
                        "lease_expires_at",
                        "row_version",
                        "updated_at",
                    )
                )
                self._record_fact(
                    actor_id=_WORKER_ACTOR_ID,
                    run=run,
                    event_type="document.ingestion.failed.v1",
                )
                return run, None, False

            run.status = "claimed"
            run.reason_code = None
            run.attempt_count += 1
            run.lease_owner = worker_id.strip()
            run.lease_expires_at = now + timedelta(seconds=_LEASE_SECONDS)
            run.heartbeat_at = now
            run.checkpoint = "claimed"
            run.row_version += 1
            run.save(
                update_fields=(
                    "status",
                    "reason_code",
                    "attempt_count",
                    "lease_owner",
                    "lease_expires_at",
                    "heartbeat_at",
                    "checkpoint",
                    "row_version",
                    "updated_at",
                )
            )
            attempt = DocumentIngestionAttempt.objects.create(
                tenant_id=tenant_id,
                ingestion_run=run,
                attempt_number=run.attempt_count,
                input_manifest_sha256=run.input_manifest_sha256,
                started_at=now,
            )
            return run, attempt, True

    def _advance(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
        expected_status: str,
        status: str,
        checkpoint: str,
    ) -> DocumentIngestionRun:
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage=status)
            try:
                run = (
                    DocumentIngestionRun.objects.select_for_update()
                    .select_related("storage_object")
                    .get(
                        tenant_id=tenant_id,
                        id=run_id,
                    )
                )
            except DocumentIngestionRun.DoesNotExist as error:
                raise SourceAdmissionError("INGESTION_RESOURCE_NOT_FOUND") from error
            now = timezone.now()
            if (
                run.status != expected_status
                or run.lease_owner != worker_id
                or run.lease_expires_at is None
                or run.lease_expires_at <= now
            ):
                raise SourceAdmissionError("INGESTION_LEASE_CONFLICT")
            if not self._active_extract_authorization(run):
                raise _RightsBlockedError
            run.status = status
            run.checkpoint = checkpoint
            run.heartbeat_at = now
            run.lease_expires_at = now + timedelta(seconds=_LEASE_SECONDS)
            run.row_version += 1
            run.save(
                update_fields=(
                    "status",
                    "checkpoint",
                    "heartbeat_at",
                    "lease_expires_at",
                    "row_version",
                    "updated_at",
                )
            )
            DocumentIngestionAttempt.objects.filter(
                tenant_id=tenant_id,
                ingestion_run_id=run.id,
                attempt_number=run.attempt_count,
                outcome="running",
            ).update(checkpoint=checkpoint)
            return run

    def _finish_failure(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
        reason_code: str,
        retryable: bool,
        rights_blocked: bool = False,
        observation: dict[str, object] | None = None,
    ) -> DocumentIngestionRun:
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="finish")
            try:
                run = DocumentIngestionRun.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    id=run_id,
                )
                attempt = DocumentIngestionAttempt.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    ingestion_run_id=run.id,
                    attempt_number=run.attempt_count,
                    outcome="running",
                )
            except (
                DocumentIngestionAttempt.DoesNotExist,
                DocumentIngestionRun.DoesNotExist,
            ) as error:
                raise SourceAdmissionError("INGESTION_STATE_CONFLICT") from error
            if run.status not in _ACTIVE_WORKER_STATES or run.lease_owner != worker_id:
                raise SourceAdmissionError("INGESTION_LEASE_CONFLICT")
            exhausted = retryable and run.attempt_count >= run.max_attempts
            run.status = (
                "rights_blocked"
                if rights_blocked
                else "failed"
                if exhausted or not retryable
                else "retryable"
            )
            run.reason_code = "INGESTION_RETRY_EXHAUSTED" if exhausted else reason_code
            run.checkpoint = (
                "rights_blocked" if rights_blocked else "retry_exhausted" if exhausted else "failed"
            )
            run.lease_owner = None
            run.lease_expires_at = None
            run.heartbeat_at = timezone.now()
            run.row_version += 1
            run.save(
                update_fields=(
                    "status",
                    "reason_code",
                    "checkpoint",
                    "lease_owner",
                    "lease_expires_at",
                    "heartbeat_at",
                    "row_version",
                    "updated_at",
                )
            )
            attempt.outcome = (
                "rights_blocked"
                if rights_blocked
                else "retryable"
                if run.status == "retryable"
                else "failed"
            )
            attempt.reason_code = reason_code
            attempt.checkpoint = run.checkpoint
            attempt.observation = observation or {}
            attempt.completed_at = timezone.now()
            attempt.save(
                update_fields=(
                    "outcome",
                    "reason_code",
                    "checkpoint",
                    "observation",
                    "completed_at",
                )
            )
            self._record_fact(
                actor_id=_WORKER_ACTOR_ID,
                run=run,
                event_type="document.ingestion.failed.v1",
            )
            return run

    def _ocr_reason(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
    ) -> str:
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="ocr_request")
            try:
                run = DocumentIngestionRun.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    id=run_id,
                )
                declaration = SourceRightsDeclaration.objects.get(
                    tenant_id=tenant_id,
                    source_version_id=run.source_version_id,
                )
            except (
                DocumentIngestionRun.DoesNotExist,
                SourceRightsDeclaration.DoesNotExist,
            ) as error:
                raise SourceAdmissionError("INGESTION_RESOURCE_NOT_FOUND") from error
            authorization, _created = SourceUseAuthorization.objects.get_or_create(
                tenant_id=tenant_id,
                source_document_id=run.source_document_id,
                source_version_id=run.source_version_id,
                rights_declaration=declaration,
                operation="ocr",
                defaults={
                    "status": "requested",
                    "requested_by_actor_id": run.requested_by_actor_id,
                },
            )
            return (
                "OCR_ADAPTER_UNAVAILABLE"
                if self._authorization_is_active(authorization)
                else "OCR_REQUIRED"
            )

    @staticmethod
    def _assert_existing(instance: object, expected: dict[str, object]) -> None:
        if any(getattr(instance, field) != value for field, value in expected.items()):
            raise SourceAdmissionError("DOCUMENT_QUALITY_INSUFFICIENT")

    def _persist_ready(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
        normalized: NormalizedSource,
    ) -> DocumentIngestionRun:
        with transaction.atomic():
            _set_worker_context(tenant_id=tenant_id, run_id=run_id, stage="quality_commit")
            try:
                run = DocumentIngestionRun.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    id=run_id,
                )
                attempt = DocumentIngestionAttempt.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    ingestion_run_id=run.id,
                    attempt_number=run.attempt_count,
                    outcome="running",
                )
            except (
                DocumentIngestionAttempt.DoesNotExist,
                DocumentIngestionRun.DoesNotExist,
            ) as error:
                raise SourceAdmissionError("INGESTION_STATE_CONFLICT") from error
            now = timezone.now()
            if (
                run.status != "quality_check"
                or run.lease_owner != worker_id
                or run.lease_expires_at is None
                or run.lease_expires_at <= now
            ):
                raise SourceAdmissionError("INGESTION_LEASE_CONFLICT")
            if not self._active_extract_authorization(run):
                raise _RightsBlockedError

            page_models: dict[UUID, DocumentPage] = {}
            element_models: dict[UUID, DocumentElement] = {}
            for page in normalized.pages:
                page_values: dict[str, object] = {
                    "source_document_id": run.source_document_id,
                    "source_version_id": run.source_version_id,
                    "parser_version": run.parser_version,
                    "configuration_version": run.configuration_version,
                    "page_number": page.number,
                    "width_points": Decimal(str(page.width_points)),
                    "height_points": Decimal(str(page.height_points)),
                    "text": page.text,
                    "text_sha256": page.text_sha256,
                    "ocr_used": page.ocr_used,
                }
                page_model, created = DocumentPage.objects.get_or_create(
                    tenant_id=tenant_id,
                    id=page.id,
                    defaults={"created_by_run": run, **page_values},
                )
                if not created:
                    self._assert_existing(page_model, page_values)
                page_models[page.id] = page_model
                for element in page.elements:
                    element_values: dict[str, object] = {
                        "source_document_id": run.source_document_id,
                        "source_version_id": run.source_version_id,
                        "page_id": page_model.id,
                        "position": element.position,
                        "kind": element.kind,
                        "text": element.text,
                        "text_sha256": element.text_sha256,
                    }
                    element_model, created = DocumentElement.objects.get_or_create(
                        tenant_id=tenant_id,
                        id=element.id,
                        defaults={"created_by_run": run, **element_values},
                    )
                    if not created:
                        self._assert_existing(element_model, element_values)
                    element_models[element.id] = element_model

            for section in normalized.sections:
                section_values: dict[str, object] = {
                    "source_document_id": run.source_document_id,
                    "source_version_id": run.source_version_id,
                    "position": section.position,
                    "title": section.title,
                    "start_page": section.start_page,
                    "end_page": section.end_page,
                }
                section_model, created = DocumentSection.objects.get_or_create(
                    tenant_id=tenant_id,
                    id=section.id,
                    defaults={"created_by_run": run, **section_values},
                )
                if not created:
                    self._assert_existing(section_model, section_values)
                for position, element_id in enumerate(section.element_ids, start=1):
                    edge_id = _stable_id(
                        "normalized-section-element",
                        tenant_id,
                        run.source_version_id,
                        section.id,
                        element_id,
                        position,
                    )
                    edge_values: dict[str, object] = {
                        "source_version_id": run.source_version_id,
                        "section_id": section_model.id,
                        "element_id": element_models[element_id].id,
                        "position": position,
                    }
                    edge, created = DocumentSectionElement.objects.get_or_create(
                        tenant_id=tenant_id,
                        id=edge_id,
                        defaults=edge_values,
                    )
                    if not created:
                        self._assert_existing(edge, edge_values)

            artifact_inputs = (
                (
                    "canonical_json",
                    normalized.canonical_json_sha256,
                    len(normalized.canonical_json.encode("utf-8")),
                    normalized.projection,
                    None,
                ),
                (
                    "normalized_markdown",
                    normalized.markdown_sha256,
                    len(normalized.markdown.encode("utf-8")),
                    None,
                    normalized.markdown,
                ),
            )
            for role, content_hash, byte_count, json_payload, text_payload in artifact_inputs:
                artifact_id = _stable_id(
                    "source-artifact",
                    tenant_id,
                    run.source_version_id,
                    normalized.schema_version,
                    role,
                )
                artifact_values: dict[str, object] = {
                    "source_document_id": run.source_document_id,
                    "source_version_id": run.source_version_id,
                    "artifact_role": role,
                    "schema_version": normalized.schema_version,
                    "content_sha256": content_hash,
                    "byte_count": byte_count,
                    "json_payload": json_payload,
                    "text_payload": text_payload,
                }
                artifact, created = SourceArtifact.objects.get_or_create(
                    tenant_id=tenant_id,
                    id=artifact_id,
                    defaults={"created_by_run": run, **artifact_values},
                )
                if not created:
                    self._assert_existing(artifact, artifact_values)

            quality_summary: dict[str, object] = {
                "schema_version": "normalized-quality.v1",
                "page_count": len(normalized.pages),
                "element_count": sum(len(page.elements) for page in normalized.pages),
                "section_count": len(normalized.sections),
                "ocr_page_count": 0,
                "canonical_json_sha256": normalized.canonical_json_sha256,
                "normalized_markdown_sha256": normalized.markdown_sha256,
            }
            run.status = "ready_for_generation"
            run.output_manifest_sha256 = normalized.manifest_sha256
            run.reason_code = None
            run.quality_summary = quality_summary
            run.checkpoint = "ready_for_generation"
            run.lease_owner = None
            run.lease_expires_at = None
            run.heartbeat_at = now
            run.row_version += 1
            run.save(
                update_fields=(
                    "status",
                    "output_manifest_sha256",
                    "reason_code",
                    "quality_summary",
                    "checkpoint",
                    "lease_owner",
                    "lease_expires_at",
                    "heartbeat_at",
                    "row_version",
                    "updated_at",
                )
            )
            attempt.outcome = "completed"
            attempt.output_manifest_sha256 = normalized.manifest_sha256
            attempt.checkpoint = "ready_for_generation"
            attempt.observation = {
                "page_count": len(normalized.pages),
                "element_count": quality_summary["element_count"],
                "section_count": len(normalized.sections),
            }
            attempt.completed_at = now
            attempt.save(
                update_fields=(
                    "outcome",
                    "output_manifest_sha256",
                    "checkpoint",
                    "observation",
                    "completed_at",
                )
            )
            self._record_fact(
                actor_id=_WORKER_ACTOR_ID,
                run=run,
                event_type="document.ingestion.ready.v1",
            )
            return run

    def run_ingestion(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        worker_id: str,
    ) -> IngestionWorkerResult:
        run, _attempt, claimed = self._claim(
            tenant_id=tenant_id,
            run_id=run_id,
            worker_id=worker_id,
        )
        if not claimed:
            return IngestionWorkerResult(run=self._record(run), claimed=False)
        try:
            run = self._advance(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                expected_status="claimed",
                status="extracting",
                checkpoint="extracting_text",
            )
            try:
                body = self._storage.read(run.storage_object.private_locator)
            except OSError:
                failed = self._finish_failure(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    reason_code="EXTRACTION_PARSER_FAILED",
                    retryable=True,
                    observation={"storage_observation": "unavailable"},
                )
                return IngestionWorkerResult(run=self._record(failed), claimed=True)
            observed_hash = f"sha256:{hashlib.sha256(body).hexdigest()}"
            if observed_hash != run.storage_object.content_sha256:
                failed = self._finish_failure(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    reason_code="EXTRACTION_PARSER_FAILED",
                    retryable=False,
                    observation={"storage_observation": "checksum_mismatch"},
                )
                return IngestionWorkerResult(run=self._record(failed), claimed=True)

            extraction = self._extractor.extract(body)
            if extraction.outcome != "extracted":
                failed = self._finish_failure(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    reason_code=extraction.reason_code or "EXTRACTION_PARSER_FAILED",
                    retryable=extraction.outcome == "retryable_failure",
                )
                return IngestionWorkerResult(run=self._record(failed), claimed=True)
            self._advance(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                expected_status="extracting",
                status="normalizing",
                checkpoint="normalizing_source",
            )
            try:
                normalized = normalize_extracted_pages(
                    tenant_id=tenant_id,
                    source_version_id=run.source_version_id,
                    content_sha256=run.storage_object.content_sha256,
                    parser_version=run.parser_version,
                    configuration_version=run.configuration_version,
                    pages=extraction.pages,
                )
            except NormalizationError as error:
                reason_code = error.reason_code
                observation: dict[str, object] = {}
                if error.page_numbers:
                    observation["ocr_page_numbers"] = list(error.page_numbers)
                    reason_code = self._ocr_reason(tenant_id=tenant_id, run_id=run_id)
                failed = self._finish_failure(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    worker_id=worker_id,
                    reason_code=reason_code,
                    retryable=reason_code in {"OCR_REQUIRED", "OCR_ADAPTER_UNAVAILABLE"},
                    observation=observation,
                )
                return IngestionWorkerResult(run=self._record(failed), claimed=True)
            self._advance(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                expected_status="normalizing",
                status="quality_check",
                checkpoint="validating_normalized_source",
            )
            ready = self._persist_ready(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                normalized=normalized,
            )
            return IngestionWorkerResult(run=self._record(ready), claimed=True)
        except _RightsBlockedError:
            failed = self._finish_failure(
                tenant_id=tenant_id,
                run_id=run_id,
                worker_id=worker_id,
                reason_code="SOURCE_OPERATION_AUTHORIZATION_INACTIVE",
                retryable=False,
                rights_blocked=True,
            )
            return IngestionWorkerResult(run=self._record(failed), claimed=True)

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import uuid
from dataclasses import asdict
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from lms.modules.tenancy.errors import TenancyError
from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact
from lms.modules.tenancy.services import authorize_tenant_permission

from .errors import FieldError, SourceAdmissionError
from .inspector import INSPECTOR_VERSION, LocalPdfInspector
from .models import (
    DocumentJob,
    DocumentJobAttempt,
    SourceDocument,
    SourceRightsDeclaration,
    SourceUseAuthorization,
    SourceVersion,
    StorageObject,
    UploadIntent,
)
from .policy import (
    ADMISSION_POLICY,
    PERMISSION_INGESTION_START,
    PERMISSION_SOURCE_RIGHTS_REVIEW,
    PERMISSION_SOURCES_ADMIT,
    PERMISSION_SOURCES_CANCEL,
    PERMISSION_SOURCES_READ,
)
from .storage import LocalQuarantineStorage
from .types import (
    AdmissionPolicy,
    AdmissionValidationResult,
    CancelAdmissionCommand,
    CreateAdmissionCommand,
    RemovalRecord,
    ReviewAuthorizationCommand,
    RightsDeclarationRecord,
    SourceAdmissionSnapshot,
    SourceAuthorizationRecord,
    SourceDocumentRecord,
    SourceOperation,
    SourceVersionRecord,
    TrustedAuthorizationBlockCommand,
    UploadIntentReceipt,
    UploadIntentSummary,
)

_PDF_FILENAME = re.compile(r"^[^/\\]+\.[Pp][Dd][Ff]$")
_EVIDENCE_REFERENCE = re.compile(r"^[A-Za-z0-9._:-]+$")
_RIGHTS_BASES = frozenset(
    {"owned", "licensed", "written_permission", "public_domain", "other_documented"}
)
_DOCUMENTED_BASES = frozenset({"licensed", "written_permission", "other_documented"})
_DECISION_CODES = {
    "activate": "RIGHTS_EVIDENCE_ACCEPTED",
    "deny": "RIGHTS_EVIDENCE_INSUFFICIENT",
    "revoke": "RIGHTS_REVOKED",
}
_TRUSTED_BLOCK_CODES = {
    "expired": "RIGHTS_EXPIRED",
    "disputed": "RIGHTS_DISPUTED",
}
_OPERATION_REQUEST_PERMISSIONS = {
    "extract": PERMISSION_INGESTION_START,
    "ocr": PERMISSION_INGESTION_START,
    "generate": "course_generation.runs.create",
}
_EVENT_REASONS = {
    "source.version.rejected.v1": frozenset(
        {
            "RIGHTS_AUTHORIZATION_DENIED",
            "PDF_SIGNATURE_MISMATCH",
            "PDF_MEDIA_TYPE_INVALID",
            "PDF_ENCRYPTED",
            "PDF_CORRUPT",
            "PDF_POLYGLOT_REJECTED",
            "PDF_SIZE_LIMIT_EXCEEDED",
            "PDF_PAGE_LIMIT_EXCEEDED",
            "PDF_PIXEL_LIMIT_EXCEEDED",
            "PDF_DECODED_LIMIT_EXCEEDED",
            "PDF_VALIDATION_TIMEOUT",
            "PDF_UNSAFE",
            "OBJECT_MISSING",
            "OBJECT_CHECKSUM_MISMATCH",
        }
    ),
    "source.version.cancelled.v1": frozenset({"USER_CANCELLED", "SOURCE_REPLACED"}),
    "source.rights.revoked.v1": frozenset({"RIGHTS_REVOKED"}),
    "source.removal.completed.v1": frozenset(
        {"USER_CANCELLED", "RIGHTS_REVOKED", "RIGHTS_EXPIRED", "RIGHTS_DISPUTED"}
    ),
}


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def _request_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _manifest_hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _secret_digest(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def _set_upload_context(token_digest: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_actor_id', '', true)")
        cursor.execute("SELECT set_config('app.current_tenant_id', '', true)")
        cursor.execute(
            "SELECT set_config('app.current_upload_token_digest', %s, true)",
            [token_digest],
        )
        cursor.execute("SELECT set_config('app.current_job_id', '', true)")
        cursor.execute("SELECT set_config('app.current_job_stage', '', true)")


def _set_worker_context(*, job_id: UUID, stage: str, tenant_id: UUID | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_actor_id', '', true)")
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            ["" if tenant_id is None else str(tenant_id)],
        )
        cursor.execute("SELECT set_config('app.current_upload_token_digest', '', true)")
        cursor.execute("SELECT set_config('app.current_job_id', %s, true)", [str(job_id)])
        cursor.execute("SELECT set_config('app.current_job_stage', %s, true)", [stage])


def _opaque_upload_token(*, intent_id: UUID, idempotency_key: str) -> str:
    digest = hmac.new(
        settings.SECRET_KEY.encode(),
        f"f003-upload:{intent_id}:{idempotency_key}".encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _validate_idempotency_key(key: str) -> None:
    if not 16 <= len(key) <= 128 or key != key.strip():
        raise SourceAdmissionError(
            "SOURCE_ADMISSION_VALIDATION_FAILED",
            field_errors=(FieldError("idempotency_key", "invalid"),),
        )


def _translate_tenancy(error: TenancyError) -> SourceAdmissionError:
    if error.code == "TENANT_ACCESS_INACTIVE":
        return SourceAdmissionError("TENANT_ACCESS_INACTIVE")
    if error.code == "TENANT_PERMISSION_DENIED":
        return SourceAdmissionError("SOURCE_PERMISSION_DENIED")
    return SourceAdmissionError("RESOURCE_NOT_FOUND")


class SourceAdmissionService:
    """One application boundary shared by HTTP, Admin, validator, and reconciler."""

    def __init__(
        self,
        *,
        storage: LocalQuarantineStorage,
        inspector: LocalPdfInspector,
        policy: AdmissionPolicy = ADMISSION_POLICY,
    ) -> None:
        self._storage = storage
        self._inspector = inspector
        self._policy = policy

    @staticmethod
    def _authorize(*, actor_id: UUID, tenant_id: UUID, permission: str) -> None:
        try:
            authorize_tenant_permission(actor_id, tenant_id, permission)
        except TenancyError as error:
            raise _translate_tenancy(error) from error

    @staticmethod
    def _reserve_idempotency(
        *,
        actor_id: UUID,
        tenant_id: UUID,
        operation: str,
        key: str,
        request: object,
    ) -> tuple[IdempotencyReservation, dict[str, object] | None]:
        _validate_idempotency_key(key)
        key_digest = _secret_digest(key)
        request_digest = _request_hash(request)
        reservation, created = IdempotencyReservation.objects.select_for_update().get_or_create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation=operation,
            key_digest=key_digest,
            defaults={"request_hash": request_digest},
        )
        if reservation.request_hash != request_digest:
            raise SourceAdmissionError("IDEMPOTENCY_CONFLICT")
        if not created and reservation.status == "completed":
            payload = reservation.response_payload
            if not isinstance(payload, dict):
                raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")
            return reservation, payload
        if not created:
            raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
        return reservation, None

    @staticmethod
    def _complete_idempotency(
        reservation: IdempotencyReservation,
        *,
        source_document_id: UUID,
        source_version_id: UUID,
        resource_id: UUID | None = None,
    ) -> None:
        response: dict[str, str] = {
            "source_document_id": str(source_document_id),
            "source_version_id": str(source_version_id),
        }
        if resource_id is not None:
            response["resource_id"] = str(resource_id)
        reservation.status = "completed"
        reservation.response_payload = response
        reservation.save(update_fields=("status", "response_payload", "updated_at"))

    @staticmethod
    def _ids_from_replay(payload: dict[str, object]) -> tuple[UUID, UUID]:
        try:
            return UUID(str(payload["source_document_id"])), UUID(str(payload["source_version_id"]))
        except (KeyError, TypeError, ValueError) as error:
            raise SourceAdmissionError("SERVICE_CONTRACT_ERROR") from error

    @staticmethod
    def _validate_create(command: CreateAdmissionCommand) -> CreateAdmissionCommand:
        declaration = command.rights_declaration
        errors: list[FieldError] = []
        if not 1 <= len(command.display_name.strip()) <= 160:
            errors.append(FieldError("display_name", "invalid"))
        if (
            len(command.declared_filename) > 255
            or _PDF_FILENAME.fullmatch(command.declared_filename) is None
        ):
            errors.append(FieldError("declared_filename", "invalid"))
        if declaration.basis not in _RIGHTS_BASES:
            errors.append(FieldError("rights_declaration.basis", "invalid"))
        if declaration.attestation_version != "f003-source-rights-attestation-v1":
            errors.append(FieldError("rights_declaration.attestation_version", "invalid"))
        if declaration.attested is not True:
            errors.append(FieldError("rights_declaration.attested", "required"))
        if declaration.basis in _DOCUMENTED_BASES:
            if (
                not declaration.rights_holder_name
                or not 1 <= len(declaration.rights_holder_name.strip()) <= 160
            ):
                errors.append(FieldError("rights_declaration.rights_holder_name", "required"))
            if (
                not declaration.evidence_reference
                or not 1 <= len(declaration.evidence_reference) <= 120
                or _EVIDENCE_REFERENCE.fullmatch(declaration.evidence_reference) is None
            ):
                errors.append(FieldError("rights_declaration.evidence_reference", "required"))
        elif declaration.evidence_reference is not None and (
            not 1 <= len(declaration.evidence_reference) <= 120
            or _EVIDENCE_REFERENCE.fullmatch(declaration.evidence_reference) is None
        ):
            errors.append(FieldError("rights_declaration.evidence_reference", "invalid"))
        if errors:
            raise SourceAdmissionError(
                "SOURCE_ADMISSION_VALIDATION_FAILED",
                field_errors=tuple(errors),
            )
        return command

    @staticmethod
    def _load_models(
        *,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        lock: bool = False,
    ) -> tuple[SourceDocument, SourceVersion, SourceRightsDeclaration, SourceUseAuthorization]:
        documents = SourceDocument.objects.all()
        versions = SourceVersion.objects.all()
        declarations = SourceRightsDeclaration.objects.all()
        authorizations = SourceUseAuthorization.objects.all()
        if lock:
            documents = documents.select_for_update()
            versions = versions.select_for_update()
            authorizations = authorizations.select_for_update()
        try:
            document = documents.get(
                id=source_document_id,
                tenant_id=tenant_id,
                current_version_id=source_version_id,
            )
            version = versions.get(
                id=source_version_id,
                tenant_id=tenant_id,
                source_document_id=source_document_id,
            )
            declaration = declarations.get(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
            )
            authorization = authorizations.get(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                rights_declaration_id=declaration.id,
                operation="store",
            )
        except (
            SourceDocument.DoesNotExist,
            SourceVersion.DoesNotExist,
            SourceRightsDeclaration.DoesNotExist,
            SourceUseAuthorization.DoesNotExist,
        ) as error:
            raise SourceAdmissionError("RESOURCE_NOT_FOUND") from error
        return document, version, declaration, authorization

    @staticmethod
    def _authorization_record(
        authorization: SourceUseAuthorization,
    ) -> SourceAuthorizationRecord:
        return SourceAuthorizationRecord(
            id=authorization.id,
            tenant_id=authorization.tenant_id,
            source_document_id=authorization.source_document_id,
            source_version_id=authorization.source_version_id,
            rights_declaration_id=authorization.rights_declaration_id,
            operation=authorization.operation,
            status=authorization.status,
            requested_by_actor_id=authorization.requested_by_actor_id,
            reviewed_by_actor_id=authorization.reviewed_by_actor_id,
            decision_code=authorization.decision_code,
            valid_from=authorization.valid_from,
            valid_until=authorization.valid_until,
            row_version=authorization.row_version,
        )

    @staticmethod
    def _snapshot(
        document: SourceDocument,
        version: SourceVersion,
        declaration: SourceRightsDeclaration,
        authorization: SourceUseAuthorization,
    ) -> SourceAdmissionSnapshot:
        if document.current_version_id is None:
            raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")
        intent = (
            UploadIntent.objects.filter(
                tenant_id=document.tenant_id,
                source_version_id=version.id,
            )
            .order_by("-created_at", "-id")
            .first()
        )
        return SourceAdmissionSnapshot(
            source_document=SourceDocumentRecord(
                id=document.id,
                tenant_id=document.tenant_id,
                display_name=document.display_name,
                current_version_id=document.current_version_id,
                row_version=document.row_version,
            ),
            source_version=SourceVersionRecord(
                id=version.id,
                tenant_id=version.tenant_id,
                source_document_id=version.source_document_id,
                version_number=version.version_number,
                admission_status=version.admission_status,
                declared_filename=version.declared_filename,
                content_sha256=version.content_sha256,
                derived_file_size_bytes=version.derived_file_size_bytes,
                derived_media_type=version.derived_media_type,
                derived_pdf_signature_valid=version.derived_pdf_signature_valid,
                derived_parser_accepted=version.derived_parser_accepted,
                derived_page_count=version.derived_page_count,
                derived_max_rendered_pixels_per_page=(version.derived_max_rendered_pixels_per_page),
                derived_rendered_pixels_total=version.derived_rendered_pixels_total,
                derived_decoded_parser_bytes=version.derived_decoded_parser_bytes,
                derived_local_inspection_result=version.derived_local_inspection_result,
                rejection_code=version.rejection_code,
                validation_attempt_count=version.validation_attempt_count,
                row_version=version.row_version,
            ),
            rights_declaration=RightsDeclarationRecord(
                id=declaration.id,
                tenant_id=declaration.tenant_id,
                source_document_id=declaration.source_document_id,
                source_version_id=declaration.source_version_id,
                declared_by_actor_id=declaration.declared_by_actor_id,
                basis=declaration.basis,
                attestation_version=declaration.attestation_version,
                attested_at=declaration.attested_at,
                valid_until=declaration.valid_until,
                evidence_reference=declaration.evidence_reference,
                row_version=declaration.row_version,
            ),
            store_authorization=SourceAdmissionService._authorization_record(authorization),
            upload_intent=(
                None
                if intent is None
                else UploadIntentSummary(
                    id=intent.id,
                    status=intent.status,
                    expires_at=intent.expires_at,
                )
            ),
            removal=RemovalRecord(
                status=version.removal_status,
                reason_code=version.removal_reason_code,
            ),
        )

    @staticmethod
    def _record_audit(
        *,
        actor_id: UUID,
        tenant_id: UUID,
        event_type: str,
        version: SourceVersion,
        correlation_id: UUID,
        reason_code: str | None,
    ) -> None:
        AuditFact.objects.create(
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            subject_type="source_version",
            subject_id=version.id,
            request_id=correlation_id,
            payload={
                "admission_status": version.admission_status,
                "reason_code": reason_code,
                "row_version": version.row_version,
            },
        )

    @classmethod
    def _record_fact(
        cls,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        event_type: str,
        document: SourceDocument,
        version: SourceVersion,
        reason_code: str | None = None,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> None:
        allowed_reasons = _EVENT_REASONS.get(event_type)
        if allowed_reasons is not None and reason_code not in allowed_reasons:
            raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")
        correlation = correlation_id or uuid.uuid4()
        causation = causation_id or uuid.uuid4()
        now = timezone.now()
        cls._record_audit(
            actor_id=actor_id,
            tenant_id=tenant_id,
            event_type=event_type,
            version=version,
            correlation_id=correlation,
            reason_code=reason_code,
        )
        OutboxFact.objects.create(
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type="source_version",
            aggregate_id=version.id,
            actor_id=actor_id,
            request_id=correlation,
            payload={
                "event_version": 1,
                "producer": "documents",
                "source_document_id": str(document.id),
                "source_version_id": str(version.id),
                "aggregate_version": version.row_version,
                "recorded_at": now.isoformat(),
                "correlation_id": str(correlation),
                "causation_id": str(causation),
                "privacy_class": "internal",
                "admission_status": version.admission_status,
                "content_sha256": (
                    version.content_sha256 if version.admission_status == "admitted" else None
                ),
                "reason_code": reason_code,
            },
        )

    def create_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateAdmissionCommand,
        idempotency_key: str,
    ) -> SourceAdmissionSnapshot:
        command = self._validate_create(command)
        declaration_input = command.rights_declaration
        request = {
            "display_name": command.display_name.strip(),
            "declared_filename": command.declared_filename,
            "rights_declaration": asdict(declaration_input),
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCES_ADMIT,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                operation="documents.admissions.create",
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                document_id, version_id = self._ids_from_replay(replay)
                return self._snapshot(
                    *self._load_models(
                        tenant_id=tenant_id,
                        source_document_id=document_id,
                        source_version_id=version_id,
                    )
                )

            now = timezone.now()
            document = SourceDocument.objects.create(
                tenant_id=tenant_id,
                display_name=command.display_name.strip(),
                owner_actor_id=actor_id,
            )
            version = SourceVersion.objects.create(
                tenant_id=tenant_id,
                source_document=document,
                version_number=1,
                admission_status="rights_pending",
                declared_filename=command.declared_filename,
            )
            document.current_version = version
            document.save(update_fields=("current_version", "updated_at"))
            declaration = SourceRightsDeclaration.objects.create(
                tenant_id=tenant_id,
                source_document=document,
                source_version=version,
                declared_by_actor_id=actor_id,
                basis=declaration_input.basis,
                attestation_version=declaration_input.attestation_version,
                attested_at=now,
                rights_holder_name=(
                    declaration_input.rights_holder_name.strip()
                    if declaration_input.rights_holder_name
                    else None
                ),
                evidence_reference=declaration_input.evidence_reference,
                valid_until=declaration_input.valid_until,
            )
            authorization = SourceUseAuthorization.objects.create(
                tenant_id=tenant_id,
                source_document=document,
                source_version=version,
                rights_declaration=declaration,
                operation="store",
                status="requested",
                requested_by_actor_id=actor_id,
            )
            self._record_fact(
                actor_id=actor_id,
                tenant_id=tenant_id,
                event_type="source.rights.declared.v1",
                document=document,
                version=version,
            )
            self._complete_idempotency(
                reservation,
                source_document_id=document.id,
                source_version_id=version.id,
            )
            return self._snapshot(document, version, declaration, authorization)

    def get_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> SourceAdmissionSnapshot:
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCES_READ,
            )
            return self._snapshot(
                *self._load_models(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    source_version_id=source_version_id,
                )
            )

    def list_operation_authorizations(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> tuple[SourceAuthorizationRecord, ...]:
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCES_READ,
            )
            self._load_models(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
            )
            authorizations = SourceUseAuthorization.objects.filter(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
            ).order_by("operation", "id")
            return tuple(self._authorization_record(item) for item in authorizations)

    def request_operation_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: SourceOperation,
        idempotency_key: str,
    ) -> SourceAuthorizationRecord:
        permission = _OPERATION_REQUEST_PERMISSIONS.get(operation)
        if permission is None:
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_FAILED")
        request = {
            "source_document_id": source_document_id,
            "source_version_id": source_version_id,
            "operation": operation,
        }
        with transaction.atomic():
            self._authorize(actor_id=actor_id, tenant_id=tenant_id, permission=permission)
            document, version, declaration, store_authorization = self._load_models(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                lock=True,
            )
            if version.admission_status != "admitted" or not self._authorization_is_active(
                store_authorization
            ):
                raise SourceAdmissionError("SOURCE_OPERATION_AUTHORIZATION_REQUIRED")
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                operation=f"documents.authorizations.{operation}.request",
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                try:
                    authorization = SourceUseAuthorization.objects.get(
                        tenant_id=tenant_id,
                        source_document_id=source_document_id,
                        source_version_id=source_version_id,
                        id=UUID(str(replay["resource_id"])),
                        operation=operation,
                    )
                except (KeyError, ValueError, SourceUseAuthorization.DoesNotExist) as error:
                    raise SourceAdmissionError("SERVICE_CONTRACT_ERROR") from error
                return self._authorization_record(authorization)

            authorization, created = SourceUseAuthorization.objects.get_or_create(
                tenant_id=tenant_id,
                source_document=document,
                source_version=version,
                operation=operation,
                defaults={
                    "rights_declaration": declaration,
                    "status": "requested",
                    "requested_by_actor_id": actor_id,
                },
            )
            if authorization.rights_declaration_id != declaration.id:
                raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")
            if created:
                self._record_fact(
                    actor_id=actor_id,
                    tenant_id=tenant_id,
                    event_type="source.operation_authorization.requested.v1",
                    document=document,
                    version=version,
                )
            self._complete_idempotency(
                reservation,
                source_document_id=document.id,
                source_version_id=version.id,
                resource_id=authorization.id,
            )
            return self._authorization_record(authorization)

    def review_operation_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: SourceOperation,
        command: ReviewAuthorizationCommand,
        idempotency_key: str,
    ) -> SourceAuthorizationRecord:
        if operation not in _OPERATION_REQUEST_PERMISSIONS:
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_FAILED")
        expected_code = _DECISION_CODES.get(command.decision)
        if expected_code is None or command.decision_code != expected_code:
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_FAILED")
        request = {
            "source_document_id": source_document_id,
            "source_version_id": source_version_id,
            "operation": operation,
            **asdict(command),
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCE_RIGHTS_REVIEW,
            )
            document, version, declaration, store_authorization = self._load_models(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                lock=True,
            )
            if version.admission_status != "admitted" or not self._authorization_is_active(
                store_authorization
            ):
                raise SourceAdmissionError("SOURCE_OPERATION_AUTHORIZATION_INACTIVE")
            try:
                authorization = SourceUseAuthorization.objects.select_for_update().get(
                    tenant_id=tenant_id,
                    source_document_id=source_document_id,
                    source_version_id=source_version_id,
                    rights_declaration_id=declaration.id,
                    operation=operation,
                )
            except SourceUseAuthorization.DoesNotExist as error:
                raise SourceAdmissionError("RESOURCE_NOT_FOUND") from error
            if authorization.requested_by_actor_id == actor_id:
                raise SourceAdmissionError("SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED")
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                operation=f"documents.authorizations.{operation}.review",
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                try:
                    replayed = SourceUseAuthorization.objects.get(
                        tenant_id=tenant_id,
                        source_version_id=source_version_id,
                        id=UUID(str(replay["resource_id"])),
                        operation=operation,
                    )
                except (KeyError, ValueError, SourceUseAuthorization.DoesNotExist) as error:
                    raise SourceAdmissionError("SERVICE_CONTRACT_ERROR") from error
                return self._authorization_record(replayed)
            if authorization.row_version != command.expected_authorization_row_version:
                raise SourceAdmissionError("SOURCE_ADMISSION_VERSION_CONFLICT")
            if command.decision in {"activate", "deny"} and authorization.status != "requested":
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if command.decision == "revoke" and authorization.status != "active":
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")

            now = timezone.now()
            authorization.reviewed_by_actor_id = actor_id
            authorization.decision_code = command.decision_code
            authorization.row_version += 1
            if command.decision == "activate":
                if declaration.valid_until is not None and declaration.valid_until <= now:
                    raise SourceAdmissionError("SOURCE_OPERATION_AUTHORIZATION_INACTIVE")
                authorization.status = "active"
                authorization.valid_from = now
                authorization.valid_until = declaration.valid_until
            elif command.decision == "deny":
                authorization.status = "denied"
            else:
                authorization.status = "revoked"
            authorization.save(
                update_fields=(
                    "status",
                    "reviewed_by_actor_id",
                    "decision_code",
                    "valid_from",
                    "valid_until",
                    "row_version",
                    "updated_at",
                )
            )
            self._record_fact(
                actor_id=actor_id,
                tenant_id=tenant_id,
                event_type=(f"source.operation_authorization.{authorization.status}.v1"),
                document=document,
                version=version,
                reason_code=(None if command.decision == "activate" else command.decision_code),
            )
            self._complete_idempotency(
                reservation,
                source_document_id=document.id,
                source_version_id=version.id,
                resource_id=authorization.id,
            )
            return self._authorization_record(authorization)

    def review_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        authorization_id: UUID,
        command: ReviewAuthorizationCommand,
        idempotency_key: str,
    ) -> SourceAdmissionSnapshot:
        expected_code = _DECISION_CODES.get(command.decision)
        if expected_code is None or command.decision_code != expected_code:
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_FAILED")
        request = {
            "source_document_id": source_document_id,
            "source_version_id": source_version_id,
            "authorization_id": authorization_id,
            **asdict(command),
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCES_READ,
            )
            document, version, declaration, authorization = self._load_models(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                lock=True,
            )
            if authorization.id != authorization_id:
                raise SourceAdmissionError("RESOURCE_NOT_FOUND")
            if authorization.requested_by_actor_id == actor_id:
                raise SourceAdmissionError("SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED")
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCE_RIGHTS_REVIEW,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                operation="documents.rights.review",
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                replay_document_id, replay_version_id = self._ids_from_replay(replay)
                return self._snapshot(
                    *self._load_models(
                        tenant_id=tenant_id,
                        source_document_id=replay_document_id,
                        source_version_id=replay_version_id,
                    )
                )
            if authorization.row_version != command.expected_authorization_row_version:
                raise SourceAdmissionError("SOURCE_ADMISSION_VERSION_CONFLICT")
            now = timezone.now()
            if command.decision in {"activate", "deny"} and authorization.status != "requested":
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if command.decision == "revoke" and authorization.status != "active":
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if command.decision == "revoke" and version.admission_status not in {
                "upload_pending",
                "quarantined",
                "validating",
                "admitted",
            }:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")

            authorization.reviewed_by_actor_id = actor_id
            authorization.decision_code = command.decision_code
            authorization.row_version += 1
            if command.decision == "activate":
                if declaration.valid_until is not None and declaration.valid_until <= now:
                    raise SourceAdmissionError("SOURCE_RIGHTS_AUTHORIZATION_REQUIRED")
                authorization.status = "active"
                authorization.valid_from = now
                authorization.valid_until = declaration.valid_until
                version.admission_status = "upload_pending"
                version.rejection_code = None
                event_type = "source.store_authorization.activated.v1"
                reason_code = None
            elif command.decision == "deny":
                authorization.status = "denied"
                version.admission_status = "rejected"
                version.rejection_code = "RIGHTS_AUTHORIZATION_DENIED"
                event_type = "source.version.rejected.v1"
                reason_code = "RIGHTS_AUTHORIZATION_DENIED"
            else:
                authorization.status = "revoked"
                version.admission_status = "blocked"
                version.rejection_code = None
                UploadIntent.objects.filter(
                    tenant_id=tenant_id,
                    source_version_id=source_version_id,
                    status="active",
                ).update(
                    status="cancelled",
                    upload_claim_digest=None,
                    upload_claim_expires_at=None,
                    row_version=models_increment(),
                )
                DocumentJob.objects.filter(
                    tenant_id=tenant_id,
                    source_version_id=source_version_id,
                    stage="validate_admission",
                    status__in=("pending", "claimed", "retryable"),
                ).update(
                    status="cancelled",
                    checkpoint="rights_revoked",
                    lease_owner=None,
                    lease_expires_at=None,
                    row_version=models_increment(),
                )
                self._schedule_removal(
                    actor_id=actor_id,
                    document=document,
                    version=version,
                    reason_code="RIGHTS_REVOKED",
                )
                event_type = "source.rights.revoked.v1"
                reason_code = "RIGHTS_REVOKED"
            authorization.save(
                update_fields=(
                    "status",
                    "reviewed_by_actor_id",
                    "decision_code",
                    "valid_from",
                    "valid_until",
                    "row_version",
                    "updated_at",
                )
            )
            version.row_version += 1
            version.save(
                update_fields=(
                    "admission_status",
                    "rejection_code",
                    "removal_status",
                    "removal_reason_code",
                    "row_version",
                    "updated_at",
                )
            )
            self._record_fact(
                actor_id=actor_id,
                tenant_id=tenant_id,
                event_type=event_type,
                document=document,
                version=version,
                reason_code=reason_code,
            )
            self._complete_idempotency(
                reservation,
                source_document_id=document.id,
                source_version_id=version.id,
            )
            return self._snapshot(document, version, declaration, authorization)

    @staticmethod
    def _authorization_is_active(authorization: SourceUseAuthorization) -> bool:
        now = timezone.now()
        return (
            authorization.status == "active"
            and authorization.valid_from is not None
            and authorization.valid_from <= now
            and (authorization.valid_until is None or authorization.valid_until > now)
        )

    def block_authorization(
        self,
        *,
        policy_actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        authorization_id: UUID,
        command: TrustedAuthorizationBlockCommand,
    ) -> SourceAdmissionSnapshot:
        """Apply a trusted expiry/dispute decision outside browser/API authority."""

        expected_code = _TRUSTED_BLOCK_CODES.get(command.status)
        if expected_code is None or command.decision_code != expected_code:
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_FAILED")
        with transaction.atomic():
            document, version, declaration, authorization = self._load_models(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                lock=True,
            )
            if authorization.id != authorization_id:
                raise SourceAdmissionError("RESOURCE_NOT_FOUND")
            if authorization.row_version != command.expected_authorization_row_version:
                raise SourceAdmissionError("SOURCE_ADMISSION_VERSION_CONFLICT")
            if authorization.status != "active":
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if command.status == "expired" and (
                authorization.valid_until is None or authorization.valid_until > timezone.now()
            ):
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if version.admission_status not in {
                "upload_pending",
                "quarantined",
                "validating",
                "admitted",
            }:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")

            authorization.status = command.status
            authorization.decision_code = command.decision_code
            authorization.row_version += 1
            authorization.save(
                update_fields=("status", "decision_code", "row_version", "updated_at")
            )
            version.admission_status = "blocked"
            version.rejection_code = None
            UploadIntent.objects.filter(
                tenant_id=tenant_id,
                source_version_id=source_version_id,
                status="active",
            ).update(
                status="cancelled",
                upload_claim_digest=None,
                upload_claim_expires_at=None,
                row_version=models_increment(),
            )
            DocumentJob.objects.filter(
                tenant_id=tenant_id,
                source_version_id=source_version_id,
                stage="validate_admission",
                status__in=("pending", "claimed", "retryable"),
            ).update(
                status="cancelled",
                checkpoint=f"rights_{command.status}",
                lease_owner=None,
                lease_expires_at=None,
                row_version=models_increment(),
            )
            self._schedule_removal(
                actor_id=policy_actor_id,
                document=document,
                version=version,
                reason_code=command.decision_code,
            )
            version.row_version += 1
            version.save(
                update_fields=(
                    "admission_status",
                    "rejection_code",
                    "removal_status",
                    "removal_reason_code",
                    "row_version",
                    "updated_at",
                )
            )
            self._record_audit(
                actor_id=policy_actor_id,
                tenant_id=tenant_id,
                event_type=f"source.rights.{command.status}.v1",
                version=version,
                correlation_id=uuid.uuid4(),
                reason_code=command.decision_code,
            )
            return self._snapshot(document, version, declaration, authorization)

    def create_upload_intent(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> UploadIntentReceipt:
        request = {
            "source_document_id": source_document_id,
            "source_version_id": source_version_id,
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCES_ADMIT,
            )
            document, version, _declaration, authorization = self._load_models(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                lock=True,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                operation="documents.upload_intents.create",
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                try:
                    intent = UploadIntent.objects.get(
                        tenant_id=tenant_id,
                        id=UUID(str(replay["resource_id"])),
                        source_document_id=source_document_id,
                        source_version_id=source_version_id,
                    )
                except (KeyError, ValueError, UploadIntent.DoesNotExist) as error:
                    raise SourceAdmissionError("SERVICE_CONTRACT_ERROR") from error
                token = _opaque_upload_token(intent_id=intent.id, idempotency_key=idempotency_key)
                return self._intent_receipt(intent, token)
            if not self._authorization_is_active(authorization):
                raise SourceAdmissionError("SOURCE_RIGHTS_AUTHORIZATION_REQUIRED")
            if version.admission_status != "upload_pending":
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            now = timezone.now()
            UploadIntent.objects.filter(
                tenant_id=tenant_id,
                source_version_id=source_version_id,
                status="active",
                expires_at__lte=now,
            ).update(status="expired", row_version=models_increment())
            if UploadIntent.objects.filter(
                tenant_id=tenant_id,
                source_version_id=source_version_id,
                status="active",
            ).exists():
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            active_intents = UploadIntent.objects.filter(
                tenant_id=tenant_id,
                status="active",
                expires_at__gt=now,
            ).count()
            recent_intents = UploadIntent.objects.filter(
                tenant_id=tenant_id,
                created_at__gte=now - timedelta(hours=24),
            )
            attempted_bytes = sum(
                value or 0
                for value in recent_intents.exclude(observed_byte_count__isnull=True).values_list(
                    "observed_byte_count", flat=True
                )
            )
            present_objects = StorageObject.objects.filter(tenant_id=tenant_id, status="present")
            quarantine_bytes = sum(present_objects.values_list("byte_count", flat=True))
            if (
                active_intents >= self._policy.max_active_upload_intents_per_tenant
                or recent_intents.count() >= self._policy.max_upload_intents_per_tenant_24h
                or attempted_bytes >= self._policy.max_upload_attempt_bytes_per_tenant_24h
                or present_objects.count() >= self._policy.max_quarantine_objects_per_tenant
                or quarantine_bytes >= self._policy.max_quarantine_bytes_per_tenant
            ):
                raise SourceAdmissionError("UPLOAD_QUOTA_EXCEEDED")
            intent_id = uuid.uuid4()
            token = _opaque_upload_token(intent_id=intent_id, idempotency_key=idempotency_key)
            intent = UploadIntent.objects.create(
                id=intent_id,
                tenant_id=tenant_id,
                source_document=document,
                source_version=version,
                authorization=authorization,
                token_digest=_secret_digest(token),
                status="active",
                expires_at=now + timedelta(seconds=self._policy.upload_intent_ttl_seconds),
                max_bytes=self._policy.max_pdf_bytes,
                accepted_media_type="application/pdf",
            )
            correlation_id = uuid.uuid4()
            self._record_audit(
                actor_id=actor_id,
                tenant_id=tenant_id,
                event_type="source.upload_intent.issued.v1",
                version=version,
                correlation_id=correlation_id,
                reason_code=None,
            )
            self._complete_idempotency(
                reservation,
                source_document_id=document.id,
                source_version_id=version.id,
                resource_id=intent.id,
            )
            return self._intent_receipt(intent, token)

    @staticmethod
    def _intent_receipt(intent: UploadIntent, token: str) -> UploadIntentReceipt:
        return UploadIntentReceipt(
            id=intent.id,
            tenant_id=intent.tenant_id,
            source_document_id=intent.source_document_id,
            source_version_id=intent.source_version_id,
            status=intent.status,
            target_url=f"/api/v1/source-upload-targets/{token}",
            opaque_token=token,
            expires_at=intent.expires_at,
            max_bytes=intent.max_bytes,
            accepted_media_type=intent.accepted_media_type,
            row_version=intent.row_version,
        )

    def _reject_before_storage(
        self,
        *,
        intent: UploadIntent,
        rejection_code: str,
        body: bytes,
        media_type: str,
    ) -> SourceAdmissionSnapshot:
        document, version, declaration, authorization = self._load_models(
            tenant_id=intent.tenant_id,
            source_document_id=intent.source_document_id,
            source_version_id=intent.source_version_id,
            lock=True,
        )
        intent.status = "consumed"
        intent.observed_content_sha256 = f"sha256:{hashlib.sha256(body).hexdigest()}"
        intent.observed_byte_count = len(body)
        intent.row_version += 1
        intent.save(
            update_fields=(
                "status",
                "observed_content_sha256",
                "observed_byte_count",
                "row_version",
                "updated_at",
            )
        )
        version.admission_status = "rejected"
        version.content_sha256 = intent.observed_content_sha256
        version.derived_file_size_bytes = len(body)
        version.derived_media_type = media_type
        version.derived_pdf_signature_valid = body.startswith(b"%PDF-")
        version.rejection_code = rejection_code
        version.validation_attempt_count = 1
        version.row_version += 1
        version.save(
            update_fields=(
                "admission_status",
                "content_sha256",
                "derived_file_size_bytes",
                "derived_media_type",
                "derived_pdf_signature_valid",
                "rejection_code",
                "validation_attempt_count",
                "row_version",
                "updated_at",
            )
        )
        self._record_fact(
            actor_id=authorization.requested_by_actor_id,
            tenant_id=intent.tenant_id,
            event_type="source.version.rejected.v1",
            document=document,
            version=version,
            reason_code=rejection_code,
        )
        return self._snapshot(document, version, declaration, authorization)

    def upload_to_intent(
        self,
        *,
        opaque_token: str,
        content_type: str,
        body: bytes,
    ) -> SourceAdmissionSnapshot:
        if len(opaque_token) < 32 or len(opaque_token) > 128:
            raise SourceAdmissionError("RESOURCE_NOT_FOUND")
        token_digest = _secret_digest(opaque_token)
        body_digest = hashlib.sha256(body).hexdigest()
        expired = False
        with transaction.atomic():
            _set_upload_context(token_digest)
            try:
                intent = UploadIntent.objects.select_for_update().get(token_digest=token_digest)
            except UploadIntent.DoesNotExist as error:
                raise SourceAdmissionError("RESOURCE_NOT_FOUND") from error
            if intent.status == "consumed":
                if (
                    intent.observed_content_sha256 == f"sha256:{body_digest}"
                    and intent.observed_byte_count == len(body)
                ):
                    return self._snapshot(
                        *self._load_models(
                            tenant_id=intent.tenant_id,
                            source_document_id=intent.source_document_id,
                            source_version_id=intent.source_version_id,
                        )
                    )
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if intent.status != "active":
                raise SourceAdmissionError("RESOURCE_NOT_FOUND")
            if intent.expires_at <= timezone.now():
                intent.status = "expired"
                intent.row_version += 1
                intent.save(update_fields=("status", "row_version", "updated_at"))
                expired = True
            elif content_type.casefold().split(";", 1)[0].strip() != "application/pdf":
                return self._reject_before_storage(
                    intent=intent,
                    rejection_code="PDF_MEDIA_TYPE_INVALID",
                    body=body,
                    media_type=content_type[:100] or "application/octet-stream",
                )
            elif len(body) > intent.max_bytes:
                return self._reject_before_storage(
                    intent=intent,
                    rejection_code="PDF_SIZE_LIMIT_EXCEEDED",
                    body=body,
                    media_type="application/pdf",
                )
            elif not body:
                return self._reject_before_storage(
                    intent=intent,
                    rejection_code="PDF_SIGNATURE_MISMATCH",
                    body=body,
                    media_type="application/pdf",
                )
            else:
                _document, version, _declaration, authorization = self._load_models(
                    tenant_id=intent.tenant_id,
                    source_document_id=intent.source_document_id,
                    source_version_id=intent.source_version_id,
                    lock=True,
                )
                if (
                    version.admission_status != "upload_pending"
                    or not self._authorization_is_active(authorization)
                ):
                    raise SourceAdmissionError("RESOURCE_NOT_FOUND")
                now = timezone.now()
                if (
                    intent.upload_claim_digest is not None
                    and intent.upload_claim_expires_at is not None
                    and intent.upload_claim_expires_at > now
                ):
                    raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
                intent.upload_claim_digest = body_digest
                intent.upload_claim_expires_at = now + timedelta(seconds=60)
                intent.row_version += 1
                intent.save(
                    update_fields=(
                        "upload_claim_digest",
                        "upload_claim_expires_at",
                        "row_version",
                        "updated_at",
                    )
                )
        if expired:
            raise SourceAdmissionError("UPLOAD_INTENT_EXPIRED")

        try:
            observation = self._storage.put(intent_id=intent.id, body=body)
        except OSError as error:
            with transaction.atomic():
                _set_upload_context(token_digest)
                UploadIntent.objects.filter(
                    id=intent.id,
                    token_digest=token_digest,
                    upload_claim_digest=body_digest,
                ).update(upload_claim_digest=None, upload_claim_expires_at=None)
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_UNAVAILABLE") from error

        cleanup_orphan = False
        job_id: UUID | None = None
        with transaction.atomic():
            _set_upload_context(token_digest)
            current = UploadIntent.objects.select_for_update().get(id=intent.id)
            document, version, _declaration, authorization = self._load_models(
                tenant_id=current.tenant_id,
                source_document_id=current.source_document_id,
                source_version_id=current.source_version_id,
                lock=True,
            )
            if (
                current.status != "active"
                or current.upload_claim_digest != body_digest
                or current.expires_at <= timezone.now()
                or version.admission_status != "upload_pending"
                or not self._authorization_is_active(authorization)
            ):
                cleanup_orphan = True
            else:
                content_sha256 = f"sha256:{body_digest}"
                storage_object = StorageObject.objects.create(
                    tenant_id=current.tenant_id,
                    source_document=document,
                    source_version=version,
                    upload_intent=current,
                    private_locator=observation.locator,
                    content_sha256=content_sha256,
                    byte_count=observation.byte_count,
                    media_type="application/pdf",
                    status="present",
                    observed_at=timezone.now(),
                )
                current.status = "consumed"
                current.observed_content_sha256 = content_sha256
                current.observed_byte_count = observation.byte_count
                current.upload_claim_digest = None
                current.upload_claim_expires_at = None
                current.row_version += 1
                current.save(
                    update_fields=(
                        "status",
                        "observed_content_sha256",
                        "observed_byte_count",
                        "upload_claim_digest",
                        "upload_claim_expires_at",
                        "row_version",
                        "updated_at",
                    )
                )
                version.admission_status = "quarantined"
                version.row_version += 1
                version.save(update_fields=("admission_status", "row_version", "updated_at"))
                correlation_id = uuid.uuid4()
                job = DocumentJob.objects.create(
                    tenant_id=current.tenant_id,
                    source_document=document,
                    source_version=version,
                    storage_object=storage_object,
                    stage="validate_admission",
                    status="pending",
                    idempotency_key=f"validate:{version.id}",
                    correlation_id=correlation_id,
                    input_manifest_sha256=_manifest_hash(
                        {
                            "tenant_id": current.tenant_id,
                            "source_document_id": document.id,
                            "source_version_id": version.id,
                            "storage_object_id": storage_object.id,
                            "content_sha256": content_sha256,
                            "byte_count": observation.byte_count,
                            "policy_version": self._policy.version,
                        }
                    ),
                )
                job_id = job.id
                self._record_fact(
                    actor_id=authorization.requested_by_actor_id,
                    tenant_id=current.tenant_id,
                    event_type="source.version.quarantined.v1",
                    document=document,
                    version=version,
                    correlation_id=correlation_id,
                    causation_id=current.id,
                )
                self._record_fact(
                    actor_id=authorization.requested_by_actor_id,
                    tenant_id=current.tenant_id,
                    event_type="source.admission.validation_requested.v1",
                    document=document,
                    version=version,
                    correlation_id=correlation_id,
                    causation_id=job.id,
                )
        if cleanup_orphan:
            self._storage.delete(observation.locator)
            raise SourceAdmissionError("RESOURCE_NOT_FOUND")
        if job_id is None:
            raise SourceAdmissionError("SERVICE_CONTRACT_ERROR")
        return self.run_validation_job(job_id=job_id)

    @staticmethod
    def _missing_result() -> AdmissionValidationResult:
        return AdmissionValidationResult(
            outcome="rejected",
            inspector_version=INSPECTOR_VERSION,
            content_sha256=None,
            file_size_bytes=None,
            media_type=None,
            pdf_signature_valid=None,
            parser_accepted=None,
            page_count=None,
            max_rendered_pixels_per_page=None,
            rendered_pixels_total=None,
            decoded_parser_bytes=None,
            local_inspection_result=None,
            rejection_code="OBJECT_MISSING",
        )

    @staticmethod
    def _checksum_mismatch_result(body: bytes) -> AdmissionValidationResult:
        return AdmissionValidationResult(
            outcome="rejected",
            inspector_version=INSPECTOR_VERSION,
            content_sha256=f"sha256:{hashlib.sha256(body).hexdigest()}",
            file_size_bytes=len(body),
            media_type=(
                "application/pdf" if body.startswith(b"%PDF-") else "application/octet-stream"
            ),
            pdf_signature_valid=body.startswith(b"%PDF-"),
            parser_accepted=None,
            page_count=None,
            max_rendered_pixels_per_page=None,
            rendered_pixels_total=None,
            decoded_parser_bytes=None,
            local_inspection_result=None,
            rejection_code="OBJECT_CHECKSUM_MISMATCH",
        )

    def run_validation_job(self, *, job_id: UUID) -> SourceAdmissionSnapshot:
        lease_owner = f"local-validator:{uuid.uuid4()}"
        with transaction.atomic():
            _set_worker_context(job_id=job_id, stage="validate_admission")
            try:
                job = (
                    DocumentJob.objects.select_for_update()
                    .select_related(
                        "storage_object",
                        "source_version",
                        "source_document",
                    )
                    .get(id=job_id, stage="validate_admission")
                )
            except DocumentJob.DoesNotExist as error:
                raise SourceAdmissionError("RESOURCE_NOT_FOUND") from error
            document, version, declaration, authorization = self._load_models(
                tenant_id=job.tenant_id,
                source_document_id=job.source_document_id,
                source_version_id=job.source_version_id,
                lock=True,
            )
            _set_worker_context(
                job_id=job_id,
                stage="validate_admission",
                tenant_id=job.tenant_id,
            )
            now = timezone.now()
            if job.status == "completed":
                return self._snapshot(document, version, declaration, authorization)
            if job.status == "claimed" and job.lease_expires_at and job.lease_expires_at > now:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if job.status not in {"pending", "retryable", "claimed"}:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if job.status == "claimed":
                previous_attempt = DocumentJobAttempt.objects.select_for_update().get(
                    job=job,
                    attempt_number=job.attempt_count,
                    outcome="running",
                )
                exhausted = job.attempt_count >= job.max_attempts
                previous_attempt.outcome = "failed" if exhausted else "retryable"
                previous_attempt.retry_class = "terminal" if exhausted else "lease_expired"
                previous_attempt.reason_code = "WORKER_LEASE_EXPIRED"
                previous_attempt.completed_at = now
                previous_attempt.save(
                    update_fields=(
                        "outcome",
                        "retry_class",
                        "reason_code",
                        "completed_at",
                    )
                )
                if exhausted:
                    job.status = "failed"
                    job.reason_code = "SOURCE_ADMISSION_VALIDATION_UNAVAILABLE"
                    job.checkpoint = "lease_expired_exhausted"
                    job.lease_owner = None
                    job.lease_expires_at = None
                    job.row_version += 1
                    job.save(
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
                    version.admission_status = "quarantined"
                    version.row_version += 1
                    version.save(update_fields=("admission_status", "row_version", "updated_at"))
                    return self._snapshot(document, version, declaration, authorization)
            event_type: str | None = None
            event_reason: str | None = None
            if not self._authorization_is_active(authorization) or version.admission_status in {
                "cancelled",
                "blocked",
            }:
                job.status = "cancelled"
                job.checkpoint = "authorization_blocked"
                job.row_version += 1
                job.save(update_fields=("status", "checkpoint", "row_version", "updated_at"))
                return self._snapshot(document, version, declaration, authorization)
            job.status = "claimed"
            job.attempt_count += 1
            job.lease_owner = lease_owner
            job.lease_expires_at = now + timedelta(minutes=2)
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
            version.admission_status = "validating"
            version.row_version += 1
            version.save(update_fields=("admission_status", "row_version", "updated_at"))
            attempt = DocumentJobAttempt.objects.create(
                tenant_id=job.tenant_id,
                job=job,
                attempt_number=job.attempt_count,
                outcome="running",
                input_manifest_sha256=job.input_manifest_sha256,
                started_at=now,
            )
            locator = job.storage_object.private_locator
            expected_checksum = job.storage_object.content_sha256
            expected_bytes = job.storage_object.byte_count

        try:
            body = self._storage.read(locator)
        except FileNotFoundError:
            result = self._missing_result()
        except OSError:
            result = AdmissionValidationResult(
                outcome="retryable_failure",
                inspector_version=INSPECTOR_VERSION,
                content_sha256=None,
                file_size_bytes=None,
                media_type=None,
                pdf_signature_valid=None,
                parser_accepted=None,
                page_count=None,
                max_rendered_pixels_per_page=None,
                rendered_pixels_total=None,
                decoded_parser_bytes=None,
                local_inspection_result="unavailable",
                rejection_code=None,
            )
        else:
            observed_checksum = f"sha256:{hashlib.sha256(body).hexdigest()}"
            if observed_checksum != expected_checksum or len(body) != expected_bytes:
                result = self._checksum_mismatch_result(body)
            else:
                result = self._inspector.inspect(body, policy=self._policy)

        output_hash = _manifest_hash(asdict(result))
        with transaction.atomic():
            _set_worker_context(job_id=job_id, stage="validate_admission")
            job = DocumentJob.objects.select_for_update().get(id=job_id)
            document, version, declaration, authorization = self._load_models(
                tenant_id=job.tenant_id,
                source_document_id=job.source_document_id,
                source_version_id=job.source_version_id,
                lock=True,
            )
            _set_worker_context(
                job_id=job_id,
                stage="validate_admission",
                tenant_id=job.tenant_id,
            )
            attempt = DocumentJobAttempt.objects.select_for_update().get(id=attempt.id)
            if job.status == "cancelled":
                now = timezone.now()
                reason_code = {
                    "user_cancelled": "USER_CANCELLED",
                    "rights_revoked": "RIGHTS_REVOKED",
                    "rights_expired": "RIGHTS_EXPIRED",
                    "rights_disputed": "RIGHTS_DISPUTED",
                }.get(job.checkpoint, "WORK_CANCELLED")
                job.output_manifest_sha256 = output_hash
                job.row_version += 1
                job.save(
                    update_fields=(
                        "output_manifest_sha256",
                        "row_version",
                        "updated_at",
                    )
                )
                attempt.outcome = "cancelled"
                attempt.retry_class = "terminal"
                attempt.reason_code = reason_code
                attempt.inspector_version = result.inspector_version
                attempt.output_manifest_sha256 = output_hash
                attempt.observation = {"result_discarded": True}
                attempt.completed_at = now
                attempt.save(
                    update_fields=(
                        "outcome",
                        "retry_class",
                        "reason_code",
                        "inspector_version",
                        "output_manifest_sha256",
                        "observation",
                        "completed_at",
                    )
                )
                return self._snapshot(document, version, declaration, authorization)
            if job.status != "claimed" or job.lease_owner != lease_owner:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            now = timezone.now()
            if not self._authorization_is_active(authorization) or version.admission_status in {
                "cancelled",
                "blocked",
            }:
                job.status = "cancelled"
                job.checkpoint = "result_discarded_after_block"
                attempt.outcome = "cancelled"
                attempt.retry_class = "terminal"
                attempt.reason_code = "RIGHTS_REVOKED"
            else:
                version.content_sha256 = result.content_sha256
                version.derived_file_size_bytes = result.file_size_bytes
                version.derived_media_type = result.media_type
                version.derived_pdf_signature_valid = result.pdf_signature_valid
                version.derived_parser_accepted = result.parser_accepted
                version.derived_page_count = result.page_count
                version.derived_max_rendered_pixels_per_page = result.max_rendered_pixels_per_page
                version.derived_rendered_pixels_total = result.rendered_pixels_total
                version.derived_decoded_parser_bytes = result.decoded_parser_bytes
                version.derived_local_inspection_result = result.local_inspection_result
                version.validation_attempt_count = job.attempt_count
                version.rejection_code = result.rejection_code
                if result.outcome == "admitted":
                    version.admission_status = "admitted"
                    job.status = "completed"
                    job.checkpoint = "admitted"
                    attempt.outcome = "completed"
                    attempt.retry_class = "none"
                    event_type = "source.version.admitted.v1"
                elif result.outcome == "rejected":
                    version.admission_status = "rejected"
                    job.status = "completed"
                    job.checkpoint = "rejected"
                    job.reason_code = result.rejection_code
                    attempt.outcome = "failed"
                    attempt.retry_class = "terminal"
                    attempt.reason_code = result.rejection_code
                    event_type = "source.version.rejected.v1"
                    event_reason = result.rejection_code
                    if result.rejection_code == "OBJECT_MISSING":
                        storage_object = job.storage_object
                        storage_object.status = "missing"
                        storage_object.row_version += 1
                        storage_object.save(update_fields=("status", "row_version", "updated_at"))
                else:
                    version.admission_status = "quarantined"
                    version.rejection_code = None
                    exhausted = job.attempt_count >= job.max_attempts
                    job.status = "failed" if exhausted else "retryable"
                    job.checkpoint = "validation_unavailable"
                    job.reason_code = "SOURCE_ADMISSION_VALIDATION_UNAVAILABLE"
                    attempt.outcome = "failed" if exhausted else "retryable"
                    attempt.retry_class = "terminal" if exhausted else "bounded_retry"
                    attempt.reason_code = "SOURCE_ADMISSION_VALIDATION_UNAVAILABLE"
            version.row_version += 1
            version.save(
                update_fields=(
                    "admission_status",
                    "content_sha256",
                    "derived_file_size_bytes",
                    "derived_media_type",
                    "derived_pdf_signature_valid",
                    "derived_parser_accepted",
                    "derived_page_count",
                    "derived_max_rendered_pixels_per_page",
                    "derived_rendered_pixels_total",
                    "derived_decoded_parser_bytes",
                    "derived_local_inspection_result",
                    "rejection_code",
                    "validation_attempt_count",
                    "row_version",
                    "updated_at",
                )
            )
            if event_type is not None:
                self._record_fact(
                    actor_id=authorization.requested_by_actor_id,
                    tenant_id=job.tenant_id,
                    event_type=event_type,
                    document=document,
                    version=version,
                    reason_code=event_reason,
                    correlation_id=job.correlation_id,
                    causation_id=job.id,
                )
            job.output_manifest_sha256 = output_hash
            job.lease_owner = None
            job.lease_expires_at = None
            job.row_version += 1
            job.save(
                update_fields=(
                    "status",
                    "reason_code",
                    "checkpoint",
                    "output_manifest_sha256",
                    "lease_owner",
                    "lease_expires_at",
                    "row_version",
                    "updated_at",
                )
            )
            attempt.inspector_version = result.inspector_version
            attempt.output_manifest_sha256 = output_hash
            attempt.observation = {
                key: value
                for key, value in asdict(result).items()
                if key not in {"inspector_version"}
            }
            attempt.completed_at = now
            attempt.save(
                update_fields=(
                    "outcome",
                    "retry_class",
                    "reason_code",
                    "inspector_version",
                    "output_manifest_sha256",
                    "observation",
                    "completed_at",
                )
            )
            return self._snapshot(document, version, declaration, authorization)

    def _schedule_removal(
        self,
        *,
        actor_id: UUID,
        document: SourceDocument,
        version: SourceVersion,
        reason_code: str,
    ) -> DocumentJob | None:
        storage_object = StorageObject.objects.filter(
            tenant_id=version.tenant_id,
            source_version_id=version.id,
            status="present",
        ).first()
        if storage_object is None:
            version.removal_status = "not_required"
            version.removal_reason_code = None
            return None
        version.removal_status = "pending"
        version.removal_reason_code = reason_code
        job, _ = DocumentJob.objects.get_or_create(
            tenant_id=version.tenant_id,
            source_document=document,
            source_version=version,
            storage_object=storage_object,
            stage="remove_quarantine_object",
            defaults={
                "status": "pending",
                "reason_code": reason_code,
                "idempotency_key": f"remove:{version.id}:{reason_code}",
                "input_manifest_sha256": _manifest_hash(
                    {
                        "tenant_id": version.tenant_id,
                        "source_document_id": document.id,
                        "source_version_id": version.id,
                        "storage_object_id": storage_object.id,
                        "content_sha256": storage_object.content_sha256,
                        "reason_code": reason_code,
                    }
                ),
            },
        )
        self._record_audit(
            actor_id=actor_id,
            tenant_id=version.tenant_id,
            event_type="source.removal.requested.v1",
            version=version,
            correlation_id=job.correlation_id,
            reason_code=reason_code,
        )
        return job

    def cancel_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        command: CancelAdmissionCommand,
        idempotency_key: str,
    ) -> SourceAdmissionSnapshot:
        if command.reason_code not in {"USER_CANCELLED", "SOURCE_REPLACED"}:
            raise SourceAdmissionError("SOURCE_ADMISSION_VALIDATION_FAILED")
        request = {
            "source_document_id": source_document_id,
            "source_version_id": source_version_id,
            **asdict(command),
        }
        with transaction.atomic():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_SOURCES_CANCEL,
            )
            reservation, replay = self._reserve_idempotency(
                actor_id=actor_id,
                tenant_id=tenant_id,
                operation="documents.admissions.cancel",
                key=idempotency_key,
                request=request,
            )
            if replay is not None:
                document_id, version_id = self._ids_from_replay(replay)
                return self._snapshot(
                    *self._load_models(
                        tenant_id=tenant_id,
                        source_document_id=document_id,
                        source_version_id=version_id,
                    )
                )
            document, version, declaration, authorization = self._load_models(
                tenant_id=tenant_id,
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                lock=True,
            )
            if version.row_version != command.expected_source_version_row_version:
                raise SourceAdmissionError("SOURCE_ADMISSION_VERSION_CONFLICT")
            if version.admission_status not in {
                "rights_pending",
                "upload_pending",
                "quarantined",
                "validating",
            }:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            version.admission_status = "cancelled"
            version.rejection_code = None
            UploadIntent.objects.filter(
                tenant_id=tenant_id,
                source_version_id=source_version_id,
                status="active",
            ).update(
                status="cancelled",
                upload_claim_digest=None,
                upload_claim_expires_at=None,
                row_version=models_increment(),
            )
            DocumentJob.objects.filter(
                tenant_id=tenant_id,
                source_version_id=source_version_id,
                stage="validate_admission",
                status__in=("pending", "claimed", "retryable"),
            ).update(
                status="cancelled",
                checkpoint="user_cancelled",
                lease_owner=None,
                lease_expires_at=None,
                row_version=models_increment(),
            )
            self._schedule_removal(
                actor_id=actor_id,
                document=document,
                version=version,
                reason_code="USER_CANCELLED",
            )
            version.row_version += 1
            version.save(
                update_fields=(
                    "admission_status",
                    "rejection_code",
                    "removal_status",
                    "removal_reason_code",
                    "row_version",
                    "updated_at",
                )
            )
            self._record_fact(
                actor_id=actor_id,
                tenant_id=tenant_id,
                event_type="source.version.cancelled.v1",
                document=document,
                version=version,
                reason_code=command.reason_code,
            )
            self._complete_idempotency(
                reservation,
                source_document_id=document.id,
                source_version_id=version.id,
            )
            return self._snapshot(document, version, declaration, authorization)

    def run_removal_job(self, *, job_id: UUID) -> SourceAdmissionSnapshot:
        lease_owner = f"local-remover:{uuid.uuid4()}"
        with transaction.atomic():
            _set_worker_context(job_id=job_id, stage="remove_quarantine_object")
            try:
                job = (
                    DocumentJob.objects.select_for_update()
                    .select_related("storage_object")
                    .get(id=job_id, stage="remove_quarantine_object")
                )
            except DocumentJob.DoesNotExist as error:
                raise SourceAdmissionError("RESOURCE_NOT_FOUND") from error
            document, version, declaration, authorization = self._load_models(
                tenant_id=job.tenant_id,
                source_document_id=job.source_document_id,
                source_version_id=job.source_version_id,
                lock=True,
            )
            _set_worker_context(
                job_id=job_id,
                stage="remove_quarantine_object",
                tenant_id=job.tenant_id,
            )
            now = timezone.now()
            if job.status == "completed":
                return self._snapshot(document, version, declaration, authorization)
            if job.status == "claimed" and job.lease_expires_at and job.lease_expires_at > now:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if job.status not in {"pending", "retryable", "claimed"}:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            if job.status == "claimed":
                previous_attempt = DocumentJobAttempt.objects.select_for_update().get(
                    job=job,
                    attempt_number=job.attempt_count,
                    outcome="running",
                )
                exhausted = job.attempt_count >= job.max_attempts
                previous_attempt.outcome = "failed" if exhausted else "retryable"
                previous_attempt.retry_class = "terminal" if exhausted else "lease_expired"
                previous_attempt.reason_code = "WORKER_LEASE_EXPIRED"
                previous_attempt.completed_at = now
                previous_attempt.save(
                    update_fields=(
                        "outcome",
                        "retry_class",
                        "reason_code",
                        "completed_at",
                    )
                )
                if exhausted:
                    job.status = "failed"
                    job.checkpoint = "lease_expired_exhausted"
                    job.lease_owner = None
                    job.lease_expires_at = None
                    job.row_version += 1
                    job.save(
                        update_fields=(
                            "status",
                            "checkpoint",
                            "lease_owner",
                            "lease_expires_at",
                            "row_version",
                            "updated_at",
                        )
                    )
                    version.removal_status = "failed"
                    version.row_version += 1
                    version.save(update_fields=("removal_status", "row_version", "updated_at"))
                    return self._snapshot(document, version, declaration, authorization)
            job.status = "claimed"
            job.attempt_count += 1
            job.lease_owner = lease_owner
            job.lease_expires_at = now + timedelta(minutes=2)
            job.checkpoint = "delete_requested"
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
            attempt = DocumentJobAttempt.objects.create(
                tenant_id=job.tenant_id,
                job=job,
                attempt_number=job.attempt_count,
                outcome="running",
                input_manifest_sha256=job.input_manifest_sha256,
                started_at=now,
            )
            locator = job.storage_object.private_locator

        failure: OSError | None = None
        try:
            self._storage.delete(locator)
            if self._storage.exists(locator):
                failure = OSError("local removal observation remained present")
        except OSError as error:
            failure = error
        result_manifest = _manifest_hash(
            {"storage_absent": failure is None, "reason_code": job.reason_code}
        )
        with transaction.atomic():
            _set_worker_context(job_id=job_id, stage="remove_quarantine_object")
            job = (
                DocumentJob.objects.select_for_update()
                .select_related("storage_object")
                .get(id=job_id)
            )
            document, version, declaration, authorization = self._load_models(
                tenant_id=job.tenant_id,
                source_document_id=job.source_document_id,
                source_version_id=job.source_version_id,
                lock=True,
            )
            _set_worker_context(
                job_id=job_id,
                stage="remove_quarantine_object",
                tenant_id=job.tenant_id,
            )
            attempt = DocumentJobAttempt.objects.select_for_update().get(id=attempt.id)
            if job.status != "claimed" or job.lease_owner != lease_owner:
                raise SourceAdmissionError("SOURCE_ADMISSION_STATE_CONFLICT")
            now = timezone.now()
            removal_event_actor: UUID | None = None
            if failure is None:
                job.storage_object.status = "deleted"
                job.storage_object.removed_at = now
                job.storage_object.row_version += 1
                job.storage_object.save(
                    update_fields=("status", "removed_at", "row_version", "updated_at")
                )
                version.removal_status = "completed"
                job.status = "completed"
                job.checkpoint = "absence_observed"
                attempt.outcome = "completed"
                attempt.retry_class = "none"
                removal_event_actor = (
                    authorization.reviewed_by_actor_id or authorization.requested_by_actor_id
                )
            else:
                exhausted = job.attempt_count >= job.max_attempts
                job.status = "failed" if exhausted else "retryable"
                job.checkpoint = "delete_unavailable"
                version.removal_status = "failed" if exhausted else "pending"
                attempt.outcome = "failed" if exhausted else "retryable"
                attempt.retry_class = "terminal" if exhausted else "bounded_retry"
                attempt.reason_code = "REMOVAL_UNAVAILABLE"
            version.row_version += 1
            version.save(update_fields=("removal_status", "row_version", "updated_at"))
            if removal_event_actor is not None:
                self._record_fact(
                    actor_id=removal_event_actor,
                    tenant_id=job.tenant_id,
                    event_type="source.removal.completed.v1",
                    document=document,
                    version=version,
                    reason_code=job.reason_code,
                    correlation_id=job.correlation_id,
                    causation_id=job.id,
                )
            job.output_manifest_sha256 = result_manifest
            job.lease_owner = None
            job.lease_expires_at = None
            job.row_version += 1
            job.save(
                update_fields=(
                    "status",
                    "checkpoint",
                    "output_manifest_sha256",
                    "lease_owner",
                    "lease_expires_at",
                    "row_version",
                    "updated_at",
                )
            )
            attempt.output_manifest_sha256 = result_manifest
            attempt.observation = {"storage_absent": failure is None}
            attempt.completed_at = now
            attempt.save(
                update_fields=(
                    "outcome",
                    "retry_class",
                    "reason_code",
                    "output_manifest_sha256",
                    "observation",
                    "completed_at",
                )
            )
            return self._snapshot(document, version, declaration, authorization)

    def reconcile_pending(self) -> tuple[UUID, ...]:
        """Run one bounded local reconciliation pass without a provider/queue."""

        self._reconcile_orphan_storage()
        job_ids = tuple(
            DocumentJob.objects.filter(status__in=("pending", "retryable"))
            .order_by("created_at", "id")
            .values_list("id", flat=True)[:100]
        )
        completed: list[UUID] = []
        for job_id in job_ids:
            job = DocumentJob.objects.only("stage").get(id=job_id)
            if job.stage == "validate_admission":
                self.run_validation_job(job_id=job_id)
            else:
                self.run_removal_job(job_id=job_id)
            completed.append(job_id)
        return tuple(completed)

    def _reconcile_orphan_storage(self) -> None:
        """Remove bounded local objects that never received an inventory row."""

        locators = self._storage.locators()[:100]
        present_locators = set(
            StorageObject.objects.filter(
                private_locator__in=locators,
                status="present",
            ).values_list("private_locator", flat=True)
        )
        for locator in locators:
            if locator in present_locators:
                continue
            try:
                self._storage.delete(locator)
                if self._storage.exists(locator):
                    continue
            except OSError, ValueError:
                continue
            try:
                intent_id = UUID(hex=locator.removesuffix(".pdf"))
            except ValueError:
                continue
            with transaction.atomic():
                intent = UploadIntent.objects.select_for_update().filter(id=intent_id).first()
                if intent is None:
                    continue
                _document, version, _declaration, authorization = self._load_models(
                    tenant_id=intent.tenant_id,
                    source_document_id=intent.source_document_id,
                    source_version_id=intent.source_version_id,
                    lock=True,
                )
                if intent.status == "active":
                    intent.upload_claim_digest = None
                    intent.upload_claim_expires_at = None
                    intent.row_version += 1
                    intent.save(
                        update_fields=(
                            "upload_claim_digest",
                            "upload_claim_expires_at",
                            "row_version",
                            "updated_at",
                        )
                    )
                self._record_audit(
                    actor_id=authorization.requested_by_actor_id,
                    tenant_id=intent.tenant_id,
                    event_type="source.orphan_object.removed.v1",
                    version=version,
                    correlation_id=uuid.uuid4(),
                    reason_code="ORPHAN_INVENTORY_MISSING",
                )


def models_increment() -> Any:
    """Keep F-expression import local to the one bulk state update."""

    from django.db.models import F

    return F("row_version") + 1

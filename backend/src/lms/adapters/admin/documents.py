from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from lms.api.schemas.documents import (
    CancelSourceAdmissionV1,
    CreateSourceAdmissionV1,
    DocumentIngestionRunV1,
    RequestedSourceOperation,
    ReviewSourceOperationAuthorizationV1,
    ReviewSourceStoreAuthorizationV1,
    SourceAdmissionContractError,
    SourceAdmissionServiceV1,
    SourceAdmissionV1,
    SourceOperationAuthorizationV1,
    UploadIntentV1,
)

SOURCE_ADMISSION_READONLY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "tenant_id",
        "source_document_id",
        "source_version_id",
        "rights_declaration_id",
        "declared_by_actor_id",
        "requested_by_actor_id",
        "reviewed_by_actor_id",
        "operation",
        "status",
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
        "removal",
        "row_version",
        "parser_version",
        "configuration_version",
        "attempt_count",
        "max_attempts",
        "checkpoint",
        "input_manifest_sha256",
        "output_manifest_sha256",
        "quality_summary",
    }
)


@dataclass(frozen=True, slots=True)
class AdminActorContext:
    """Trusted actor plus explicit tenant selector established by Django Admin."""

    actor_id: UUID
    tenant_id: UUID | None
    privileged_access_grant_id: UUID | None = None


class SourceAdmissionAdminActions:
    """Admin operations delegate to the same policy-enforcing service as FastAPI."""

    readonly_fields = SOURCE_ADMISSION_READONLY_FIELDS

    def __init__(self, *, service: SourceAdmissionServiceV1) -> None:
        self._service = service

    @staticmethod
    def _tenant_id(context: AdminActorContext) -> UUID:
        if context.tenant_id is None:
            raise SourceAdmissionContractError(code="TENANT_CONTEXT_REQUIRED")
        return context.tenant_id

    @staticmethod
    def _idempotency_key(value: str) -> str:
        if not 16 <= len(value) <= 128 or value != value.strip():
            raise SourceAdmissionContractError(code="SOURCE_ADMISSION_VALIDATION_FAILED")
        return value

    def create_admission(
        self,
        *,
        context: AdminActorContext,
        request: CreateSourceAdmissionV1,
        idempotency_key: str,
    ) -> SourceAdmissionV1:
        result = self._service.create_admission(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return SourceAdmissionV1.model_validate(result, from_attributes=True)

    def review_authorization(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
        authorization_id: UUID,
        request: ReviewSourceStoreAuthorizationV1,
        idempotency_key: str,
    ) -> SourceAdmissionV1:
        result = self._service.review_authorization(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            authorization_id=authorization_id,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return SourceAdmissionV1.model_validate(result, from_attributes=True)

    def create_upload_intent(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> UploadIntentV1:
        result = self._service.create_upload_intent(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return UploadIntentV1.model_validate(result, from_attributes=True)

    def upload_to_intent(
        self,
        *,
        opaque_token: str,
        content_type: str,
        body: bytes,
    ) -> SourceAdmissionV1:
        if not 32 <= len(opaque_token) <= 128:
            raise SourceAdmissionContractError(code="RESOURCE_NOT_FOUND")
        result = self._service.upload_to_intent(
            opaque_token=opaque_token,
            content_type=content_type,
            body=body,
        )
        return SourceAdmissionV1.model_validate(result, from_attributes=True)

    def get_admission(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> SourceAdmissionV1:
        result = self._service.get_admission(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
        )
        return SourceAdmissionV1.model_validate(result, from_attributes=True)

    def cancel_admission(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
        request: CancelSourceAdmissionV1,
        idempotency_key: str,
    ) -> SourceAdmissionV1:
        result = self._service.cancel_admission(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return SourceAdmissionV1.model_validate(result, from_attributes=True)

    def list_operation_authorizations(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> tuple[SourceOperationAuthorizationV1, ...]:
        result = self._service.list_operation_authorizations(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
        )
        if not isinstance(result, (list, tuple)):
            raise SourceAdmissionContractError(code="SERVICE_CONTRACT_ERROR")
        return tuple(
            SourceOperationAuthorizationV1.model_validate(item, from_attributes=True)
            for item in result
        )

    def request_operation_authorization(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        idempotency_key: str,
    ) -> SourceOperationAuthorizationV1:
        result = self._service.request_operation_authorization(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            operation=operation,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return SourceOperationAuthorizationV1.model_validate(result, from_attributes=True)

    def review_operation_authorization(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        request: ReviewSourceOperationAuthorizationV1,
        idempotency_key: str,
    ) -> SourceOperationAuthorizationV1:
        result = self._service.review_operation_authorization(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            operation=operation,
            command=request,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return SourceOperationAuthorizationV1.model_validate(result, from_attributes=True)

    def start_ingestion(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> DocumentIngestionRunV1:
        result = self._service.start_ingestion(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            idempotency_key=self._idempotency_key(idempotency_key),
        )
        return DocumentIngestionRunV1.model_validate(result, from_attributes=True)

    def get_ingestion(
        self,
        *,
        context: AdminActorContext,
        source_document_id: UUID,
        source_version_id: UUID,
        run_id: UUID,
    ) -> DocumentIngestionRunV1:
        result = self._service.get_ingestion(
            actor_id=context.actor_id,
            tenant_id=self._tenant_id(context),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            run_id=run_id,
        )
        return DocumentIngestionRunV1.model_validate(result, from_attributes=True)

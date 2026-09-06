from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

RightsBasis = Literal[
    "owned",
    "licensed",
    "written_permission",
    "public_domain",
    "other_documented",
]
AuthorizationDecision = Literal["activate", "deny", "revoke"]
TrustedAuthorizationBlockStatus = Literal["expired", "disputed"]
CancellationReason = Literal["USER_CANCELLED", "SOURCE_REPLACED"]
ValidationOutcome = Literal["admitted", "rejected", "retryable_failure"]
SourceOperation = Literal["store", "extract", "ocr", "generate"]


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    version: str
    accepted_media_types: tuple[str, ...]
    max_pdf_bytes: int
    max_page_count: int
    max_rendered_pixels_per_page: int
    max_rendered_pixels_total: int
    max_decoded_parser_bytes: int
    validation_cpu_seconds: int
    validation_wall_seconds: int
    upload_intent_ttl_seconds: int
    max_active_upload_intents_per_tenant: int
    max_upload_intents_per_tenant_24h: int
    max_upload_attempt_bytes_per_tenant_24h: int
    max_quarantine_objects_per_tenant: int
    max_quarantine_bytes_per_tenant: int


@dataclass(frozen=True, slots=True)
class RightsDeclarationInput:
    basis: RightsBasis
    attestation_version: str
    attested: bool
    rights_holder_name: str | None = None
    evidence_reference: str | None = None
    valid_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class CreateAdmissionCommand:
    display_name: str
    declared_filename: str
    rights_declaration: RightsDeclarationInput


@dataclass(frozen=True, slots=True)
class ReviewAuthorizationCommand:
    decision: AuthorizationDecision
    expected_authorization_row_version: int
    decision_code: str


@dataclass(frozen=True, slots=True)
class TrustedAuthorizationBlockCommand:
    status: TrustedAuthorizationBlockStatus
    expected_authorization_row_version: int
    decision_code: str


@dataclass(frozen=True, slots=True)
class CancelAdmissionCommand:
    expected_source_version_row_version: int
    reason_code: CancellationReason


@dataclass(frozen=True, slots=True)
class AdmissionValidationResult:
    outcome: ValidationOutcome
    inspector_version: str
    content_sha256: str | None
    file_size_bytes: int | None
    media_type: str | None
    pdf_signature_valid: bool | None
    parser_accepted: bool | None
    page_count: int | None
    max_rendered_pixels_per_page: int | None
    rendered_pixels_total: int | None
    decoded_parser_bytes: int | None
    local_inspection_result: Literal["accepted", "unsafe", "unavailable"] | None
    rejection_code: str | None


@dataclass(frozen=True, slots=True)
class SourceDocumentRecord:
    id: UUID
    tenant_id: UUID
    display_name: str
    current_version_id: UUID
    row_version: int


@dataclass(frozen=True, slots=True)
class SourceVersionRecord:
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    version_number: int
    admission_status: str
    declared_filename: str
    content_sha256: str | None
    derived_file_size_bytes: int | None
    derived_media_type: str | None
    derived_pdf_signature_valid: bool | None
    derived_parser_accepted: bool | None
    derived_page_count: int | None
    derived_max_rendered_pixels_per_page: int | None
    derived_rendered_pixels_total: int | None
    derived_decoded_parser_bytes: int | None
    derived_local_inspection_result: str | None
    rejection_code: str | None
    validation_attempt_count: int
    row_version: int


@dataclass(frozen=True, slots=True)
class RightsDeclarationRecord:
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    declared_by_actor_id: UUID
    basis: str
    attestation_version: str
    attested_at: datetime
    valid_until: datetime | None
    evidence_reference: str | None
    row_version: int


@dataclass(frozen=True, slots=True)
class SourceAuthorizationRecord:
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    rights_declaration_id: UUID
    operation: str
    status: str
    requested_by_actor_id: UUID
    reviewed_by_actor_id: UUID | None
    decision_code: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class UploadIntentSummary:
    id: UUID
    status: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RemovalRecord:
    status: str
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class SourceAdmissionSnapshot:
    source_document: SourceDocumentRecord
    source_version: SourceVersionRecord
    rights_declaration: RightsDeclarationRecord
    store_authorization: SourceAuthorizationRecord
    upload_intent: UploadIntentSummary | None
    removal: RemovalRecord


@dataclass(frozen=True, slots=True)
class UploadIntentReceipt:
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    status: str
    target_url: str
    opaque_token: str
    expires_at: datetime
    max_bytes: int
    accepted_media_type: str
    row_version: int


@dataclass(frozen=True, slots=True)
class IngestionRunRecord:
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    status: str
    parser_version: str
    configuration_version: str
    locale: str
    attempt_count: int
    max_attempts: int
    checkpoint: str
    input_manifest_sha256: str
    output_manifest_sha256: str | None
    reason_code: str | None
    quality_summary: dict[str, object]
    row_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class IngestionWorkerResult:
    run: IngestionRunRecord
    claimed: bool

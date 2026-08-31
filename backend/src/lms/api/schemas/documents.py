from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Literal, Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.config import JsonDict
from pydantic.json_schema import SkipJsonSchema

RightsBasis = Literal[
    "owned",
    "licensed",
    "written_permission",
    "public_domain",
    "other_documented",
]
AuthorizationDecision = Literal["activate", "deny", "revoke"]
AuthorizationStatus = Literal["requested", "active", "denied", "revoked", "expired", "disputed"]
AdmissionStatus = Literal[
    "rights_pending",
    "upload_pending",
    "quarantined",
    "validating",
    "admitted",
    "rejected",
    "cancelled",
    "blocked",
]
UploadIntentStatus = Literal["active", "consumed", "expired", "cancelled"]
RemovalStatus = Literal["not_required", "pending", "completed", "failed"]
CancellationReason = Literal["USER_CANCELLED", "SOURCE_REPLACED"]
SourceOperation = Literal["store", "extract", "ocr", "generate"]
RequestedSourceOperation = Literal["extract", "ocr", "generate"]
IngestionStatus = Literal[
    "queued",
    "claimed",
    "extracting",
    "normalizing",
    "quality_check",
    "ready_for_generation",
    "retryable",
    "failed",
    "cancelled",
    "rights_blocked",
]
AdmissionRejectionCode = Literal[
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
]

Sha256 = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
EvidenceReference = Annotated[
    str,
    Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$"),
]


def _omit_none_default(schema: JsonDict) -> None:
    schema.pop("default", None)


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timestamp must include a timezone")
    return value


class SourceAdmissionContractError(Exception):
    """Stable service failure translated without trusting arbitrary text."""

    def __init__(
        self,
        *,
        code: str,
        errors: Sequence[dict[str, object]] = (),
    ) -> None:
        super().__init__(code)
        self.code = code
        self.errors = tuple(errors)


class VerifiedActorResult(Protocol):
    @property
    def principal_id(self) -> UUID: ...


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CreateRightsDeclarationV1(StrictSchema):
    basis: RightsBasis
    attestation_version: Literal["f003-source-rights-attestation-v1"]
    attested: Literal[True]
    rights_holder_name: (
        Annotated[str, Field(min_length=1, max_length=160)] | SkipJsonSchema[None]
    ) = Field(default=None, json_schema_extra=_omit_none_default)
    evidence_reference: EvidenceReference | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )
    valid_until: datetime | SkipJsonSchema[None] = Field(
        default=None,
        json_schema_extra=_omit_none_default,
    )

    _timezone = field_validator("valid_until")(_require_timezone)

    @model_validator(mode="after")
    def require_documented_evidence(self) -> Self:
        supplied_nullable = {"rights_holder_name", "evidence_reference", "valid_until"}
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in supplied_nullable - {"valid_until"}
        ):
            raise ValueError("supplied rights evidence fields cannot be null")
        if self.basis in {"licensed", "written_permission", "other_documented"} and (
            self.rights_holder_name is None or self.evidence_reference is None
        ):
            raise ValueError("documented rights require holder and evidence reference")
        return self


class CreateSourceAdmissionV1(StrictSchema):
    display_name: Annotated[str, Field(min_length=1, max_length=160)]
    declared_filename: Annotated[
        str,
        Field(min_length=1, max_length=255, pattern=r"^[^/\\]+\.[Pp][Dd][Ff]$"),
    ]
    rights_declaration: CreateRightsDeclarationV1


class ReviewSourceStoreAuthorizationV1(StrictSchema):
    decision: AuthorizationDecision
    expected_authorization_row_version: int = Field(ge=1, strict=True)
    decision_code: Literal[
        "RIGHTS_EVIDENCE_ACCEPTED",
        "RIGHTS_EVIDENCE_INSUFFICIENT",
        "RIGHTS_REVOKED",
    ]

    @model_validator(mode="after")
    def require_matching_decision_code(self) -> Self:
        expected = {
            "activate": "RIGHTS_EVIDENCE_ACCEPTED",
            "deny": "RIGHTS_EVIDENCE_INSUFFICIENT",
            "revoke": "RIGHTS_REVOKED",
        }[self.decision]
        if self.decision_code != expected:
            raise ValueError("decision_code does not match decision")
        return self


class ReviewSourceOperationAuthorizationV1(ReviewSourceStoreAuthorizationV1):
    pass


class CancelSourceAdmissionV1(StrictSchema):
    expected_source_version_row_version: int = Field(ge=1, strict=True)
    reason_code: CancellationReason


class SourceDocumentV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    display_name: str = Field(min_length=1, max_length=160)
    current_version_id: UUID
    row_version: int = Field(ge=1, strict=True)


class SourceVersionV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    version_number: int = Field(ge=1, strict=True)
    admission_status: AdmissionStatus
    declared_filename: str = Field(min_length=1, max_length=255)
    content_sha256: Sha256 | None
    derived_file_size_bytes: int | None = Field(ge=0)
    derived_media_type: str | None = Field(min_length=1, max_length=100)
    derived_pdf_signature_valid: bool | None
    derived_parser_accepted: bool | None
    derived_page_count: int | None = Field(ge=0)
    derived_max_rendered_pixels_per_page: int | None = Field(ge=0)
    derived_rendered_pixels_total: int | None = Field(ge=0)
    derived_decoded_parser_bytes: int | None = Field(ge=0)
    derived_local_inspection_result: Literal["accepted", "unsafe", "unavailable"] | None
    rejection_code: AdmissionRejectionCode | None
    validation_attempt_count: int = Field(ge=0, strict=True)
    row_version: int = Field(ge=1, strict=True)


class RightsDeclarationV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    declared_by_actor_id: UUID
    basis: RightsBasis
    attestation_version: Literal["f003-source-rights-attestation-v1"]
    attested_at: datetime
    valid_until: datetime | None
    evidence_reference: EvidenceReference | None
    row_version: int = Field(ge=1, strict=True)

    _attested_timezone = field_validator("attested_at")(_require_timezone)
    _valid_timezone = field_validator("valid_until")(_require_timezone)


class SourceUseAuthorizationV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    rights_declaration_id: UUID
    operation: Literal["store"]
    status: AuthorizationStatus
    requested_by_actor_id: UUID
    reviewed_by_actor_id: UUID | None
    decision_code: (
        Literal[
            "RIGHTS_EVIDENCE_ACCEPTED",
            "RIGHTS_EVIDENCE_INSUFFICIENT",
            "RIGHTS_REVOKED",
            "RIGHTS_EXPIRED",
            "RIGHTS_DISPUTED",
        ]
        | None
    )
    valid_from: datetime | None
    valid_until: datetime | None
    row_version: int = Field(ge=1, strict=True)

    _from_timezone = field_validator("valid_from")(_require_timezone)
    _until_timezone = field_validator("valid_until")(_require_timezone)


class SourceOperationAuthorizationV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    rights_declaration_id: UUID
    operation: SourceOperation
    status: AuthorizationStatus
    requested_by_actor_id: UUID
    reviewed_by_actor_id: UUID | None
    decision_code: str | None = Field(max_length=80)
    valid_from: datetime | None
    valid_until: datetime | None
    row_version: int = Field(ge=1, strict=True)

    _from_timezone = field_validator("valid_from")(_require_timezone)
    _until_timezone = field_validator("valid_until")(_require_timezone)


class DocumentIngestionRunV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    status: IngestionStatus
    parser_version: str = Field(min_length=1, max_length=80)
    configuration_version: str = Field(min_length=1, max_length=64)
    locale: Literal["en"]
    attempt_count: int = Field(ge=0, le=10, strict=True)
    max_attempts: int = Field(ge=1, le=10, strict=True)
    checkpoint: str = Field(min_length=1, max_length=64)
    input_manifest_sha256: Sha256
    output_manifest_sha256: Sha256 | None
    reason_code: str | None = Field(max_length=80)
    quality_summary: dict[str, object]
    row_version: int = Field(ge=1, strict=True)
    created_at: datetime
    updated_at: datetime

    _created_timezone = field_validator("created_at")(_require_timezone)
    _updated_timezone = field_validator("updated_at")(_require_timezone)

    @model_validator(mode="after")
    def require_terminal_evidence_shape(self) -> Self:
        if self.attempt_count > self.max_attempts:
            raise ValueError("attempt_count exceeds max_attempts")
        if self.status == "ready_for_generation":
            if self.output_manifest_sha256 is None or self.reason_code is not None:
                raise ValueError("ready ingestion requires only an output manifest")
        elif self.status in {"retryable", "failed", "rights_blocked"}:
            if self.reason_code is None:
                raise ValueError("failed ingestion state requires a reason")
        elif self.output_manifest_sha256 is not None:
            raise ValueError("non-ready ingestion cannot expose an output manifest")
        return self


class UploadIntentSummaryV1(StrictSchema):
    id: UUID
    status: UploadIntentStatus
    expires_at: datetime

    _timezone = field_validator("expires_at")(_require_timezone)


class RemovalV1(StrictSchema):
    status: RemovalStatus
    reason_code: (
        Literal[
            "USER_CANCELLED",
            "RIGHTS_REVOKED",
            "RIGHTS_EXPIRED",
            "RIGHTS_DISPUTED",
        ]
        | None
    )


class SourceAdmissionV1(StrictSchema):
    source_document: SourceDocumentV1
    source_version: SourceVersionV1
    rights_declaration: RightsDeclarationV1
    store_authorization: SourceUseAuthorizationV1
    upload_intent: UploadIntentSummaryV1 | None
    removal: RemovalV1

    @model_validator(mode="after")
    def require_scoped_fail_closed_snapshot(self) -> Self:
        document = self.source_document
        version = self.source_version
        declaration = self.rights_declaration
        authorization = self.store_authorization
        if document.current_version_id != version.id:
            raise ValueError("current source version does not match snapshot")
        if version.tenant_id != document.tenant_id or version.source_document_id != document.id:
            raise ValueError("source version scope does not match document")
        if (
            declaration.tenant_id != document.tenant_id
            or declaration.source_document_id != document.id
            or declaration.source_version_id != version.id
        ):
            raise ValueError("rights declaration scope does not match source")
        if (
            authorization.tenant_id != document.tenant_id
            or authorization.source_document_id != document.id
            or authorization.source_version_id != version.id
            or authorization.rights_declaration_id != declaration.id
        ):
            raise ValueError("authorization scope does not match source")
        if version.admission_status == "admitted":
            admitted = (
                version.content_sha256 is not None
                and version.derived_file_size_bytes is not None
                and 1 <= version.derived_file_size_bytes <= 6_291_456
                and version.derived_media_type == "application/pdf"
                and version.derived_pdf_signature_valid is True
                and version.derived_parser_accepted is True
                and version.derived_page_count is not None
                and 1 <= version.derived_page_count <= 100
                and version.derived_max_rendered_pixels_per_page is not None
                and 1 <= version.derived_max_rendered_pixels_per_page <= 25_000_000
                and version.derived_rendered_pixels_total is not None
                and 1 <= version.derived_rendered_pixels_total <= 250_000_000
                and version.derived_decoded_parser_bytes is not None
                and version.derived_decoded_parser_bytes <= 67_108_864
                and version.derived_local_inspection_result == "accepted"
                and version.rejection_code is None
                and version.validation_attempt_count >= 1
                and authorization.status == "active"
            )
            if not admitted:
                raise ValueError("admitted source is missing required validation evidence")
        elif version.admission_status == "rejected":
            if version.rejection_code is None:
                raise ValueError("rejected source requires a stable rejection code")
        elif version.rejection_code is not None:
            raise ValueError("non-rejected source cannot expose a rejection code")
        if self.upload_intent is not None and self.upload_intent.expires_at.tzinfo is None:
            raise ValueError("upload intent expiry must include a timezone")
        if self.removal.status == "not_required" and self.removal.reason_code is not None:
            raise ValueError("non-required removal cannot include a reason")
        if self.removal.status != "not_required" and self.removal.reason_code is None:
            raise ValueError("required removal must include a reason")
        return self


class UploadIntentV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    status: UploadIntentStatus
    target_url: Annotated[
        str,
        Field(pattern=r"^/api/v1/source-upload-targets/[A-Za-z0-9_-]{32,}$"),
    ]
    expires_at: datetime
    max_bytes: Literal[6_291_456]
    accepted_media_type: Literal["application/pdf"]
    row_version: int = Field(ge=1, strict=True)

    _timezone = field_validator("expires_at")(_require_timezone)


class SourceAdmissionServiceV1(Protocol):
    """Structural port shared by FastAPI and trusted Django Admin actions."""

    def create_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateSourceAdmissionV1,
        idempotency_key: str,
    ) -> object: ...

    def review_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        authorization_id: UUID,
        command: ReviewSourceStoreAuthorizationV1,
        idempotency_key: str,
    ) -> object: ...

    def create_upload_intent(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> object: ...

    def upload_to_intent(
        self,
        *,
        opaque_token: str,
        content_type: str,
        body: bytes,
    ) -> object: ...

    def get_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> object: ...

    def cancel_admission(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        command: CancelSourceAdmissionV1,
        idempotency_key: str,
    ) -> object: ...

    def list_operation_authorizations(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
    ) -> object: ...

    def request_operation_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        idempotency_key: str,
    ) -> object: ...

    def review_operation_authorization(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        command: ReviewSourceOperationAuthorizationV1,
        idempotency_key: str,
    ) -> object: ...

    def start_ingestion(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: str,
    ) -> object: ...

    def get_ingestion(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        run_id: UUID,
    ) -> object: ...

from __future__ import annotations

import uuid
from decimal import Decimal
from uuid import UUID

from django.db import models

ADMISSION_STATUSES = (
    "rights_pending",
    "upload_pending",
    "quarantined",
    "validating",
    "admitted",
    "rejected",
    "cancelled",
    "blocked",
)
AUTHORIZATION_STATUSES = ("requested", "active", "denied", "revoked", "expired", "disputed")
AUTHORIZATION_OPERATIONS = ("store", "extract", "ocr", "generate")
UPLOAD_INTENT_STATUSES = ("active", "consumed", "expired", "cancelled")
REMOVAL_STATUSES = ("not_required", "pending", "completed", "failed")
STORAGE_OBJECT_STATUSES = ("present", "missing", "deleted")
JOB_STAGES = ("validate_admission", "remove_quarantine_object")
JOB_STATUSES = ("pending", "claimed", "retryable", "completed", "failed", "cancelled")
JOB_ATTEMPT_OUTCOMES = ("running", "completed", "retryable", "failed", "cancelled")
INGESTION_RUN_STATUSES = (
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
)
NON_TERMINAL_INGESTION_STATUSES = (
    "queued",
    "claimed",
    "extracting",
    "normalizing",
    "quality_check",
    "retryable",
)
INGESTION_ATTEMPT_OUTCOMES = (
    "running",
    "completed",
    "retryable",
    "failed",
    "cancelled",
    "rights_blocked",
)
SOURCE_ARTIFACT_ROLES = ("canonical_json", "normalized_markdown")
DOCUMENT_ELEMENT_KINDS = ("heading", "paragraph")
SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class TimestampedDocumentModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SourceDocument(TimestampedDocumentModel):
    objects: models.Manager[SourceDocument] = models.Manager()
    tenant_id: UUID
    current_version_id: UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    display_name = models.CharField(max_length=160)
    owner_actor_id = models.UUIDField()
    current_version = models.ForeignKey(
        "SourceVersion",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="current_for_documents",
    )
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."source_documents'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_source_documents_tenant_id"),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_source_documents_row_version",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "owner_actor_id"), name="ix_source_docs_owner"),
        ]


class SourceVersion(TimestampedDocumentModel):
    objects: models.Manager[SourceVersion] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.RESTRICT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField(default=1)
    admission_status = models.CharField(max_length=24, default="rights_pending")
    declared_filename = models.CharField(max_length=255)
    content_sha256 = models.CharField(max_length=71, null=True, blank=True)
    derived_file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    derived_media_type = models.CharField(max_length=100, null=True, blank=True)
    derived_pdf_signature_valid = models.BooleanField(null=True, blank=True)
    derived_parser_accepted = models.BooleanField(null=True, blank=True)
    derived_page_count = models.PositiveIntegerField(null=True, blank=True)
    derived_max_rendered_pixels_per_page = models.PositiveBigIntegerField(null=True, blank=True)
    derived_rendered_pixels_total = models.PositiveBigIntegerField(null=True, blank=True)
    derived_decoded_parser_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    derived_local_inspection_result = models.CharField(max_length=16, null=True, blank=True)
    rejection_code = models.CharField(max_length=80, null=True, blank=True)
    validation_attempt_count = models.PositiveIntegerField(default=0)
    removal_status = models.CharField(max_length=16, default="not_required")
    removal_reason_code = models.CharField(max_length=32, null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."source_document_versions'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_source_versions_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_document", "id"),
                name="uq_source_versions_tenant_doc_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "source_document", "version_number"),
                name="uq_source_versions_doc_number",
            ),
            models.CheckConstraint(
                condition=models.Q(admission_status__in=ADMISSION_STATUSES),
                name="ck_source_versions_status",
            ),
            models.CheckConstraint(
                condition=models.Q(removal_status__in=REMOVAL_STATUSES),
                name="ck_source_versions_removal_status",
            ),
            models.CheckConstraint(
                condition=models.Q(content_sha256__isnull=True)
                | models.Q(content_sha256__regex=SHA256_PATTERN),
                name="ck_source_versions_checksum",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_source_versions_row_version",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "admission_status"), name="ix_source_versions_status"),
        ]


class SourceRightsDeclaration(models.Model):
    objects: models.Manager[SourceRightsDeclaration] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    declared_by_actor_id = models.UUIDField()
    basis = models.CharField(max_length=32)
    attestation_version = models.CharField(max_length=64)
    attested_at = models.DateTimeField()
    rights_holder_name = models.CharField(max_length=160, null=True, blank=True)
    evidence_reference = models.CharField(max_length=120, null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."source_rights_declarations'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_source_rights_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version"),
                name="uq_source_rights_version",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "source_version"), name="ix_source_rights_version"),
        ]


class SourceUseAuthorization(TimestampedDocumentModel):
    objects: models.Manager[SourceUseAuthorization] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    rights_declaration_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    rights_declaration = models.ForeignKey(SourceRightsDeclaration, on_delete=models.RESTRICT)
    operation = models.CharField(max_length=16, default="store")
    status = models.CharField(max_length=16, default="requested")
    requested_by_actor_id = models.UUIDField()
    reviewed_by_actor_id = models.UUIDField(null=True, blank=True)
    decision_code = models.CharField(max_length=64, null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."source_use_authorizations'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_source_auth_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_source_auth_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "operation"),
                name="uq_source_auth_version_operation",
            ),
            models.CheckConstraint(
                condition=models.Q(operation__in=AUTHORIZATION_OPERATIONS),
                name="ck_source_auth_operation",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=AUTHORIZATION_STATUSES),
                name="ck_source_auth_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "source_version", "operation", "status"),
                name="ix_source_auth_active",
            ),
        ]


class UploadIntent(TimestampedDocumentModel):
    objects: models.Manager[UploadIntent] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    authorization_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    authorization = models.ForeignKey(SourceUseAuthorization, on_delete=models.RESTRICT)
    token_digest = models.CharField(max_length=64, unique=True, editable=False)
    purpose = models.CharField(max_length=32, default="source_quarantine")
    status = models.CharField(max_length=16, default="active")
    expires_at = models.DateTimeField()
    max_bytes = models.PositiveBigIntegerField()
    accepted_media_type = models.CharField(max_length=100, default="application/pdf")
    observed_content_sha256 = models.CharField(max_length=71, null=True, blank=True)
    observed_byte_count = models.PositiveBigIntegerField(null=True, blank=True)
    upload_claim_digest = models.CharField(max_length=64, null=True, blank=True)
    upload_claim_expires_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."source_upload_intents'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_source_intents_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version"),
                condition=models.Q(status="active"),
                name="uq_source_intents_active_version",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=UPLOAD_INTENT_STATUSES),
                name="ck_source_intents_status",
            ),
            models.CheckConstraint(
                condition=models.Q(purpose="source_quarantine"),
                name="ck_source_intents_purpose",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "status", "expires_at"),
                name="ix_source_intents_active",
            ),
        ]


class StorageObject(TimestampedDocumentModel):
    objects: models.Manager[StorageObject] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    upload_intent_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    upload_intent = models.OneToOneField(UploadIntent, on_delete=models.RESTRICT)
    private_locator = models.CharField(max_length=80, unique=True)
    content_sha256 = models.CharField(max_length=71)
    byte_count = models.PositiveBigIntegerField()
    media_type = models.CharField(max_length=100)
    status = models.CharField(max_length=16, default="present")
    observed_at = models.DateTimeField()
    removed_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."source_storage_objects'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_source_objects_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_source_objects_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "source_version"),
                name="uq_source_objects_version",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=STORAGE_OBJECT_STATUSES),
                name="ck_source_objects_status",
            ),
            models.CheckConstraint(
                condition=models.Q(content_sha256__regex=SHA256_PATTERN),
                name="ck_source_objects_checksum",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status"), name="ix_source_objects_status"),
        ]


class DocumentJob(TimestampedDocumentModel):
    objects: models.Manager[DocumentJob] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    storage_object_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    storage_object = models.ForeignKey(StorageObject, on_delete=models.RESTRICT)
    stage = models.CharField(max_length=32)
    status = models.CharField(max_length=16, default="pending")
    reason_code = models.CharField(max_length=80, null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    lease_owner = models.CharField(max_length=80, null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    checkpoint = models.CharField(max_length=64, default="created")
    idempotency_key = models.CharField(max_length=128)
    correlation_id = models.UUIDField(default=uuid.uuid4)
    input_manifest_sha256 = models.CharField(max_length=71)
    output_manifest_sha256 = models.CharField(max_length=71, null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'integration"."document_jobs'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_document_jobs_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "stage"),
                name="uq_document_jobs_version_stage",
            ),
            models.CheckConstraint(
                condition=models.Q(stage__in=JOB_STAGES),
                name="ck_document_jobs_stage",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=JOB_STATUSES),
                name="ck_document_jobs_status",
            ),
            models.CheckConstraint(
                condition=models.Q(input_manifest_sha256__regex=SHA256_PATTERN),
                name="ck_document_jobs_input_hash",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "stage", "status"), name="ix_document_jobs_claim"),
        ]


class DocumentJobAttempt(models.Model):
    objects: models.Manager[DocumentJobAttempt] = models.Manager()
    tenant_id: UUID
    job_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    job = models.ForeignKey(DocumentJob, on_delete=models.RESTRICT, related_name="attempts")
    attempt_number = models.PositiveIntegerField()
    outcome = models.CharField(max_length=16, default="running")
    retry_class = models.CharField(max_length=32, null=True, blank=True)
    reason_code = models.CharField(max_length=80, null=True, blank=True)
    inspector_version = models.CharField(max_length=80, null=True, blank=True)
    input_manifest_sha256 = models.CharField(max_length=71)
    output_manifest_sha256 = models.CharField(max_length=71, null=True, blank=True)
    observation = models.JSONField(default=dict)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'integration"."document_job_attempts'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_document_attempts_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "job", "attempt_number"),
                name="uq_document_attempts_job_number",
            ),
            models.CheckConstraint(
                condition=models.Q(outcome__in=JOB_ATTEMPT_OUTCOMES),
                name="ck_document_attempts_outcome",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "job", "attempt_number"), name="ix_doc_attempts_job"),
        ]


class DocumentIngestionRun(TimestampedDocumentModel):
    objects: models.Manager[DocumentIngestionRun] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    storage_object_id: UUID
    extract_authorization_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    storage_object = models.ForeignKey(StorageObject, on_delete=models.RESTRICT)
    extract_authorization = models.ForeignKey(SourceUseAuthorization, on_delete=models.RESTRICT)
    requested_by_actor_id = models.UUIDField()
    status = models.CharField(max_length=24, default="queued")
    parser_version = models.CharField(max_length=80)
    configuration_version = models.CharField(max_length=64)
    locale = models.CharField(max_length=8, default="en")
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    lease_owner = models.CharField(max_length=80, null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    checkpoint = models.CharField(max_length=64, default="created")
    input_manifest_sha256 = models.CharField(max_length=71)
    output_manifest_sha256 = models.CharField(max_length=71, null=True, blank=True)
    reason_code = models.CharField(max_length=80, null=True, blank=True)
    quality_summary = models.JSONField(default=dict)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'integration"."document_ingestion_runs'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_ingestion_runs_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_ingestion_runs_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "parser_version", "configuration_version"),
                condition=models.Q(status__in=NON_TERMINAL_INGESTION_STATUSES),
                name="uq_ingestion_runs_active_version",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=INGESTION_RUN_STATUSES),
                name="ck_ingestion_runs_status",
            ),
            models.CheckConstraint(
                condition=models.Q(locale="en"),
                name="ck_ingestion_runs_locale",
            ),
            models.CheckConstraint(
                condition=models.Q(input_manifest_sha256__regex=SHA256_PATTERN),
                name="ck_ingestion_runs_input_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(output_manifest_sha256__isnull=True)
                | models.Q(output_manifest_sha256__regex=SHA256_PATTERN),
                name="ck_ingestion_runs_output_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(max_attempts__gte=1)
                & models.Q(max_attempts__lte=10)
                & models.Q(attempt_count__lte=models.F("max_attempts")),
                name="ck_ingestion_runs_attempts",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_ingestion_runs_row_version",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "created_at"), name="ix_ingest_runs_claim"),
            models.Index(
                fields=("tenant", "source_version", "created_at"),
                name="ix_ingest_runs_source",
            ),
        ]


class DocumentIngestionAttempt(models.Model):
    objects: models.Manager[DocumentIngestionAttempt] = models.Manager()
    tenant_id: UUID
    ingestion_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    ingestion_run = models.ForeignKey(
        DocumentIngestionRun,
        on_delete=models.RESTRICT,
        related_name="attempts",
    )
    attempt_number = models.PositiveIntegerField()
    outcome = models.CharField(max_length=24, default="running")
    reason_code = models.CharField(max_length=80, null=True, blank=True)
    checkpoint = models.CharField(max_length=64, default="claimed")
    input_manifest_sha256 = models.CharField(max_length=71)
    output_manifest_sha256 = models.CharField(max_length=71, null=True, blank=True)
    observation = models.JSONField(default=dict)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'integration"."document_ingestion_attempts'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_ingestion_attempts_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "ingestion_run", "attempt_number"),
                name="uq_ingestion_attempts_run_number",
            ),
            models.CheckConstraint(
                condition=models.Q(outcome__in=INGESTION_ATTEMPT_OUTCOMES),
                name="ck_ingestion_attempts_outcome",
            ),
            models.CheckConstraint(
                condition=models.Q(input_manifest_sha256__regex=SHA256_PATTERN),
                name="ck_ingestion_attempts_input_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(output_manifest_sha256__isnull=True)
                | models.Q(output_manifest_sha256__regex=SHA256_PATTERN),
                name="ck_ingestion_attempts_output_hash",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "ingestion_run", "attempt_number"),
                name="ix_ingest_attempts_run",
            ),
        ]


class SourceArtifact(models.Model):
    objects: models.Manager[SourceArtifact] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    created_by_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    created_by_run = models.ForeignKey(DocumentIngestionRun, on_delete=models.RESTRICT)
    artifact_role = models.CharField(max_length=24)
    schema_version = models.CharField(max_length=64)
    content_sha256 = models.CharField(max_length=71)
    byte_count = models.PositiveBigIntegerField()
    json_payload = models.JSONField(null=True, blank=True)
    text_payload = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."source_artifacts'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_source_artifacts_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_source_artifacts_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "artifact_role", "schema_version"),
                name="uq_source_artifacts_version_role",
            ),
            models.CheckConstraint(
                condition=models.Q(artifact_role__in=SOURCE_ARTIFACT_ROLES),
                name="ck_source_artifacts_role",
            ),
            models.CheckConstraint(
                condition=models.Q(content_sha256__regex=SHA256_PATTERN),
                name="ck_source_artifacts_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(byte_count__gte=1),
                name="ck_source_artifacts_bytes",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        artifact_role="canonical_json",
                        json_payload__isnull=False,
                        text_payload__isnull=True,
                    )
                    | models.Q(
                        artifact_role="normalized_markdown",
                        json_payload__isnull=True,
                        text_payload__isnull=False,
                    )
                ),
                name="ck_source_artifacts_payload",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "source_version", "artifact_role"),
                name="ix_source_artifacts_version",
            ),
        ]


class DocumentPage(models.Model):
    objects: models.Manager[DocumentPage] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    created_by_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    created_by_run = models.ForeignKey(DocumentIngestionRun, on_delete=models.RESTRICT)
    parser_version = models.CharField(max_length=80)
    configuration_version = models.CharField(max_length=64)
    page_number = models.PositiveIntegerField()
    width_points = models.DecimalField(max_digits=12, decimal_places=3)
    height_points = models.DecimalField(max_digits=12, decimal_places=3)
    text = models.TextField()
    text_sha256 = models.CharField(max_length=71)
    ocr_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."document_pages'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_document_pages_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_document_pages_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=(
                    "tenant",
                    "source_version",
                    "parser_version",
                    "configuration_version",
                    "page_number",
                ),
                name="uq_document_pages_version_number",
            ),
            models.CheckConstraint(
                condition=models.Q(page_number__gte=1),
                name="ck_document_pages_number",
            ),
            models.CheckConstraint(
                condition=models.Q(width_points__gt=Decimal("0"))
                & models.Q(height_points__gt=Decimal("0")),
                name="ck_document_pages_dimensions",
            ),
            models.CheckConstraint(
                condition=models.Q(text_sha256__regex=SHA256_PATTERN),
                name="ck_document_pages_text_hash",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "source_version", "page_number"),
                name="ix_document_pages_version",
            ),
        ]


class DocumentElement(models.Model):
    objects: models.Manager[DocumentElement] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    page_id: UUID
    created_by_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    page = models.ForeignKey(DocumentPage, on_delete=models.RESTRICT, related_name="elements")
    created_by_run = models.ForeignKey(DocumentIngestionRun, on_delete=models.RESTRICT)
    position = models.PositiveIntegerField()
    kind = models.CharField(max_length=16)
    text = models.TextField()
    text_sha256 = models.CharField(max_length=71)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."document_elements'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_document_elements_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_document_elements_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "page", "position"),
                name="uq_document_elements_page_position",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="ck_document_elements_position",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=DOCUMENT_ELEMENT_KINDS),
                name="ck_document_elements_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(text_sha256__regex=SHA256_PATTERN),
                name="ck_document_elements_text_hash",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "page", "position"), name="ix_document_elements_page"),
        ]


class DocumentSection(models.Model):
    objects: models.Manager[DocumentSection] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    created_by_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey(SourceDocument, on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    created_by_run = models.ForeignKey(DocumentIngestionRun, on_delete=models.RESTRICT)
    position = models.PositiveIntegerField()
    title = models.CharField(max_length=160)
    start_page = models.PositiveIntegerField()
    end_page = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."document_sections'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_document_sections_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_document_sections_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "position"),
                name="uq_document_sections_version_position",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="ck_document_sections_position",
            ),
            models.CheckConstraint(
                condition=models.Q(start_page__gte=1)
                & models.Q(end_page__gte=models.F("start_page")),
                name="ck_document_sections_page_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "source_version", "position"),
                name="ix_document_sections_version",
            ),
        ]


class DocumentSectionElement(models.Model):
    objects: models.Manager[DocumentSectionElement] = models.Manager()
    tenant_id: UUID
    source_version_id: UUID
    section_id: UUID
    element_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.RESTRICT)
    section = models.ForeignKey(
        DocumentSection,
        on_delete=models.RESTRICT,
        related_name="element_edges",
    )
    element = models.ForeignKey(DocumentElement, on_delete=models.RESTRICT)
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."document_section_elements'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_document_section_elements_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_document_section_elements_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "section", "position"),
                name="uq_document_section_elements_position",
            ),
            models.UniqueConstraint(
                fields=("tenant", "section", "element"),
                name="uq_document_section_elements_edge",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="ck_document_section_elements_position",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "section", "position"),
                name="ix_doc_section_elements",
            ),
        ]

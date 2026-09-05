from __future__ import annotations

import uuid
from uuid import UUID

from django.db import models

HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"
GENERATION_RUN_STATUSES = (
    "queued",
    "planning",
    "blueprint_review",
    "generation_queued",
    "generating",
    "review_ready",
    "canonicalized",
    "rejected",
    "retryable",
    "failed",
    "rights_blocked",
)
NON_TERMINAL_GENERATION_STATUSES = (
    "queued",
    "planning",
    "blueprint_review",
    "generation_queued",
    "generating",
    "review_ready",
    "retryable",
)
GENERATION_ATTEMPT_OUTCOMES = (
    "running",
    "completed",
    "retryable",
    "failed",
    "rights_blocked",
)
BLUEPRINT_STATUSES = ("reviewable", "approved", "rejected")
BLUEPRINT_ITEM_KINDS = ("module", "lesson")
BLUEPRINT_DECISIONS = ("approve", "reject")
SOURCE_EDGE_KINDS = ("blueprint_item", "generated_lesson")
TARGET_LEVELS = ("beginner", "intermediate", "advanced")
TEACHING_STYLES = ("concise", "guided", "reference")


class TimestampedGenerationModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CourseGenerationRun(TimestampedGenerationModel):
    objects: models.Manager[CourseGenerationRun] = models.Manager()
    tenant_id: UUID
    source_document_id: UUID
    source_version_id: UUID
    ingestion_run_id: UUID
    generate_authorization_id: UUID
    supersedes_run_id: UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    source_document = models.ForeignKey("documents.SourceDocument", on_delete=models.RESTRICT)
    source_version = models.ForeignKey("documents.SourceVersion", on_delete=models.RESTRICT)
    ingestion_run = models.ForeignKey(
        "documents.DocumentIngestionRun",
        on_delete=models.RESTRICT,
    )
    generate_authorization = models.ForeignKey(
        "documents.SourceUseAuthorization",
        on_delete=models.RESTRICT,
    )
    supersedes_run = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="successor_runs",
    )
    requested_by_actor_id = models.UUIDField()
    status = models.CharField(max_length=24, default="queued")
    target_level = models.CharField(max_length=16)
    target_duration_minutes = models.PositiveIntegerField()
    intended_audience = models.CharField(max_length=300)
    teaching_style = models.CharField(max_length=16)
    locale = models.CharField(max_length=8, default="en")
    adapter = models.CharField(max_length=64)
    provider = models.CharField(max_length=32, default="local_deterministic")
    model = models.CharField(max_length=32, default="none")
    normalized_schema_version = models.CharField(max_length=64)
    blueprint_schema_version = models.CharField(max_length=64)
    draft_schema_version = models.CharField(max_length=64)
    policy_version = models.CharField(max_length=64)
    prompt_template_sha256 = models.CharField(max_length=71)
    input_manifest_sha256 = models.CharField(max_length=71)
    blueprint_content_sha256 = models.CharField(max_length=71, null=True, blank=True)
    output_manifest_sha256 = models.CharField(max_length=71, null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    lease_owner = models.CharField(max_length=80, null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    checkpoint = models.CharField(max_length=64, default="created")
    reason_code = models.CharField(max_length=80, null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'integration"."course_generation_runs'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_generation_runs_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "source_version", "id"),
                name="uq_generation_runs_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "ingestion_run", "adapter"),
                condition=models.Q(status__in=NON_TERMINAL_GENERATION_STATUSES),
                name="uq_generation_runs_active_ingestion",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=GENERATION_RUN_STATUSES),
                name="ck_generation_runs_status",
            ),
            models.CheckConstraint(
                condition=models.Q(target_level__in=TARGET_LEVELS),
                name="ck_generation_runs_level",
            ),
            models.CheckConstraint(
                condition=models.Q(target_duration_minutes__gte=1)
                & models.Q(target_duration_minutes__lte=10_000),
                name="ck_generation_runs_duration",
            ),
            models.CheckConstraint(
                condition=models.Q(teaching_style__in=TEACHING_STYLES),
                name="ck_generation_runs_style",
            ),
            models.CheckConstraint(condition=models.Q(locale="en"), name="ck_generation_locale"),
            models.CheckConstraint(
                condition=models.Q(provider="local_deterministic", model="none"),
                name="ck_generation_local_provider",
            ),
            models.CheckConstraint(
                condition=models.Q(input_manifest_sha256__regex=HASH_PATTERN)
                & models.Q(prompt_template_sha256__regex=HASH_PATTERN),
                name="ck_generation_input_hashes",
            ),
            models.CheckConstraint(
                condition=models.Q(blueprint_content_sha256__isnull=True)
                | models.Q(blueprint_content_sha256__regex=HASH_PATTERN),
                name="ck_generation_run_blueprint_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(output_manifest_sha256__isnull=True)
                | models.Q(output_manifest_sha256__regex=HASH_PATTERN),
                name="ck_generation_output_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(max_attempts__gte=1)
                & models.Q(max_attempts__lte=10)
                & models.Q(attempt_count__lte=models.F("max_attempts")),
                name="ck_generation_attempt_bounds",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_generation_runs_row_version",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "created_at"), name="ix_generation_claim"),
            models.Index(
                fields=("tenant", "source_version", "created_at"),
                name="ix_generation_source",
            ),
        ]


class CourseGenerationAttempt(models.Model):
    objects: models.Manager[CourseGenerationAttempt] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.ForeignKey(
        CourseGenerationRun,
        on_delete=models.RESTRICT,
        related_name="attempts",
    )
    attempt_number = models.PositiveIntegerField()
    stage = models.CharField(max_length=24)
    outcome = models.CharField(max_length=24, default="running")
    reason_code = models.CharField(max_length=80, null=True, blank=True)
    checkpoint = models.CharField(max_length=64)
    input_manifest_sha256 = models.CharField(max_length=71)
    output_manifest_sha256 = models.CharField(max_length=71, null=True, blank=True)
    observation = models.JSONField(default=dict)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'integration"."course_generation_attempts'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_generation_attempts_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run", "attempt_number"),
                name="uq_generation_attempts_run_no",
            ),
            models.CheckConstraint(
                condition=models.Q(outcome__in=GENERATION_ATTEMPT_OUTCOMES),
                name="ck_generation_attempts_outcome",
            ),
            models.CheckConstraint(
                condition=models.Q(input_manifest_sha256__regex=HASH_PATTERN),
                name="ck_generation_attempt_input",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "generation_run", "attempt_number"),
                name="ix_generation_attempts_run",
            )
        ]


class GenerationRunSnapshot(models.Model):
    objects: models.Manager[GenerationRunSnapshot] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.OneToOneField(
        CourseGenerationRun,
        on_delete=models.RESTRICT,
        related_name="snapshot",
    )
    metadata = models.JSONField()
    content_sha256 = models.CharField(max_length=71)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'integration"."course_generation_snapshots'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_generation_snapshots_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run"),
                name="uq_generation_snapshots_run",
            ),
            models.CheckConstraint(
                condition=models.Q(content_sha256__regex=HASH_PATTERN),
                name="ck_generation_snapshot_hash",
            ),
        ]


class CourseBlueprint(models.Model):
    objects: models.Manager[CourseBlueprint] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.ForeignKey(
        CourseGenerationRun,
        on_delete=models.RESTRICT,
        related_name="blueprints",
    )
    revision = models.PositiveIntegerField(default=1)
    schema_version = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default="reviewable")
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=2000)
    intended_audience = models.CharField(max_length=300)
    prerequisites = models.JSONField(default=list)
    learning_outcomes = models.JSONField(default=list)
    projection = models.JSONField()
    content_sha256 = models.CharField(max_length=71)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."course_generation_blueprints'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_generation_blueprints_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run", "revision"),
                name="uq_generation_blueprints_revision",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run", "id"),
                name="uq_generation_blueprints_run_id",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=BLUEPRINT_STATUSES),
                name="ck_generation_blueprint_status",
            ),
            models.CheckConstraint(
                condition=models.Q(content_sha256__regex=HASH_PATTERN),
                name="ck_generation_blueprint_hash",
            ),
        ]


class CourseBlueprintItem(models.Model):
    objects: models.Manager[CourseBlueprintItem] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID
    blueprint_id: UUID
    parent_id: UUID | None
    source_version_id: UUID
    source_section_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.ForeignKey(CourseGenerationRun, on_delete=models.RESTRICT)
    blueprint = models.ForeignKey(
        CourseBlueprint,
        on_delete=models.RESTRICT,
        related_name="items",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="child_items",
    )
    source_version = models.ForeignKey("documents.SourceVersion", on_delete=models.RESTRICT)
    source_section = models.ForeignKey("documents.DocumentSection", on_delete=models.RESTRICT)
    kind = models.CharField(max_length=16)
    position = models.PositiveIntegerField()
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."course_generation_blueprint_items'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_generation_items_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run", "id"),
                name="uq_generation_items_run_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "blueprint", "id"),
                name="uq_generation_items_blueprint_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "blueprint", "kind", "parent", "position"),
                name="uq_generation_items_position",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=BLUEPRINT_ITEM_KINDS),
                name="ck_generation_items_kind",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(kind="module", parent__isnull=True)
                    | models.Q(kind="lesson", parent__isnull=False)
                ),
                name="ck_generation_items_parent",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="ck_generation_items_positive_position",
            ),
        ]


class GeneratedLessonArtifact(models.Model):
    objects: models.Manager[GeneratedLessonArtifact] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID
    blueprint_item_id: UUID
    source_version_id: UUID
    source_section_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.ForeignKey(
        CourseGenerationRun,
        on_delete=models.RESTRICT,
        related_name="lesson_artifacts",
    )
    blueprint_item = models.ForeignKey(CourseBlueprintItem, on_delete=models.RESTRICT)
    source_version = models.ForeignKey("documents.SourceVersion", on_delete=models.RESTRICT)
    source_section = models.ForeignKey("documents.DocumentSection", on_delete=models.RESTRICT)
    revision = models.PositiveIntegerField(default=1)
    schema_version = models.CharField(max_length=64)
    title = models.CharField(max_length=160)
    document = models.JSONField()
    content_sha256 = models.CharField(max_length=71)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."generated_lesson_artifacts'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_generated_lessons_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run", "blueprint_item", "revision"),
                name="uq_generated_lessons_revision",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run", "id"),
                name="uq_generated_lessons_run_id",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gte=1),
                name="ck_generated_lessons_revision",
            ),
            models.CheckConstraint(
                condition=models.Q(content_sha256__regex=HASH_PATTERN),
                name="ck_generated_lessons_hash",
            ),
        ]


class GenerationSourceEdge(models.Model):
    objects: models.Manager[GenerationSourceEdge] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID
    source_version_id: UUID
    source_section_id: UUID
    blueprint_item_id: UUID | None
    generated_artifact_id: UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.ForeignKey(CourseGenerationRun, on_delete=models.RESTRICT)
    source_version = models.ForeignKey("documents.SourceVersion", on_delete=models.RESTRICT)
    source_section = models.ForeignKey("documents.DocumentSection", on_delete=models.RESTRICT)
    edge_kind = models.CharField(max_length=24)
    blueprint_item = models.ForeignKey(
        CourseBlueprintItem,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
    )
    generated_artifact = models.ForeignKey(
        GeneratedLessonArtifact,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."course_generation_source_edges'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_generation_edges_id"),
            models.CheckConstraint(
                condition=models.Q(edge_kind__in=SOURCE_EDGE_KINDS),
                name="ck_generation_edges_kind",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        edge_kind="blueprint_item",
                        blueprint_item__isnull=False,
                        generated_artifact__isnull=True,
                    )
                    | models.Q(
                        edge_kind="generated_lesson",
                        blueprint_item__isnull=True,
                        generated_artifact__isnull=False,
                    )
                ),
                name="ck_generation_edges_target",
            ),
        ]


class BlueprintReviewDecision(models.Model):
    objects: models.Manager[BlueprintReviewDecision] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID
    blueprint_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.ForeignKey(CourseGenerationRun, on_delete=models.RESTRICT)
    blueprint = models.ForeignKey(CourseBlueprint, on_delete=models.RESTRICT)
    decided_by_actor_id = models.UUIDField()
    decision = models.CharField(max_length=16)
    reviewed_content_sha256 = models.CharField(max_length=71)
    reason_code = models.CharField(max_length=80, null=True, blank=True)
    decided_at = models.DateTimeField()

    class Meta:
        db_table = 'audit"."course_generation_blueprint_decisions'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_generation_decisions_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run", "blueprint"),
                name="uq_generation_decisions_blueprint",
            ),
            models.CheckConstraint(
                condition=models.Q(decision__in=BLUEPRINT_DECISIONS),
                name="ck_generation_decisions_value",
            ),
            models.CheckConstraint(
                condition=models.Q(reviewed_content_sha256__regex=HASH_PATTERN),
                name="ck_generation_decisions_hash",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(decision="approve", reason_code__isnull=True)
                    | models.Q(decision="reject", reason_code__isnull=False)
                ),
                name="ck_generation_decisions_reason",
            ),
        ]


class CourseGenerationRejection(models.Model):
    objects: models.Manager[CourseGenerationRejection] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.OneToOneField(
        CourseGenerationRun,
        on_delete=models.RESTRICT,
        related_name="rejection",
    )
    rejected_by_actor_id = models.UUIDField()
    reviewed_output_sha256 = models.CharField(max_length=71)
    reason_code = models.CharField(max_length=80)
    rejected_at = models.DateTimeField()

    class Meta:
        db_table = 'audit"."course_generation_rejections'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_generation_rejections_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run"),
                name="uq_generation_rejections_run",
            ),
            models.CheckConstraint(
                condition=models.Q(reviewed_output_sha256__regex=HASH_PATTERN),
                name="ck_generation_rejections_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    reason_code__in=(
                        "GENERATION_CONTENT_REJECTED",
                        "GENERATION_SOURCE_ALIGNMENT_REJECTED",
                    )
                ),
                name="ck_generation_rejections_reason",
            ),
        ]


class GenerationCanonicalization(models.Model):
    objects: models.Manager[GenerationCanonicalization] = models.Manager()
    tenant_id: UUID
    generation_run_id: UUID
    course_id: UUID
    course_version_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    generation_run = models.OneToOneField(
        CourseGenerationRun,
        on_delete=models.RESTRICT,
        related_name="canonicalization",
    )
    course = models.ForeignKey("courses.Course", on_delete=models.RESTRICT)
    course_version = models.ForeignKey("courses.CourseVersion", on_delete=models.RESTRICT)
    canonicalized_by_actor_id = models.UUIDField()
    requested_course_slug = models.SlugField(max_length=63)
    reviewed_output_sha256 = models.CharField(max_length=71)
    canonical_content_sha256 = models.CharField(max_length=71)
    canonicalization_sha256 = models.CharField(max_length=71)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit"."course_generation_canonicalizations'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"), name="uq_generation_canonical_tenant_id"
            ),
            models.UniqueConstraint(
                fields=("tenant", "generation_run"), name="uq_generation_canonical_run"
            ),
            models.UniqueConstraint(
                fields=("tenant", "course"), name="uq_generation_canonical_course"
            ),
            models.CheckConstraint(
                condition=models.Q(reviewed_output_sha256__regex=HASH_PATTERN)
                & models.Q(canonical_content_sha256__regex=HASH_PATTERN)
                & models.Q(canonicalization_sha256__regex=HASH_PATTERN),
                name="ck_generation_canonical_hashes",
            ),
        ]


class CanonicalizationSourceEdge(models.Model):
    objects: models.Manager[CanonicalizationSourceEdge] = models.Manager()
    tenant_id: UUID
    canonicalization_id: UUID
    generation_run_id: UUID
    generated_artifact_id: UUID
    source_version_id: UUID
    source_section_id: UUID
    course_id: UUID
    course_version_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    canonicalization = models.ForeignKey(
        GenerationCanonicalization,
        on_delete=models.RESTRICT,
        related_name="source_edges",
    )
    generation_run = models.ForeignKey(CourseGenerationRun, on_delete=models.RESTRICT)
    generated_artifact = models.OneToOneField(
        GeneratedLessonArtifact,
        on_delete=models.RESTRICT,
        related_name="canonicalization_edge",
    )
    source_version = models.ForeignKey("documents.SourceVersion", on_delete=models.RESTRICT)
    source_section = models.ForeignKey("documents.DocumentSection", on_delete=models.RESTRICT)
    course = models.ForeignKey("courses.Course", on_delete=models.RESTRICT)
    course_version = models.ForeignKey("courses.CourseVersion", on_delete=models.RESTRICT)
    # Immutable acceptance-time identities, validated under row locks by a DB trigger.
    # Current draft rows may be removed by a later authorized curriculum replacement.
    curriculum_section_id = models.UUIDField()
    lesson_id = models.UUIDField()
    content_block_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app"."course_generation_canonicalization_edges'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_canonical_edges_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "canonicalization", "generated_artifact"),
                name="uq_canonical_edges_artifact",
            ),
            models.UniqueConstraint(
                fields=("tenant", "canonicalization", "content_block_id"),
                name="uq_canonical_edges_block",
            ),
        ]

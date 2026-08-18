from __future__ import annotations

import uuid
from uuid import UUID

from django.db import models

COURSE_REVIEWER_POLICIES = ("self_review_allowed", "separate_reviewer_required")
COURSE_VERSION_STATUSES = (
    "draft",
    "under_review",
    "changes_requested",
    "approved",
    "scheduled",
    "published",
    "withdrawn",
    "archived",
)
COURSE_ORIGIN_TYPES = ("manual", "ai_assisted")
COURSE_REVIEW_DECISIONS = ("changes_requested", "approved")
CONTENT_BLOCK_KINDS = ("rich_text",)
HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"


class TimestampedCourseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Course(TimestampedCourseModel):
    objects: models.Manager[Course] = models.Manager()
    tenant_id: UUID
    current_published_version_id: UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.RESTRICT,
        related_name="courses",
    )
    slug = models.SlugField(max_length=63)
    reviewer_policy = models.CharField(max_length=32, default="self_review_allowed")
    current_published_version = models.ForeignKey(
        "CourseVersion",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="published_for_courses",
    )
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."courses'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_courses_tenant_id"),
            models.UniqueConstraint(fields=("tenant", "slug"), name="uq_courses_tenant_slug"),
            models.CheckConstraint(
                condition=models.Q(reviewer_policy__in=COURSE_REVIEWER_POLICIES),
                name="ck_courses_reviewer_policy",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_courses_row_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "current_published_version"),
                name="ix_courses_tenant_current",
            )
        ]


class CourseVersion(TimestampedCourseModel):
    objects: models.Manager[CourseVersion] = models.Manager()
    tenant_id: UUID
    course_id: UUID
    predecessor_version_id: UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    course = models.ForeignKey(Course, on_delete=models.RESTRICT, related_name="versions")
    predecessor_version = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="successor_versions",
    )
    version_number = models.PositiveIntegerField()
    status = models.CharField(max_length=24, default="draft")
    origin_type = models.CharField(max_length=16, default="manual")
    primary_locale = models.CharField(max_length=10)
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=2000)
    content_hash = models.CharField(max_length=71)
    submitted_hash = models.CharField(max_length=71, null=True, blank=True)
    approved_hash = models.CharField(max_length=71, null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."course_versions'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_versions_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "course", "id"),
                name="uq_versions_tenant_course_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "course", "version_number"),
                name="uq_versions_tenant_course_no",
            ),
            models.UniqueConstraint(
                fields=("tenant", "course", "predecessor_version"),
                condition=models.Q(predecessor_version__isnull=False),
                name="uq_versions_one_successor",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=COURSE_VERSION_STATUSES),
                name="ck_versions_status",
            ),
            models.CheckConstraint(
                condition=models.Q(origin_type__in=COURSE_ORIGIN_TYPES),
                name="ck_versions_origin",
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gte=1),
                name="ck_versions_number",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_versions_row_version",
            ),
            models.CheckConstraint(
                condition=models.Q(content_hash__regex=HASH_PATTERN),
                name="ck_versions_content_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(submitted_hash__isnull=True)
                | models.Q(submitted_hash__regex=HASH_PATTERN),
                name="ck_versions_submitted_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(approved_hash__isnull=True)
                | models.Q(approved_hash__regex=HASH_PATTERN),
                name="ck_versions_approved_hash",
            ),
            models.CheckConstraint(
                condition=models.Q(approved_hash__isnull=True)
                | models.Q(submitted_hash__isnull=False),
                name="ck_versions_hash_order",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "course", "-version_number", "-id"),
                name="ix_versions_tenant_course_no",
            ),
            models.Index(
                fields=("tenant", "status", "course"),
                name="ix_versions_tenant_status",
            ),
        ]


class CourseInstructor(TimestampedCourseModel):
    objects: models.Manager[CourseInstructor] = models.Manager()
    tenant_id: UUID
    course_id: UUID
    membership_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="instructors")
    membership = models.ForeignKey(
        "tenancy.TenantMembership",
        on_delete=models.RESTRICT,
        related_name="instructed_courses",
    )
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."course_instructors'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_instructors_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "course", "membership"),
                name="uq_instructors_course_member",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_instructors_row_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "course", "membership"),
                name="ix_instructors_tenant_course",
            )
        ]


class CurriculumSection(TimestampedCourseModel):
    objects: models.Manager[CurriculumSection] = models.Manager()
    tenant_id: UUID
    course_version_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    course_version = models.ForeignKey(
        CourseVersion,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    title = models.CharField(max_length=160)
    position = models.PositiveIntegerField()
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."curriculum_sections'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_sections_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "course_version", "id"),
                name="uq_sections_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "course_version", "position"),
                name="uq_sections_version_position",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="ck_sections_position",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_sections_row_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "course_version", "position"),
                name="ix_sections_tenant_version",
            )
        ]


class Lesson(TimestampedCourseModel):
    objects: models.Manager[Lesson] = models.Manager()
    tenant_id: UUID
    course_version_id: UUID
    section_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    course_version = models.ForeignKey(
        CourseVersion,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    section = models.ForeignKey(
        CurriculumSection,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=160)
    position = models.PositiveIntegerField()
    is_required = models.BooleanField(default=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."lessons'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_lessons_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "course_version", "id"),
                name="uq_lessons_tenant_ver_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "section", "position"),
                name="uq_lessons_section_position",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="ck_lessons_position",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_lessons_row_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "section", "position"),
                name="ix_lessons_tenant_section",
            )
        ]


class LessonContentBlock(TimestampedCourseModel):
    objects: models.Manager[LessonContentBlock] = models.Manager()
    tenant_id: UUID
    course_version_id: UUID
    lesson_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    course_version = models.ForeignKey(
        CourseVersion,
        on_delete=models.CASCADE,
        related_name="content_blocks",
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="content_blocks")
    kind = models.CharField(max_length=16, default="rich_text")
    position = models.PositiveIntegerField()
    document = models.JSONField()
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."lesson_content_blocks'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_blocks_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "lesson", "position"),
                name="uq_blocks_lesson_position",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=CONTENT_BLOCK_KINDS),
                name="ck_blocks_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1),
                name="ck_blocks_position",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_blocks_row_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "lesson", "position"),
                name="ix_blocks_tenant_lesson",
            )
        ]


class CoursePublicationReview(TimestampedCourseModel):
    objects: models.Manager[CoursePublicationReview] = models.Manager()
    tenant_id: UUID
    course_version_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    course_version = models.ForeignKey(
        CourseVersion,
        on_delete=models.RESTRICT,
        related_name="publication_reviews",
    )
    decision = models.CharField(max_length=24)
    reviewed_hash = models.CharField(max_length=71)
    reviewer_id = models.UUIDField()
    self_review = models.BooleanField(default=False)
    reason_codes = models.JSONField(default=list)
    decided_at = models.DateTimeField()

    class Meta:
        db_table = 'app"."course_publication_reviews'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_reviews_tenant_id"),
            models.CheckConstraint(
                condition=models.Q(decision__in=COURSE_REVIEW_DECISIONS),
                name="ck_reviews_decision",
            ),
            models.CheckConstraint(
                condition=models.Q(reviewed_hash__regex=HASH_PATTERN),
                name="ck_reviews_hash",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "course_version", "-decided_at", "-id"),
                name="ix_reviews_tenant_version",
            )
        ]

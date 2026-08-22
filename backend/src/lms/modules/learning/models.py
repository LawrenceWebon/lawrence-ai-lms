from __future__ import annotations

import uuid
from uuid import UUID

from django.db import models
from django.utils import timezone

ENROLLMENT_STATUSES = ("active", "revoked")
ENROLLMENT_ADMISSION_SOURCES = ("manual_assignment",)
COURSE_PROGRESS_STATES = ("not_started", "in_progress", "completed")
LESSON_PROGRESS_STATES = COURSE_PROGRESS_STATES
REASON_CODE_PATTERN = r"^[A-Z][A-Z0-9_]{2,63}$"


class TimestampedLearningModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Enrollment(TimestampedLearningModel):
    objects: models.Manager[Enrollment] = models.Manager()
    tenant_id: UUID
    learner_membership_id: UUID
    course_id: UUID
    course_version_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.RESTRICT,
        related_name="learning_enrollments",
    )
    learner_membership = models.ForeignKey(
        "tenancy.TenantMembership",
        on_delete=models.RESTRICT,
        related_name="learning_enrollments",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.RESTRICT,
        related_name="learning_enrollments",
    )
    course_version = models.ForeignKey(
        "courses.CourseVersion",
        on_delete=models.RESTRICT,
        related_name="learning_enrollments",
    )
    admission_source = models.CharField(max_length=24, default="manual_assignment")
    status = models.CharField(max_length=16, default="active")
    enrolled_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason_code = models.CharField(max_length=64, null=True, blank=True)
    assigned_by_actor_id = models.UUIDField(default=uuid.uuid4)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."enrollments'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_enrollments_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "learner_membership", "course"),
                condition=models.Q(status="active"),
                name="uq_enrollments_active_learner_course",
            ),
            models.CheckConstraint(
                condition=models.Q(admission_source__in=ENROLLMENT_ADMISSION_SOURCES),
                name="ck_enrollments_admission_source",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ENROLLMENT_STATUSES),
                name="ck_enrollments_status",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_enrollments_row_version",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="active",
                        revoked_at__isnull=True,
                        revocation_reason_code__isnull=True,
                    )
                    | (
                        models.Q(status="revoked", revoked_at__isnull=False)
                        & models.Q(revocation_reason_code__regex=REASON_CODE_PATTERN)
                    )
                ),
                name="ck_enrollments_revocation_shape",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "learner_membership", "status", "-enrolled_at", "-id"),
                name="ix_enrollments_dashboard",
            ),
            models.Index(
                fields=("tenant", "course", "status"),
                name="ix_enrollments_course_status",
            ),
        ]


class CourseProgress(TimestampedLearningModel):
    objects: models.Manager[CourseProgress] = models.Manager()
    tenant_id: UUID
    enrollment_id: UUID
    course_version_id: UUID
    resume_lesson_id: UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.RESTRICT,
        related_name="course_progress_rows",
    )
    course_version = models.ForeignKey(
        "courses.CourseVersion",
        on_delete=models.RESTRICT,
        related_name="course_progress_rows",
    )
    state = models.CharField(max_length=16, default="not_started")
    required_lesson_count = models.PositiveIntegerField()
    completed_required_lesson_count = models.PositiveIntegerField(default=0)
    resume_lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="resumed_course_progress_rows",
    )
    last_progress_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."course_progress'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_course_progress_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "enrollment"),
                name="uq_course_progress_enrollment",
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=COURSE_PROGRESS_STATES),
                name="ck_course_progress_state",
            ),
            models.CheckConstraint(
                condition=models.Q(required_lesson_count__gte=1),
                name="ck_course_progress_required_count",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    completed_required_lesson_count__lte=models.F("required_lesson_count")
                ),
                name="ck_course_progress_completed_count",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_course_progress_row_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "enrollment"),
                name="ix_course_progress_enrollment",
            )
        ]


class LessonProgress(TimestampedLearningModel):
    objects: models.Manager[LessonProgress] = models.Manager()
    tenant_id: UUID
    enrollment_id: UUID
    course_version_id: UUID
    lesson_id: UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.RESTRICT)
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.RESTRICT,
        related_name="lesson_progress_rows",
    )
    course_version = models.ForeignKey(
        "courses.CourseVersion",
        on_delete=models.RESTRICT,
        related_name="lesson_progress_rows",
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.RESTRICT,
        related_name="learner_progress_rows",
    )
    state = models.CharField(max_length=16, default="not_started")
    completed_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."lesson_progress'
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "id"),
                name="uq_lesson_progress_tenant_id",
            ),
            models.UniqueConstraint(
                fields=("tenant", "enrollment", "lesson"),
                name="uq_lesson_progress_enrollment_lesson",
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=LESSON_PROGRESS_STATES),
                name="ck_lesson_progress_state",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(state="completed", completed_at__isnull=False)
                    | (~models.Q(state="completed") & models.Q(completed_at__isnull=True))
                ),
                name="ck_lesson_progress_completion_shape",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1),
                name="ck_lesson_progress_row_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "enrollment", "lesson"),
                name="ix_lesson_progress_lookup",
            ),
            models.Index(
                fields=("tenant", "enrollment", "state"),
                name="ix_lesson_progress_state",
            ),
        ]

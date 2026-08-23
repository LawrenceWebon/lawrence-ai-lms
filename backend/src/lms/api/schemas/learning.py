from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lms.api.schemas.courses import RichTextDocument

EnrollmentStatus = Literal["active", "revoked"]
ProgressState = Literal["not_started", "in_progress", "completed"]
ProgressCommandName = Literal["open_lesson", "complete_lesson", "reopen_lesson"]
ContentHash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
Locale = Annotated[str, Field(max_length=10, pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")]
Title = Annotated[str, Field(min_length=1, max_length=160)]
Description = Annotated[str, Field(min_length=1, max_length=2000)]
ReasonCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]
Cursor = Annotated[
    str,
    Field(min_length=16, max_length=1024, pattern=r"^[A-Za-z0-9_-]+$"),
]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timestamp must include a timezone")
    return value


class LearningAdministrationError(Exception):
    """Stable learning failure safe for HTTP and trusted Admin translation."""

    def __init__(
        self,
        *,
        code: str,
        status: int = 500,
        errors: Sequence[dict[str, object]] = (),
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.errors = tuple(errors)


class VerifiedActorResult(Protocol):
    @property
    def principal_id(self) -> UUID: ...


class CreateEnrollmentV1(StrictSchema):
    learner_membership_id: UUID
    course_id: UUID


class RevokeEnrollmentV1(StrictSchema):
    expected_enrollment_row_version: int = Field(ge=1, strict=True)
    reason_code: ReasonCode


class EnrollmentV1(StrictSchema):
    id: UUID
    tenant_id: UUID
    learner_membership_id: UUID
    course_id: UUID
    course_version_id: UUID
    admission_source: Literal["manual_assignment"]
    status: EnrollmentStatus
    enrolled_at: datetime
    revoked_at: datetime | None
    row_version: int = Field(ge=1, strict=True)

    @field_validator("enrolled_at", "revoked_at")
    @classmethod
    def require_timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        return _require_timezone(value)

    @model_validator(mode="after")
    def require_status_timestamp_shape(self) -> EnrollmentV1:
        if (self.status == "active") != (self.revoked_at is None):
            raise ValueError("revoked_at must match enrollment status")
        return self


class CourseProgressV1(StrictSchema):
    state: ProgressState
    required_lesson_count: int = Field(ge=1, le=20_000, strict=True)
    completed_required_lesson_count: int = Field(ge=0, le=20_000, strict=True)
    resume_lesson_id: UUID | None
    row_version: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def require_bounded_completion(self) -> CourseProgressV1:
        if self.completed_required_lesson_count > self.required_lesson_count:
            raise ValueError("completed count cannot exceed required count")
        if (self.state == "completed") != (
            self.completed_required_lesson_count == self.required_lesson_count
        ):
            raise ValueError("course completion state must match required completion count")
        return self


class DashboardCardV1(StrictSchema):
    enrollment_id: UUID
    course_id: UUID
    course_version_id: UUID
    course_version_number: int = Field(ge=1, strict=True)
    primary_locale: Locale
    title: Title
    description: Description
    content_hash: ContentHash
    enrolled_at: datetime
    progress: CourseProgressV1

    @field_validator("enrolled_at")
    @classmethod
    def require_enrolled_at_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]


class LearnerDashboardV1(StrictSchema):
    tenant_id: UUID
    items: list[DashboardCardV1] = Field(max_length=50)
    next_cursor: Cursor | None


class OutlineLessonV1(StrictSchema):
    id: UUID
    title: Title
    position: int = Field(ge=1, strict=True)
    is_required: bool = Field(strict=True)
    progress_state: ProgressState


class OutlineSectionV1(StrictSchema):
    id: UUID
    title: Title
    position: int = Field(ge=1, strict=True)
    lessons: list[OutlineLessonV1] = Field(min_length=1, max_length=200)


class PlaybackSnapshotV1(StrictSchema):
    tenant_id: UUID
    enrollment_id: UUID
    course_id: UUID
    course_version_id: UUID
    course_version_number: int = Field(ge=1, strict=True)
    primary_locale: Locale
    title: Title
    description: Description
    content_hash: ContentHash
    sections: list[OutlineSectionV1] = Field(min_length=1, max_length=100)
    progress: CourseProgressV1


class LessonContentBlockV1(StrictSchema):
    id: UUID
    kind: Literal["rich_text"]
    position: int = Field(ge=1, strict=True)
    document: RichTextDocument


class LessonDetailV1(StrictSchema):
    id: UUID
    section_id: UUID
    title: Title
    position: int = Field(ge=1, strict=True)
    is_required: bool = Field(strict=True)
    progress_state: ProgressState
    content_blocks: list[LessonContentBlockV1] = Field(min_length=1, max_length=100)


class LessonPlaybackV1(StrictSchema):
    tenant_id: UUID
    enrollment_id: UUID
    course_version_id: UUID
    primary_locale: Locale
    content_hash: ContentHash
    lesson: LessonDetailV1
    previous_lesson_id: UUID | None
    next_lesson_id: UUID | None
    progress: CourseProgressV1


class ProgressCommandV1(StrictSchema):
    command: ProgressCommandName
    lesson_id: UUID
    expected_progress_row_version: int = Field(ge=0, strict=True)


class ProgressResultV1(StrictSchema):
    tenant_id: UUID
    enrollment_id: UUID
    course_version_id: UUID
    lesson_id: UUID
    lesson_state: ProgressState
    course_state: ProgressState
    required_lesson_count: int = Field(ge=1, le=20_000, strict=True)
    completed_required_lesson_count: int = Field(ge=0, le=20_000, strict=True)
    resume_lesson_id: UUID | None
    progress_row_version: int = Field(ge=1, strict=True)
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def require_updated_at_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]

    @model_validator(mode="after")
    def require_course_completion_shape(self) -> ProgressResultV1:
        if self.completed_required_lesson_count > self.required_lesson_count:
            raise ValueError("completed count cannot exceed required count")
        if (self.course_state == "completed") != (
            self.completed_required_lesson_count == self.required_lesson_count
        ):
            raise ValueError("course state must match required completion count")
        return self


class LearningServiceV1(Protocol):
    def create_enrollment(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateEnrollmentV1,
        idempotency_key: str,
    ) -> object: ...

    def revoke_enrollment(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: RevokeEnrollmentV1,
        idempotency_key: str,
    ) -> object: ...

    def list_learner_courses(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> object: ...

    def get_learner_playback(
        self, *, actor_id: UUID, tenant_id: UUID, enrollment_id: UUID
    ) -> object: ...

    def get_learner_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        lesson_id: UUID,
    ) -> object: ...

    def open_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
    ) -> object: ...

    def complete_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
    ) -> object: ...

    def reopen_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
    ) -> object: ...

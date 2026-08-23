from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

type JsonPrimitive = str | int | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class EnrollmentStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class LessonProgressState(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CourseProgressState(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ProgressCommandName(StrEnum):
    OPEN_LESSON = "open_lesson"
    COMPLETE_LESSON = "complete_lesson"
    REOPEN_LESSON = "reopen_lesson"


@dataclass(frozen=True, slots=True)
class PublishedContentBlock:
    id: UUID
    kind: str
    position: int
    document: JsonObject


@dataclass(frozen=True, slots=True)
class PublishedLesson:
    id: UUID
    section_id: UUID
    title: str
    position: int
    is_required: bool
    content_blocks: tuple[PublishedContentBlock, ...]


@dataclass(frozen=True, slots=True)
class PublishedSection:
    id: UUID
    title: str
    position: int
    lessons: tuple[PublishedLesson, ...]


@dataclass(frozen=True, slots=True)
class PublishedCourse:
    tenant_id: UUID
    course_id: UUID
    course_version_id: UUID
    course_version_number: int
    primary_locale: str
    title: str
    description: str
    content_hash: str
    sections: tuple[PublishedSection, ...]


@dataclass(frozen=True, slots=True)
class AuthorizedActor:
    principal_id: UUID
    tenant_id: UUID
    membership_id: UUID | None
    permissions: frozenset[str]


@dataclass(frozen=True, slots=True)
class Enrollment:
    id: UUID
    tenant_id: UUID
    learner_membership_id: UUID
    course_id: UUID
    course_version_id: UUID
    admission_source: str
    status: EnrollmentStatus
    enrolled_at: datetime
    revoked_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class CourseProgress:
    state: CourseProgressState
    required_lesson_count: int
    completed_required_lesson_count: int
    resume_lesson_id: UUID | None
    row_version: int


@dataclass(frozen=True, slots=True)
class DashboardCard:
    enrollment_id: UUID
    course_id: UUID
    course_version_id: UUID
    course_version_number: int
    primary_locale: str
    title: str
    description: str
    content_hash: str
    enrolled_at: datetime
    progress: CourseProgress


@dataclass(frozen=True, slots=True)
class LearnerDashboard:
    tenant_id: UUID
    items: tuple[DashboardCard, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class OutlineLesson:
    id: UUID
    title: str
    position: int
    is_required: bool
    progress_state: LessonProgressState


@dataclass(frozen=True, slots=True)
class OutlineSection:
    id: UUID
    title: str
    position: int
    lessons: tuple[OutlineLesson, ...]


@dataclass(frozen=True, slots=True)
class PlaybackSnapshot:
    tenant_id: UUID
    enrollment_id: UUID
    course_id: UUID
    course_version_id: UUID
    course_version_number: int
    primary_locale: str
    title: str
    description: str
    content_hash: str
    sections: tuple[OutlineSection, ...]
    progress: CourseProgress


@dataclass(frozen=True, slots=True)
class LessonContentBlock:
    id: UUID
    kind: str
    position: int
    document: JsonObject


@dataclass(frozen=True, slots=True)
class LessonDetail:
    id: UUID
    section_id: UUID
    title: str
    position: int
    is_required: bool
    progress_state: LessonProgressState
    content_blocks: tuple[LessonContentBlock, ...]


@dataclass(frozen=True, slots=True)
class LessonPlayback:
    tenant_id: UUID
    enrollment_id: UUID
    course_version_id: UUID
    primary_locale: str
    content_hash: str
    lesson: LessonDetail
    previous_lesson_id: UUID | None
    next_lesson_id: UUID | None
    progress: CourseProgress


@dataclass(frozen=True, slots=True)
class ProgressCommand:
    command: ProgressCommandName
    lesson_id: UUID
    expected_progress_row_version: int


@dataclass(frozen=True, slots=True)
class ProgressResult:
    tenant_id: UUID
    enrollment_id: UUID
    course_version_id: UUID
    lesson_id: UUID
    lesson_state: LessonProgressState
    course_state: CourseProgressState
    required_lesson_count: int
    completed_required_lesson_count: int
    resume_lesson_id: UUID | None
    progress_row_version: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProgressMutation:
    result: ProgressResult
    previous_lesson_state: LessonProgressState
    previous_course_state: CourseProgressState
    previous_progress_row_version: int


type IdempotentResponse = Enrollment | ProgressResult


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    request_hash: str
    created: bool
    response: IdempotentResponse | None


@dataclass(frozen=True, slots=True)
class LearningFact:
    id: UUID
    tenant_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    aggregate_version: int
    actor_id: UUID
    payload: JsonObject
    occurred_at: datetime

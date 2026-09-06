from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

SNAPSHOT_SCHEMA_URI = "https://contracts.ai-lms.local/f002/canonical-course.v1.schema.json"

type JsonPrimitive = str | int | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class CourseStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


class OriginType(StrEnum):
    MANUAL = "manual"
    AI_ASSISTED = "ai_assisted"


class ReviewerPolicy(StrEnum):
    SELF_REVIEW_ALLOWED = "self_review_allowed"
    SEPARATE_REVIEWER_REQUIRED = "separate_reviewer_required"


class PrincipalType(StrEnum):
    USER = "user"
    AI = "ai"
    WORKER = "worker"
    SERVICE = "service"
    PROVIDER = "provider"
    PRIVILEGED_OPERATOR = "privileged_operator"


class Transition(StrEnum):
    SUBMIT_REVIEW = "submit_review"
    REQUEST_CHANGES = "request_changes"
    APPROVE = "approve"
    PUBLISH = "publish"
    WITHDRAW = "withdraw"
    ARCHIVE = "archive"


class ReviewDecision(StrEnum):
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"


@dataclass(frozen=True, slots=True)
class Course:
    id: UUID
    tenant_id: UUID
    slug: str
    reviewer_policy: ReviewerPolicy
    current_published_version_id: UUID | None
    instructor_membership_ids: tuple[UUID, ...]
    row_version: int


@dataclass(frozen=True, slots=True)
class CourseVersion:
    id: UUID
    tenant_id: UUID
    course_id: UUID
    predecessor_version_id: UUID | None
    version_number: int
    status: CourseStatus
    origin_type: OriginType
    primary_locale: str
    title: str
    description: str
    content_hash: str
    submitted_hash: str | None
    approved_hash: str | None
    row_version: int


@dataclass(frozen=True, slots=True)
class RichTextBlock:
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    lesson_id: UUID
    kind: str
    position: int
    row_version: int
    document: JsonObject


@dataclass(frozen=True, slots=True)
class Lesson:
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    section_id: UUID
    title: str
    position: int
    is_required: bool
    row_version: int
    content_blocks: tuple[RichTextBlock, ...]


@dataclass(frozen=True, slots=True)
class CurriculumSection:
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    title: str
    position: int
    row_version: int
    lessons: tuple[Lesson, ...]


@dataclass(frozen=True, slots=True)
class CourseReview:
    id: UUID
    tenant_id: UUID
    course_version_id: UUID
    decision: ReviewDecision
    reviewed_hash: str
    reviewer_id: UUID
    self_review: bool
    reason_codes: tuple[str, ...]
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class CourseSnapshot:
    course: Course
    version: CourseVersion
    sections: tuple[CurriculumSection, ...]
    latest_review: CourseReview | None
    schema_uri: str = SNAPSHOT_SCHEMA_URI


@dataclass(frozen=True, slots=True)
class CourseAggregate:
    course: Course
    version: CourseVersion
    sections: tuple[CurriculumSection, ...]
    latest_review: CourseReview | None
    submitted_by_actor_id: UUID | None

    def snapshot(self) -> CourseSnapshot:
        return CourseSnapshot(
            course=self.course,
            version=self.version,
            sections=self.sections,
            latest_review=self.latest_review,
        )


@dataclass(frozen=True, slots=True)
class AuthorizedActor:
    principal_id: UUID
    tenant_id: UUID
    membership_id: UUID | None
    principal_type: PrincipalType
    permissions: frozenset[str]


@dataclass(frozen=True, slots=True)
class CreateCourseCommand:
    slug: str
    primary_locale: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class CreateAiAssistedDraftCommand:
    slug: str
    primary_locale: str
    title: str
    description: str
    sections: tuple[CurriculumSectionInput, ...]


@dataclass(frozen=True, slots=True)
class UpdateCourseVersionCommand:
    expected_version_row_version: int
    primary_locale: str | None = None
    title: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ContentBlockInput:
    kind: str
    position: int
    document: JsonObject
    id: UUID | None = None
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class LessonInput:
    title: str
    position: int
    is_required: bool
    content_blocks: tuple[ContentBlockInput, ...]
    id: UUID | None = None
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class CurriculumSectionInput:
    title: str
    position: int
    lessons: tuple[LessonInput, ...]
    id: UUID | None = None
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class ReplaceCurriculumCommand:
    expected_version_row_version: int
    sections: tuple[CurriculumSectionInput, ...]


@dataclass(frozen=True, slots=True)
class TransitionCourseVersionCommand:
    transition: Transition
    expected_version_row_version: int
    expected_content_hash: str
    expected_course_row_version: int | None = None
    reason_code: str | None = None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreateSuccessorDraftCommand:
    expected_course_row_version: int
    expected_source_version_row_version: int
    expected_source_content_hash: str


@dataclass(frozen=True, slots=True)
class CourseVersionSummary:
    id: UUID
    tenant_id: UUID
    course_id: UUID
    predecessor_version_id: UUID | None
    version_number: int
    status: CourseStatus
    title: str
    content_hash: str
    row_version: int
    is_current_published: bool


@dataclass(frozen=True, slots=True)
class CourseVersionHistory:
    tenant_id: UUID
    course_id: UUID
    current_published_version_id: UUID | None
    versions: tuple[CourseVersionSummary, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class SuccessorDraftResult:
    source_version_id: UUID
    successor_version_id: UUID
    snapshot: CourseSnapshot


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    target_status: CourseStatus
    required_permission: str
    self_review: bool


@dataclass(frozen=True, slots=True)
class AuditFact:
    id: UUID
    tenant_id: UUID
    event_type: str
    actor_id: UUID
    course_id: UUID
    course_version_id: UUID
    payload: JsonObject
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class OutboxFact:
    id: UUID
    tenant_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    actor_id: UUID
    payload: JsonObject
    recorded_at: datetime


type IdempotentResponse = CourseSnapshot | SuccessorDraftResult


@dataclass(frozen=True, slots=True)
class IdempotencyScope:
    tenant_id: UUID
    actor_id: UUID
    operation: str
    key: str


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    request_hash: str
    created: bool
    response: IdempotentResponse | None

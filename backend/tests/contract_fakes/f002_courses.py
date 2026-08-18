from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from lms.modules.courses.errors import CourseLifecycleError
from lms.modules.courses.policies import (
    PERMISSION_COURSES_DRAFTS_WRITE,
    PERMISSION_COURSES_PUBLISH,
    PERMISSION_COURSES_READ,
    PERMISSION_COURSES_REVIEW,
)
from lms.modules.courses.services import CourseLifecycleService
from lms.modules.courses.types import (
    AuditFact,
    AuthorizedActor,
    ContentBlockInput,
    Course,
    CourseAggregate,
    CourseReview,
    CourseSnapshot,
    CourseStatus,
    CourseVersion,
    CourseVersionHistory,
    CourseVersionSummary,
    CurriculumSection,
    CurriculumSectionInput,
    IdempotencyRecord,
    IdempotencyScope,
    Lesson,
    LessonInput,
    OriginType,
    OutboxFact,
    PrincipalType,
    ReplaceCurriculumCommand,
    ReviewDecision,
    ReviewerPolicy,
    RichTextBlock,
    SuccessorDraftResult,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_EXAMPLE = REPO_ROOT / "contracts/f002/canonical-course.v1.example.json"

ALPHA_TENANT_ID = UUID("00000000-0000-4000-8000-0000000000a1")
BETA_TENANT_ID = UUID("00000000-0000-4000-8000-0000000000b1")
ALPHA_AUTHOR_ID = UUID("00000000-0000-4000-8000-000000000101")
ALPHA_REVIEWER_ID = UUID("00000000-0000-4000-8000-000000000102")
ALPHA_SERVICE_ID = UUID("00000000-0000-4000-8000-000000000106")
ALPHA_AUTHOR_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000301")
ALPHA_REVIEWER_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000302")
ALPHA_SERVICE_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000306")
BETA_AUTHOR_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000401")

ALL_COURSE_PERMISSIONS = frozenset(
    {
        PERMISSION_COURSES_READ,
        PERMISSION_COURSES_DRAFTS_WRITE,
        PERMISSION_COURSES_REVIEW,
        PERMISSION_COURSES_PUBLISH,
    }
)


def _uuid(value: object) -> UUID:
    return UUID(str(value))


def snapshot_from_contract() -> CourseSnapshot:
    raw = json.loads(SNAPSHOT_EXAMPLE.read_text(encoding="utf-8"))
    course_raw = raw["course"]
    version_raw = raw["version"]
    course = Course(
        id=_uuid(course_raw["id"]),
        tenant_id=_uuid(course_raw["tenant_id"]),
        slug=course_raw["slug"],
        reviewer_policy=ReviewerPolicy(course_raw["reviewer_policy"]),
        current_published_version_id=(
            _uuid(course_raw["current_published_version_id"])
            if course_raw["current_published_version_id"] is not None
            else None
        ),
        instructor_membership_ids=tuple(
            _uuid(value) for value in course_raw["instructor_membership_ids"]
        ),
        row_version=course_raw["row_version"],
    )
    version = CourseVersion(
        id=_uuid(version_raw["id"]),
        tenant_id=_uuid(version_raw["tenant_id"]),
        course_id=_uuid(version_raw["course_id"]),
        predecessor_version_id=(
            _uuid(version_raw["predecessor_version_id"])
            if version_raw["predecessor_version_id"] is not None
            else None
        ),
        version_number=version_raw["version_number"],
        status=CourseStatus(version_raw["status"]),
        origin_type=OriginType(version_raw["origin_type"]),
        primary_locale=version_raw["primary_locale"],
        title=version_raw["title"],
        description=version_raw["description"],
        content_hash=version_raw["content_hash"],
        submitted_hash=version_raw["submitted_hash"],
        approved_hash=version_raw["approved_hash"],
        row_version=version_raw["row_version"],
    )
    sections: list[CurriculumSection] = []
    for section_raw in raw["sections"]:
        lessons: list[Lesson] = []
        for lesson_raw in section_raw["lessons"]:
            blocks = tuple(
                RichTextBlock(
                    id=_uuid(block_raw["id"]),
                    tenant_id=_uuid(block_raw["tenant_id"]),
                    course_version_id=_uuid(block_raw["course_version_id"]),
                    lesson_id=_uuid(block_raw["lesson_id"]),
                    kind=block_raw["kind"],
                    position=block_raw["position"],
                    row_version=block_raw["row_version"],
                    document=deepcopy(block_raw["document"]),
                )
                for block_raw in lesson_raw["content_blocks"]
            )
            lessons.append(
                Lesson(
                    id=_uuid(lesson_raw["id"]),
                    tenant_id=_uuid(lesson_raw["tenant_id"]),
                    course_version_id=_uuid(lesson_raw["course_version_id"]),
                    section_id=_uuid(lesson_raw["section_id"]),
                    title=lesson_raw["title"],
                    position=lesson_raw["position"],
                    is_required=lesson_raw["is_required"],
                    row_version=lesson_raw["row_version"],
                    content_blocks=blocks,
                )
            )
        sections.append(
            CurriculumSection(
                id=_uuid(section_raw["id"]),
                tenant_id=_uuid(section_raw["tenant_id"]),
                course_version_id=_uuid(section_raw["course_version_id"]),
                title=section_raw["title"],
                position=section_raw["position"],
                row_version=section_raw["row_version"],
                lessons=tuple(lessons),
            )
        )
    review_raw = raw["latest_review"]
    review = None
    if review_raw is not None:
        review = CourseReview(
            id=_uuid(review_raw["id"]),
            tenant_id=_uuid(review_raw["tenant_id"]),
            course_version_id=_uuid(review_raw["course_version_id"]),
            decision=ReviewDecision(review_raw["decision"]),
            reviewed_hash=review_raw["reviewed_hash"],
            reviewer_id=_uuid(review_raw["reviewer_id"]),
            self_review=review_raw["self_review"],
            reason_codes=tuple(review_raw["reason_codes"]),
            decided_at=datetime.fromisoformat(review_raw["decided_at"]),
        )
    return CourseSnapshot(course, version, tuple(sections), review)


def aggregate_from_contract(
    *, status: str = "draft", submitted_by_actor_id: UUID | None = None
) -> CourseAggregate:
    snapshot = snapshot_from_contract()
    return CourseAggregate(
        course=snapshot.course,
        version=replace(snapshot.version, status=CourseStatus(status)),
        sections=snapshot.sections,
        latest_review=snapshot.latest_review,
        submitted_by_actor_id=submitted_by_actor_id,
    )


def actor(
    *,
    permissions: frozenset[str] = ALL_COURSE_PERMISSIONS,
    principal_type: PrincipalType = PrincipalType.USER,
    reviewer: bool = False,
) -> AuthorizedActor:
    return AuthorizedActor(
        principal_id=ALPHA_REVIEWER_ID if reviewer else ALPHA_AUTHOR_ID,
        tenant_id=ALPHA_TENANT_ID,
        membership_id=(ALPHA_REVIEWER_MEMBERSHIP_ID if reviewer else ALPHA_AUTHOR_MEMBERSHIP_ID),
        principal_type=principal_type,
        permissions=permissions,
    )


def new_curriculum_command(
    *,
    expected_version_row_version: int = 1,
    section_count: int = 1,
    text: str = "This is synthetic replacement content.",
) -> ReplaceCurriculumCommand:
    sections = tuple(
        CurriculumSectionInput(
            title=f"Synthetic section {index + 1}",
            position=index + 1,
            lessons=(
                LessonInput(
                    title=f"Synthetic lesson {index + 1}",
                    position=1,
                    is_required=True,
                    content_blocks=(
                        ContentBlockInput(
                            kind="rich_text",
                            position=1,
                            document={
                                "type": "document",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": text, "marks": []}],
                                    }
                                ],
                            },
                        ),
                    ),
                ),
            ),
        )
        for index in range(section_count)
    )
    return ReplaceCurriculumCommand(expected_version_row_version, sections)


class SequenceUUIDFactory:
    def __init__(self) -> None:
        self._next = int("10000000000040008000000000000000", 16)

    def new_uuid(self) -> UUID:
        value = UUID(int=self._next)
        self._next += 1
        return value


class AdvancingClock:
    def __init__(self) -> None:
        self._current = datetime(2026, 8, 18, tzinfo=UTC)

    def now(self) -> datetime:
        result = self._current
        self._current += timedelta(microseconds=1)
        return result


class InMemoryAuthorization:
    def __init__(self) -> None:
        self._actors: dict[tuple[UUID, UUID], AuthorizedActor] = {}
        self._denied_courses: set[tuple[UUID, UUID, UUID]] = set()

    def add(self, value: AuthorizedActor) -> None:
        self._actors[(value.principal_id, value.tenant_id)] = value

    def authorize(self, *, actor_id: UUID, tenant_id: UUID) -> AuthorizedActor:
        value = self._actors.get((actor_id, tenant_id))
        if value is None:
            raise CourseLifecycleError("TENANT_ACCESS_INACTIVE")
        return value

    def actor_for(self, actor_id: UUID, tenant_id: UUID) -> AuthorizedActor:
        return self.authorize(actor_id=actor_id, tenant_id=tenant_id)

    def deny_course(self, actor_id: UUID, tenant_id: UUID, course_id: UUID) -> None:
        self._denied_courses.add((actor_id, tenant_id, course_id))

    def authorize_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        permission: str,
    ) -> AuthorizedActor:
        value = self.authorize(actor_id=actor_id, tenant_id=tenant_id)
        if (actor_id, tenant_id, course_id) in self._denied_courses:
            raise CourseLifecycleError("RESOURCE_NOT_FOUND")
        if permission not in value.permissions:
            raise CourseLifecycleError("COURSE_PERMISSION_DENIED")
        return value


class StaticReviewerPolicies:
    def __init__(self, value: ReviewerPolicy) -> None:
        self.value = value

    def reviewer_policy_for_new_course(self, *, tenant_id: UUID) -> ReviewerPolicy:
        assert tenant_id in {ALPHA_TENANT_ID, BETA_TENANT_ID}
        return self.value


class InMemoryCourseRepository:
    def __init__(self) -> None:
        self._courses: dict[tuple[UUID, UUID], Course] = {}
        self._versions: dict[tuple[UUID, UUID, UUID], CourseAggregate] = {}
        self._reviews: dict[tuple[UUID, UUID, UUID], list[CourseReview]] = {}

    @property
    def version_count(self) -> int:
        return len(self._versions)

    def snapshot_state(self) -> object:
        return deepcopy((self._courses, self._versions, self._reviews))

    def restore_state(self, state: object) -> None:
        self._courses, self._versions, self._reviews = deepcopy(state)

    def create(self, aggregate: CourseAggregate) -> CourseAggregate:
        course_key = (aggregate.course.tenant_id, aggregate.course.id)
        version_key = (*course_key, aggregate.version.id)
        if course_key in self._courses or version_key in self._versions:
            raise CourseLifecycleError("VERSION_CONFLICT")
        if any(
            course.tenant_id == aggregate.course.tenant_id and course.slug == aggregate.course.slug
            for course in self._courses.values()
        ):
            raise CourseLifecycleError("VERSION_CONFLICT")
        self._courses[course_key] = deepcopy(aggregate.course)
        self._versions[version_key] = deepcopy(aggregate)
        self._reviews[version_key] = []
        return deepcopy(aggregate)

    def load(self, *, tenant_id: UUID, course_id: UUID, version_id: UUID) -> CourseAggregate | None:
        course = self._courses.get((tenant_id, course_id))
        aggregate = self._versions.get((tenant_id, course_id, version_id))
        if course is None or aggregate is None:
            return None
        reviews = self._reviews.get((tenant_id, course_id, version_id), [])
        latest_review = reviews[-1] if reviews else None
        return deepcopy(replace(aggregate, course=course, latest_review=latest_review))

    def load_required(self, tenant_id: UUID, course_id: UUID, version_id: UUID) -> CourseAggregate:
        result = self.load(tenant_id=tenant_id, course_id=course_id, version_id=version_id)
        assert result is not None
        return result

    def reviews_for(
        self, tenant_id: UUID, course_id: UUID, version_id: UUID
    ) -> tuple[CourseReview, ...]:
        return tuple(deepcopy(self._reviews.get((tenant_id, course_id, version_id), [])))

    def save(
        self,
        aggregate: CourseAggregate,
        *,
        expected_version_row_version: int,
        expected_course_row_version: int | None,
    ) -> CourseAggregate:
        current = self.load(
            tenant_id=aggregate.course.tenant_id,
            course_id=aggregate.course.id,
            version_id=aggregate.version.id,
        )
        if current is None:
            raise CourseLifecycleError("RESOURCE_NOT_FOUND")
        if current.version.row_version != expected_version_row_version:
            raise CourseLifecycleError("VERSION_CONFLICT")
        if (
            expected_course_row_version is not None
            and current.course.row_version != expected_course_row_version
        ):
            raise CourseLifecycleError("VERSION_CONFLICT")
        course_key = (aggregate.course.tenant_id, aggregate.course.id)
        version_key = (*course_key, aggregate.version.id)
        if aggregate.latest_review is not None:
            reviews = self._reviews.setdefault(version_key, [])
            existing = next(
                (review for review in reviews if review.id == aggregate.latest_review.id),
                None,
            )
            if existing is not None and existing != aggregate.latest_review:
                raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
            if existing is None:
                reviews.append(deepcopy(aggregate.latest_review))
        self._courses[course_key] = deepcopy(aggregate.course)
        self._versions[version_key] = deepcopy(aggregate)
        return deepcopy(aggregate)

    def list_versions(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> CourseVersionHistory | None:
        course = self._courses.get((tenant_id, course_id))
        if course is None:
            return None
        aggregates = sorted(
            (
                aggregate
                for (row_tenant, row_course, _), aggregate in self._versions.items()
                if row_tenant == tenant_id and row_course == course_id
            ),
            key=lambda item: (item.version.version_number, item.version.id),
            reverse=True,
        )
        offset = int(cursor) if cursor is not None and cursor.isdigit() else 0
        page = aggregates[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(aggregates) else None
        summaries = tuple(
            CourseVersionSummary(
                id=item.version.id,
                tenant_id=tenant_id,
                course_id=course_id,
                predecessor_version_id=item.version.predecessor_version_id,
                version_number=item.version.version_number,
                status=item.version.status,
                title=item.version.title,
                content_hash=item.version.content_hash,
                row_version=item.version.row_version,
                is_current_published=(course.current_published_version_id == item.version.id),
            )
            for item in page
        )
        return CourseVersionHistory(
            tenant_id,
            course_id,
            course.current_published_version_id,
            summaries,
            next_cursor,
        )

    def find_successor(
        self, *, tenant_id: UUID, course_id: UUID, source_version_id: UUID
    ) -> CourseAggregate | None:
        matches = [
            aggregate
            for (row_tenant, row_course, _), aggregate in self._versions.items()
            if row_tenant == tenant_id
            and row_course == course_id
            and aggregate.version.predecessor_version_id == source_version_id
        ]
        if len(matches) > 1:
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        if not matches:
            return None
        return self.load(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=matches[0].version.id,
        )

    def next_version_number(self, *, tenant_id: UUID, course_id: UUID) -> int:
        numbers = [
            aggregate.version.version_number
            for (row_tenant, row_course, _), aggregate in self._versions.items()
            if row_tenant == tenant_id and row_course == course_id
        ]
        if not numbers:
            raise CourseLifecycleError("RESOURCE_NOT_FOUND")
        return max(numbers) + 1

    def add_successor(
        self,
        *,
        source_version_id: UUID,
        successor: CourseAggregate,
        expected_course_row_version: int,
        expected_source_version_row_version: int,
    ) -> CourseAggregate:
        source = self.load(
            tenant_id=successor.course.tenant_id,
            course_id=successor.course.id,
            version_id=source_version_id,
        )
        if source is None:
            raise CourseLifecycleError("RESOURCE_NOT_FOUND")
        if (
            source.course.row_version != expected_course_row_version
            or source.version.row_version != expected_source_version_row_version
        ):
            raise CourseLifecycleError("VERSION_CONFLICT")
        if (
            self.find_successor(
                tenant_id=successor.course.tenant_id,
                course_id=successor.course.id,
                source_version_id=source_version_id,
            )
            is not None
        ):
            raise CourseLifecycleError("VERSION_CONFLICT")
        course_key = (successor.course.tenant_id, successor.course.id)
        version_key = (*course_key, successor.version.id)
        self._courses[course_key] = deepcopy(successor.course)
        self._versions[version_key] = deepcopy(successor)
        self._reviews[version_key] = []
        return deepcopy(successor)


class InMemoryIdempotency:
    def __init__(self) -> None:
        self._records: dict[
            IdempotencyScope, tuple[str, CourseSnapshot | SuccessorDraftResult | None]
        ] = {}

    def snapshot_state(self) -> object:
        return deepcopy(self._records)

    def restore_state(self, state: object) -> None:
        self._records = deepcopy(state)

    def reserve(self, scope: IdempotencyScope, request_hash: str) -> IdempotencyRecord:
        existing = self._records.get(scope)
        if existing is None:
            self._records[scope] = (request_hash, None)
            return IdempotencyRecord(request_hash, True, None)
        stored_hash, response = existing
        return IdempotencyRecord(stored_hash, False, deepcopy(response))

    def complete(
        self,
        scope: IdempotencyScope,
        request_hash: str,
        response: CourseSnapshot | SuccessorDraftResult,
    ) -> None:
        existing = self._records.get(scope)
        if existing is None or existing[0] != request_hash:
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        self._records[scope] = (request_hash, deepcopy(response))

    def is_completed(self, key: str) -> bool:
        return any(
            scope.key == key and response is not None
            for scope, (_, response) in self._records.items()
        )


class InMemoryFacts:
    def __init__(self) -> None:
        self.audit: list[AuditFact] = []
        self.outbox: list[OutboxFact] = []
        self.fail_event_type: str | None = None

    def snapshot_state(self) -> object:
        return deepcopy((self.audit, self.outbox))

    def restore_state(self, state: object) -> None:
        self.audit, self.outbox = deepcopy(state)

    def append(self, audit: AuditFact, outbox: OutboxFact) -> None:
        self.audit.append(deepcopy(audit))
        if outbox.event_type == self.fail_event_type:
            raise RuntimeError("injected fact failure")
        self.outbox.append(deepcopy(outbox))


class InMemoryUnitOfWork:
    def __init__(self, *participants: object) -> None:
        self._participants = participants
        self._lock = threading.RLock()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            states = [participant.snapshot_state() for participant in self._participants]
            try:
                yield
            except BaseException:
                for participant, state in zip(self._participants, states, strict=True):
                    participant.restore_state(state)
                raise


class CourseServiceHarness:
    def __init__(
        self,
        *,
        reviewer_policy: ReviewerPolicy = ReviewerPolicy.SELF_REVIEW_ALLOWED,
    ) -> None:
        self.author_membership_id = ALPHA_AUTHOR_MEMBERSHIP_ID
        self.ids = SequenceUUIDFactory()
        self.clock = AdvancingClock()
        self.authorization = InMemoryAuthorization()
        self.authorization.add(actor())
        self.authorization.add(
            AuthorizedActor(
                ALPHA_REVIEWER_ID,
                ALPHA_TENANT_ID,
                ALPHA_REVIEWER_MEMBERSHIP_ID,
                PrincipalType.USER,
                frozenset({PERMISSION_COURSES_READ, PERMISSION_COURSES_REVIEW}),
            )
        )
        self.authorization.add(
            AuthorizedActor(
                ALPHA_SERVICE_ID,
                ALPHA_TENANT_ID,
                ALPHA_SERVICE_MEMBERSHIP_ID,
                PrincipalType.SERVICE,
                ALL_COURSE_PERMISSIONS,
            )
        )
        self.authorization.add(
            AuthorizedActor(
                ALPHA_AUTHOR_ID,
                BETA_TENANT_ID,
                BETA_AUTHOR_MEMBERSHIP_ID,
                PrincipalType.USER,
                ALL_COURSE_PERMISSIONS,
            )
        )
        self.reviewer_policies = StaticReviewerPolicies(reviewer_policy)
        self.repository = InMemoryCourseRepository()
        self.idempotency = InMemoryIdempotency()
        self.facts = InMemoryFacts()
        self.unit_of_work = InMemoryUnitOfWork(
            self.repository,
            self.idempotency,
            self.facts,
        )
        self.service = CourseLifecycleService(
            authorization=self.authorization,
            reviewer_policies=self.reviewer_policies,
            repository=self.repository,
            idempotency=self.idempotency,
            facts=self.facts,
            unit_of_work=self.unit_of_work,
            ids=self.ids,
            clock=self.clock,
        )

    def preserve_curriculum(
        self,
        snapshot: CourseSnapshot,
        *,
        lesson_title: str | None = None,
    ) -> ReplaceCurriculumCommand:
        sections = tuple(
            CurriculumSectionInput(
                id=section.id,
                expected_row_version=section.row_version,
                title=section.title,
                position=section.position,
                lessons=tuple(
                    LessonInput(
                        id=lesson.id,
                        expected_row_version=lesson.row_version,
                        title=lesson_title or lesson.title,
                        position=lesson.position,
                        is_required=lesson.is_required,
                        content_blocks=tuple(
                            ContentBlockInput(
                                id=block.id,
                                expected_row_version=block.row_version,
                                kind=block.kind,
                                position=block.position,
                                document=deepcopy(block.document),
                            )
                            for block in lesson.content_blocks
                        ),
                    )
                    for lesson in section.lessons
                ),
            )
            for section in snapshot.sections
        )
        return ReplaceCurriculumCommand(snapshot.version.row_version, sections)

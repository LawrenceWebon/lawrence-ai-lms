from __future__ import annotations

from contextlib import AbstractContextManager
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from .errors import CourseLifecycleError, FieldError, validation_failed
from .hashing import canonical_content_hash, canonical_request_hash
from .policies import (
    PERMISSION_COURSES_DRAFTS_WRITE,
    PERMISSION_COURSES_READ,
    authorize_transition,
    require_human,
    require_mutable_version,
    require_permission,
    transition_permission,
    transition_requires_human,
)
from .types import (
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
    CreateCourseCommand,
    CreateSuccessorDraftCommand,
    CurriculumSection,
    CurriculumSectionInput,
    IdempotencyRecord,
    IdempotencyScope,
    JsonObject,
    Lesson,
    LessonInput,
    OriginType,
    OutboxFact,
    ReplaceCurriculumCommand,
    ReviewDecision,
    ReviewerPolicy,
    RichTextBlock,
    SuccessorDraftResult,
    Transition,
    TransitionCourseVersionCommand,
    UpdateCourseVersionCommand,
)
from .validation import (
    validate_complete_course,
    validate_create_course,
    validate_idempotency_key,
    validate_replace_curriculum,
    validate_successor,
    validate_transition,
    validate_update_course,
)

_ZERO_HASH = f"sha256:{'0' * 64}"
_SUCCESSOR_SOURCE_STATES = frozenset(
    {
        CourseStatus.APPROVED,
        CourseStatus.SCHEDULED,
        CourseStatus.PUBLISHED,
        CourseStatus.WITHDRAWN,
        CourseStatus.ARCHIVED,
    }
)


class AuthorizationPort(Protocol):
    def authorize(self, *, actor_id: UUID, tenant_id: UUID) -> AuthorizedActor: ...

    def authorize_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        permission: str,
    ) -> AuthorizedActor: ...


class ReviewerPolicyPort(Protocol):
    def reviewer_policy_for_new_course(self, *, tenant_id: UUID) -> ReviewerPolicy: ...


class CourseRepositoryPort(Protocol):
    def create(self, aggregate: CourseAggregate) -> CourseAggregate: ...

    def load(
        self, *, tenant_id: UUID, course_id: UUID, version_id: UUID
    ) -> CourseAggregate | None: ...

    def save(
        self,
        aggregate: CourseAggregate,
        *,
        expected_version_row_version: int,
        expected_course_row_version: int | None,
    ) -> CourseAggregate:
        """CAS the aggregate and append, never replace, a newly supplied review."""
        ...

    def list_versions(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> CourseVersionHistory | None: ...

    def find_successor(
        self, *, tenant_id: UUID, course_id: UUID, source_version_id: UUID
    ) -> CourseAggregate | None: ...

    def next_version_number(self, *, tenant_id: UUID, course_id: UUID) -> int: ...

    def add_successor(
        self,
        *,
        source_version_id: UUID,
        successor: CourseAggregate,
        expected_course_row_version: int,
        expected_source_version_row_version: int,
    ) -> CourseAggregate: ...


class IdempotencyPort(Protocol):
    def reserve(self, scope: IdempotencyScope, request_hash: str) -> IdempotencyRecord: ...

    def complete(
        self,
        scope: IdempotencyScope,
        request_hash: str,
        response: CourseSnapshot | SuccessorDraftResult,
    ) -> None: ...


class FactWriterPort(Protocol):
    def append(self, audit: AuditFact, outbox: OutboxFact) -> None: ...


class UnitOfWorkPort(Protocol):
    def transaction(self) -> AbstractContextManager[None]: ...


class UUIDFactory(Protocol):
    def new_uuid(self) -> UUID: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class RandomUUIDFactory:
    def new_uuid(self) -> UUID:
        return uuid4()


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class CourseLifecycleService:
    def __init__(
        self,
        *,
        authorization: AuthorizationPort,
        reviewer_policies: ReviewerPolicyPort,
        repository: CourseRepositoryPort,
        idempotency: IdempotencyPort,
        facts: FactWriterPort,
        unit_of_work: UnitOfWorkPort,
        ids: UUIDFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._authorization = authorization
        self._reviewer_policies = reviewer_policies
        self._repository = repository
        self._idempotency = idempotency
        self._facts = facts
        self._unit_of_work = unit_of_work
        self._ids = ids or RandomUUIDFactory()
        self._clock = clock or SystemClock()

    def _authorize(self, *, actor_id: UUID, tenant_id: UUID) -> AuthorizedActor:
        actor = self._authorization.authorize(actor_id=actor_id, tenant_id=tenant_id)
        if actor.principal_id != actor_id or actor.tenant_id != tenant_id:
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        return actor

    def _authorize_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        permission: str,
    ) -> AuthorizedActor:
        actor = self._authorization.authorize_course(
            actor_id=actor_id,
            tenant_id=tenant_id,
            course_id=course_id,
            permission=permission,
        )
        if actor.principal_id != actor_id or actor.tenant_id != tenant_id:
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        require_permission(actor, permission)
        return actor

    def _load(self, *, tenant_id: UUID, course_id: UUID, version_id: UUID) -> CourseAggregate:
        aggregate = self._repository.load(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
        )
        if aggregate is None:
            raise CourseLifecycleError("RESOURCE_NOT_FOUND")
        if (
            aggregate.course.tenant_id != tenant_id
            or aggregate.course.id != course_id
            or aggregate.version.tenant_id != tenant_id
            or aggregate.version.course_id != course_id
            or aggregate.version.id != version_id
        ):
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        return aggregate

    def _reserve(
        self, scope: IdempotencyScope, request_hash: str
    ) -> CourseSnapshot | SuccessorDraftResult | None:
        record = self._idempotency.reserve(scope, request_hash)
        if record.request_hash != request_hash:
            raise CourseLifecycleError("IDEMPOTENCY_CONFLICT")
        if record.response is not None:
            return record.response
        if not record.created:
            raise CourseLifecycleError("VERSION_CONFLICT")
        return None

    def create_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateCourseCommand,
        idempotency_key: str,
    ) -> CourseSnapshot:
        validate_create_course(command)
        validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(
            {
                "slug": command.slug,
                "primary_locale": command.primary_locale,
                "title": command.title,
                "description": command.description,
            }
        )
        scope = IdempotencyScope(tenant_id, actor_id, "create_course", idempotency_key)
        with self._unit_of_work.transaction():
            actor = self._authorize(actor_id=actor_id, tenant_id=tenant_id)
            require_permission(actor, PERMISSION_COURSES_DRAFTS_WRITE)
            if actor.membership_id is None:
                raise CourseLifecycleError("COURSE_PERMISSION_DENIED")
            replay = self._reserve(scope, request_hash)
            if replay is not None:
                if not isinstance(replay, CourseSnapshot):
                    raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
                return replay

            course_id = self._ids.new_uuid()
            version_id = self._ids.new_uuid()
            course = Course(
                id=course_id,
                tenant_id=tenant_id,
                slug=command.slug,
                reviewer_policy=self._reviewer_policies.reviewer_policy_for_new_course(
                    tenant_id=tenant_id
                ),
                current_published_version_id=None,
                instructor_membership_ids=(actor.membership_id,),
                row_version=1,
            )
            version = CourseVersion(
                id=version_id,
                tenant_id=tenant_id,
                course_id=course_id,
                predecessor_version_id=None,
                version_number=1,
                status=CourseStatus.DRAFT,
                origin_type=OriginType.MANUAL,
                primary_locale=command.primary_locale,
                title=command.title,
                description=command.description,
                content_hash=_ZERO_HASH,
                submitted_hash=None,
                approved_hash=None,
                row_version=1,
            )
            aggregate = CourseAggregate(course, version, (), None, None)
            aggregate = replace(
                aggregate,
                version=replace(
                    aggregate.version,
                    content_hash=canonical_content_hash(aggregate.snapshot()),
                ),
            )
            stored = self._repository.create(aggregate)
            snapshot = stored.snapshot()
            self._idempotency.complete(scope, request_hash, snapshot)
            return snapshot

    def get_course_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
    ) -> CourseSnapshot:
        with self._unit_of_work.transaction():
            self._authorize_course(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                permission=PERMISSION_COURSES_READ,
            )
            return self._load(
                tenant_id=tenant_id, course_id=course_id, version_id=version_id
            ).snapshot()

    def list_course_versions(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> CourseVersionHistory:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise validation_failed(
                (FieldError("limit", "invalid", "The page size must be between 1 and 100."),)
            )
        if cursor is not None and (not cursor or len(cursor) > 2_048):
            raise validation_failed(
                (FieldError("cursor", "invalid", "The history cursor is invalid."),)
            )
        with self._unit_of_work.transaction():
            self._authorize_course(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                permission=PERMISSION_COURSES_READ,
            )
            result = self._repository.list_versions(
                tenant_id=tenant_id,
                course_id=course_id,
                cursor=cursor,
                limit=limit,
            )
            if result is None:
                raise CourseLifecycleError("RESOURCE_NOT_FOUND")
            if result.tenant_id != tenant_id or result.course_id != course_id:
                raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
            return result

    def update_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: UpdateCourseVersionCommand,
    ) -> CourseSnapshot:
        validate_update_course(command)
        with self._unit_of_work.transaction():
            self._authorize_course(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                permission=PERMISSION_COURSES_DRAFTS_WRITE,
            )
            aggregate = self._load(tenant_id=tenant_id, course_id=course_id, version_id=version_id)
            require_mutable_version(aggregate.version)
            if aggregate.version.row_version != command.expected_version_row_version:
                raise CourseLifecycleError("VERSION_CONFLICT")
            version = replace(
                aggregate.version,
                primary_locale=command.primary_locale or aggregate.version.primary_locale,
                title=command.title or aggregate.version.title,
                description=command.description or aggregate.version.description,
                submitted_hash=None,
                approved_hash=None,
                row_version=aggregate.version.row_version + 1,
            )
            updated = replace(aggregate, version=version, submitted_by_actor_id=None)
            updated = replace(
                updated,
                version=replace(
                    updated.version,
                    content_hash=canonical_content_hash(updated.snapshot()),
                ),
            )
            stored = self._repository.save(
                updated,
                expected_version_row_version=command.expected_version_row_version,
                expected_course_row_version=None,
            )
            return stored.snapshot()

    def replace_curriculum(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: ReplaceCurriculumCommand,
    ) -> CourseSnapshot:
        validate_replace_curriculum(command)
        with self._unit_of_work.transaction():
            self._authorize_course(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                permission=PERMISSION_COURSES_DRAFTS_WRITE,
            )
            aggregate = self._load(tenant_id=tenant_id, course_id=course_id, version_id=version_id)
            require_mutable_version(aggregate.version)
            if aggregate.version.row_version != command.expected_version_row_version:
                raise CourseLifecycleError("VERSION_CONFLICT")
            updated = self._materialize_curriculum(aggregate, command.sections)
            stored = self._repository.save(
                updated,
                expected_version_row_version=command.expected_version_row_version,
                expected_course_row_version=None,
            )
            return stored.snapshot()

    def _materialize_curriculum(
        self,
        aggregate: CourseAggregate,
        section_inputs: tuple[CurriculumSectionInput, ...],
    ) -> CourseAggregate:
        current_sections = {section.id: section for section in aggregate.sections}
        current_lessons = {
            lesson.id: lesson for section in aggregate.sections for lesson in section.lessons
        }
        current_blocks = {
            block.id: block
            for section in aggregate.sections
            for lesson in section.lessons
            for block in lesson.content_blocks
        }
        sections: list[CurriculumSection] = []
        for section_input in section_inputs:
            previous_section = self._preserved(current_sections, section_input)
            section_id = previous_section.id if previous_section else self._ids.new_uuid()
            lessons: list[Lesson] = []
            for lesson_input in section_input.lessons:
                previous_lesson = self._preserved(current_lessons, lesson_input)
                if previous_lesson is not None and previous_lesson.section_id != section_id:
                    raise CourseLifecycleError("RESOURCE_NOT_FOUND")
                lesson_id = previous_lesson.id if previous_lesson else self._ids.new_uuid()
                blocks: list[RichTextBlock] = []
                for block_input in lesson_input.content_blocks:
                    previous_block = self._preserved(current_blocks, block_input)
                    if previous_block is not None and previous_block.lesson_id != lesson_id:
                        raise CourseLifecycleError("RESOURCE_NOT_FOUND")
                    block_id = previous_block.id if previous_block else self._ids.new_uuid()
                    changed = previous_block is not None and (
                        previous_block.kind != block_input.kind
                        or previous_block.position != block_input.position
                        or previous_block.document != block_input.document
                    )
                    blocks.append(
                        RichTextBlock(
                            id=block_id,
                            tenant_id=aggregate.course.tenant_id,
                            course_version_id=aggregate.version.id,
                            lesson_id=lesson_id,
                            kind=block_input.kind,
                            position=block_input.position,
                            row_version=(
                                previous_block.row_version + int(changed)
                                if previous_block is not None
                                else 1
                            ),
                            document=deepcopy(block_input.document),
                        )
                    )
                lesson_changed = previous_lesson is not None and (
                    previous_lesson.title != lesson_input.title
                    or previous_lesson.position != lesson_input.position
                    or previous_lesson.is_required != lesson_input.is_required
                )
                lessons.append(
                    Lesson(
                        id=lesson_id,
                        tenant_id=aggregate.course.tenant_id,
                        course_version_id=aggregate.version.id,
                        section_id=section_id,
                        title=lesson_input.title,
                        position=lesson_input.position,
                        is_required=lesson_input.is_required,
                        row_version=(
                            previous_lesson.row_version + int(lesson_changed)
                            if previous_lesson is not None
                            else 1
                        ),
                        content_blocks=tuple(sorted(blocks, key=lambda item: item.position)),
                    )
                )
            section_changed = previous_section is not None and (
                previous_section.title != section_input.title
                or previous_section.position != section_input.position
            )
            sections.append(
                CurriculumSection(
                    id=section_id,
                    tenant_id=aggregate.course.tenant_id,
                    course_version_id=aggregate.version.id,
                    title=section_input.title,
                    position=section_input.position,
                    row_version=(
                        previous_section.row_version + int(section_changed)
                        if previous_section is not None
                        else 1
                    ),
                    lessons=tuple(sorted(lessons, key=lambda item: item.position)),
                )
            )
        updated = replace(
            aggregate,
            sections=tuple(sorted(sections, key=lambda item: item.position)),
            version=replace(
                aggregate.version,
                submitted_hash=None,
                approved_hash=None,
                row_version=aggregate.version.row_version + 1,
            ),
            submitted_by_actor_id=None,
        )
        return replace(
            updated,
            version=replace(
                updated.version,
                content_hash=canonical_content_hash(updated.snapshot()),
            ),
        )

    @staticmethod
    def _preserved[
        Stored: CurriculumSection | Lesson | RichTextBlock,
        Incoming: CurriculumSectionInput | LessonInput | ContentBlockInput,
    ](current: dict[UUID, Stored], incoming: Incoming) -> Stored | None:
        if incoming.id is None:
            return None
        stored = current.get(incoming.id)
        if stored is None:
            raise CourseLifecycleError("RESOURCE_NOT_FOUND")
        if incoming.expected_row_version != stored.row_version:
            raise CourseLifecycleError("VERSION_CONFLICT")
        return stored

    def transition_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionCommand,
        idempotency_key: str,
    ) -> CourseSnapshot:
        validate_transition(command)
        validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(self._transition_request(command))
        scope = IdempotencyScope(
            tenant_id,
            actor_id,
            f"transition:{course_id}:{version_id}:{command.transition}",
            idempotency_key,
        )
        with self._unit_of_work.transaction():
            permission = transition_permission(command.transition)
            actor = self._authorize_course(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                permission=permission,
            )
            if transition_requires_human(command.transition):
                require_human(actor)
            replay = self._reserve(scope, request_hash)
            if replay is not None:
                if not isinstance(replay, CourseSnapshot):
                    raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
                return replay
            aggregate = self._load(tenant_id=tenant_id, course_id=course_id, version_id=version_id)
            if aggregate.version.row_version != command.expected_version_row_version:
                raise CourseLifecycleError("VERSION_CONFLICT")
            current_hash = canonical_content_hash(aggregate.snapshot())
            if aggregate.version.content_hash != current_hash:
                raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
            if command.expected_content_hash != current_hash:
                raise CourseLifecycleError("CONTENT_HASH_MISMATCH")
            decision = authorize_transition(actor, aggregate, command.transition)
            if command.transition is Transition.SUBMIT_REVIEW:
                validate_complete_course(aggregate.snapshot())
            if command.transition in {Transition.REQUEST_CHANGES, Transition.APPROVE} and (
                aggregate.version.submitted_hash != current_hash
            ):
                raise CourseLifecycleError("CONTENT_HASH_MISMATCH")
            if command.transition is Transition.PUBLISH and (
                aggregate.version.submitted_hash != current_hash
                or aggregate.version.approved_hash != current_hash
            ):
                raise CourseLifecycleError("CONTENT_HASH_MISMATCH")

            previous_published = aggregate.course.current_published_version_id
            course = aggregate.course
            if command.transition is Transition.PUBLISH:
                course = replace(
                    course,
                    current_published_version_id=aggregate.version.id,
                    row_version=course.row_version + 1,
                )
            elif command.transition is Transition.WITHDRAW:
                if course.current_published_version_id != aggregate.version.id:
                    raise CourseLifecycleError("VERSION_CONFLICT")
                course = replace(
                    course, current_published_version_id=None, row_version=course.row_version + 1
                )

            submitted_hash = aggregate.version.submitted_hash
            approved_hash = aggregate.version.approved_hash
            submitted_by = aggregate.submitted_by_actor_id
            if command.transition is Transition.SUBMIT_REVIEW:
                submitted_hash = current_hash
                approved_hash = None
                submitted_by = actor.principal_id
            elif command.transition is Transition.APPROVE:
                approved_hash = current_hash
            version = replace(
                aggregate.version,
                status=decision.target_status,
                content_hash=current_hash,
                submitted_hash=submitted_hash,
                approved_hash=approved_hash,
                row_version=aggregate.version.row_version + 1,
            )
            review = aggregate.latest_review
            if command.transition in {Transition.REQUEST_CHANGES, Transition.APPROVE}:
                if actor.membership_id is None:
                    raise CourseLifecycleError("COURSE_PERMISSION_DENIED")
                review = CourseReview(
                    id=self._ids.new_uuid(),
                    tenant_id=tenant_id,
                    course_version_id=version_id,
                    decision=(
                        ReviewDecision.CHANGES_REQUESTED
                        if command.transition is Transition.REQUEST_CHANGES
                        else ReviewDecision.APPROVED
                    ),
                    reviewed_hash=current_hash,
                    reviewer_id=actor.membership_id,
                    self_review=decision.self_review,
                    reason_codes=command.reason_codes,
                    decided_at=self._clock.now(),
                )
            updated = CourseAggregate(course, version, aggregate.sections, review, submitted_by)
            stored = self._repository.save(
                updated,
                expected_version_row_version=command.expected_version_row_version,
                expected_course_row_version=command.expected_course_row_version,
            )
            event_type, payload = self._transition_fact(
                transition=command.transition,
                aggregate=stored,
                review=review,
                self_review=decision.self_review,
                reason_code=command.reason_code,
                reason_codes=command.reason_codes,
                previous_published_version_id=previous_published,
            )
            self._write_facts(actor=actor, aggregate=stored, event_type=event_type, payload=payload)
            snapshot = stored.snapshot()
            self._idempotency.complete(scope, request_hash, snapshot)
            return snapshot

    def create_successor_draft(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        source_version_id: UUID,
        command: CreateSuccessorDraftCommand,
        idempotency_key: str,
    ) -> SuccessorDraftResult:
        validate_successor(command)
        validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(
            {
                "expected_course_row_version": command.expected_course_row_version,
                "expected_source_version_row_version": command.expected_source_version_row_version,
                "expected_source_content_hash": command.expected_source_content_hash,
            }
        )
        scope = IdempotencyScope(
            tenant_id,
            actor_id,
            f"successor:{course_id}:{source_version_id}",
            idempotency_key,
        )
        with self._unit_of_work.transaction():
            actor = self._authorize_course(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                permission=PERMISSION_COURSES_DRAFTS_WRITE,
            )
            replay = self._reserve(scope, request_hash)
            if replay is not None:
                if not isinstance(replay, SuccessorDraftResult):
                    raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
                return replay
            source = self._load(
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=source_version_id,
            )
            source_hash = canonical_content_hash(source.snapshot())
            if source.version.content_hash != source_hash:
                raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
            if source.version.row_version != command.expected_source_version_row_version:
                raise CourseLifecycleError("VERSION_CONFLICT")
            if source_hash != command.expected_source_content_hash:
                raise CourseLifecycleError("CONTENT_HASH_MISMATCH")
            if source.version.status not in _SUCCESSOR_SOURCE_STATES:
                raise CourseLifecycleError("COURSE_VERSION_IMMUTABLE")

            existing = self._repository.find_successor(
                tenant_id=tenant_id,
                course_id=course_id,
                source_version_id=source_version_id,
            )
            if existing is not None:
                if existing.version.status not in {
                    CourseStatus.DRAFT,
                    CourseStatus.CHANGES_REQUESTED,
                }:
                    raise CourseLifecycleError("COURSE_VERSION_IMMUTABLE")
                if command.expected_course_row_version not in {
                    existing.course.row_version,
                    existing.course.row_version - 1,
                }:
                    raise CourseLifecycleError("VERSION_CONFLICT")
                result = SuccessorDraftResult(
                    source_version_id,
                    existing.version.id,
                    existing.snapshot(),
                )
                self._idempotency.complete(scope, request_hash, result)
                return result

            if source.course.row_version != command.expected_course_row_version:
                raise CourseLifecycleError("VERSION_CONFLICT")
            successor = self._copy_successor(source)
            stored = self._repository.add_successor(
                source_version_id=source_version_id,
                successor=successor,
                expected_course_row_version=command.expected_course_row_version,
                expected_source_version_row_version=command.expected_source_version_row_version,
            )
            payload: JsonObject = {
                "course_id": str(course_id),
                "source_version_id": str(source_version_id),
                "successor_version_id": str(stored.version.id),
                "source_version_number": source.version.version_number,
                "successor_version_number": stored.version.version_number,
                "source_content_hash": source_hash,
                "content_hash": stored.version.content_hash,
            }
            self._write_facts(
                actor=actor,
                aggregate=stored,
                event_type="course.version.successor_created.v1",
                payload=payload,
            )
            result = SuccessorDraftResult(source_version_id, stored.version.id, stored.snapshot())
            self._idempotency.complete(scope, request_hash, result)
            return result

    def _copy_successor(self, source: CourseAggregate) -> CourseAggregate:
        version_id = self._ids.new_uuid()
        sections: list[CurriculumSection] = []
        for source_section in sorted(source.sections, key=lambda item: item.position):
            section_id = self._ids.new_uuid()
            lessons: list[Lesson] = []
            for source_lesson in sorted(source_section.lessons, key=lambda item: item.position):
                lesson_id = self._ids.new_uuid()
                blocks = tuple(
                    RichTextBlock(
                        id=self._ids.new_uuid(),
                        tenant_id=source.course.tenant_id,
                        course_version_id=version_id,
                        lesson_id=lesson_id,
                        kind=block.kind,
                        position=block.position,
                        row_version=1,
                        document=deepcopy(block.document),
                    )
                    for block in sorted(
                        source_lesson.content_blocks, key=lambda item: item.position
                    )
                )
                lessons.append(
                    Lesson(
                        id=lesson_id,
                        tenant_id=source.course.tenant_id,
                        course_version_id=version_id,
                        section_id=section_id,
                        title=source_lesson.title,
                        position=source_lesson.position,
                        is_required=source_lesson.is_required,
                        row_version=1,
                        content_blocks=blocks,
                    )
                )
            sections.append(
                CurriculumSection(
                    id=section_id,
                    tenant_id=source.course.tenant_id,
                    course_version_id=version_id,
                    title=source_section.title,
                    position=source_section.position,
                    row_version=1,
                    lessons=tuple(lessons),
                )
            )
        course = replace(source.course, row_version=source.course.row_version + 1)
        version = CourseVersion(
            id=version_id,
            tenant_id=source.course.tenant_id,
            course_id=source.course.id,
            predecessor_version_id=source.version.id,
            version_number=self._repository.next_version_number(
                tenant_id=source.course.tenant_id, course_id=source.course.id
            ),
            status=CourseStatus.DRAFT,
            origin_type=source.version.origin_type,
            primary_locale=source.version.primary_locale,
            title=source.version.title,
            description=source.version.description,
            content_hash=_ZERO_HASH,
            submitted_hash=None,
            approved_hash=None,
            row_version=1,
        )
        successor = CourseAggregate(course, version, tuple(sections), None, None)
        return replace(
            successor,
            version=replace(
                successor.version,
                content_hash=canonical_content_hash(successor.snapshot()),
            ),
        )

    @staticmethod
    def _transition_request(command: TransitionCourseVersionCommand) -> JsonObject:
        return {
            "transition": str(command.transition),
            "expected_version_row_version": command.expected_version_row_version,
            "expected_course_row_version": command.expected_course_row_version,
            "expected_content_hash": command.expected_content_hash,
            "reason_code": command.reason_code,
            "reason_codes": list(command.reason_codes),
        }

    @staticmethod
    def _transition_fact(
        *,
        transition: Transition,
        aggregate: CourseAggregate,
        review: CourseReview | None,
        self_review: bool,
        reason_code: str | None,
        reason_codes: tuple[str, ...],
        previous_published_version_id: UUID | None,
    ) -> tuple[str, JsonObject]:
        event_types = {
            Transition.SUBMIT_REVIEW: "course.version.submitted.v1",
            Transition.REQUEST_CHANGES: "course.version.changes_requested.v1",
            Transition.APPROVE: "course.version.approved.v1",
            Transition.PUBLISH: "course.version.published.v1",
            Transition.WITHDRAW: "course.version.withdrawn.v1",
            Transition.ARCHIVE: "course.version.archived.v1",
        }
        payload: JsonObject = {
            "course_id": str(aggregate.course.id),
            "course_version_id": str(aggregate.version.id),
            "content_hash": aggregate.version.content_hash,
            "aggregate_version": aggregate.version.row_version,
        }
        if transition in {Transition.REQUEST_CHANGES, Transition.APPROVE}:
            if review is None:
                raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
            payload["review_id"] = str(review.id)
        if transition is Transition.REQUEST_CHANGES:
            payload["reason_codes"] = list(reason_codes)
        elif transition is Transition.APPROVE:
            payload["self_review"] = self_review
        elif transition is Transition.PUBLISH:
            payload["previous_published_version_id"] = (
                str(previous_published_version_id)
                if previous_published_version_id is not None
                else None
            )
        elif transition is Transition.WITHDRAW:
            payload["reason_code"] = reason_code
        elif transition is Transition.ARCHIVE and reason_code is not None:
            payload["reason_code"] = reason_code
        return event_types[transition], payload

    def _write_facts(
        self,
        *,
        actor: AuthorizedActor,
        aggregate: CourseAggregate,
        event_type: str,
        payload: JsonObject,
    ) -> None:
        recorded_at = self._clock.now()
        audit = AuditFact(
            id=self._ids.new_uuid(),
            tenant_id=aggregate.course.tenant_id,
            event_type=event_type,
            actor_id=actor.principal_id,
            course_id=aggregate.course.id,
            course_version_id=aggregate.version.id,
            payload=deepcopy(payload),
            recorded_at=recorded_at,
        )
        outbox = OutboxFact(
            id=self._ids.new_uuid(),
            tenant_id=aggregate.course.tenant_id,
            event_type=event_type,
            aggregate_type="course_version",
            aggregate_id=aggregate.version.id,
            actor_id=actor.principal_id,
            payload=deepcopy(payload),
            recorded_at=recorded_at,
        )
        self._facts.append(audit, outbox)

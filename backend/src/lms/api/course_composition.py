from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import cast
from uuid import UUID

from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.db import IntegrityError, transaction

from lms.api.schemas.courses import (
    CourseAdministrationError,
    CourseSnapshotV1,
    CreateCourseV1,
    CreateSuccessorDraftV1,
    ReplaceCurriculumV1,
    SuccessorDraftResultV1,
    TransitionCourseVersionV1,
    UpdateCourseVersionV1,
)
from lms.modules.course_generation.publication import GenerationPublicationSources
from lms.modules.courses.errors import CourseLifecycleError, FieldError, validation_failed
from lms.modules.courses.repositories import (
    CoursePersistenceConflictError,
    CourseRepository,
    Snapshot,
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
    CreateAiAssistedDraftCommand,
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
    PrincipalType,
    ReplaceCurriculumCommand,
    ReviewDecision,
    ReviewerPolicy,
    RichTextBlock,
    SuccessorDraftResult,
    Transition,
    TransitionCourseVersionCommand,
    UpdateCourseVersionCommand,
)
from lms.modules.tenancy import services as tenancy_services
from lms.modules.tenancy.errors import TenancyError

_CURSOR_SALT = "ai-lms.f002.course-version-history.v1"
_CURSOR_MAX_AGE_SECONDS = 86_400


def _course_error_from_tenancy(error: TenancyError) -> CourseLifecycleError:
    if error.code == "TENANT_ACCESS_INACTIVE":
        return CourseLifecycleError("TENANT_ACCESS_INACTIVE")
    return CourseLifecycleError("RESOURCE_NOT_FOUND")


class DjangoCourseAuthorization:
    """Re-derive current membership and permissions inside the command transaction."""

    def authorize(self, *, actor_id: UUID, tenant_id: UUID) -> AuthorizedActor:
        try:
            context = tenancy_services.get_authentication_context(actor_id, tenant_id)
        except TenancyError as error:
            raise _course_error_from_tenancy(error) from error
        membership = context.membership
        if (
            context.active_tenant is None
            or context.active_tenant.id != tenant_id
            or membership is None
            or membership.tenant_id != tenant_id
            or membership.status != "active"
        ):
            raise CourseLifecycleError("RESOURCE_NOT_FOUND")
        return AuthorizedActor(
            principal_id=actor_id,
            tenant_id=tenant_id,
            membership_id=membership.id,
            principal_type=PrincipalType.USER,
            permissions=frozenset(membership.permission_codes),
        )

    def authorize_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        permission: str,
    ) -> AuthorizedActor:
        del course_id
        actor = self.authorize(actor_id=actor_id, tenant_id=tenant_id)
        if permission not in actor.permissions:
            raise CourseLifecycleError("COURSE_PERMISSION_DENIED")
        return actor


class DefaultReviewerPolicies:
    def reviewer_policy_for_new_course(self, *, tenant_id: UUID) -> ReviewerPolicy:
        del tenant_id
        return ReviewerPolicy.SELF_REVIEW_ALLOWED


class DjangoCourseUnitOfWork:
    @contextmanager
    def transaction(self) -> Iterator[None]:
        with transaction.atomic():
            yield


def _snapshot_model(value: object) -> CourseSnapshotV1:
    return CourseSnapshotV1.model_validate(value, from_attributes=True)


def _snapshot_from_contract(
    value: object,
    *,
    submitted_by_actor_id: UUID | None,
) -> CourseAggregate:
    snapshot = _snapshot_model(value)
    course = Course(
        id=snapshot.course.id,
        tenant_id=snapshot.course.tenant_id,
        slug=snapshot.course.slug,
        reviewer_policy=ReviewerPolicy(snapshot.course.reviewer_policy),
        current_published_version_id=snapshot.course.current_published_version_id,
        instructor_membership_ids=tuple(snapshot.course.instructor_membership_ids),
        row_version=snapshot.course.row_version,
    )
    version = CourseVersion(
        id=snapshot.version.id,
        tenant_id=snapshot.version.tenant_id,
        course_id=snapshot.version.course_id,
        predecessor_version_id=snapshot.version.predecessor_version_id,
        version_number=snapshot.version.version_number,
        status=CourseStatus(snapshot.version.status),
        origin_type=OriginType(snapshot.version.origin_type),
        primary_locale=snapshot.version.primary_locale,
        title=snapshot.version.title,
        description=snapshot.version.description,
        content_hash=snapshot.version.content_hash,
        submitted_hash=snapshot.version.submitted_hash,
        approved_hash=snapshot.version.approved_hash,
        row_version=snapshot.version.row_version,
    )
    sections = tuple(
        CurriculumSection(
            id=section.id,
            tenant_id=section.tenant_id,
            course_version_id=section.course_version_id,
            title=section.title,
            position=section.position,
            row_version=section.row_version,
            lessons=tuple(
                Lesson(
                    id=lesson.id,
                    tenant_id=lesson.tenant_id,
                    course_version_id=lesson.course_version_id,
                    section_id=lesson.section_id,
                    title=lesson.title,
                    position=lesson.position,
                    is_required=lesson.is_required,
                    row_version=lesson.row_version,
                    content_blocks=tuple(
                        RichTextBlock(
                            id=block.id,
                            tenant_id=block.tenant_id,
                            course_version_id=block.course_version_id,
                            lesson_id=block.lesson_id,
                            kind=block.kind,
                            position=block.position,
                            row_version=block.row_version,
                            document=cast(
                                JsonObject,
                                block.document.model_dump(mode="python"),
                            ),
                        )
                        for block in lesson.content_blocks
                    ),
                )
                for lesson in section.lessons
            ),
        )
        for section in snapshot.sections
    )
    review = None
    if snapshot.latest_review is not None:
        review = CourseReview(
            id=snapshot.latest_review.id,
            tenant_id=snapshot.latest_review.tenant_id,
            course_version_id=snapshot.latest_review.course_version_id,
            decision=ReviewDecision(snapshot.latest_review.decision),
            reviewed_hash=snapshot.latest_review.reviewed_hash,
            reviewer_id=snapshot.latest_review.reviewer_id,
            self_review=snapshot.latest_review.self_review,
            reason_codes=tuple(snapshot.latest_review.reason_codes),
            decided_at=snapshot.latest_review.decided_at,
        )
    return CourseAggregate(course, version, sections, review, submitted_by_actor_id)


def _snapshot_payload(snapshot: CourseSnapshot) -> dict[str, object]:
    return _snapshot_model(snapshot).model_dump(mode="json", by_alias=True)


def _successor_payload(result: SuccessorDraftResult) -> dict[str, object]:
    return SuccessorDraftResultV1.model_validate(result, from_attributes=True).model_dump(
        mode="json",
        by_alias=True,
    )


def _response_payload(
    response: CourseSnapshot | SuccessorDraftResult,
) -> dict[str, object]:
    if isinstance(response, CourseSnapshot):
        return {"kind": "course_snapshot", "response": _snapshot_payload(response)}
    return {"kind": "successor_draft", "response": _successor_payload(response)}


def _response_from_payload(payload: Mapping[str, object]) -> CourseSnapshot | SuccessorDraftResult:
    response = payload.get("response")
    if payload.get("kind") == "course_snapshot":
        return _snapshot_from_contract(response, submitted_by_actor_id=None).snapshot()
    if payload.get("kind") == "successor_draft":
        parsed = SuccessorDraftResultV1.model_validate(response)
        aggregate = _snapshot_from_contract(parsed.snapshot, submitted_by_actor_id=None)
        return SuccessorDraftResult(
            source_version_id=parsed.source_version_id,
            successor_version_id=parsed.successor_version_id,
            snapshot=aggregate.snapshot(),
        )
    raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")


def _encode_cursor(position: tuple[int, str] | None) -> str | None:
    if position is None:
        return None
    version_number, version_id = position
    return signing.dumps(
        {"version_number": version_number, "version_id": version_id},
        salt=_CURSOR_SALT,
        compress=False,
    )


def _decode_cursor(cursor: str | None) -> tuple[int, UUID] | None:
    if cursor is None:
        return None
    try:
        payload = signing.loads(
            cursor,
            salt=_CURSOR_SALT,
            max_age=_CURSOR_MAX_AGE_SECONDS,
        )
        if not isinstance(payload, dict):
            raise ValueError
        version_number = payload["version_number"]
        version_id = payload["version_id"]
        if type(version_number) is not int or version_number < 1 or not isinstance(version_id, str):
            raise ValueError
        return version_number, UUID(version_id)
    except (BadSignature, KeyError, SignatureExpired, TypeError, ValueError) as error:
        raise validation_failed(
            (FieldError("cursor", "invalid", "The history cursor is invalid."),)
        ) from error


def _curriculum_payload(
    incoming: CourseAggregate,
    current: CourseAggregate,
) -> list[dict[str, object]]:
    current_sections = {section.id: section for section in current.sections}
    current_lessons = {
        lesson.id: lesson for section in current.sections for lesson in section.lessons
    }
    current_blocks = {
        block.id: block
        for section in current.sections
        for lesson in section.lessons
        for block in lesson.content_blocks
    }
    section_payloads: list[dict[str, object]] = []
    for section in incoming.sections:
        section_payload: dict[str, object] = {
            "title": section.title,
            "position": section.position,
            "lessons": [],
        }
        previous_section = current_sections.get(section.id)
        if previous_section is not None:
            section_payload.update(
                id=str(section.id),
                expected_row_version=previous_section.row_version,
            )
        lesson_payloads = cast(list[dict[str, object]], section_payload["lessons"])
        for lesson in section.lessons:
            lesson_payload: dict[str, object] = {
                "title": lesson.title,
                "position": lesson.position,
                "is_required": lesson.is_required,
                "content_blocks": [],
            }
            previous_lesson = current_lessons.get(lesson.id)
            if previous_lesson is not None:
                lesson_payload.update(
                    id=str(lesson.id),
                    expected_row_version=previous_lesson.row_version,
                )
            block_payloads = cast(
                list[dict[str, object]],
                lesson_payload["content_blocks"],
            )
            for block in lesson.content_blocks:
                block_payload: dict[str, object] = {
                    "kind": block.kind,
                    "position": block.position,
                    "document": copy.deepcopy(block.document),
                }
                previous_block = current_blocks.get(block.id)
                if previous_block is not None:
                    block_payload.update(
                        id=str(block.id),
                        expected_row_version=previous_block.row_version,
                    )
                block_payloads.append(block_payload)
            lesson_payloads.append(lesson_payload)
        section_payloads.append(section_payload)
    return section_payloads


class DjangoCourseRepository:
    """Adapt the persistence lane's snapshot mechanics to the lifecycle port."""

    def __init__(self, repository: CourseRepository | None = None) -> None:
        self._repository = repository or CourseRepository()

    def _submitted_by(self, *, tenant_id: UUID, version_id: UUID) -> UUID | None:
        return self._repository.latest_submission_actor(tenant_id, version_id)

    def create(self, aggregate: CourseAggregate) -> CourseAggregate:
        try:
            stored = self._repository.insert_course_with_v1(
                tenant_id=aggregate.course.tenant_id,
                slug=aggregate.course.slug,
                primary_locale=aggregate.version.primary_locale,
                title=aggregate.version.title,
                description=aggregate.version.description,
                content_hash=aggregate.version.content_hash,
                instructor_membership_ids=aggregate.course.instructor_membership_ids,
                course_id=aggregate.course.id,
                version_id=aggregate.version.id,
                reviewer_policy=str(aggregate.course.reviewer_policy),
                origin_type=str(aggregate.version.origin_type),
            )
        except (CoursePersistenceConflictError, IntegrityError) as error:
            raise CourseLifecycleError("VERSION_CONFLICT") from error
        return _snapshot_from_contract(stored, submitted_by_actor_id=None)

    def load(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
    ) -> CourseAggregate | None:
        stored = self._repository.load_snapshot(tenant_id, course_id, version_id)
        if stored is None:
            return None
        snapshot = _snapshot_model(stored)
        return _snapshot_from_contract(
            snapshot,
            submitted_by_actor_id=(
                None
                if snapshot.version.submitted_hash is None
                else self._submitted_by(
                    tenant_id=tenant_id,
                    version_id=version_id,
                )
            ),
        )

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
        try:
            if aggregate.version.status != current.version.status:
                stored = self._save_transition(
                    aggregate,
                    current,
                    expected_version_row_version=expected_version_row_version,
                    expected_course_row_version=expected_course_row_version,
                )
            elif aggregate.sections != current.sections:
                if (
                    aggregate.version.primary_locale != current.version.primary_locale
                    or aggregate.version.title != current.version.title
                    or aggregate.version.description != current.version.description
                ):
                    raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
                stored = self._repository.replace_curriculum(
                    tenant_id=aggregate.course.tenant_id,
                    course_id=aggregate.course.id,
                    version_id=aggregate.version.id,
                    expected_row_version=expected_version_row_version,
                    sections=_curriculum_payload(aggregate, current),
                    content_hash=aggregate.version.content_hash,
                    submitted_hash=aggregate.version.submitted_hash,
                    approved_hash=aggregate.version.approved_hash,
                )
            else:
                updates = {
                    name: cast(str, getattr(aggregate.version, name))
                    for name in ("primary_locale", "title", "description")
                    if getattr(aggregate.version, name) != getattr(current.version, name)
                }
                if updates:
                    stored = self._repository.compare_and_update_version(
                        tenant_id=aggregate.course.tenant_id,
                        course_id=aggregate.course.id,
                        version_id=aggregate.version.id,
                        expected_row_version=expected_version_row_version,
                        updates=updates,
                        content_hash=aggregate.version.content_hash,
                        submitted_hash=aggregate.version.submitted_hash,
                        approved_hash=aggregate.version.approved_hash,
                    )
                else:
                    # A complete identical curriculum replacement still consumes the
                    # expected version row while preserving unchanged child versions.
                    stored = self._repository.replace_curriculum(
                        tenant_id=aggregate.course.tenant_id,
                        course_id=aggregate.course.id,
                        version_id=aggregate.version.id,
                        expected_row_version=expected_version_row_version,
                        sections=_curriculum_payload(aggregate, current),
                        content_hash=aggregate.version.content_hash,
                        submitted_hash=aggregate.version.submitted_hash,
                        approved_hash=aggregate.version.approved_hash,
                    )
        except CoursePersistenceConflictError as error:
            raise CourseLifecycleError("VERSION_CONFLICT") from error
        return _snapshot_from_contract(
            stored,
            submitted_by_actor_id=aggregate.submitted_by_actor_id,
        )

    def _save_transition(
        self,
        aggregate: CourseAggregate,
        current: CourseAggregate,
        *,
        expected_version_row_version: int,
        expected_course_row_version: int | None,
    ) -> Snapshot:
        if aggregate.sections != current.sections:
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        publication_pointer = None
        if aggregate.course != current.course:
            if (
                aggregate.course.slug != current.course.slug
                or aggregate.course.reviewer_policy != current.course.reviewer_policy
                or aggregate.course.instructor_membership_ids
                != current.course.instructor_membership_ids
                or expected_course_row_version is None
            ):
                raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
            publication_pointer = (
                expected_course_row_version,
                current.course.current_published_version_id,
                aggregate.course.current_published_version_id,
            )
        stored = self._repository.compare_and_transition_version(
            tenant_id=aggregate.course.tenant_id,
            course_id=aggregate.course.id,
            version_id=aggregate.version.id,
            expected_row_version=expected_version_row_version,
            expected_status=str(current.version.status),
            expected_content_hash=current.version.content_hash,
            next_status=str(aggregate.version.status),
            hash_updates={
                "submitted_hash": aggregate.version.submitted_hash,
                "approved_hash": aggregate.version.approved_hash,
            },
            publication_pointer=publication_pointer,
        )
        if aggregate.latest_review is not None and aggregate.latest_review != current.latest_review:
            review = aggregate.latest_review
            stored = self._repository.append_review(
                tenant_id=aggregate.course.tenant_id,
                course_id=aggregate.course.id,
                version_id=aggregate.version.id,
                decision=str(review.decision),
                reviewed_hash=review.reviewed_hash,
                reviewer_id=review.reviewer_id,
                self_review=review.self_review,
                reason_codes=review.reason_codes,
                review_id=review.id,
                decided_at=review.decided_at,
            )
        return stored

    def list_versions(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> CourseVersionHistory | None:
        before = _decode_cursor(cursor)
        try:
            rows, next_position = self._repository.list_version_summaries(
                tenant_id,
                course_id,
                limit=limit,
                before=before,
            )
            pointer = self._repository.course_publication_pointer(tenant_id, course_id)
        except CoursePersistenceConflictError:
            return None
        versions = tuple(
            CourseVersionSummary(
                id=UUID(str(row["id"])),
                tenant_id=UUID(str(row["tenant_id"])),
                course_id=UUID(str(row["course_id"])),
                predecessor_version_id=(
                    None
                    if row["predecessor_version_id"] is None
                    else UUID(str(row["predecessor_version_id"]))
                ),
                version_number=cast(int, row["version_number"]),
                status=CourseStatus(str(row["status"])),
                title=cast(str, row["title"]),
                content_hash=cast(str, row["content_hash"]),
                row_version=cast(int, row["row_version"]),
                is_current_published=cast(bool, row["is_current_published"]),
            )
            for row in rows
        )
        return CourseVersionHistory(
            tenant_id=tenant_id,
            course_id=course_id,
            current_published_version_id=pointer,
            versions=versions,
            next_cursor=_encode_cursor(next_position),
        )

    def find_successor(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        source_version_id: UUID,
    ) -> CourseAggregate | None:
        stored = self._repository.find_successor_snapshot(
            tenant_id,
            course_id,
            source_version_id,
        )
        if stored is None:
            return None
        version_id = UUID(str(cast(Mapping[str, object], stored["version"])["id"]))
        return _snapshot_from_contract(
            stored,
            submitted_by_actor_id=self._submitted_by(
                tenant_id=tenant_id,
                version_id=version_id,
            ),
        )

    def next_version_number(self, *, tenant_id: UUID, course_id: UUID) -> int:
        try:
            return self._repository.next_version_number(tenant_id, course_id)
        except CoursePersistenceConflictError as error:
            raise CourseLifecycleError("RESOURCE_NOT_FOUND") from error

    def add_successor(
        self,
        *,
        source_version_id: UUID,
        successor: CourseAggregate,
        expected_course_row_version: int,
        expected_source_version_row_version: int,
    ) -> CourseAggregate:
        try:
            stored = self._repository.create_successor_draft(
                tenant_id=successor.course.tenant_id,
                course_id=successor.course.id,
                source_version_id=source_version_id,
                expected_course_row_version=expected_course_row_version,
                expected_source_row_version=expected_source_version_row_version,
                expected_source_content_hash=successor.version.content_hash,
            )
        except (CoursePersistenceConflictError, IntegrityError) as error:
            raise CourseLifecycleError("VERSION_CONFLICT") from error
        result = _snapshot_from_contract(stored, submitted_by_actor_id=None)
        if result.version.content_hash != successor.version.content_hash:
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        return result


class DjangoCourseIdempotency:
    def __init__(self, repository: CourseRepository) -> None:
        self._repository = repository

    @staticmethod
    def _persistence_scope(scope: IdempotencyScope) -> tuple[str, str]:
        key_digest = hashlib.sha256(scope.key.encode("utf-8")).hexdigest()
        operation = scope.operation
        if len(operation) > 64:
            operation = f"sha256:{hashlib.sha256(operation.encode('utf-8')).hexdigest()[:56]}"
        return operation, key_digest

    def reserve(self, scope: IdempotencyScope, request_hash: str) -> IdempotencyRecord:
        operation, key_digest = self._persistence_scope(scope)
        try:
            reservation, replay = self._repository.reserve_idempotency(
                tenant_id=scope.tenant_id,
                actor_id=scope.actor_id,
                operation=operation,
                key_digest=key_digest,
                request_hash=request_hash,
            )
        except CoursePersistenceConflictError as error:
            raise CourseLifecycleError("IDEMPOTENCY_CONFLICT") from error
        response = None
        if replay and reservation.status == "completed":
            if not isinstance(reservation.response_payload, Mapping):
                raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
            response = _response_from_payload(reservation.response_payload)
        return IdempotencyRecord(
            request_hash=reservation.request_hash,
            created=not replay,
            response=response,
        )

    def complete(
        self,
        scope: IdempotencyScope,
        request_hash: str,
        response: CourseSnapshot | SuccessorDraftResult,
    ) -> None:
        operation, key_digest = self._persistence_scope(scope)
        try:
            reservation, replay = self._repository.reserve_idempotency(
                tenant_id=scope.tenant_id,
                actor_id=scope.actor_id,
                operation=operation,
                key_digest=key_digest,
                request_hash=request_hash,
            )
        except CoursePersistenceConflictError as error:
            raise CourseLifecycleError("IDEMPOTENCY_CONFLICT") from error
        if not replay or reservation.status != "reserved":
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        self._repository.complete_idempotency(
            reservation.id,
            _response_payload(response),
        )


class DjangoCourseFacts:
    def __init__(self, repository: CourseRepository) -> None:
        self._repository = repository

    def append(self, audit: AuditFact, outbox: OutboxFact) -> None:
        if (
            audit.tenant_id != outbox.tenant_id
            or audit.actor_id != outbox.actor_id
            or audit.event_type != outbox.event_type
            or audit.course_version_id != outbox.aggregate_id
            or audit.payload != outbox.payload
        ):
            raise CourseLifecycleError("SERVICE_CONTRACT_ERROR")
        self._repository.append_atomic_facts(
            tenant_id=audit.tenant_id,
            actor_id=audit.actor_id,
            event_type=audit.event_type,
            subject_type="course_version",
            subject_id=audit.course_version_id,
            aggregate_type=outbox.aggregate_type,
            aggregate_id=outbox.aggregate_id,
            payload=audit.payload,
        )


def _curriculum_command(command: ReplaceCurriculumV1) -> ReplaceCurriculumCommand:
    return ReplaceCurriculumCommand(
        expected_version_row_version=command.expected_version_row_version,
        sections=tuple(
            CurriculumSectionInput(
                id=section.id,
                expected_row_version=section.expected_row_version,
                title=section.title,
                position=section.position,
                lessons=tuple(
                    LessonInput(
                        id=lesson.id,
                        expected_row_version=lesson.expected_row_version,
                        title=lesson.title,
                        position=lesson.position,
                        is_required=lesson.is_required,
                        content_blocks=tuple(
                            ContentBlockInput(
                                id=block.id,
                                expected_row_version=block.expected_row_version,
                                kind=block.kind,
                                position=block.position,
                                document=cast(
                                    JsonObject,
                                    block.document.model_dump(mode="python"),
                                ),
                            )
                            for block in lesson.content_blocks
                        ),
                    )
                    for lesson in section.lessons
                ),
            )
            for section in command.sections
        ),
    )


def _translate[Result](operation: Callable[[], Result]) -> Result:
    try:
        return operation()
    except CourseLifecycleError as error:
        raise CourseAdministrationError(
            code=error.code,
            status=error.status,
            errors=tuple(
                {
                    "location": ("body", *field.path.split(".")),
                    "code": field.code,
                }
                for field in error.field_errors
            ),
        ) from error


class DjangoCourseAdministrationService:
    """Real API/Admin composition over one lifecycle service and PostgreSQL adapter."""

    def __init__(self) -> None:
        persistence = CourseRepository()
        repository = DjangoCourseRepository(persistence)
        self._service = CourseLifecycleService(
            authorization=DjangoCourseAuthorization(),
            reviewer_policies=DefaultReviewerPolicies(),
            repository=repository,
            idempotency=DjangoCourseIdempotency(persistence),
            facts=DjangoCourseFacts(persistence),
            unit_of_work=DjangoCourseUnitOfWork(),
            publication_sources=GenerationPublicationSources(),
        )

    def create_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateCourseV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.create_course(
                actor_id=actor_id,
                tenant_id=tenant_id,
                command=CreateCourseCommand(
                    slug=command.slug,
                    primary_locale=command.primary_locale,
                    title=command.title,
                    description=command.description,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def create_ai_assisted_draft(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateAiAssistedDraftCommand,
        idempotency_key: str,
    ) -> CourseSnapshot:
        """Internal cross-domain command; no separate HTTP mutation is exposed."""

        return self._service.create_ai_assisted_draft(
            actor_id=actor_id,
            tenant_id=tenant_id,
            command=command,
            idempotency_key=idempotency_key,
        )

    def get_course_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
    ) -> object:
        return _translate(
            lambda: self._service.get_course_version(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
            )
        )

    def list_course_versions(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> object:
        return _translate(
            lambda: self._service.list_course_versions(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                cursor=cursor,
                limit=limit,
            )
        )

    def update_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: UpdateCourseVersionV1,
    ) -> object:
        return _translate(
            lambda: self._service.update_version(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
                command=UpdateCourseVersionCommand(
                    expected_version_row_version=command.expected_version_row_version,
                    primary_locale=command.primary_locale,
                    title=command.title,
                    description=command.description,
                ),
            )
        )

    def replace_curriculum(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: ReplaceCurriculumV1,
    ) -> object:
        return _translate(
            lambda: self._service.replace_curriculum(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
                command=_curriculum_command(command),
            )
        )

    def transition_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.transition_version(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
                command=TransitionCourseVersionCommand(
                    transition=Transition(command.transition),
                    expected_version_row_version=command.expected_version_row_version,
                    expected_content_hash=command.expected_content_hash,
                    expected_course_row_version=command.expected_course_row_version,
                    reason_code=command.reason_code,
                    reason_codes=tuple(command.reason_codes or ()),
                ),
                idempotency_key=idempotency_key,
            )
        )

    def create_successor_draft(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        source_version_id: UUID,
        command: CreateSuccessorDraftV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.create_successor_draft(
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                source_version_id=source_version_id,
                command=CreateSuccessorDraftCommand(
                    expected_course_row_version=command.expected_course_row_version,
                    expected_source_version_row_version=(
                        command.expected_source_version_row_version
                    ),
                    expected_source_content_hash=command.expected_source_content_hash,
                ),
                idempotency_key=idempotency_key,
            )
        )

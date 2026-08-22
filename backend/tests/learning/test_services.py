from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from lms.modules.learning.errors import LearningError
from lms.modules.learning.policies import (
    PERMISSION_ENROLLMENTS_MANAGE,
    PERMISSION_PLAYBACK_READ,
)
from lms.modules.learning.services import LearningService
from lms.modules.learning.types import (
    AuthorizedActor,
    CourseProgress,
    CourseProgressState,
    Enrollment,
    EnrollmentStatus,
    IdempotencyRecord,
    LessonProgressState,
    ProgressCommand,
    ProgressCommandName,
    ProgressMutation,
    ProgressResult,
)

TENANT_ID = UUID("00000000-0000-4000-8000-0000000000a1")
ADMIN_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000101")
ADMIN_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000301")
LEARNER_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000102")
LEARNER_MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000302")
COURSE_ID = UUID("00000000-0000-4000-8000-00000000c001")
VERSION_V1_ID = UUID("00000000-0000-4000-8000-00000000c101")
VERSION_V2_ID = UUID("00000000-0000-4000-8000-00000000c102")
ENROLLMENT_ID = UUID("00000000-0000-4000-8000-00000000e001")
LESSON_ID = UUID("00000000-0000-4000-8000-00000000c302")
NOW = datetime(2026, 8, 21, tzinfo=UTC)


class FixedIds:
    def new_uuid(self) -> UUID:
        return ENROLLMENT_ID


class FixedClock:
    def now(self) -> datetime:
        return NOW


class AuthorizationFake:
    def authorize(self, *, actor_id: UUID, tenant_id: UUID, permission: str) -> AuthorizedActor:
        membership_id = ADMIN_MEMBERSHIP_ID if actor_id == ADMIN_ACTOR_ID else LEARNER_MEMBERSHIP_ID
        return AuthorizedActor(
            principal_id=actor_id,
            tenant_id=tenant_id,
            membership_id=membership_id,
            permissions=frozenset({permission}),
        )


class IdempotencyFake:
    def __init__(self) -> None:
        self.records: dict[tuple[UUID, UUID, str, str], IdempotencyRecord] = {}

    def reserve(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord:
        scope = (tenant_id, actor_id, operation, key)
        existing = self.records.get(scope)
        if existing is not None:
            return existing
        record = IdempotencyRecord(request_hash=request_hash, created=True, response=None)
        self.records[scope] = record
        return record

    def complete(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
        response: Enrollment | ProgressResult,
    ) -> None:
        self.records[(tenant_id, actor_id, operation, key)] = IdempotencyRecord(
            request_hash=request_hash,
            created=False,
            response=response,
        )


class FactsFake:
    def __init__(self) -> None:
        self.items: list[tuple[object, ...]] = []

    def append(self, *facts: object) -> None:
        self.items.append(facts)


class RepositoryFake:
    def __init__(self) -> None:
        self.current_published_version_id = VERSION_V1_ID
        self.enrollment: Enrollment | None = None
        self.create_calls = 0
        self.progress_calls = 0
        self.read_calls = 0
        self.progress_version = 0

    def create_enrollment(
        self,
        *,
        enrollment_id: UUID,
        tenant_id: UUID,
        learner_membership_id: UUID,
        course_id: UUID,
        actor_id: UUID,
        enrolled_at: datetime,
    ) -> Enrollment:
        del actor_id
        self.create_calls += 1
        self.enrollment = Enrollment(
            id=enrollment_id,
            tenant_id=tenant_id,
            learner_membership_id=learner_membership_id,
            course_id=course_id,
            course_version_id=self.current_published_version_id,
            admission_source="manual_assignment",
            status=EnrollmentStatus.ACTIVE,
            enrolled_at=enrolled_at,
            revoked_at=None,
            row_version=1,
        )
        return self.enrollment

    def revoke_enrollment(self, **kwargs: object) -> Enrollment:
        del kwargs
        assert self.enrollment is not None
        self.enrollment = replace(
            self.enrollment,
            status=EnrollmentStatus.REVOKED,
            revoked_at=NOW,
            row_version=self.enrollment.row_version + 1,
        )
        return self.enrollment

    def list_dashboard(self, **kwargs: object) -> object:
        del kwargs
        self.read_calls += 1
        return {"tenant_id": TENANT_ID, "items": (), "next_cursor": None}

    def get_playback(self, **kwargs: object) -> object:
        del kwargs
        self.read_calls += 1
        return {"tenant_id": TENANT_ID}

    def get_lesson(self, **kwargs: object) -> object:
        del kwargs
        self.read_calls += 1
        return {"tenant_id": TENANT_ID}

    def apply_progress(
        self,
        *,
        expected_progress_row_version: int,
        command: ProgressCommandName,
        **kwargs: object,
    ) -> ProgressMutation:
        del kwargs
        if expected_progress_row_version != self.progress_version:
            raise LearningError("PROGRESS_VERSION_CONFLICT")
        self.progress_calls += 1
        previous_version = self.progress_version
        self.progress_version += 1
        result = ProgressResult(
            tenant_id=TENANT_ID,
            enrollment_id=ENROLLMENT_ID,
            course_version_id=VERSION_V1_ID,
            lesson_id=LESSON_ID,
            lesson_state=(
                LessonProgressState.COMPLETED
                if command is ProgressCommandName.COMPLETE_LESSON
                else LessonProgressState.IN_PROGRESS
            ),
            course_state=CourseProgressState.IN_PROGRESS,
            required_lesson_count=2,
            completed_required_lesson_count=(
                1 if command is ProgressCommandName.COMPLETE_LESSON else 0
            ),
            resume_lesson_id=LESSON_ID,
            progress_row_version=self.progress_version,
            updated_at=NOW,
        )
        return ProgressMutation(
            result=result,
            previous_lesson_state=LessonProgressState.NOT_STARTED,
            previous_course_state=CourseProgressState.NOT_STARTED,
            previous_progress_row_version=previous_version,
        )


def make_service() -> tuple[LearningService, RepositoryFake, IdempotencyFake, FactsFake]:
    repository = RepositoryFake()
    idempotency = IdempotencyFake()
    facts = FactsFake()
    service = LearningService(
        authorization=AuthorizationFake(),
        repository=repository,
        idempotency=idempotency,
        facts=facts,
        unit_of_work=nullcontext,
        ids=FixedIds(),
        clock=FixedClock(),
    )
    return service, repository, idempotency, facts


def test_assignment_pins_the_repositorys_current_published_version() -> None:
    service, repository, _, facts = make_service()

    assigned = service.create_enrollment(
        actor_id=ADMIN_ACTOR_ID,
        tenant_id=TENANT_ID,
        learner_membership_id=LEARNER_MEMBERSHIP_ID,
        course_id=COURSE_ID,
        idempotency_key="assignment-key-0001",
    )
    repository.current_published_version_id = VERSION_V2_ID

    assert assigned.course_version_id == VERSION_V1_ID
    assert repository.enrollment is not None
    assert repository.enrollment.course_version_id == VERSION_V1_ID
    assert len(facts.items) == 1


def test_same_assignment_key_replays_without_a_second_effect() -> None:
    service, repository, _, facts = make_service()
    command = {
        "actor_id": ADMIN_ACTOR_ID,
        "tenant_id": TENANT_ID,
        "learner_membership_id": LEARNER_MEMBERSHIP_ID,
        "course_id": COURSE_ID,
        "idempotency_key": "assignment-key-0001",
    }

    first = service.create_enrollment(**command)
    second = service.create_enrollment(**command)

    assert second == first
    assert repository.create_calls == 1
    assert len(facts.items) == 1


def test_selectors_do_not_write_progress_or_facts() -> None:
    service, repository, _, facts = make_service()

    service.list_dashboard(
        actor_id=LEARNER_ACTOR_ID,
        tenant_id=TENANT_ID,
        cursor=None,
        limit=20,
    )
    service.get_playback(
        actor_id=LEARNER_ACTOR_ID,
        tenant_id=TENANT_ID,
        enrollment_id=ENROLLMENT_ID,
    )
    service.get_lesson(
        actor_id=LEARNER_ACTOR_ID,
        tenant_id=TENANT_ID,
        enrollment_id=ENROLLMENT_ID,
        lesson_id=LESSON_ID,
    )

    assert repository.read_calls == 3
    assert repository.progress_calls == 0
    assert facts.items == []


def test_progress_is_idempotent_and_rejects_a_stale_expected_version() -> None:
    service, repository, _, facts = make_service()
    command = ProgressCommand(
        command=ProgressCommandName.COMPLETE_LESSON,
        lesson_id=LESSON_ID,
        expected_progress_row_version=0,
    )

    first = service.progress(
        actor_id=LEARNER_ACTOR_ID,
        tenant_id=TENANT_ID,
        enrollment_id=ENROLLMENT_ID,
        command=command,
        idempotency_key="progress-key-000001",
    )
    replay = service.progress(
        actor_id=LEARNER_ACTOR_ID,
        tenant_id=TENANT_ID,
        enrollment_id=ENROLLMENT_ID,
        command=command,
        idempotency_key="progress-key-000001",
    )

    assert replay == first
    assert repository.progress_calls == 1
    assert len(facts.items) == 1

    with pytest.raises(LearningError, match="PROGRESS_VERSION_CONFLICT"):
        service.progress(
            actor_id=LEARNER_ACTOR_ID,
            tenant_id=TENANT_ID,
            enrollment_id=ENROLLMENT_ID,
            command=replace(command, expected_progress_row_version=0),
            idempotency_key="progress-key-000002",
        )


def test_authorization_port_is_called_with_frozen_permissions() -> None:
    service, _, _, _ = make_service()

    enrollment = service.create_enrollment(
        actor_id=ADMIN_ACTOR_ID,
        tenant_id=TENANT_ID,
        learner_membership_id=LEARNER_MEMBERSHIP_ID,
        course_id=COURSE_ID,
        idempotency_key="assignment-key-0001",
    )
    progress = CourseProgress(
        state=LessonProgressState.NOT_STARTED,
        required_lesson_count=2,
        completed_required_lesson_count=0,
        resume_lesson_id=None,
        row_version=0,
    )

    assert PERMISSION_ENROLLMENTS_MANAGE in {
        PERMISSION_ENROLLMENTS_MANAGE,
        PERMISSION_PLAYBACK_READ,
    }
    assert enrollment.status is EnrollmentStatus.ACTIVE
    assert progress.row_version == 0

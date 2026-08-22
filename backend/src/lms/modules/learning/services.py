from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from .errors import FieldError, LearningError, validation_failed
from .policies import (
    PERMISSION_ENROLLMENTS_MANAGE,
    PERMISSION_PLAYBACK_READ,
    require_permission,
)
from .types import (
    AuthorizedActor,
    Enrollment,
    IdempotencyRecord,
    JsonObject,
    LearnerDashboard,
    LearningFact,
    LessonPlayback,
    PlaybackSnapshot,
    ProgressCommand,
    ProgressCommandName,
    ProgressMutation,
    ProgressResult,
)

_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


class AuthorizationPort(Protocol):
    def authorize(self, *, actor_id: UUID, tenant_id: UUID, permission: str) -> AuthorizedActor: ...


class LearningRepositoryPort(Protocol):
    def create_enrollment(
        self,
        *,
        enrollment_id: UUID,
        tenant_id: UUID,
        learner_membership_id: UUID,
        course_id: UUID,
        actor_id: UUID,
        enrolled_at: datetime,
    ) -> Enrollment: ...

    def revoke_enrollment(
        self,
        *,
        tenant_id: UUID,
        enrollment_id: UUID,
        expected_enrollment_row_version: int,
        reason_code: str,
        revoked_at: datetime,
    ) -> Enrollment: ...

    def list_dashboard(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> LearnerDashboard: ...

    def get_playback(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        enrollment_id: UUID,
    ) -> PlaybackSnapshot: ...

    def get_lesson(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        enrollment_id: UUID,
        lesson_id: UUID,
    ) -> LessonPlayback: ...

    def apply_progress(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        enrollment_id: UUID,
        lesson_id: UUID,
        command: ProgressCommandName,
        expected_progress_row_version: int,
        updated_at: datetime,
    ) -> ProgressMutation: ...


class IdempotencyPort(Protocol):
    def reserve(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord: ...

    def complete(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
        response: Enrollment | ProgressResult,
    ) -> None: ...


class FactWriterPort(Protocol):
    def append(self, *facts: LearningFact) -> None: ...


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


def canonical_request_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class LearningService:
    def __init__(
        self,
        *,
        authorization: AuthorizationPort,
        repository: LearningRepositoryPort,
        idempotency: IdempotencyPort,
        facts: FactWriterPort,
        unit_of_work: Callable[[], AbstractContextManager[None]],
        ids: UUIDFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._authorization = authorization
        self._repository = repository
        self._idempotency = idempotency
        self._facts = facts
        self._unit_of_work = unit_of_work
        self._ids = ids or RandomUUIDFactory()
        self._clock = clock or SystemClock()

    @staticmethod
    def _validate_idempotency_key(key: str) -> None:
        if not 16 <= len(key) <= 128:
            raise validation_failed(
                FieldError(
                    path="idempotency_key",
                    code="invalid_length",
                    detail="The idempotency key is outside the bounded contract.",
                )
            )

    def _authorize(self, *, actor_id: UUID, tenant_id: UUID, permission: str) -> AuthorizedActor:
        actor = self._authorization.authorize(
            actor_id=actor_id,
            tenant_id=tenant_id,
            permission=permission,
        )
        if actor.principal_id != actor_id or actor.tenant_id != tenant_id:
            raise LearningError("SERVICE_CONTRACT_ERROR")
        require_permission(actor, permission)
        return actor

    def _reserve(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
    ) -> Enrollment | ProgressResult | None:
        record = self._idempotency.reserve(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if record.request_hash != request_hash:
            raise LearningError("IDEMPOTENCY_CONFLICT")
        if record.response is not None:
            return record.response
        if not record.created:
            raise LearningError("IDEMPOTENCY_CONFLICT")
        return None

    def create_enrollment(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        learner_membership_id: UUID,
        course_id: UUID,
        idempotency_key: str,
    ) -> Enrollment:
        self._validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(
            {
                "learner_membership_id": str(learner_membership_id),
                "course_id": str(course_id),
            }
        )
        with self._unit_of_work():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_ENROLLMENTS_MANAGE,
            )
            replay = self._reserve(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operation="learning.create_enrollment",
                key=idempotency_key,
                request_hash=request_hash,
            )
            if replay is not None:
                if not isinstance(replay, Enrollment):
                    raise LearningError("SERVICE_CONTRACT_ERROR")
                return replay
            now = self._clock.now()
            enrollment = self._repository.create_enrollment(
                enrollment_id=self._ids.new_uuid(),
                tenant_id=tenant_id,
                learner_membership_id=learner_membership_id,
                course_id=course_id,
                actor_id=actor_id,
                enrolled_at=now,
            )
            self._require_enrollment_scope(
                enrollment,
                tenant_id=tenant_id,
                learner_membership_id=learner_membership_id,
                course_id=course_id,
            )
            fact = LearningFact(
                id=self._ids.new_uuid(),
                tenant_id=tenant_id,
                event_type="learning.enrollment.created.v1",
                aggregate_type="enrollment",
                aggregate_id=enrollment.id,
                aggregate_version=enrollment.row_version,
                actor_id=actor_id,
                occurred_at=now,
                payload={
                    "enrollment_id": str(enrollment.id),
                    "learner_membership_id": str(enrollment.learner_membership_id),
                    "course_id": str(enrollment.course_id),
                    "course_version_id": str(enrollment.course_version_id),
                    "admission_source": enrollment.admission_source,
                    "status": enrollment.status.value,
                    "aggregate_version": enrollment.row_version,
                },
            )
            self._facts.append(fact)
            self._idempotency.complete(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operation="learning.create_enrollment",
                key=idempotency_key,
                request_hash=request_hash,
                response=enrollment,
            )
            return enrollment

    def revoke_enrollment(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        expected_enrollment_row_version: int,
        reason_code: str,
        idempotency_key: str,
    ) -> Enrollment:
        self._validate_idempotency_key(idempotency_key)
        if expected_enrollment_row_version < 1 or _REASON_CODE.fullmatch(reason_code) is None:
            raise validation_failed()
        request_hash = canonical_request_hash(
            {
                "enrollment_id": str(enrollment_id),
                "expected_enrollment_row_version": expected_enrollment_row_version,
                "reason_code": reason_code,
            }
        )
        with self._unit_of_work():
            self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_ENROLLMENTS_MANAGE,
            )
            replay = self._reserve(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operation="learning.revoke_enrollment",
                key=idempotency_key,
                request_hash=request_hash,
            )
            if replay is not None:
                if not isinstance(replay, Enrollment):
                    raise LearningError("SERVICE_CONTRACT_ERROR")
                return replay
            now = self._clock.now()
            enrollment = self._repository.revoke_enrollment(
                tenant_id=tenant_id,
                enrollment_id=enrollment_id,
                expected_enrollment_row_version=expected_enrollment_row_version,
                reason_code=reason_code,
                revoked_at=now,
            )
            if enrollment.tenant_id != tenant_id or enrollment.id != enrollment_id:
                raise LearningError("SERVICE_CONTRACT_ERROR")
            fact = LearningFact(
                id=self._ids.new_uuid(),
                tenant_id=tenant_id,
                event_type="learning.enrollment.revoked.v1",
                aggregate_type="enrollment",
                aggregate_id=enrollment.id,
                aggregate_version=enrollment.row_version,
                actor_id=actor_id,
                occurred_at=now,
                payload={
                    "enrollment_id": str(enrollment.id),
                    "learner_membership_id": str(enrollment.learner_membership_id),
                    "course_id": str(enrollment.course_id),
                    "course_version_id": str(enrollment.course_version_id),
                    "status": enrollment.status.value,
                    "reason_code": reason_code,
                    "aggregate_version": enrollment.row_version,
                },
            )
            self._facts.append(fact)
            self._idempotency.complete(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operation="learning.revoke_enrollment",
                key=idempotency_key,
                request_hash=request_hash,
                response=enrollment,
            )
            return enrollment

    def list_dashboard(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> LearnerDashboard:
        if not 1 <= limit <= 50:
            raise validation_failed()
        with self._unit_of_work():
            actor = self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_PLAYBACK_READ,
            )
            if actor.membership_id is None:
                raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
            return self._repository.list_dashboard(
                tenant_id=tenant_id,
                learner_membership_id=actor.membership_id,
                cursor=cursor,
                limit=limit,
            )

    def get_playback(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
    ) -> PlaybackSnapshot:
        with self._unit_of_work():
            actor = self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_PLAYBACK_READ,
            )
            if actor.membership_id is None:
                raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
            return self._repository.get_playback(
                tenant_id=tenant_id,
                learner_membership_id=actor.membership_id,
                enrollment_id=enrollment_id,
            )

    def get_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        lesson_id: UUID,
    ) -> LessonPlayback:
        with self._unit_of_work():
            actor = self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_PLAYBACK_READ,
            )
            if actor.membership_id is None:
                raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
            return self._repository.get_lesson(
                tenant_id=tenant_id,
                learner_membership_id=actor.membership_id,
                enrollment_id=enrollment_id,
                lesson_id=lesson_id,
            )

    def progress(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommand,
        idempotency_key: str,
    ) -> ProgressResult:
        self._validate_idempotency_key(idempotency_key)
        if command.expected_progress_row_version < 0:
            raise validation_failed()
        request_hash = canonical_request_hash(
            {
                "enrollment_id": str(enrollment_id),
                "command": command.command.value,
                "lesson_id": str(command.lesson_id),
                "expected_progress_row_version": command.expected_progress_row_version,
            }
        )
        operation = f"learning.progress.{command.command.value}"
        with self._unit_of_work():
            actor = self._authorize(
                actor_id=actor_id,
                tenant_id=tenant_id,
                permission=PERMISSION_PLAYBACK_READ,
            )
            if actor.membership_id is None:
                raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
            replay = self._reserve(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operation=operation,
                key=idempotency_key,
                request_hash=request_hash,
            )
            if replay is not None:
                if not isinstance(replay, ProgressResult):
                    raise LearningError("SERVICE_CONTRACT_ERROR")
                return replay
            now = self._clock.now()
            mutation = self._repository.apply_progress(
                tenant_id=tenant_id,
                learner_membership_id=actor.membership_id,
                enrollment_id=enrollment_id,
                lesson_id=command.lesson_id,
                command=command.command,
                expected_progress_row_version=command.expected_progress_row_version,
                updated_at=now,
            )
            result = mutation.result
            if (
                result.tenant_id != tenant_id
                or result.enrollment_id != enrollment_id
                or result.lesson_id != command.lesson_id
            ):
                raise LearningError("SERVICE_CONTRACT_ERROR")
            facts = self._progress_facts(
                actor_id=actor_id,
                command=command.command,
                mutation=mutation,
            )
            self._facts.append(*facts)
            self._idempotency.complete(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operation=operation,
                key=idempotency_key,
                request_hash=request_hash,
                response=result,
            )
            return result

    def _progress_facts(
        self,
        *,
        actor_id: UUID,
        command: ProgressCommandName,
        mutation: ProgressMutation,
    ) -> tuple[LearningFact, ...]:
        result = mutation.result
        shared: JsonObject = {
            "enrollment_id": str(result.enrollment_id),
            "course_version_id": str(result.course_version_id),
            "lesson_id": str(result.lesson_id),
            "aggregate_version": result.progress_row_version,
        }
        facts = [
            LearningFact(
                id=self._ids.new_uuid(),
                tenant_id=result.tenant_id,
                event_type="learning.lesson.progressed.v1",
                aggregate_type="enrollment_progress",
                aggregate_id=result.enrollment_id,
                aggregate_version=result.progress_row_version,
                actor_id=actor_id,
                occurred_at=result.updated_at,
                payload={
                    **shared,
                    "command": command.value,
                    "previous_lesson_state": mutation.previous_lesson_state.value,
                    "lesson_state": result.lesson_state.value,
                },
            )
        ]
        if (
            mutation.previous_course_state.value != "completed"
            and result.course_state.value == "completed"
        ):
            facts.append(
                LearningFact(
                    id=self._ids.new_uuid(),
                    tenant_id=result.tenant_id,
                    event_type="learning.course.completed.v1",
                    aggregate_type="enrollment_progress",
                    aggregate_id=result.enrollment_id,
                    aggregate_version=result.progress_row_version,
                    actor_id=actor_id,
                    occurred_at=result.updated_at,
                    payload={
                        "enrollment_id": str(result.enrollment_id),
                        "course_version_id": str(result.course_version_id),
                        "required_lesson_count": result.required_lesson_count,
                        "completed_required_lesson_count": (result.completed_required_lesson_count),
                        "aggregate_version": result.progress_row_version,
                    },
                )
            )
        elif (
            mutation.previous_course_state.value == "completed"
            and result.course_state.value != "completed"
        ):
            facts.append(
                LearningFact(
                    id=self._ids.new_uuid(),
                    tenant_id=result.tenant_id,
                    event_type="learning.course.reopened.v1",
                    aggregate_type="enrollment_progress",
                    aggregate_id=result.enrollment_id,
                    aggregate_version=result.progress_row_version,
                    actor_id=actor_id,
                    occurred_at=result.updated_at,
                    payload={
                        "enrollment_id": str(result.enrollment_id),
                        "course_version_id": str(result.course_version_id),
                        "lesson_id": str(result.lesson_id),
                        "required_lesson_count": result.required_lesson_count,
                        "completed_required_lesson_count": (result.completed_required_lesson_count),
                        "aggregate_version": result.progress_row_version,
                    },
                )
            )
        return tuple(facts)

    @staticmethod
    def _require_enrollment_scope(
        enrollment: Enrollment,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        course_id: UUID,
    ) -> None:
        if (
            enrollment.tenant_id != tenant_id
            or enrollment.learner_membership_id != learner_membership_id
            or enrollment.course_id != course_id
            or enrollment.admission_source != "manual_assignment"
        ):
            raise LearningError("SERVICE_CONTRACT_ERROR")

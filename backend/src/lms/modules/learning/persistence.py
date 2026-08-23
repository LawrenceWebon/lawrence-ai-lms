from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

from django.db import connection

from lms.modules.tenancy.models import AuditFact, IdempotencyReservation, OutboxFact

from .errors import LearningError
from .types import (
    CourseProgressState,
    Enrollment,
    EnrollmentStatus,
    IdempotencyRecord,
    LearningFact,
    LessonProgressState,
    ProgressResult,
)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LearningError("SERVICE_CONTRACT_ERROR")
    return cast(Mapping[str, object], value)


def _enrollment_payload(value: Enrollment) -> dict[str, object]:
    return {
        "id": str(value.id),
        "tenant_id": str(value.tenant_id),
        "learner_membership_id": str(value.learner_membership_id),
        "course_id": str(value.course_id),
        "course_version_id": str(value.course_version_id),
        "admission_source": value.admission_source,
        "status": value.status.value,
        "enrolled_at": value.enrolled_at.isoformat(),
        "revoked_at": None if value.revoked_at is None else value.revoked_at.isoformat(),
        "row_version": value.row_version,
    }


def _progress_payload(value: ProgressResult) -> dict[str, object]:
    return {
        "tenant_id": str(value.tenant_id),
        "enrollment_id": str(value.enrollment_id),
        "course_version_id": str(value.course_version_id),
        "lesson_id": str(value.lesson_id),
        "lesson_state": value.lesson_state.value,
        "course_state": value.course_state.value,
        "required_lesson_count": value.required_lesson_count,
        "completed_required_lesson_count": value.completed_required_lesson_count,
        "resume_lesson_id": (
            None if value.resume_lesson_id is None else str(value.resume_lesson_id)
        ),
        "progress_row_version": value.progress_row_version,
        "updated_at": value.updated_at.isoformat(),
    }


def _response_payload(value: Enrollment | ProgressResult) -> dict[str, object]:
    if isinstance(value, Enrollment):
        return {"kind": "enrollment", "response": _enrollment_payload(value)}
    return {"kind": "progress_result", "response": _progress_payload(value)}


def _response_from_payload(value: object) -> Enrollment | ProgressResult:
    payload = _mapping(value)
    response = _mapping(payload.get("response"))
    try:
        if payload.get("kind") == "enrollment":
            revoked_at = response["revoked_at"]
            return Enrollment(
                id=UUID(cast(str, response["id"])),
                tenant_id=UUID(cast(str, response["tenant_id"])),
                learner_membership_id=UUID(cast(str, response["learner_membership_id"])),
                course_id=UUID(cast(str, response["course_id"])),
                course_version_id=UUID(cast(str, response["course_version_id"])),
                admission_source=cast(str, response["admission_source"]),
                status=EnrollmentStatus(cast(str, response["status"])),
                enrolled_at=datetime.fromisoformat(cast(str, response["enrolled_at"])),
                revoked_at=(
                    None if revoked_at is None else datetime.fromisoformat(cast(str, revoked_at))
                ),
                row_version=int(cast(int, response["row_version"])),
            )
        if payload.get("kind") == "progress_result":
            resume_lesson_id = response["resume_lesson_id"]
            return ProgressResult(
                tenant_id=UUID(cast(str, response["tenant_id"])),
                enrollment_id=UUID(cast(str, response["enrollment_id"])),
                course_version_id=UUID(cast(str, response["course_version_id"])),
                lesson_id=UUID(cast(str, response["lesson_id"])),
                lesson_state=LessonProgressState(cast(str, response["lesson_state"])),
                course_state=CourseProgressState(cast(str, response["course_state"])),
                required_lesson_count=int(cast(int, response["required_lesson_count"])),
                completed_required_lesson_count=int(
                    cast(int, response["completed_required_lesson_count"])
                ),
                resume_lesson_id=(
                    None if resume_lesson_id is None else UUID(cast(str, resume_lesson_id))
                ),
                progress_row_version=int(cast(int, response["progress_row_version"])),
                updated_at=datetime.fromisoformat(cast(str, response["updated_at"])),
            )
    except (KeyError, TypeError, ValueError) as error:
        raise LearningError("SERVICE_CONTRACT_ERROR") from error
    raise LearningError("SERVICE_CONTRACT_ERROR")


class DjangoLearningIdempotency:
    @staticmethod
    def _key_digest(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def reserve(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        operation: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord:
        reservation, created = IdempotencyReservation.objects.get_or_create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation=operation,
            key_digest=self._key_digest(key),
            defaults={"request_hash": request_hash},
        )
        reservation = IdempotencyReservation.objects.select_for_update().get(id=reservation.id)
        if reservation.request_hash != request_hash:
            raise LearningError("IDEMPOTENCY_CONFLICT")
        response = None
        if reservation.status == "completed":
            response = _response_from_payload(reservation.response_payload)
        return IdempotencyRecord(
            request_hash=reservation.request_hash,
            created=created,
            response=response,
        )

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
        reservation = (
            IdempotencyReservation.objects.select_for_update()
            .filter(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operation=operation,
                key_digest=self._key_digest(key),
            )
            .first()
        )
        if (
            reservation is None
            or reservation.request_hash != request_hash
            or reservation.status != "reserved"
        ):
            raise LearningError("SERVICE_CONTRACT_ERROR")
        reservation.status = "completed"
        reservation.response_payload = _response_payload(response)
        reservation.save(update_fields=("status", "response_payload", "updated_at"))


class DjangoLearningFacts:
    def append(self, *facts: LearningFact) -> None:
        request_id = self._request_id()
        for fact in facts:
            AuditFact.objects.create(
                id=fact.id,
                tenant_id=fact.tenant_id,
                event_type=fact.event_type,
                actor_id=fact.actor_id,
                subject_type=fact.aggregate_type,
                subject_id=fact.aggregate_id,
                request_id=request_id,
                payload=fact.payload,
            )
            OutboxFact.objects.create(
                id=fact.id,
                tenant_id=fact.tenant_id,
                event_type=fact.event_type,
                aggregate_type=fact.aggregate_type,
                aggregate_id=fact.aggregate_id,
                actor_id=fact.actor_id,
                request_id=request_id,
                payload=fact.payload,
            )

    @staticmethod
    def _request_id() -> UUID:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_request_id', true)")
            row = cursor.fetchone()
        if row is None or not row[0]:
            return uuid.uuid4()
        try:
            return UUID(str(row[0]))
        except ValueError as error:
            raise LearningError("SERVICE_CONTRACT_ERROR") from error

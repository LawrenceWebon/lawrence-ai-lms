from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

ALPHA_TENANT_ID = UUID("00000000-0000-4000-8000-0000000000a1")
BETA_TENANT_ID = UUID("00000000-0000-4000-8000-0000000000b1")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000103")
ENROLLMENT_ID = UUID("00000000-0000-4000-8000-00000000e001")
LESSON_ID = UUID("00000000-0000-4000-8000-00000000c302")
IDEMPOTENCY_KEY = "learning-command-000001"
REPO_ROOT = Path(__file__).resolve().parents[3]


def load_examples() -> dict[str, Any]:
    return json.loads(
        (REPO_ROOT / "contracts/f007/learner-playback.v1.examples.json").read_text(encoding="utf-8")
    )


@dataclass(frozen=True, slots=True)
class VerifiedActorValue:
    principal_id: UUID


@dataclass(frozen=True, slots=True)
class Call:
    operation: str
    actor_id: UUID
    tenant_id: UUID
    enrollment_id: UUID | None = None
    lesson_id: UUID | None = None
    idempotency_key: str | None = None
    cursor: str | None = None
    limit: int | None = None
    command: object | None = None


class RecordingLearningServiceFake:
    def __init__(self) -> None:
        examples = load_examples()
        self.enrollment = copy.deepcopy(examples["EnrollmentV1"])
        self.dashboard = copy.deepcopy(examples["LearnerDashboardV1"])
        self.playback = copy.deepcopy(examples["PlaybackSnapshotV1"])
        self.lesson = copy.deepcopy(examples["LessonPlaybackV1"])
        self.progress = copy.deepcopy(examples["ProgressResultV1"])
        self.calls: list[Call] = []
        self.problem_by_operation: dict[str, Exception] = {}

    def _record(self, call: Call, response: object) -> object:
        problem = self.problem_by_operation.get(call.operation)
        if problem is not None:
            raise problem
        self.calls.append(call)
        return copy.deepcopy(response)

    def create_enrollment(self, **kwargs: Any) -> object:
        return self._record(
            Call(
                "create_enrollment",
                kwargs["actor_id"],
                kwargs["tenant_id"],
                idempotency_key=kwargs["idempotency_key"],
                command=kwargs["command"],
            ),
            self.enrollment,
        )

    def revoke_enrollment(self, **kwargs: Any) -> object:
        response = copy.deepcopy(self.enrollment)
        response["status"] = "revoked"
        response["revoked_at"] = "2026-08-21T00:06:00Z"
        response["row_version"] = 2
        return self._record(
            Call(
                "revoke_enrollment",
                kwargs["actor_id"],
                kwargs["tenant_id"],
                enrollment_id=kwargs["enrollment_id"],
                idempotency_key=kwargs["idempotency_key"],
                command=kwargs["command"],
            ),
            response,
        )

    def list_learner_courses(self, **kwargs: Any) -> object:
        return self._record(
            Call(
                "list_learner_courses",
                kwargs["actor_id"],
                kwargs["tenant_id"],
                cursor=kwargs["cursor"],
                limit=kwargs["limit"],
            ),
            self.dashboard,
        )

    def get_learner_playback(self, **kwargs: Any) -> object:
        return self._record(
            Call(
                "get_learner_playback",
                kwargs["actor_id"],
                kwargs["tenant_id"],
                enrollment_id=kwargs["enrollment_id"],
            ),
            self.playback,
        )

    def get_learner_lesson(self, **kwargs: Any) -> object:
        return self._record(
            Call(
                "get_learner_lesson",
                kwargs["actor_id"],
                kwargs["tenant_id"],
                enrollment_id=kwargs["enrollment_id"],
                lesson_id=kwargs["lesson_id"],
            ),
            self.lesson,
        )

    def _progress(self, operation: str, kwargs: dict[str, Any]) -> object:
        return self._record(
            Call(
                operation,
                kwargs["actor_id"],
                kwargs["tenant_id"],
                enrollment_id=kwargs["enrollment_id"],
                lesson_id=kwargs["command"].lesson_id,
                idempotency_key=kwargs["idempotency_key"],
                command=kwargs["command"],
            ),
            self.progress,
        )

    def open_lesson(self, **kwargs: Any) -> object:
        return self._progress("open_lesson", kwargs)

    def complete_lesson(self, **kwargs: Any) -> object:
        return self._progress("complete_lesson", kwargs)

    def reopen_lesson(self, **kwargs: Any) -> object:
        return self._progress("reopen_lesson", kwargs)

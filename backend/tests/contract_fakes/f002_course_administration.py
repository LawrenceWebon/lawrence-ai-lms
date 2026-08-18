from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[3]
LIFECYCLE_EXAMPLES_PATH = REPO_ROOT / "contracts/f002/course-lifecycle.v1.examples.json"

ALPHA_TENANT_ID: Final = UUID("00000000-0000-4000-8000-0000000000a1")
BETA_TENANT_ID: Final = UUID("00000000-0000-4000-8000-0000000000b1")
ACTOR_ID: Final = UUID("00000000-0000-4000-8000-000000000101")
OUTSIDER_ID: Final = UUID("00000000-0000-4000-8000-000000000105")
COURSE_ID: Final = UUID("00000000-0000-4000-8000-00000000c001")
VERSION_ID: Final = UUID("00000000-0000-4000-8000-00000000c101")
IDEMPOTENCY_KEY: Final = "fixture-course-command-0001"


def load_lifecycle_examples() -> dict[str, object]:
    return json.loads(LIFECYCLE_EXAMPLES_PATH.read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class VerifiedActorValue:
    principal_id: UUID


@dataclass(frozen=True, slots=True)
class ServiceCall:
    operation: str
    actor_id: UUID
    tenant_id: UUID
    course_id: UUID | None = None
    version_id: UUID | None = None
    source_version_id: UUID | None = None
    command: object | None = None
    idempotency_key: str | None = None
    cursor: str | None = None
    limit: int | None = None


class RecordingCourseAdministrationServiceFake:
    """Structural Lane B/C fake backed only by synthetic committed examples."""

    def __init__(self) -> None:
        examples = load_lifecycle_examples()
        self.snapshot = examples["CourseSnapshotV1"]
        self.history = examples["CourseVersionHistoryV1"]
        self.successor = examples["SuccessorDraftResultV1"]
        self.calls: list[ServiceCall] = []
        self.problem_by_operation: dict[str, Exception] = {}
        self.response_by_operation: dict[str, object] = {}

    def _result(self, operation: str, default: object) -> object:
        problem = self.problem_by_operation.get(operation)
        if problem is not None:
            raise problem
        return copy.deepcopy(self.response_by_operation.get(operation, default))

    def create_course(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: object,
        idempotency_key: str,
    ) -> object:
        self.calls.append(
            ServiceCall(
                operation="create_course",
                actor_id=actor_id,
                tenant_id=tenant_id,
                command=command,
                idempotency_key=idempotency_key,
            )
        )
        return self._result("create_course", self.snapshot)

    def get_course_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
    ) -> object:
        self.calls.append(
            ServiceCall(
                operation="get_course_version",
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
            )
        )
        return self._result("get_course_version", self.snapshot)

    def list_course_versions(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> object:
        self.calls.append(
            ServiceCall(
                operation="list_course_versions",
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                cursor=cursor,
                limit=limit,
            )
        )
        return self._result("list_course_versions", self.history)

    def update_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: object,
    ) -> object:
        self.calls.append(
            ServiceCall(
                operation="update_version",
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
                command=command,
            )
        )
        return self._result("update_version", self.snapshot)

    def replace_curriculum(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: object,
    ) -> object:
        self.calls.append(
            ServiceCall(
                operation="replace_curriculum",
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
                command=command,
            )
        )
        return self._result("replace_curriculum", self.snapshot)

    def transition_version(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: object,
        idempotency_key: str,
    ) -> object:
        self.calls.append(
            ServiceCall(
                operation="transition_version",
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                version_id=version_id,
                command=command,
                idempotency_key=idempotency_key,
            )
        )
        return self._result("transition_version", self.snapshot)

    def create_successor_draft(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        course_id: UUID,
        source_version_id: UUID,
        command: object,
        idempotency_key: str,
    ) -> object:
        self.calls.append(
            ServiceCall(
                operation="create_successor_draft",
                actor_id=actor_id,
                tenant_id=tenant_id,
                course_id=course_id,
                source_version_id=source_version_id,
                command=command,
                idempotency_key=idempotency_key,
            )
        )
        return self._result("create_successor_draft", self.successor)

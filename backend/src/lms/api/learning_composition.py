from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import cast
from uuid import UUID

from django.db import transaction
from pydantic import ValidationError

from lms.api.schemas.courses import RichTextDocument
from lms.api.schemas.learning import (
    CreateEnrollmentV1,
    LearningAdministrationError,
    ProgressCommandV1,
    RevokeEnrollmentV1,
)
from lms.modules.courses.repositories import CourseRepository
from lms.modules.learning.errors import LearningError
from lms.modules.learning.persistence import DjangoLearningFacts, DjangoLearningIdempotency
from lms.modules.learning.repositories import DjangoLearningRepository
from lms.modules.learning.services import LearningService
from lms.modules.learning.types import (
    AuthorizedActor,
    JsonObject,
    ProgressCommand,
    ProgressCommandName,
    PublishedContentBlock,
    PublishedCourse,
    PublishedLesson,
    PublishedSection,
)
from lms.modules.tenancy import services as tenancy_services
from lms.modules.tenancy.errors import TenancyError


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LearningError("SERVICE_CONTRACT_ERROR")
    return cast(Mapping[str, object], value)


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise LearningError("SERVICE_CONTRACT_ERROR")
    return cast(Sequence[object], value)


class DjangoPublishedCourseReader:
    """Infrastructure adapter exposing only learner-safe F-002 publication data."""

    def __init__(self, repository: CourseRepository | None = None) -> None:
        self._repository = repository or CourseRepository()

    def lock_current_published(self, *, tenant_id: UUID, course_id: UUID) -> PublishedCourse | None:
        course_version_id = self._repository.lock_current_published_version_id(
            tenant_id,
            course_id,
        )
        if course_version_id is None:
            return None
        return self.load_published(
            tenant_id=tenant_id,
            course_id=course_id,
            course_version_id=course_version_id,
        )

    def load_published(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        course_version_id: UUID,
    ) -> PublishedCourse | None:
        snapshot = self._repository.load_snapshot(tenant_id, course_id, course_version_id)
        if snapshot is None:
            return None
        course = _mapping(snapshot.get("course"))
        version = _mapping(snapshot.get("version"))
        try:
            if (
                UUID(cast(str, course["id"])) != course_id
                or UUID(cast(str, course["tenant_id"])) != tenant_id
                or UUID(cast(str, version["id"])) != course_version_id
                or UUID(cast(str, version["tenant_id"])) != tenant_id
                or UUID(cast(str, version["course_id"])) != course_id
                or version["status"] != "published"
                or version["primary_locale"] != "en"
            ):
                return None
            sections = tuple(
                self._section(
                    value,
                    tenant_id=tenant_id,
                    course_version_id=course_version_id,
                )
                for value in _sequence(snapshot.get("sections"))
            )
            return PublishedCourse(
                tenant_id=tenant_id,
                course_id=course_id,
                course_version_id=course_version_id,
                course_version_number=int(cast(int, version["version_number"])),
                primary_locale="en",
                title=cast(str, version["title"]),
                description=cast(str, version["description"]),
                content_hash=cast(str, version["content_hash"]),
                sections=sections,
            )
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise LearningError("SERVICE_CONTRACT_ERROR") from error

    @staticmethod
    def _section(
        value: object,
        *,
        tenant_id: UUID,
        course_version_id: UUID,
    ) -> PublishedSection:
        section = _mapping(value)
        section_id = UUID(cast(str, section["id"]))
        if (
            UUID(cast(str, section["tenant_id"])) != tenant_id
            or UUID(cast(str, section["course_version_id"])) != course_version_id
        ):
            raise LearningError("SERVICE_CONTRACT_ERROR")
        lessons = tuple(
            DjangoPublishedCourseReader._lesson(
                item,
                tenant_id=tenant_id,
                course_version_id=course_version_id,
                section_id=section_id,
            )
            for item in _sequence(section["lessons"])
        )
        return PublishedSection(
            id=section_id,
            title=cast(str, section["title"]),
            position=int(cast(int, section["position"])),
            lessons=lessons,
        )

    @staticmethod
    def _lesson(
        value: object,
        *,
        tenant_id: UUID,
        course_version_id: UUID,
        section_id: UUID,
    ) -> PublishedLesson:
        lesson = _mapping(value)
        lesson_id = UUID(cast(str, lesson["id"]))
        if (
            UUID(cast(str, lesson["tenant_id"])) != tenant_id
            or UUID(cast(str, lesson["course_version_id"])) != course_version_id
            or UUID(cast(str, lesson["section_id"])) != section_id
        ):
            raise LearningError("SERVICE_CONTRACT_ERROR")
        blocks: list[PublishedContentBlock] = []
        for value in _sequence(lesson["content_blocks"]):
            block = _mapping(value)
            if (
                UUID(cast(str, block["tenant_id"])) != tenant_id
                or UUID(cast(str, block["course_version_id"])) != course_version_id
                or UUID(cast(str, block["lesson_id"])) != lesson_id
                or block["kind"] != "rich_text"
            ):
                raise LearningError("SERVICE_CONTRACT_ERROR")
            document = RichTextDocument.model_validate(block["document"])
            blocks.append(
                PublishedContentBlock(
                    id=UUID(cast(str, block["id"])),
                    kind="rich_text",
                    position=int(cast(int, block["position"])),
                    document=cast(JsonObject, document.model_dump(mode="python")),
                )
            )
        return PublishedLesson(
            id=lesson_id,
            section_id=section_id,
            title=cast(str, lesson["title"]),
            position=int(cast(int, lesson["position"])),
            is_required=cast(bool, lesson["is_required"]),
            content_blocks=tuple(blocks),
        )


class DjangoLearningAuthorization:
    def authorize(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        permission: str,
    ) -> AuthorizedActor:
        try:
            membership = tenancy_services.authorize_tenant_permission(
                actor_id,
                tenant_id,
                permission,
            )
        except TenancyError as error:
            code = (
                "TENANT_ACCESS_INACTIVE"
                if error.code == "TENANT_ACCESS_INACTIVE"
                else "LEARNING_RESOURCE_NOT_FOUND"
            )
            raise LearningError(code) from error
        return AuthorizedActor(
            principal_id=actor_id,
            tenant_id=tenant_id,
            membership_id=membership.id,
            permissions=frozenset(membership.permission_codes),
        )


@contextmanager
def _learning_transaction() -> Iterator[None]:
    with transaction.atomic():
        yield


def _translate[Result](operation: Callable[[], Result]) -> Result:
    try:
        return operation()
    except LearningError as error:
        raise LearningAdministrationError(
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


class DjangoLearningService:
    """Real API/Admin adapter over one transactional Learning application service."""

    def __init__(self) -> None:
        self._service = LearningService(
            authorization=DjangoLearningAuthorization(),
            repository=DjangoLearningRepository(courses=DjangoPublishedCourseReader()),
            idempotency=DjangoLearningIdempotency(),
            facts=DjangoLearningFacts(),
            unit_of_work=_learning_transaction,
        )

    def create_enrollment(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        command: CreateEnrollmentV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.create_enrollment(
                actor_id=actor_id,
                tenant_id=tenant_id,
                learner_membership_id=command.learner_membership_id,
                course_id=command.course_id,
                idempotency_key=idempotency_key,
            )
        )

    def revoke_enrollment(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: RevokeEnrollmentV1,
        idempotency_key: str,
    ) -> object:
        return _translate(
            lambda: self._service.revoke_enrollment(
                actor_id=actor_id,
                tenant_id=tenant_id,
                enrollment_id=enrollment_id,
                expected_enrollment_row_version=command.expected_enrollment_row_version,
                reason_code=command.reason_code,
                idempotency_key=idempotency_key,
            )
        )

    def list_learner_courses(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> object:
        return _translate(
            lambda: self._service.list_dashboard(
                actor_id=actor_id,
                tenant_id=tenant_id,
                cursor=cursor,
                limit=limit,
            )
        )

    def get_learner_playback(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
    ) -> object:
        return _translate(
            lambda: self._service.get_playback(
                actor_id=actor_id,
                tenant_id=tenant_id,
                enrollment_id=enrollment_id,
            )
        )

    def get_learner_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        lesson_id: UUID,
    ) -> object:
        return _translate(
            lambda: self._service.get_lesson(
                actor_id=actor_id,
                tenant_id=tenant_id,
                enrollment_id=enrollment_id,
                lesson_id=lesson_id,
            )
        )

    def _progress(
        self,
        *,
        expected: ProgressCommandName,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
    ) -> object:
        if command.command != expected.value:
            raise LearningAdministrationError(
                code="ENROLLMENT_VALIDATION_FAILED",
                status=422,
                errors=({"location": ("body", "command")},),
            )
        return _translate(
            lambda: self._service.progress(
                actor_id=actor_id,
                tenant_id=tenant_id,
                enrollment_id=enrollment_id,
                command=ProgressCommand(
                    command=expected,
                    lesson_id=command.lesson_id,
                    expected_progress_row_version=command.expected_progress_row_version,
                ),
                idempotency_key=idempotency_key,
            )
        )

    def open_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
    ) -> object:
        return self._progress(
            expected=ProgressCommandName.OPEN_LESSON,
            actor_id=actor_id,
            tenant_id=tenant_id,
            enrollment_id=enrollment_id,
            command=command,
            idempotency_key=idempotency_key,
        )

    def complete_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
    ) -> object:
        return self._progress(
            expected=ProgressCommandName.COMPLETE_LESSON,
            actor_id=actor_id,
            tenant_id=tenant_id,
            enrollment_id=enrollment_id,
            command=command,
            idempotency_key=idempotency_key,
        )

    def reopen_lesson(
        self,
        *,
        actor_id: UUID,
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
    ) -> object:
        return self._progress(
            expected=ProgressCommandName.REOPEN_LESSON,
            actor_id=actor_id,
            tenant_id=tenant_id,
            enrollment_id=enrollment_id,
            command=command,
            idempotency_key=idempotency_key,
        )

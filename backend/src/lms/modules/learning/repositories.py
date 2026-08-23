from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from lms.modules.tenancy.models import MembershipRole, TenantMembership

from .errors import FieldError, LearningError, validation_failed
from .models import CourseProgress as CourseProgressModel
from .models import Enrollment as EnrollmentModel
from .models import LessonProgress as LessonProgressModel
from .types import (
    CourseProgress,
    CourseProgressState,
    DashboardCard,
    Enrollment,
    EnrollmentStatus,
    JsonObject,
    LearnerDashboard,
    LessonContentBlock,
    LessonDetail,
    LessonPlayback,
    LessonProgressState,
    OutlineLesson,
    OutlineSection,
    PlaybackSnapshot,
    ProgressCommandName,
    ProgressMutation,
    ProgressResult,
    PublishedCourse,
    PublishedLesson,
)

_CURSOR_MAX_AGE_SECONDS = 86_400
_CURSOR_FETCH_SIZE = 51


class PublishedCoursePort(Protocol):
    """Read-only F-002 boundary consumed by Learning."""

    def lock_current_published(
        self, *, tenant_id: UUID, course_id: UUID
    ) -> PublishedCourse | None: ...

    def load_published(
        self,
        *,
        tenant_id: UUID,
        course_id: UUID,
        course_version_id: UUID,
    ) -> PublishedCourse | None: ...


def _enrollment(model: EnrollmentModel) -> Enrollment:
    try:
        status = EnrollmentStatus(model.status)
    except ValueError as error:
        raise LearningError("SERVICE_CONTRACT_ERROR") from error
    return Enrollment(
        id=model.id,
        tenant_id=model.tenant_id,
        learner_membership_id=model.learner_membership_id,
        course_id=model.course_id,
        course_version_id=model.course_version_id,
        admission_source=model.admission_source,
        status=status,
        enrolled_at=model.enrolled_at,
        revoked_at=model.revoked_at,
        row_version=model.row_version,
    )


def _progress(
    model: CourseProgressModel | None,
    *,
    required_lesson_count: int,
) -> CourseProgress:
    if required_lesson_count < 1:
        raise LearningError("SERVICE_CONTRACT_ERROR")
    if model is None:
        return CourseProgress(
            state=CourseProgressState.NOT_STARTED,
            required_lesson_count=required_lesson_count,
            completed_required_lesson_count=0,
            resume_lesson_id=None,
            row_version=0,
        )
    try:
        state = CourseProgressState(model.state)
    except ValueError as error:
        raise LearningError("SERVICE_CONTRACT_ERROR") from error
    if model.required_lesson_count != required_lesson_count:
        raise LearningError("SERVICE_CONTRACT_ERROR")
    return CourseProgress(
        state=state,
        required_lesson_count=model.required_lesson_count,
        completed_required_lesson_count=model.completed_required_lesson_count,
        resume_lesson_id=model.resume_lesson_id,
        row_version=model.row_version,
    )


def _lessons(course: PublishedCourse) -> tuple[PublishedLesson, ...]:
    return tuple(lesson for section in course.sections for lesson in section.lessons)


def _required_lesson_count(course: PublishedCourse) -> int:
    count = sum(1 for lesson in _lessons(course) if lesson.is_required)
    if count < 1 or count > 20_000:
        raise LearningError("SERVICE_CONTRACT_ERROR")
    return count


def _cursor_secret() -> bytes:
    return settings.SECRET_KEY.encode("utf-8")


def _encode_cursor(
    *,
    tenant_id: UUID,
    learner_membership_id: UUID,
    enrolled_at: datetime,
    enrollment_id: UUID,
) -> str:
    payload = json.dumps(
        {
            "tenant_id": str(tenant_id),
            "learner_membership_id": str(learner_membership_id),
            "enrolled_at": enrolled_at.astimezone(UTC).isoformat(),
            "enrollment_id": str(enrollment_id),
            "issued_at": int(timezone.now().timestamp()),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hmac.new(_cursor_secret(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + signature).decode("ascii").rstrip("=")


def _decode_cursor(
    cursor: str,
    *,
    tenant_id: UUID,
    learner_membership_id: UUID,
) -> tuple[datetime, UUID]:
    try:
        if not 16 <= len(cursor) <= 1024 or any(
            not (character.isalnum() or character in "-_") for character in cursor
        ):
            raise ValueError
        padding = "=" * (-len(cursor) % 4)
        encoded = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        if len(encoded) <= hashlib.sha256().digest_size:
            raise ValueError
        payload = encoded[: -hashlib.sha256().digest_size]
        supplied_signature = encoded[-hashlib.sha256().digest_size :]
        expected_signature = hmac.new(_cursor_secret(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError
        if UUID(cast(str, value["tenant_id"])) != tenant_id:
            raise ValueError
        if UUID(cast(str, value["learner_membership_id"])) != learner_membership_id:
            raise ValueError
        issued_at = int(cast(int, value["issued_at"]))
        age = int(timezone.now().timestamp()) - issued_at
        if age < 0 or age > _CURSOR_MAX_AGE_SECONDS:
            raise ValueError
        enrolled_at = datetime.fromisoformat(cast(str, value["enrolled_at"]))
        if enrolled_at.tzinfo is None:
            raise ValueError
        return enrolled_at, UUID(cast(str, value["enrollment_id"]))
    except (KeyError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise validation_failed(
            FieldError("cursor", "invalid", "The learner dashboard cursor is invalid.")
        ) from error


class DjangoLearningRepository:
    """Tenant-scoped enrollment/progress persistence over the F-002 read boundary."""

    def __init__(self, *, courses: PublishedCoursePort) -> None:
        self._courses = courses

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
        learner = (
            TenantMembership.objects.select_for_update()
            .filter(
                tenant_id=tenant_id,
                id=learner_membership_id,
                status="active",
            )
            .first()
        )
        has_learner_role = (
            learner is not None
            and MembershipRole.objects.filter(
                tenant_id=tenant_id,
                membership_id=learner_membership_id,
                role__code="learner",
            ).exists()
        )
        if not has_learner_role:
            raise validation_failed(
                FieldError(
                    "learner_membership_id",
                    "invalid_learner",
                    "The selected active learner membership is unavailable.",
                )
            )
        course = self._courses.lock_current_published(
            tenant_id=tenant_id,
            course_id=course_id,
        )
        if course is None:
            raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
        _required_lesson_count(course)
        try:
            with transaction.atomic():
                model = EnrollmentModel.objects.create(
                    id=enrollment_id,
                    tenant_id=tenant_id,
                    learner_membership_id=learner_membership_id,
                    course_id=course_id,
                    course_version_id=course.course_version_id,
                    admission_source="manual_assignment",
                    status="active",
                    enrolled_at=enrolled_at,
                    assigned_by_actor_id=actor_id,
                    row_version=1,
                )
        except IntegrityError as error:
            raise validation_failed(
                FieldError(
                    "learner_membership_id",
                    "active_enrollment_exists",
                    "The learner already has an active enrollment for this course.",
                )
            ) from error
        return _enrollment(model)

    def revoke_enrollment(
        self,
        *,
        tenant_id: UUID,
        enrollment_id: UUID,
        expected_enrollment_row_version: int,
        reason_code: str,
        revoked_at: datetime,
    ) -> Enrollment:
        model = (
            EnrollmentModel.objects.select_for_update()
            .filter(tenant_id=tenant_id, id=enrollment_id, status="active")
            .first()
        )
        if model is None:
            raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
        if model.row_version != expected_enrollment_row_version:
            raise validation_failed(
                FieldError(
                    "expected_enrollment_row_version",
                    "stale",
                    "The enrollment changed before this command completed.",
                )
            )
        model.status = "revoked"
        model.revoked_at = revoked_at
        model.revocation_reason_code = reason_code
        model.row_version += 1
        model.save(
            update_fields=(
                "status",
                "revoked_at",
                "revocation_reason_code",
                "row_version",
                "updated_at",
            )
        )
        return _enrollment(model)

    def list_dashboard(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> LearnerDashboard:
        position = (
            None
            if cursor is None
            else _decode_cursor(
                cursor,
                tenant_id=tenant_id,
                learner_membership_id=learner_membership_id,
            )
        )
        cards: list[DashboardCard] = []
        scan_position = position
        while len(cards) <= limit:
            query = EnrollmentModel.objects.filter(
                tenant_id=tenant_id,
                learner_membership_id=learner_membership_id,
                learner_membership__status="active",
                status="active",
            )
            if scan_position is not None:
                enrolled_at, enrollment_id = scan_position
                query = query.filter(
                    Q(enrolled_at__lt=enrolled_at)
                    | Q(enrolled_at=enrolled_at, id__lt=enrollment_id)
                )
            rows = list(query.order_by("-enrolled_at", "-id")[:_CURSOR_FETCH_SIZE])
            if not rows:
                break
            for row in rows:
                scan_position = (row.enrolled_at, row.id)
                course = self._courses.load_published(
                    tenant_id=tenant_id,
                    course_id=row.course_id,
                    course_version_id=row.course_version_id,
                )
                if course is None:
                    continue
                progress_model = CourseProgressModel.objects.filter(
                    tenant_id=tenant_id,
                    enrollment_id=row.id,
                    course_version_id=row.course_version_id,
                ).first()
                cards.append(
                    DashboardCard(
                        enrollment_id=row.id,
                        course_id=row.course_id,
                        course_version_id=row.course_version_id,
                        course_version_number=course.course_version_number,
                        primary_locale=course.primary_locale,
                        title=course.title,
                        description=course.description,
                        content_hash=course.content_hash,
                        enrolled_at=row.enrolled_at,
                        progress=_progress(
                            progress_model,
                            required_lesson_count=_required_lesson_count(course),
                        ),
                    )
                )
                if len(cards) > limit:
                    break
            if len(cards) > limit or len(rows) < _CURSOR_FETCH_SIZE:
                break
        page = tuple(cards[:limit])
        next_cursor = None
        if len(cards) > limit and page:
            last = page[-1]
            next_cursor = _encode_cursor(
                tenant_id=tenant_id,
                learner_membership_id=learner_membership_id,
                enrolled_at=last.enrolled_at,
                enrollment_id=last.enrollment_id,
            )
        return LearnerDashboard(tenant_id=tenant_id, items=page, next_cursor=next_cursor)

    def get_playback(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        enrollment_id: UUID,
    ) -> PlaybackSnapshot:
        model, course = self._active_enrollment(
            tenant_id=tenant_id,
            learner_membership_id=learner_membership_id,
            enrollment_id=enrollment_id,
            for_update=False,
        )
        lesson_states = self._lesson_states(tenant_id=tenant_id, enrollment_id=model.id)
        sections = tuple(
            OutlineSection(
                id=section.id,
                title=section.title,
                position=section.position,
                lessons=tuple(
                    OutlineLesson(
                        id=lesson.id,
                        title=lesson.title,
                        position=lesson.position,
                        is_required=lesson.is_required,
                        progress_state=lesson_states.get(
                            lesson.id, LessonProgressState.NOT_STARTED
                        ),
                    )
                    for lesson in section.lessons
                ),
            )
            for section in course.sections
        )
        progress_model = CourseProgressModel.objects.filter(
            tenant_id=tenant_id,
            enrollment_id=model.id,
            course_version_id=model.course_version_id,
        ).first()
        return PlaybackSnapshot(
            tenant_id=tenant_id,
            enrollment_id=model.id,
            course_id=model.course_id,
            course_version_id=model.course_version_id,
            course_version_number=course.course_version_number,
            primary_locale=course.primary_locale,
            title=course.title,
            description=course.description,
            content_hash=course.content_hash,
            sections=sections,
            progress=_progress(
                progress_model,
                required_lesson_count=_required_lesson_count(course),
            ),
        )

    def get_lesson(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        enrollment_id: UUID,
        lesson_id: UUID,
    ) -> LessonPlayback:
        model, course = self._active_enrollment(
            tenant_id=tenant_id,
            learner_membership_id=learner_membership_id,
            enrollment_id=enrollment_id,
            for_update=False,
        )
        lessons = _lessons(course)
        lesson_index = next(
            (index for index, lesson in enumerate(lessons) if lesson.id == lesson_id),
            None,
        )
        if lesson_index is None:
            raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
        lesson = lessons[lesson_index]
        states = self._lesson_states(tenant_id=tenant_id, enrollment_id=model.id)
        progress_model = CourseProgressModel.objects.filter(
            tenant_id=tenant_id,
            enrollment_id=model.id,
            course_version_id=model.course_version_id,
        ).first()
        return LessonPlayback(
            tenant_id=tenant_id,
            enrollment_id=model.id,
            course_version_id=model.course_version_id,
            primary_locale=course.primary_locale,
            content_hash=course.content_hash,
            lesson=LessonDetail(
                id=lesson.id,
                section_id=lesson.section_id,
                title=lesson.title,
                position=lesson.position,
                is_required=lesson.is_required,
                progress_state=states.get(lesson.id, LessonProgressState.NOT_STARTED),
                content_blocks=tuple(
                    LessonContentBlock(
                        id=block.id,
                        kind=block.kind,
                        position=block.position,
                        document=cast(JsonObject, json.loads(json.dumps(block.document))),
                    )
                    for block in lesson.content_blocks
                ),
            ),
            previous_lesson_id=(None if lesson_index == 0 else lessons[lesson_index - 1].id),
            next_lesson_id=(
                None if lesson_index + 1 == len(lessons) else lessons[lesson_index + 1].id
            ),
            progress=_progress(
                progress_model,
                required_lesson_count=_required_lesson_count(course),
            ),
        )

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
    ) -> ProgressMutation:
        enrollment, course = self._active_enrollment(
            tenant_id=tenant_id,
            learner_membership_id=learner_membership_id,
            enrollment_id=enrollment_id,
            for_update=True,
        )
        lesson = next((item for item in _lessons(course) if item.id == lesson_id), None)
        if lesson is None:
            raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
        required_count = _required_lesson_count(course)
        aggregate = (
            CourseProgressModel.objects.select_for_update()
            .filter(
                tenant_id=tenant_id,
                enrollment_id=enrollment.id,
                course_version_id=enrollment.course_version_id,
            )
            .first()
        )
        actual_version = 0 if aggregate is None else aggregate.row_version
        if actual_version != expected_progress_row_version:
            raise LearningError("PROGRESS_VERSION_CONFLICT")
        lesson_progress = (
            LessonProgressModel.objects.select_for_update()
            .filter(
                tenant_id=tenant_id,
                enrollment_id=enrollment.id,
                course_version_id=enrollment.course_version_id,
                lesson_id=lesson.id,
            )
            .first()
        )
        previous_lesson_state = (
            LessonProgressState.NOT_STARTED
            if lesson_progress is None
            else LessonProgressState(lesson_progress.state)
        )
        previous_course_state = (
            CourseProgressState.NOT_STARTED
            if aggregate is None
            else CourseProgressState(aggregate.state)
        )
        next_lesson_state = self._next_lesson_state(
            command=command,
            current=previous_lesson_state,
        )
        completed_at = updated_at if next_lesson_state is LessonProgressState.COMPLETED else None
        if lesson_progress is None:
            lesson_progress = LessonProgressModel.objects.create(
                tenant_id=tenant_id,
                enrollment_id=enrollment.id,
                course_version_id=enrollment.course_version_id,
                lesson_id=lesson.id,
                state=next_lesson_state.value,
                completed_at=completed_at,
                row_version=1,
            )
        else:
            lesson_progress.state = next_lesson_state.value
            lesson_progress.completed_at = completed_at
            lesson_progress.row_version += 1
            lesson_progress.save(
                update_fields=("state", "completed_at", "row_version", "updated_at")
            )
        required_ids = tuple(item.id for item in _lessons(course) if item.is_required)
        completed_required_count = LessonProgressModel.objects.filter(
            tenant_id=tenant_id,
            enrollment_id=enrollment.id,
            course_version_id=enrollment.course_version_id,
            lesson_id__in=required_ids,
            state="completed",
        ).count()
        course_state = (
            CourseProgressState.COMPLETED
            if completed_required_count == required_count
            else CourseProgressState.IN_PROGRESS
        )
        if aggregate is None:
            aggregate = CourseProgressModel.objects.create(
                tenant_id=tenant_id,
                enrollment_id=enrollment.id,
                course_version_id=enrollment.course_version_id,
                state=course_state.value,
                required_lesson_count=required_count,
                completed_required_lesson_count=completed_required_count,
                resume_lesson_id=lesson.id,
                last_progress_at=updated_at,
                row_version=1,
            )
        else:
            if aggregate.required_lesson_count != required_count:
                raise LearningError("SERVICE_CONTRACT_ERROR")
            aggregate.state = course_state.value
            aggregate.completed_required_lesson_count = completed_required_count
            aggregate.resume_lesson_id = lesson.id
            aggregate.last_progress_at = updated_at
            aggregate.row_version += 1
            aggregate.save(
                update_fields=(
                    "state",
                    "completed_required_lesson_count",
                    "resume_lesson_id",
                    "last_progress_at",
                    "row_version",
                    "updated_at",
                )
            )
        result = ProgressResult(
            tenant_id=tenant_id,
            enrollment_id=enrollment.id,
            course_version_id=enrollment.course_version_id,
            lesson_id=lesson.id,
            lesson_state=next_lesson_state,
            course_state=course_state,
            required_lesson_count=required_count,
            completed_required_lesson_count=completed_required_count,
            resume_lesson_id=lesson.id,
            progress_row_version=aggregate.row_version,
            updated_at=updated_at,
        )
        return ProgressMutation(
            result=result,
            previous_lesson_state=previous_lesson_state,
            previous_course_state=previous_course_state,
            previous_progress_row_version=actual_version,
        )

    def _active_enrollment(
        self,
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
        enrollment_id: UUID,
        for_update: bool,
    ) -> tuple[EnrollmentModel, PublishedCourse]:
        query = EnrollmentModel.objects.filter(
            tenant_id=tenant_id,
            learner_membership_id=learner_membership_id,
            id=enrollment_id,
            status="active",
        )
        if for_update:
            if not self._lock_active_membership(
                tenant_id=tenant_id,
                learner_membership_id=learner_membership_id,
            ):
                raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
            query = query.select_for_update()
        else:
            query = query.filter(learner_membership__status="active")
        model = query.first()
        if model is None:
            raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
        course = self._courses.load_published(
            tenant_id=tenant_id,
            course_id=model.course_id,
            course_version_id=model.course_version_id,
        )
        if course is None:
            raise LearningError("LEARNING_RESOURCE_NOT_FOUND")
        return model, course

    @staticmethod
    def _lock_active_membership(
        *,
        tenant_id: UUID,
        learner_membership_id: UUID,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            role = cursor.fetchone()
            if role is not None and role[0] == "lms_api_runtime":
                cursor.execute(
                    "SELECT app.lock_active_learning_membership(%s, %s)",
                    [tenant_id, learner_membership_id],
                )
                row = cursor.fetchone()
                return row is not None and row[0] is True
        return (
            TenantMembership.objects.select_for_update()
            .filter(
                tenant_id=tenant_id,
                id=learner_membership_id,
                status="active",
            )
            .exists()
        )

    @staticmethod
    def _lesson_states(*, tenant_id: UUID, enrollment_id: UUID) -> dict[UUID, LessonProgressState]:
        try:
            return {
                lesson_id: LessonProgressState(state)
                for lesson_id, state in LessonProgressModel.objects.filter(
                    tenant_id=tenant_id,
                    enrollment_id=enrollment_id,
                ).values_list("lesson_id", "state")
            }
        except ValueError as error:
            raise LearningError("SERVICE_CONTRACT_ERROR") from error

    @staticmethod
    def _next_lesson_state(
        *,
        command: ProgressCommandName,
        current: LessonProgressState,
    ) -> LessonProgressState:
        if command is ProgressCommandName.OPEN_LESSON:
            return (
                LessonProgressState.IN_PROGRESS
                if current is LessonProgressState.NOT_STARTED
                else current
            )
        if command is ProgressCommandName.COMPLETE_LESSON:
            return LessonProgressState.COMPLETED
        if command is ProgressCommandName.REOPEN_LESSON:
            if current is not LessonProgressState.COMPLETED:
                raise validation_failed(
                    FieldError(
                        "command",
                        "invalid_transition",
                        "Only a completed lesson can be reopened.",
                    )
                )
            return LessonProgressState.IN_PROGRESS
        raise LearningError("SERVICE_CONTRACT_ERROR")

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import Any
from uuid import uuid4

import pytest
from django.db import close_old_connections, transaction
from django.db.models import F

from lms.api.learning_composition import DjangoPublishedCourseReader
from lms.modules.courses.models import (
    Course,
    CourseInstructor,
    CourseVersion,
    CurriculumSection,
    Lesson,
    LessonContentBlock,
)
from lms.modules.learning.errors import LearningError
from lms.modules.learning.models import CourseProgress, Enrollment, LessonProgress
from lms.modules.learning.repositories import DjangoLearningRepository
from lms.modules.learning.types import (
    CourseProgressState,
    LessonProgressState,
    ProgressCommandName,
)
from tests.courses.test_models import CONTENT_HASH, DOCUMENT, create_course_graph
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def create_two_lesson_published_course(
    seed: dict[str, Any], *, second_is_required: bool = True
) -> dict[str, Any]:
    graph = create_course_graph(seed)
    second = Lesson.objects.create(
        tenant=seed["alpha"],
        course_version=graph["version"],
        section=graph["section"],
        title="Lesson two",
        position=2,
        is_required=second_is_required,
    )
    LessonContentBlock.objects.create(
        tenant=seed["alpha"],
        course_version=graph["version"],
        lesson=second,
        position=1,
        document=DOCUMENT,
    )
    CourseVersion.objects.filter(id=graph["version"].id).update(
        status="published",
        submitted_hash=graph["version"].content_hash,
        approved_hash=graph["version"].content_hash,
    )
    Course.objects.filter(id=graph["course"].id).update(
        current_published_version_id=graph["version"].id
    )
    graph["course"].refresh_from_db()
    graph["version"].refresh_from_db()
    graph["second_lesson"] = second
    return graph


def create_second_published_course(seed: dict[str, Any]) -> dict[str, Any]:
    course = Course.objects.create(tenant=seed["alpha"], slug="second-course")
    version = CourseVersion.objects.create(
        tenant=seed["alpha"],
        course=course,
        version_number=1,
        primary_locale="en",
        title="Second synthetic course",
        description="A second rights-cleared synthetic fixture.",
        content_hash=CONTENT_HASH,
    )
    CourseInstructor.objects.create(
        tenant=seed["alpha"],
        course=course,
        membership=seed["memberships"]["instructor_alpha"],
    )
    section = CurriculumSection.objects.create(
        tenant=seed["alpha"],
        course_version=version,
        title="Second section",
        position=1,
    )
    lesson = Lesson.objects.create(
        tenant=seed["alpha"],
        course_version=version,
        section=section,
        title="Second lesson",
        position=1,
        is_required=True,
    )
    LessonContentBlock.objects.create(
        tenant=seed["alpha"],
        course_version=version,
        lesson=lesson,
        position=1,
        document=DOCUMENT,
    )
    CourseVersion.objects.filter(id=version.id).update(
        status="published",
        submitted_hash=version.content_hash,
        approved_hash=version.content_hash,
    )
    Course.objects.filter(id=course.id).update(current_published_version_id=version.id)
    version.refresh_from_db()
    return {"course": course, "version": version, "section": section, "lesson": lesson}


def create_enrollment(
    repository: DjangoLearningRepository,
    seed: dict[str, Any],
    graph: dict[str, Any],
) -> object:
    return repository.create_enrollment(
        enrollment_id=uuid4(),
        tenant_id=seed["alpha"].id,
        learner_membership_id=seed["memberships"]["learner"].id,
        course_id=graph["course"].id,
        actor_id=seed["profiles"]["admin"].provider_subject,
        enrolled_at=NOW,
    )


@pytest.mark.django_db
def test_assignment_pins_only_an_active_learner_to_the_locked_publication(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
    graph = create_two_lesson_published_course(tenancy_seed)

    assigned = create_enrollment(repository, tenancy_seed, graph)

    assert assigned.course_version_id == graph["version"].id
    assert assigned.row_version == 1
    with pytest.raises(LearningError, match="ENROLLMENT_VALIDATION_FAILED"):
        repository.create_enrollment(
            enrollment_id=uuid4(),
            tenant_id=tenancy_seed["alpha"].id,
            learner_membership_id=tenancy_seed["memberships"]["instructor_alpha"].id,
            course_id=graph["course"].id,
            actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
            enrolled_at=NOW,
        )


@pytest.mark.django_db
def test_selectors_are_read_only_and_emit_only_the_pinned_safe_content(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
    graph = create_two_lesson_published_course(tenancy_seed)
    assigned = create_enrollment(repository, tenancy_seed, graph)
    learner_id = tenancy_seed["memberships"]["learner"].id

    dashboard = repository.list_dashboard(
        tenant_id=tenancy_seed["alpha"].id,
        learner_membership_id=learner_id,
        cursor=None,
        limit=50,
    )
    playback = repository.get_playback(
        tenant_id=tenancy_seed["alpha"].id,
        learner_membership_id=learner_id,
        enrollment_id=assigned.id,
    )
    lesson = repository.get_lesson(
        tenant_id=tenancy_seed["alpha"].id,
        learner_membership_id=learner_id,
        enrollment_id=assigned.id,
        lesson_id=graph["lesson"].id,
    )

    assert dashboard.items[0].course_version_id == graph["version"].id
    assert playback.progress.row_version == 0
    assert playback.progress.state is CourseProgressState.NOT_STARTED
    assert lesson.lesson.content_blocks[0].kind == "rich_text"
    assert lesson.lesson.content_blocks[0].document == DOCUMENT
    assert CourseProgress.objects.count() == 0
    assert LessonProgress.objects.count() == 0


@pytest.mark.django_db
def test_progress_commands_derive_course_completion_and_reopen_optimistically(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
    graph = create_two_lesson_published_course(tenancy_seed)
    assigned = create_enrollment(repository, tenancy_seed, graph)
    scope = {
        "tenant_id": tenancy_seed["alpha"].id,
        "learner_membership_id": tenancy_seed["memberships"]["learner"].id,
        "enrollment_id": assigned.id,
        "updated_at": NOW,
    }

    opened = repository.apply_progress(
        **scope,
        lesson_id=graph["lesson"].id,
        command=ProgressCommandName.OPEN_LESSON,
        expected_progress_row_version=0,
    )
    first_complete = repository.apply_progress(
        **scope,
        lesson_id=graph["lesson"].id,
        command=ProgressCommandName.COMPLETE_LESSON,
        expected_progress_row_version=1,
    )
    course_complete = repository.apply_progress(
        **scope,
        lesson_id=graph["second_lesson"].id,
        command=ProgressCommandName.COMPLETE_LESSON,
        expected_progress_row_version=2,
    )
    reopened = repository.apply_progress(
        **scope,
        lesson_id=graph["lesson"].id,
        command=ProgressCommandName.REOPEN_LESSON,
        expected_progress_row_version=3,
    )

    assert opened.result.lesson_state is LessonProgressState.IN_PROGRESS
    assert first_complete.result.completed_required_lesson_count == 1
    assert course_complete.result.course_state is CourseProgressState.COMPLETED
    assert course_complete.result.completed_required_lesson_count == 2
    assert reopened.previous_course_state is CourseProgressState.COMPLETED
    assert reopened.result.course_state is CourseProgressState.IN_PROGRESS
    assert reopened.result.completed_required_lesson_count == 1
    assert reopened.result.progress_row_version == 4

    with pytest.raises(LearningError, match="PROGRESS_VERSION_CONFLICT"):
        repository.apply_progress(
            **scope,
            lesson_id=graph["lesson"].id,
            command=ProgressCommandName.OPEN_LESSON,
            expected_progress_row_version=3,
        )


@pytest.mark.django_db
def test_optional_lesson_changes_do_not_control_required_course_completion(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
    graph = create_two_lesson_published_course(
        tenancy_seed,
        second_is_required=False,
    )
    assigned = create_enrollment(repository, tenancy_seed, graph)
    scope = {
        "tenant_id": tenancy_seed["alpha"].id,
        "learner_membership_id": tenancy_seed["memberships"]["learner"].id,
        "enrollment_id": assigned.id,
        "updated_at": NOW,
    }

    optional_complete = repository.apply_progress(
        **scope,
        lesson_id=graph["second_lesson"].id,
        command=ProgressCommandName.COMPLETE_LESSON,
        expected_progress_row_version=0,
    )
    required_complete = repository.apply_progress(
        **scope,
        lesson_id=graph["lesson"].id,
        command=ProgressCommandName.COMPLETE_LESSON,
        expected_progress_row_version=1,
    )
    optional_reopen = repository.apply_progress(
        **scope,
        lesson_id=graph["second_lesson"].id,
        command=ProgressCommandName.REOPEN_LESSON,
        expected_progress_row_version=2,
    )

    assert optional_complete.result.course_state is CourseProgressState.IN_PROGRESS
    assert optional_complete.result.completed_required_lesson_count == 0
    assert required_complete.result.course_state is CourseProgressState.COMPLETED
    assert required_complete.result.completed_required_lesson_count == 1
    assert optional_reopen.result.course_state is CourseProgressState.COMPLETED
    assert optional_reopen.result.completed_required_lesson_count == 1


@pytest.mark.django_db
def test_revocation_and_withdrawal_make_playback_neutrally_unavailable(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
    graph = create_two_lesson_published_course(tenancy_seed)
    first = create_enrollment(repository, tenancy_seed, graph)
    learner_id = tenancy_seed["memberships"]["learner"].id
    repository.revoke_enrollment(
        tenant_id=tenancy_seed["alpha"].id,
        enrollment_id=first.id,
        expected_enrollment_row_version=1,
        reason_code="ADMIN_REVOKED",
        revoked_at=NOW,
    )
    with pytest.raises(LearningError, match="LEARNING_RESOURCE_NOT_FOUND"):
        repository.get_playback(
            tenant_id=tenancy_seed["alpha"].id,
            learner_membership_id=learner_id,
            enrollment_id=first.id,
        )

    second = create_enrollment(repository, tenancy_seed, graph)
    Course.objects.filter(id=graph["course"].id).update(
        current_published_version_id=None,
        row_version=F("row_version") + 1,
    )
    CourseVersion.objects.filter(id=graph["version"].id).update(
        status="withdrawn",
        row_version=F("row_version") + 1,
    )
    with pytest.raises(LearningError, match="LEARNING_RESOURCE_NOT_FOUND"):
        repository.get_playback(
            tenant_id=tenancy_seed["alpha"].id,
            learner_membership_id=learner_id,
            enrollment_id=second.id,
        )


@pytest.mark.django_db
def test_reenrollment_pins_the_new_pointer_without_copying_historical_progress(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
    graph = create_two_lesson_published_course(tenancy_seed)
    first = create_enrollment(repository, tenancy_seed, graph)
    repository.apply_progress(
        tenant_id=tenancy_seed["alpha"].id,
        learner_membership_id=tenancy_seed["memberships"]["learner"].id,
        enrollment_id=first.id,
        lesson_id=graph["lesson"].id,
        command=ProgressCommandName.COMPLETE_LESSON,
        expected_progress_row_version=0,
        updated_at=NOW,
    )
    repository.revoke_enrollment(
        tenant_id=tenancy_seed["alpha"].id,
        enrollment_id=first.id,
        expected_enrollment_row_version=1,
        reason_code="ADMIN_REVOKED",
        revoked_at=NOW,
    )

    successor = CourseVersion.objects.create(
        tenant=tenancy_seed["alpha"],
        course=graph["course"],
        predecessor_version=graph["version"],
        version_number=2,
        primary_locale="en",
        title="Synthetic successor",
        description="A new synthetic publication.",
        content_hash="sha256:" + "2" * 64,
    )
    section = CurriculumSection.objects.create(
        tenant=tenancy_seed["alpha"],
        course_version=successor,
        title="Successor section",
        position=1,
    )
    lesson = Lesson.objects.create(
        tenant=tenancy_seed["alpha"],
        course_version=successor,
        section=section,
        title="Successor lesson",
        position=1,
        is_required=True,
    )
    LessonContentBlock.objects.create(
        tenant=tenancy_seed["alpha"],
        course_version=successor,
        lesson=lesson,
        position=1,
        document=DOCUMENT,
    )
    CourseVersion.objects.filter(id=successor.id).update(
        status="published",
        submitted_hash=successor.content_hash,
        approved_hash=successor.content_hash,
    )
    successor.refresh_from_db()
    Course.objects.filter(id=graph["course"].id).update(current_published_version_id=successor.id)

    second = create_enrollment(repository, tenancy_seed, graph)

    assert second.id != first.id
    assert second.course_version_id == successor.id
    assert CourseProgress.objects.filter(enrollment_id=first.id).count() == 1
    assert CourseProgress.objects.filter(enrollment_id=second.id).count() == 0
    assert LessonProgress.objects.filter(enrollment_id=second.id).count() == 0
    assert (
        repository.get_playback(
            tenant_id=tenancy_seed["alpha"].id,
            learner_membership_id=tenancy_seed["memberships"]["learner"].id,
            enrollment_id=second.id,
        ).progress.row_version
        == 0
    )


@pytest.mark.django_db
def test_dashboard_cursor_is_bounded_opaque_and_stably_ordered(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
    first_graph = create_two_lesson_published_course(tenancy_seed)
    first = create_enrollment(repository, tenancy_seed, first_graph)
    second_graph = create_second_published_course(tenancy_seed)
    second = repository.create_enrollment(
        enrollment_id=uuid4(),
        tenant_id=tenancy_seed["alpha"].id,
        learner_membership_id=tenancy_seed["memberships"]["learner"].id,
        course_id=second_graph["course"].id,
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        enrolled_at=NOW - timedelta(hours=1),
    )

    first_page = repository.list_dashboard(
        tenant_id=tenancy_seed["alpha"].id,
        learner_membership_id=tenancy_seed["memberships"]["learner"].id,
        cursor=None,
        limit=1,
    )
    second_page = repository.list_dashboard(
        tenant_id=tenancy_seed["alpha"].id,
        learner_membership_id=tenancy_seed["memberships"]["learner"].id,
        cursor=first_page.next_cursor,
        limit=1,
    )

    assert [item.enrollment_id for item in first_page.items] == [first.id]
    assert [item.enrollment_id for item in second_page.items] == [second.id]
    assert first_page.next_cursor is not None
    assert all(character.isalnum() or character in "-_" for character in first_page.next_cursor)


@pytest.mark.django_db(transaction=True)
def test_simultaneous_assignments_create_exactly_one_active_enrollment(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_two_lesson_published_course(tenancy_seed)
    barrier = Barrier(2)

    def attempt_assignment() -> str:
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            with transaction.atomic():
                DjangoLearningRepository(courses=DjangoPublishedCourseReader()).create_enrollment(
                    enrollment_id=uuid4(),
                    tenant_id=tenancy_seed["alpha"].id,
                    learner_membership_id=tenancy_seed["memberships"]["learner"].id,
                    course_id=graph["course"].id,
                    actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
                    enrolled_at=NOW,
                )
            return "created"
        except LearningError as error:
            return error.code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt_assignment(), range(2)))

    assert sorted(outcomes) == ["ENROLLMENT_VALIDATION_FAILED", "created"]
    assert Enrollment.objects.filter(status="active").count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_progress_commands_have_one_winner_and_one_stable_conflict(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_two_lesson_published_course(tenancy_seed)
    with transaction.atomic():
        repository = DjangoLearningRepository(courses=DjangoPublishedCourseReader())
        assigned = create_enrollment(repository, tenancy_seed, graph)
        repository.apply_progress(
            tenant_id=tenancy_seed["alpha"].id,
            learner_membership_id=tenancy_seed["memberships"]["learner"].id,
            enrollment_id=assigned.id,
            lesson_id=graph["lesson"].id,
            command=ProgressCommandName.OPEN_LESSON,
            expected_progress_row_version=0,
            updated_at=NOW,
        )
    barrier = Barrier(2)

    def attempt_completion() -> str:
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            with transaction.atomic():
                DjangoLearningRepository(courses=DjangoPublishedCourseReader()).apply_progress(
                    tenant_id=tenancy_seed["alpha"].id,
                    learner_membership_id=tenancy_seed["memberships"]["learner"].id,
                    enrollment_id=assigned.id,
                    lesson_id=graph["lesson"].id,
                    command=ProgressCommandName.COMPLETE_LESSON,
                    expected_progress_row_version=1,
                    updated_at=NOW,
                )
            return "completed"
        except LearningError as error:
            return error.code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt_completion(), range(2)))

    assert sorted(outcomes) == ["PROGRESS_VERSION_CONFLICT", "completed"]
    progress = CourseProgress.objects.get(enrollment_id=assigned.id)
    assert progress.row_version == 2
    assert progress.completed_required_lesson_count == 1
    assert LessonProgress.objects.get(enrollment_id=assigned.id).state == "completed"

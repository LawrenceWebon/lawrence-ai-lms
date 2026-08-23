from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from lms.modules.courses.models import Course, CourseVersion
from lms.modules.learning.models import CourseProgress, Enrollment, LessonProgress
from tests.courses.test_models import CONTENT_HASH
from tests.learning.test_models import create_published_course
from tests.tenancy.conftest import tenancy_seed as tenancy_seed


def create_enrollment(
    seed: dict[str, Any], tenant_key: str = "alpha"
) -> tuple[dict[str, Any], Enrollment]:
    graph = create_published_course(seed, tenant_key)
    membership_key = "learner" if tenant_key == "alpha" else "instructor_beta"
    enrollment = Enrollment.objects.create(
        tenant=seed[tenant_key],
        learner_membership=seed["memberships"][membership_key],
        course=graph["course"],
        course_version=graph["version"],
    )
    return graph, enrollment


@pytest.mark.django_db
def test_learning_edges_reject_cross_tenant_and_wrong_version_relationships(
    tenancy_seed: dict[str, Any],
) -> None:
    alpha = create_published_course(tenancy_seed, "alpha")
    beta = create_published_course(tenancy_seed, "beta")

    with pytest.raises(IntegrityError), transaction.atomic():
        Enrollment.objects.create(
            tenant=tenancy_seed["alpha"],
            learner_membership=tenancy_seed["memberships"]["instructor_beta"],
            course=alpha["course"],
            course_version=alpha["version"],
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        Enrollment.objects.create(
            tenant=tenancy_seed["alpha"],
            learner_membership=tenancy_seed["memberships"]["learner"],
            course=alpha["course"],
            course_version=beta["version"],
        )

    other_course = Course.objects.create(tenant=tenancy_seed["alpha"], slug="wrong-version")
    other_version = CourseVersion.objects.create(
        tenant=tenancy_seed["alpha"],
        course=other_course,
        version_number=1,
        status="published",
        primary_locale="en",
        title="Wrong course version",
        description="Synthetic.",
        content_hash=CONTENT_HASH,
        submitted_hash=CONTENT_HASH,
        approved_hash=CONTENT_HASH,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Enrollment.objects.create(
            tenant=tenancy_seed["alpha"],
            learner_membership=tenancy_seed["memberships"]["learner"],
            course=alpha["course"],
            course_version=other_version,
        )


@pytest.mark.django_db
def test_only_one_active_enrollment_exists_per_learner_and_course(
    tenancy_seed: dict[str, Any],
) -> None:
    graph, _ = create_enrollment(tenancy_seed)
    with pytest.raises(IntegrityError), transaction.atomic():
        Enrollment.objects.create(
            tenant=tenancy_seed["alpha"],
            learner_membership=tenancy_seed["memberships"]["learner"],
            course=graph["course"],
            course_version=graph["version"],
        )


@pytest.mark.django_db
def test_enrollment_pin_and_revoked_history_are_immutable(
    tenancy_seed: dict[str, Any],
) -> None:
    graph, enrollment = create_enrollment(tenancy_seed)
    second_version = CourseVersion.objects.create(
        tenant=tenancy_seed["alpha"],
        course=graph["course"],
        predecessor_version=graph["version"],
        version_number=2,
        status="published",
        primary_locale="en",
        title="Synthetic successor",
        description="Synthetic.",
        content_hash="sha256:" + "2" * 64,
        submitted_hash="sha256:" + "2" * 64,
        approved_hash="sha256:" + "2" * 64,
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        Enrollment.objects.filter(id=enrollment.id).update(course_version=second_version)

    Enrollment.objects.filter(id=enrollment.id).update(
        status="revoked",
        revoked_at=timezone.now(),
        revocation_reason_code="ADMIN_REVOKED",
        row_version=2,
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        Enrollment.objects.filter(id=enrollment.id).update(status="active", row_version=3)
    with pytest.raises(DatabaseError), transaction.atomic():
        Enrollment.objects.filter(id=enrollment.id).delete()


@pytest.mark.django_db
def test_progress_parent_and_lesson_edges_are_version_safe(
    tenancy_seed: dict[str, Any],
) -> None:
    graph, enrollment = create_enrollment(tenancy_seed)
    progress = CourseProgress.objects.create(
        tenant=tenancy_seed["alpha"],
        enrollment=enrollment,
        course_version=graph["version"],
        required_lesson_count=1,
    )
    LessonProgress.objects.create(
        tenant=tenancy_seed["alpha"],
        enrollment=enrollment,
        course_version=graph["version"],
        lesson=graph["lesson"],
    )

    beta = create_published_course(tenancy_seed, "beta")
    with pytest.raises(IntegrityError), transaction.atomic():
        LessonProgress.objects.create(
            tenant=tenancy_seed["alpha"],
            enrollment=enrollment,
            course_version=graph["version"],
            lesson=beta["lesson"],
        )

    assert progress.required_lesson_count == 1

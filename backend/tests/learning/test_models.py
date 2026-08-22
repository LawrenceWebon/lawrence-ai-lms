from __future__ import annotations

from typing import Any

import pytest
from django.utils import timezone

from lms.modules.courses.models import Course, CourseVersion
from lms.modules.learning.models import (
    COURSE_PROGRESS_STATES,
    ENROLLMENT_STATUSES,
    LESSON_PROGRESS_STATES,
    CourseProgress,
    Enrollment,
    LessonProgress,
)
from lms.modules.tenancy.models import RolePermission
from tests.courses.test_models import CONTENT_HASH, create_course_graph
from tests.tenancy.conftest import tenancy_seed as tenancy_seed


def create_published_course(seed: dict[str, Any], tenant_key: str = "alpha") -> dict[str, Any]:
    graph = create_course_graph(seed, tenant_key)
    CourseVersion.objects.filter(id=graph["version"].id).update(
        status="published",
        submitted_hash=CONTENT_HASH,
        approved_hash=CONTENT_HASH,
    )
    Course.objects.filter(id=graph["course"].id).update(
        current_published_version_id=graph["version"].id
    )
    graph["course"].refresh_from_db()
    graph["version"].refresh_from_db()
    return graph


def test_learning_models_use_frozen_tables_and_states() -> None:
    assert {
        Enrollment._meta.db_table,
        CourseProgress._meta.db_table,
        LessonProgress._meta.db_table,
    } == {
        'app"."enrollments',
        'app"."course_progress',
        'app"."lesson_progress',
    }
    assert ENROLLMENT_STATUSES == ("active", "revoked")
    assert COURSE_PROGRESS_STATES == ("not_started", "in_progress", "completed")
    assert LESSON_PROGRESS_STATES == COURSE_PROGRESS_STATES


@pytest.mark.django_db
def test_fixed_learning_permission_matrix_is_provisioned(
    tenancy_seed: dict[str, Any],
) -> None:
    expected = {
        "tenant_admin": {"learning.enrollments.manage"},
        "instructor": set(),
        "reviewer": set(),
        "learner": {"learning.playback.read"},
    }
    for role_code, permission_codes in expected.items():
        actual = set(
            RolePermission.objects.filter(
                tenant=tenancy_seed["alpha"],
                role__code=role_code,
                permission__code__startswith="learning.",
            ).values_list("permission__code", flat=True)
        )
        assert actual == permission_codes


@pytest.mark.django_db
def test_revoked_enrollment_history_allows_a_fresh_version_pin(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_published_course(tenancy_seed)
    learner = tenancy_seed["memberships"]["learner"]
    first = Enrollment.objects.create(
        tenant=tenancy_seed["alpha"],
        learner_membership=learner,
        course=graph["course"],
        course_version=graph["version"],
        status="revoked",
        revoked_at=timezone.now(),
        revocation_reason_code="ADMIN_REVOKED",
        row_version=2,
    )
    second = Enrollment.objects.create(
        tenant=tenancy_seed["alpha"],
        learner_membership=learner,
        course=graph["course"],
        course_version=graph["version"],
    )

    assert first.id != second.id
    assert first.course_version_id == second.course_version_id
    assert first.status == "revoked"
    assert second.status == "active"

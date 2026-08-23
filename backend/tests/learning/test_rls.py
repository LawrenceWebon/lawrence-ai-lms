from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from django.db import DatabaseError, connection, transaction

from lms.api.learning_composition import DjangoLearningService
from lms.api.schemas.learning import ProgressCommandV1
from lms.modules.courses.models import Course, CourseVersion, Lesson
from lms.modules.identity.models import UserProfile
from lms.modules.learning.models import CourseProgress, Enrollment, LessonProgress
from lms.modules.tenancy.models import (
    MembershipRole,
    Role,
    RolePermission,
    TenantMembership,
)
from tests.learning.test_models import create_published_course
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

pytestmark = [pytest.mark.rls, pytest.mark.django_db(transaction=True)]

LEARNING_TABLES = {"enrollments", "course_progress", "lesson_progress"}


def set_context(actor_id: object | None, tenant_id: object | None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_actor_id', %s, true)",
            ["" if actor_id is None else str(actor_id)],
        )
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            ["" if tenant_id is None else str(tenant_id)],
        )


def set_runtime_role() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL ROLE lms_api_runtime")


def create_enrollment(
    seed: dict[str, Any], graph: dict[str, Any], membership: object
) -> Enrollment:
    return Enrollment.objects.create(
        tenant=seed["alpha"],
        learner_membership=membership,
        course=graph["course"],
        course_version=graph["version"],
        assigned_by_actor_id=seed["profiles"]["admin"].provider_subject,
    )


def create_other_learner(seed: dict[str, Any]) -> tuple[UserProfile, TenantMembership]:
    profile = UserProfile.objects.create(provider_subject=uuid4())
    membership = TenantMembership.objects.create(
        tenant=seed["alpha"],
        user_profile=profile,
        status="active",
    )
    MembershipRole.objects.create(
        tenant=seed["alpha"],
        membership=membership,
        role=Role.objects.get(tenant=seed["alpha"], code="learner"),
    )
    return profile, membership


def test_learning_tables_are_non_runtime_owned_with_forced_rls() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT class.relname, role.rolname, class.relrowsecurity, class.relforcerowsecurity
              FROM pg_class class
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              JOIN pg_roles role ON role.oid = class.relowner
             WHERE namespace.nspname = 'app' AND class.relname = ANY(%s)
            """,
            [sorted(LEARNING_TABLES)],
        )
        rows = cursor.fetchall()
    assert {row[0] for row in rows} == LEARNING_TABLES
    assert all(owner == "lms_object_owner" for _, owner, _, _ in rows)
    assert all(enabled and forced for _, _, enabled, forced in rows)


def test_runtime_learner_sees_only_own_active_pin_and_safe_course_graph(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_published_course(tenancy_seed)
    own = create_enrollment(tenancy_seed, graph, tenancy_seed["memberships"]["learner"])
    _, other_membership = create_other_learner(tenancy_seed)
    other = create_enrollment(tenancy_seed, graph, other_membership)
    actor_id = tenancy_seed["profiles"]["learner"].provider_subject

    with transaction.atomic():
        set_context(actor_id, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert list(Enrollment.objects.values_list("id", flat=True)) == [own.id]
        assert Course.objects.filter(id=graph["course"].id).exists()
        assert CourseVersion.objects.filter(id=graph["version"].id).exists()
        assert Lesson.objects.filter(id=graph["lesson"].id).exists()
        assert not Enrollment.objects.filter(id=other.id).exists()
        with pytest.raises(DatabaseError), transaction.atomic():
            Enrollment.objects.create(
                tenant_id=tenancy_seed["alpha"].id,
                learner_membership_id=tenancy_seed["memberships"]["learner"].id,
                course_id=graph["course"].id,
                course_version_id=graph["version"].id,
                assigned_by_actor_id=actor_id,
            )
        with pytest.raises(DatabaseError), transaction.atomic():
            LessonProgress.objects.create(
                tenant_id=tenancy_seed["alpha"].id,
                enrollment_id=other.id,
                course_version_id=graph["version"].id,
                lesson_id=graph["lesson"].id,
                state="in_progress",
            )

    Enrollment.objects.filter(id=own.id).update(
        status="revoked",
        revoked_at="2026-08-21T00:00:00Z",
        revocation_reason_code="ADMIN_REVOKED",
        row_version=2,
    )
    with transaction.atomic():
        set_context(actor_id, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert Enrollment.objects.count() == 0
        assert Course.objects.count() == 0
        assert CourseVersion.objects.count() == 0
        assert Lesson.objects.count() == 0


def test_real_progress_service_commits_as_non_owner_and_permission_revocation_closes_access(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_published_course(tenancy_seed)
    enrollment = create_enrollment(
        tenancy_seed,
        graph,
        tenancy_seed["memberships"]["learner"],
    )
    actor_id = tenancy_seed["profiles"]["learner"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    service = DjangoLearningService()

    with transaction.atomic():
        set_context(actor_id, tenant_id)
        set_runtime_role()
        assert Enrollment.objects.select_for_update().filter(id=enrollment.id).first() is not None
        result = service.complete_lesson(
            actor_id=actor_id,
            tenant_id=tenant_id,
            enrollment_id=enrollment.id,
            command=ProgressCommandV1(
                command="complete_lesson",
                lesson_id=graph["lesson"].id,
                expected_progress_row_version=0,
            ),
            idempotency_key="runtime-progress-000001",
        )
        assert result.course_state.value == "completed"
        assert CourseProgress.objects.get(enrollment_id=enrollment.id).row_version == 1
        assert LessonProgress.objects.get(enrollment_id=enrollment.id).state == "completed"

    RolePermission.objects.filter(
        tenant=tenancy_seed["alpha"],
        role__code="learner",
        permission__code="learning.playback.read",
    ).delete()
    with transaction.atomic():
        set_context(actor_id, tenant_id)
        set_runtime_role()
        assert Enrollment.objects.count() == 0
        assert CourseProgress.objects.count() == 0
        assert LessonProgress.objects.count() == 0


def test_absent_or_wrong_tenant_context_exposes_no_learning_rows(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_published_course(tenancy_seed)
    create_enrollment(tenancy_seed, graph, tenancy_seed["memberships"]["learner"])
    actor_id = tenancy_seed["profiles"]["learner"].provider_subject

    with transaction.atomic():
        set_runtime_role()
        assert Enrollment.objects.count() == 0
        assert CourseProgress.objects.count() == 0

    with transaction.atomic():
        set_context(actor_id, tenancy_seed["beta"].id)
        set_runtime_role()
        assert Enrollment.objects.count() == 0
        assert Course.objects.count() == 0

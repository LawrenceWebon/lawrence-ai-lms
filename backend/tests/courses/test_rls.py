from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, connection, transaction
from django.db.models import F

from lms.modules.courses.models import Course, CourseVersion
from lms.modules.courses.repositories import CourseRepository
from lms.modules.tenancy.models import MembershipRole, Role, RolePermission
from tests.courses.test_models import CONTENT_HASH, create_course_graph
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

pytestmark = [pytest.mark.rls, pytest.mark.django_db(transaction=True)]

COURSE_TABLES = {
    "courses",
    "course_versions",
    "course_instructors",
    "curriculum_sections",
    "lessons",
    "lesson_content_blocks",
    "course_publication_reviews",
}


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


def test_all_course_tables_are_non_runtime_owned_with_forced_rls() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT class.relname, role.rolname, class.relrowsecurity, class.relforcerowsecurity
              FROM pg_class class
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              JOIN pg_roles role ON role.oid = class.relowner
             WHERE namespace.nspname = 'app' AND class.relname = ANY(%s)
            """,
            [sorted(COURSE_TABLES)],
        )
        rows = cursor.fetchall()
    assert {row[0] for row in rows} == COURSE_TABLES
    assert all(owner == "lms_object_owner" for _, owner, _, _ in rows)
    assert all(enabled and forced for _, _, enabled, forced in rows)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'lms_api_runtime'"
        )
        runtime_flags = cursor.fetchone()
    assert runtime_flags == (False, False)


def test_runtime_context_is_tenant_scoped_and_guessed_ids_are_invisible(
    tenancy_seed: dict[str, Any],
) -> None:
    alpha = create_course_graph(tenancy_seed, "alpha")
    beta = create_course_graph(tenancy_seed, "beta")
    actor = tenancy_seed["profiles"]["instructor"].provider_subject

    with transaction.atomic():
        set_context(actor, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert list(Course.objects.values_list("id", flat=True)) == [alpha["course"].id]
        assert not Course.objects.filter(id=beta["course"].id).exists()

    with transaction.atomic():
        set_runtime_role()
        assert Course.objects.count() == 0

    with transaction.atomic():
        set_context(tenancy_seed["profiles"]["outsider"].provider_subject, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert Course.objects.count() == 0


def test_runtime_cross_tenant_crud_and_tenant_mutation_fail_closed(
    tenancy_seed: dict[str, Any],
) -> None:
    alpha = create_course_graph(tenancy_seed, "alpha")
    beta = create_course_graph(tenancy_seed, "beta")
    actor = tenancy_seed["profiles"]["instructor"].provider_subject

    with transaction.atomic():
        set_context(actor, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert Course.objects.filter(id=beta["course"].id).update(row_version=2) == 0
        assert CourseVersion.objects.filter(id=beta["version"].id).delete()[0] == 0
        with pytest.raises(DatabaseError), transaction.atomic():
            CourseVersion.objects.create(
                tenant=tenancy_seed["beta"],
                course=beta["course"],
                version_number=2,
                primary_locale="en",
                title="Cross tenant",
                description="Synthetic.",
                content_hash=CONTENT_HASH,
            )
        with pytest.raises(DatabaseError), transaction.atomic():
            Course.objects.filter(id=alpha["course"].id).update(tenant_id=tenancy_seed["beta"].id)


def test_inactive_membership_or_entitlement_revokes_course_access(
    tenancy_seed: dict[str, Any],
) -> None:
    create_course_graph(tenancy_seed, "alpha")
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    with transaction.atomic():
        set_context(actor, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert Course.objects.count() == 1

    from lms.modules.tenancy.models import EntitlementPeriod, TenantMembership

    TenantMembership.objects.filter(id=tenancy_seed["memberships"]["instructor_alpha"].id).update(
        status="inactive"
    )
    with transaction.atomic():
        set_context(actor, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert Course.objects.count() == 0

    TenantMembership.objects.filter(id=tenancy_seed["memberships"]["instructor_alpha"].id).update(
        status="active"
    )
    EntitlementPeriod.objects.filter(tenant=tenancy_seed["alpha"]).update(status="expired")
    with transaction.atomic():
        set_context(actor, tenancy_seed["alpha"].id)
        set_runtime_role()
        assert Course.objects.count() == 0


def test_explicit_permission_removal_revokes_course_reads(
    tenancy_seed: dict[str, Any],
) -> None:
    create_course_graph(tenancy_seed, "alpha")
    RolePermission.objects.filter(
        tenant=tenancy_seed["alpha"],
        role__code="instructor",
        permission__code="courses.read",
    ).delete()
    with transaction.atomic():
        set_context(
            tenancy_seed["profiles"]["instructor"].provider_subject,
            tenancy_seed["alpha"].id,
        )
        set_runtime_role()
        assert Course.objects.count() == 0


def test_reviewer_permission_cannot_mutate_draft_content(
    tenancy_seed: dict[str, Any],
) -> None:
    graph = create_course_graph(tenancy_seed, "alpha")
    membership = tenancy_seed["memberships"]["learner"]
    MembershipRole.objects.create(
        tenant=tenancy_seed["alpha"],
        membership=membership,
        role=Role.objects.get(tenant=tenancy_seed["alpha"], code="reviewer"),
    )
    with transaction.atomic():
        set_context(
            tenancy_seed["profiles"]["learner"].provider_subject,
            tenancy_seed["alpha"].id,
        )
        set_runtime_role()
        assert CourseVersion.objects.filter(id=graph["version"].id).exists()
        with pytest.raises(DatabaseError), transaction.atomic():
            CourseVersion.objects.filter(id=graph["version"].id).update(
                title="Unauthorized content edit",
                row_version=F("row_version") + 1,
            )


def test_repository_and_atomic_facts_work_as_runtime_role(
    tenancy_seed: dict[str, Any],
) -> None:
    repository = CourseRepository()
    actor_id = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    with transaction.atomic():
        set_context(actor_id, tenant_id)
        set_runtime_role()
        snapshot = repository.insert_course_with_v1(
            tenant_id=tenant_id,
            slug="runtime-repository-course",
            primary_locale="en",
            title="Runtime repository course",
            description="Rights-cleared synthetic fixture.",
            content_hash=CONTENT_HASH,
            instructor_membership_ids=(tenancy_seed["memberships"]["instructor_alpha"].id,),
        )
        reservation, replay = repository.reserve_idempotency(
            tenant_id=tenant_id,
            actor_id=actor_id,
            operation="courses.create",
            key_digest="c" * 64,
            request_hash="d" * 64,
        )
        assert replay is False
        repository.complete_idempotency(reservation.id, {"status": 201})
        repository.append_atomic_facts(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type="course.version.submitted.v1",
            subject_type="course_version",
            subject_id=snapshot["version"]["id"],
            aggregate_type="course",
            aggregate_id=snapshot["course"]["id"],
            payload={"course_version_id": snapshot["version"]["id"]},
        )
        assert (
            repository.load_snapshot(tenant_id, snapshot["course"]["id"], snapshot["version"]["id"])
            == snapshot
        )

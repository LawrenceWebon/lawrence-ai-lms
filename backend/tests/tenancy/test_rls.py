from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from lms.modules.tenancy.errors import TenancyError
from lms.modules.tenancy.models import EntitlementPeriod, TenantInvitation, TenantMembership
from lms.modules.tenancy.services import (
    accept_invitation,
    create_invitation,
    get_authentication_context,
    list_memberships,
)

pytestmark = [pytest.mark.rls, pytest.mark.django_db(transaction=True)]


def test_every_tenant_table_is_owned_and_forced_through_rls() -> None:
    expected = {
        ("app", "tenants"),
        ("app", "entitlement_periods"),
        ("app", "tenant_memberships"),
        ("app", "roles"),
        ("app", "role_permissions"),
        ("app", "membership_roles"),
        ("app", "tenant_invitations"),
        ("app", "tenant_invitation_roles"),
        ("audit", "tenant_audit_facts"),
        ("integration", "idempotency_reservations"),
        ("integration", "tenant_outbox_facts"),
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT namespace.nspname, class.relname, role.rolname,
                   class.relrowsecurity, class.relforcerowsecurity
              FROM pg_class class
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              JOIN pg_roles role ON role.oid = class.relowner
             WHERE (namespace.nspname, class.relname) IN (
                SELECT * FROM unnest(%s::text[], %s::text[])
             )
            """,
            [
                [schema for schema, _ in sorted(expected)],
                [table for _, table in sorted(expected)],
            ],
        )
        rows = cursor.fetchall()
    assert {(schema, table) for schema, table, *_ in rows} == expected
    assert all(owner == "lms_object_owner" for _, _, owner, _, _ in rows)
    assert all(enabled and forced for _, _, _, enabled, forced in rows)


def set_context(actor_id: object, tenant_id: object | None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_actor_id', %s, true)", [str(actor_id)])
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            ["" if tenant_id is None else str(tenant_id)],
        )
        cursor.execute(
            "SELECT set_config('app.current_request_id', %s, true)",
            ["00000000-0000-4000-8000-00000000f001"],
        )


def test_runtime_role_selects_only_current_authorized_tenant(
    tenancy_seed: dict, runtime_role: None
) -> None:
    set_context(
        tenancy_seed["profiles"]["instructor"].provider_subject,
        tenancy_seed["alpha"].id,
    )
    assert list(TenantMembership.objects.values_list("tenant_id", flat=True)) == [
        tenancy_seed["alpha"].id
    ]


def test_missing_or_expired_entitlement_denies_runtime_role(
    tenancy_seed: dict, runtime_role: None
) -> None:
    set_context(
        tenancy_seed["profiles"]["instructor"].provider_subject,
        tenancy_seed["alpha"].id,
    )
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")
        EntitlementPeriod.objects.filter(tenant=tenancy_seed["alpha"]).update(status="expired")
        cursor.execute("SET LOCAL ROLE lms_api_runtime")
    assert TenantMembership.objects.count() == 0


def test_runtime_role_cannot_cross_tenant_update_or_delete(
    tenancy_seed: dict, runtime_role: None
) -> None:
    set_context(
        tenancy_seed["profiles"]["admin"].provider_subject,
        tenancy_seed["alpha"].id,
    )
    assert (
        TenantMembership.objects.filter(
            id=tenancy_seed["memberships"]["instructor_beta"].id
        ).update(status="inactive")
        == 0
    )
    assert (
        TenantMembership.objects.filter(
            id=tenancy_seed["memberships"]["instructor_beta"].id
        ).delete()[0]
        == 0
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        TenantMembership.objects.create(
            tenant=tenancy_seed["beta"],
            user_profile=tenancy_seed["profiles"]["outsider"],
            status="active",
        )


def test_public_invitation_services_work_under_runtime_role(
    tenancy_seed: dict, runtime_role: None
) -> None:
    alpha = tenancy_seed["alpha"]
    admin_actor = tenancy_seed["profiles"]["admin"].provider_subject
    invitee_actor = tenancy_seed["profiles"]["invitee"].provider_subject

    context = get_authentication_context(
        tenancy_seed["profiles"]["instructor"].provider_subject, alpha.id
    )
    assert [candidate.slug for candidate in context.available_tenants] == ["alpha", "beta"]
    assert len(list_memberships(admin_actor, alpha.id)) == 4
    receipt = create_invitation(
        admin_actor,
        alpha.id,
        "runtime-invitee@example.invalid",
        ["instructor"],
        "runtime-role-invite-0001",
    )
    assert receipt.delivery_token is not None
    membership = accept_invitation(
        invitee_actor, "runtime-invitee@example.invalid", receipt.delivery_token
    )
    assert membership.role_codes == ("instructor",)


def test_runtime_invitation_rejects_wrong_verified_email_before_write(
    tenancy_seed: dict, runtime_role: None
) -> None:
    alpha = tenancy_seed["alpha"]
    receipt = create_invitation(
        tenancy_seed["profiles"]["admin"].provider_subject,
        alpha.id,
        "runtime-invitee@example.invalid",
        ["instructor"],
        "runtime-wrong-identity-0001",
    )

    with pytest.raises(TenancyError, match="INVITATION_INVALID"):
        accept_invitation(
            tenancy_seed["profiles"]["outsider"].provider_subject,
            "outsider@example.invalid",
            receipt.delivery_token,
        )

    set_context(tenancy_seed["profiles"]["outsider"].provider_subject, None)
    assert not TenantMembership.objects.filter(
        user_profile=tenancy_seed["profiles"]["outsider"]
    ).exists()


def test_runtime_invitation_expiry_transition_is_persisted(
    tenancy_seed: dict, runtime_role: None
) -> None:
    receipt = create_invitation(
        tenancy_seed["profiles"]["admin"].provider_subject,
        tenancy_seed["alpha"].id,
        "invitee@example.invalid",
        ["instructor"],
        "runtime-expired-invite-0001",
    )
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")
        TenantInvitation.objects.filter(id=receipt.id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        cursor.execute("SET LOCAL ROLE lms_api_runtime")

    with pytest.raises(TenancyError, match="INVITATION_EXPIRED"):
        accept_invitation(
            tenancy_seed["profiles"]["invitee"].provider_subject,
            "invitee@example.invalid",
            receipt.delivery_token,
        )

    set_context(tenancy_seed["profiles"]["admin"].provider_subject, tenancy_seed["alpha"].id)
    assert TenantInvitation.objects.get(id=receipt.id).status == "expired"

    with pytest.raises(TenancyError, match="INVITATION_EXPIRED"):
        accept_invitation(
            tenancy_seed["profiles"]["invitee"].provider_subject,
            "invitee@example.invalid",
            receipt.delivery_token,
        )

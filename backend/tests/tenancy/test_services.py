from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone

from lms.modules.tenancy.errors import TenancyError
from lms.modules.tenancy.models import (
    AuditFact,
    IdempotencyReservation,
    OutboxFact,
    TenantInvitation,
    TenantMembership,
)
from lms.modules.tenancy.services import (
    accept_invitation,
    create_invitation,
    get_authentication_context,
    list_memberships,
    update_membership,
)


def test_authentication_context_is_explicit_and_postgres_authoritative(tenancy_seed: dict) -> None:
    actor_id = tenancy_seed["profiles"]["instructor"].provider_subject

    unselected = get_authentication_context(actor_id, None)
    assert unselected.active_tenant is None
    assert [candidate.slug for candidate in unselected.available_tenants] == ["alpha", "beta"]

    selected = get_authentication_context(actor_id, tenancy_seed["alpha"].id)
    assert selected.active_tenant is not None
    assert selected.active_tenant.slug == "alpha"
    assert selected.membership is not None
    assert selected.membership.role_codes == ("instructor",)
    assert selected.entitlement is not None
    assert selected.entitlement.status == "active"


def test_inactive_and_cross_tenant_contexts_fail_closed(tenancy_seed: dict) -> None:
    inactive_actor = tenancy_seed["profiles"]["inactive"].provider_subject
    outsider_actor = tenancy_seed["profiles"]["outsider"].provider_subject

    with pytest.raises(TenancyError, match="TENANT_ACCESS_INACTIVE"):
        get_authentication_context(inactive_actor, tenancy_seed["alpha"].id)
    with pytest.raises(TenancyError, match="TENANT_ACCESS_DENIED"):
        get_authentication_context(outsider_actor, tenancy_seed["alpha"].id)


def test_only_tenant_admin_can_list_and_change_memberships(tenancy_seed: dict) -> None:
    alpha = tenancy_seed["alpha"]
    admin_actor = tenancy_seed["profiles"]["admin"].provider_subject
    learner_actor = tenancy_seed["profiles"]["learner"].provider_subject

    summaries = list_memberships(admin_actor, alpha.id)
    assert [summary.role_codes for summary in summaries] == [
        ("tenant_admin",),
        ("instructor",),
        ("learner",),
        ("learner",),
    ]

    with pytest.raises(TenancyError, match="TENANT_ACCESS_DENIED"):
        update_membership(
            learner_actor,
            alpha.id,
            tenancy_seed["memberships"]["instructor_alpha"].id,
            role_codes=["reviewer"],
            row_version=2,
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_membership_updates_have_one_winner(tenancy_seed: dict) -> None:
    alpha = tenancy_seed["alpha"]
    actor_id = tenancy_seed["profiles"]["admin"].provider_subject
    membership_id = tenancy_seed["memberships"]["learner"].id

    def update(role_code: str) -> str:
        close_old_connections()
        try:
            result = update_membership(
                actor_id,
                alpha.id,
                membership_id,
                role_codes=[role_code],
                row_version=1,
            )
            return f"ok:{result.role_codes[0]}"
        except TenancyError as error:
            return error.code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update, ["instructor", "reviewer"]))

    assert len([result for result in results if result.startswith("ok:")]) == 1
    assert results.count("VERSION_CONFLICT") == 1


def test_invitation_and_idempotency_are_single_effect_and_token_safe(tenancy_seed: dict) -> None:
    alpha = tenancy_seed["alpha"]
    actor_id = tenancy_seed["profiles"]["admin"].provider_subject

    first = create_invitation(
        actor_id,
        alpha.id,
        "invitee@example.invalid",
        ["instructor", "reviewer", "instructor"],
        "invite-idempotency-0001",
    )
    replay = create_invitation(
        actor_id,
        alpha.id,
        "invitee@example.invalid",
        ["reviewer", "instructor"],
        "invite-idempotency-0001",
    )

    assert first.id == replay.id
    assert first.delivery_token is not None
    assert replay.delivery_token is None
    invitation = TenantInvitation.objects.get(id=first.id)
    assert first.delivery_token not in invitation.token_digest
    assert "invitee@example.invalid" not in invitation.token_digest
    assert TenantInvitation.objects.count() == 1
    assert IdempotencyReservation.objects.count() == 1

    with pytest.raises(TenancyError, match="IDEMPOTENCY_CONFLICT"):
        create_invitation(
            actor_id,
            alpha.id,
            "changed@example.invalid",
            ["learner"],
            "invite-idempotency-0001",
        )

    accepted = accept_invitation(
        tenancy_seed["profiles"]["invitee"].provider_subject,
        "invitee@example.invalid",
        first.delivery_token,
    )
    accepted_replay = accept_invitation(
        tenancy_seed["profiles"]["invitee"].provider_subject,
        "invitee@example.invalid",
        first.delivery_token,
    )
    assert accepted == accepted_replay
    assert accepted.role_codes == ("instructor", "reviewer")
    assert (
        TenantMembership.objects.filter(
            tenant=alpha, user_profile=tenancy_seed["profiles"]["invitee"]
        ).count()
        == 1
    )


def test_invitation_rejects_wrong_verified_identity_without_side_effects(
    tenancy_seed: dict,
) -> None:
    alpha = tenancy_seed["alpha"]
    receipt = create_invitation(
        tenancy_seed["profiles"]["admin"].provider_subject,
        alpha.id,
        "invitee@example.invalid",
        ["instructor"],
        "wrong-identity-invite-0001",
    )
    audit_count = AuditFact.objects.count()
    outbox_count = OutboxFact.objects.count()

    with pytest.raises(TenancyError, match="INVITATION_INVALID"):
        accept_invitation(
            tenancy_seed["profiles"]["outsider"].provider_subject,
            "outsider@example.invalid",
            receipt.delivery_token,
        )

    assert not TenantMembership.objects.filter(
        tenant=alpha, user_profile=tenancy_seed["profiles"]["outsider"]
    ).exists()
    assert AuditFact.objects.count() == audit_count
    assert OutboxFact.objects.count() == outbox_count


@pytest.mark.parametrize(
    ("tenant_status", "entitlement_status"),
    [("suspended", "active"), ("active", "expired"), ("active", "suspended")],
)
def test_invitation_rechecks_tenant_and_entitlement_before_mutation(
    tenancy_seed: dict, tenant_status: str, entitlement_status: str
) -> None:
    alpha = tenancy_seed["alpha"]
    receipt = create_invitation(
        tenancy_seed["profiles"]["admin"].provider_subject,
        alpha.id,
        "invitee@example.invalid",
        ["instructor"],
        f"lifecycle-{tenant_status}-{entitlement_status}-0001",
    )
    alpha.status = tenant_status
    alpha.save(update_fields=("status", "updated_at"))
    alpha.entitlements.update(status=entitlement_status)

    with pytest.raises(TenancyError, match="INVITATION_INVALID"):
        accept_invitation(
            tenancy_seed["profiles"]["invitee"].provider_subject,
            "invitee@example.invalid",
            receipt.delivery_token,
        )

    assert not TenantMembership.objects.filter(
        tenant=alpha, user_profile=tenancy_seed["profiles"]["invitee"]
    ).exists()


def test_expired_invitation_status_is_persisted_before_error(tenancy_seed: dict) -> None:
    receipt = create_invitation(
        tenancy_seed["profiles"]["admin"].provider_subject,
        tenancy_seed["alpha"].id,
        "invitee@example.invalid",
        ["instructor"],
        "expired-state-invite-0001",
    )
    TenantInvitation.objects.filter(id=receipt.id).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    with pytest.raises(TenancyError, match="INVITATION_EXPIRED"):
        accept_invitation(
            tenancy_seed["profiles"]["invitee"].provider_subject,
            "invitee@example.invalid",
            receipt.delivery_token,
        )

    invitation = TenantInvitation.objects.get(id=receipt.id)
    assert invitation.status == "expired"
    assert invitation.row_version == 2


def test_audit_and_outbox_rollback_with_failed_mutation_fact(tenancy_seed: dict) -> None:
    alpha = tenancy_seed["alpha"]
    actor_id = tenancy_seed["profiles"]["admin"].provider_subject
    membership = tenancy_seed["memberships"]["learner"]

    with patch.object(OutboxFact.objects, "create", side_effect=RuntimeError("outbox unavailable")):
        with pytest.raises(RuntimeError, match="outbox unavailable"):
            update_membership(
                actor_id,
                alpha.id,
                membership.id,
                status="inactive",
                row_version=1,
            )

    membership.refresh_from_db()
    assert membership.status == "active"
    assert membership.row_version == 1
    assert AuditFact.objects.count() == 0
    assert OutboxFact.objects.count() == 0

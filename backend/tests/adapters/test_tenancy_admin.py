from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lms.adapters.admin.tenancy import AdminActorContext, TenancyAdminActions
from lms.api.schemas.tenancy import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    MembershipAdministrationError,
    UpdateMembershipRequest,
)
from tests.contract_fakes.f001_membership_admin import (
    ACTIVE_TOKEN,
    ALPHA_ADMIN_ID,
    ALPHA_TENANT_ID,
    MEMBERSHIP_ID,
    RecordingMembershipAdministrationServiceFake,
)


def test_admin_actions_delegate_to_the_same_service_operations_as_http() -> None:
    service = RecordingMembershipAdministrationServiceFake()
    actions = TenancyAdminActions(service=service)
    context = AdminActorContext(actor_id=ALPHA_ADMIN_ID, tenant_id=ALPHA_TENANT_ID)

    actions.list_memberships(context=context)
    invitation = actions.create_invitation(
        context=context,
        request=CreateInvitationRequest(
            email="instructor@example.invalid", role_codes=["instructor"]
        ),
        idempotency_key="fixture-create-invitation-0001",
    )
    actions.accept_invitation(
        context=AdminActorContext(actor_id=ALPHA_ADMIN_ID, tenant_id=None),
        request=AcceptInvitationRequest(invitation_token=ACTIVE_TOKEN),
    )
    actions.update_membership(
        context=context,
        membership_id=MEMBERSHIP_ID,
        request=UpdateMembershipRequest(status="inactive", role_codes=["reviewer"], row_version=1),
    )

    assert invitation.id == service.invitation.id
    assert [call.operation for call in service.calls] == [
        "list_memberships",
        "create_invitation",
        "accept_invitation",
        "update_membership",
    ]
    assert all(call.actor_id == ALPHA_ADMIN_ID for call in service.calls)
    assert service.calls[1].tenant_selector == ALPHA_TENANT_ID


@pytest.mark.parametrize("operation", ["list", "create", "update"])
def test_tenant_scoped_admin_actions_require_explicit_tenant_context(operation: str) -> None:
    actions = TenancyAdminActions(service=RecordingMembershipAdministrationServiceFake())
    context = AdminActorContext(actor_id=ALPHA_ADMIN_ID, tenant_id=None)

    with pytest.raises(MembershipAdministrationError) as caught:
        if operation == "list":
            actions.list_memberships(context=context)
        elif operation == "create":
            actions.create_invitation(
                context=context,
                request=CreateInvitationRequest(
                    email="learner@example.invalid", role_codes=["learner"]
                ),
                idempotency_key="fixture-create-invitation-0001",
            )
        else:
            actions.update_membership(
                context=context,
                membership_id=MEMBERSHIP_ID,
                request=UpdateMembershipRequest(status="inactive", row_version=1),
            )

    assert caught.value.code == "TENANT_CONTEXT_REQUIRED"


def test_admin_adapter_has_no_orm_import_or_direct_write_escape_hatch() -> None:
    source_path = Path("backend/src/lms/adapters/admin/tenancy.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}

    assert not any(module.endswith(".models") for module in imports)
    assert {"objects", "save", "delete"}.isdisjoint(attributes)

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from lms.api.schemas.tenancy import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    InvitationReceiptResponse,
    MembershipAdministrationError,
    MembershipAdministrationServiceV1,
    MembershipSummaryResponse,
    UpdateMembershipRequest,
)


@dataclass(frozen=True, slots=True)
class AdminActorContext:
    """Trusted identity and explicit tenant/JIT selectors from Django Admin."""

    actor_id: UUID
    verified_email: str
    tenant_id: UUID | None
    privileged_access_grant_id: UUID | None = None


class TenancyAdminActions:
    """Adapter-only actions; the service remains authorization and mutation authority."""

    def __init__(self, *, service: MembershipAdministrationServiceV1) -> None:
        self._service = service

    @staticmethod
    def _tenant_selector(context: AdminActorContext) -> UUID:
        if context.tenant_id is None:
            raise MembershipAdministrationError(
                code="TENANT_CONTEXT_REQUIRED",
                status=400,
                title="Tenant context required",
                detail="Select a tenant before performing this action.",
            )
        return context.tenant_id

    def list_memberships(self, *, context: AdminActorContext) -> list[MembershipSummaryResponse]:
        results = self._service.list_memberships(
            actor_id=context.actor_id,
            tenant_selector=self._tenant_selector(context),
        )
        return [
            MembershipSummaryResponse.model_validate(result, from_attributes=True)
            for result in results
        ]

    def create_invitation(
        self,
        *,
        context: AdminActorContext,
        request: CreateInvitationRequest,
        idempotency_key: str,
    ) -> InvitationReceiptResponse:
        result = self._service.create_invitation(
            actor_id=context.actor_id,
            tenant_selector=self._tenant_selector(context),
            email=request.email,
            role_codes=tuple(request.role_codes),
            idempotency_key=idempotency_key,
        )
        return InvitationReceiptResponse.model_validate(result, from_attributes=True)

    def accept_invitation(
        self, *, context: AdminActorContext, request: AcceptInvitationRequest
    ) -> MembershipSummaryResponse:
        result = self._service.accept_invitation(
            actor_id=context.actor_id,
            verified_email=context.verified_email,
            invitation_token=request.invitation_token.get_secret_value(),
        )
        return MembershipSummaryResponse.model_validate(result, from_attributes=True)

    def update_membership(
        self,
        *,
        context: AdminActorContext,
        membership_id: UUID,
        request: UpdateMembershipRequest,
    ) -> MembershipSummaryResponse:
        result = self._service.update_membership(
            actor_id=context.actor_id,
            tenant_selector=self._tenant_selector(context),
            membership_id=membership_id,
            status=request.status,
            role_codes=(tuple(request.role_codes) if request.role_codes is not None else None),
            row_version=request.row_version,
        )
        return MembershipSummaryResponse.model_validate(result, from_attributes=True)

from __future__ import annotations

from uuid import UUID

from lms.api.schemas.tenancy import MembershipAdministrationError
from lms.modules.tenancy import services
from lms.modules.tenancy.errors import TenancyError
from lms.modules.tenancy.types import (
    AuthenticationContextResult,
    InvitationReceipt,
    MembershipSummary,
)

_PROBLEM_STATUS = {
    "AUTHENTICATION_REQUIRED": 401,
    "TOKEN_INVALID": 401,
    "TENANT_CONTEXT_REQUIRED": 400,
    "TENANT_ACCESS_DENIED": 404,
    "TENANT_ACCESS_INACTIVE": 403,
    "INVITATION_INVALID": 404,
    "INVITATION_EXPIRED": 410,
    "IDEMPOTENCY_CONFLICT": 409,
    "VERSION_CONFLICT": 409,
}


def _translate(error: TenancyError) -> MembershipAdministrationError:
    return MembershipAdministrationError(
        code=error.code,
        status=_PROBLEM_STATUS.get(error.code, 500),
        title="Request unavailable",
        detail="The requested operation is unavailable.",
    )


class DjangoTenancyService:
    """HTTP-facing adapter over the real tenancy application service module."""

    def get_authentication_context(
        self, *, actor_id: UUID, tenant_selector: UUID | None
    ) -> AuthenticationContextResult:
        try:
            return services.get_authentication_context(actor_id, tenant_selector)
        except TenancyError as error:
            raise _translate(error) from error

    def list_memberships(
        self, *, actor_id: UUID, tenant_selector: UUID
    ) -> tuple[MembershipSummary, ...]:
        try:
            return services.list_memberships(actor_id, tenant_selector)
        except TenancyError as error:
            raise _translate(error) from error

    def create_invitation(
        self,
        *,
        actor_id: UUID,
        tenant_selector: UUID,
        email: str,
        role_codes: tuple[str, ...],
        idempotency_key: str,
    ) -> InvitationReceipt:
        try:
            return services.create_invitation(
                actor_id,
                tenant_selector,
                email,
                role_codes,
                idempotency_key,
            )
        except TenancyError as error:
            raise _translate(error) from error

    def accept_invitation(
        self, *, actor_id: UUID, verified_email: str, invitation_token: str
    ) -> MembershipSummary:
        try:
            return services.accept_invitation(actor_id, verified_email, invitation_token)
        except TenancyError as error:
            raise _translate(error) from error

    def update_membership(
        self,
        *,
        actor_id: UUID,
        tenant_selector: UUID,
        membership_id: UUID,
        status: str | None,
        role_codes: tuple[str, ...] | None,
        row_version: int,
    ) -> MembershipSummary:
        try:
            return services.update_membership(
                actor_id,
                tenant_selector,
                membership_id,
                status=status,
                role_codes=role_codes,
                row_version=row_version,
            )
        except TenancyError as error:
            raise _translate(error) from error

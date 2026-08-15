from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Final
from uuid import UUID

from lms.api.schemas.tenancy import MembershipAdministrationError

ALPHA_TENANT_ID: Final = UUID("00000000-0000-4000-8000-0000000000a1")
BETA_TENANT_ID: Final = UUID("00000000-0000-4000-8000-0000000000b1")
ALPHA_ADMIN_ID: Final = UUID("00000000-0000-4000-8000-000000000101")
ALPHA_LEARNER_ID: Final = UUID("00000000-0000-4000-8000-000000000103")
OUTSIDER_ID: Final = UUID("00000000-0000-4000-8000-000000000105")
ALPHA_ADMIN_EMAIL: Final = "instructor@example.invalid"
OUTSIDER_EMAIL: Final = "outsider@example.invalid"
MEMBERSHIP_ID: Final = UUID("00000000-0000-4000-8000-000000000301")
INVITATION_ID: Final = UUID("00000000-0000-4000-8000-000000000201")
ACTIVE_TOKEN: Final = "synthetic-active-token-000000000001"  # noqa: S105
EXPIRED_TOKEN: Final = "synthetic-expired-token-00000000001"  # noqa: S105
REVOKED_TOKEN: Final = "synthetic-revoked-token-00000000001"  # noqa: S105
CONSUMED_TOKEN: Final = "synthetic-consumed-token-0000000001"  # noqa: S105
CROSS_TENANT_TOKEN: Final = "synthetic-cross-tenant-token-00000001"  # noqa: S105


@dataclass(frozen=True, slots=True)
class MembershipSummaryValue:
    id: UUID
    tenant_id: UUID
    status: str
    row_version: int
    role_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InvitationReceiptValue:
    id: UUID
    tenant_id: UUID
    status: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class VerifiedActorValue:
    principal_id: UUID
    verified_email: str


@dataclass(frozen=True, slots=True)
class ServiceCall:
    operation: str
    actor_id: UUID
    tenant_selector: UUID | None = None
    membership_id: UUID | None = None
    email: str | None = None
    role_codes: tuple[str, ...] | None = None
    idempotency_key: str | None = None
    invitation_token_digest: str | None = None
    verified_email: str | None = None
    status: str | None = None
    row_version: int | None = None


class RecordingMembershipAdministrationServiceFake:
    """Synthetic Lane B/C boundary fake with no raw-token recording."""

    def __init__(self) -> None:
        self.membership = MembershipSummaryValue(
            id=MEMBERSHIP_ID,
            tenant_id=ALPHA_TENANT_ID,
            status="active",
            row_version=1,
            role_codes=("instructor", "reviewer"),
        )
        self.invitation = InvitationReceiptValue(
            id=INVITATION_ID,
            tenant_id=ALPHA_TENANT_ID,
            status="active",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        self.calls: list[ServiceCall] = []
        self.problem_by_operation: dict[str, MembershipAdministrationError] = {}
        self._invitation_requests: dict[
            str, tuple[tuple[UUID, str, tuple[str, ...]], InvitationReceiptValue]
        ] = {}

    def _raise_scripted_problem(self, operation: str) -> None:
        problem = self.problem_by_operation.get(operation)
        if problem is not None:
            raise problem

    def list_memberships(
        self, *, actor_id: UUID, tenant_selector: UUID
    ) -> tuple[MembershipSummaryValue, ...]:
        self.calls.append(
            ServiceCall(
                operation="list_memberships",
                actor_id=actor_id,
                tenant_selector=tenant_selector,
            )
        )
        self._raise_scripted_problem("list_memberships")
        return (self.membership,)

    def create_invitation(
        self,
        *,
        actor_id: UUID,
        tenant_selector: UUID,
        email: str,
        role_codes: tuple[str, ...],
        idempotency_key: str,
    ) -> InvitationReceiptValue:
        self.calls.append(
            ServiceCall(
                operation="create_invitation",
                actor_id=actor_id,
                tenant_selector=tenant_selector,
                email=email,
                role_codes=role_codes,
                idempotency_key=idempotency_key,
            )
        )
        self._raise_scripted_problem("create_invitation")
        request_fingerprint = (tenant_selector, email, role_codes)
        previous = self._invitation_requests.get(idempotency_key)
        if previous is None:
            self._invitation_requests[idempotency_key] = (
                request_fingerprint,
                self.invitation,
            )
            return self.invitation
        if previous[0] != request_fingerprint:
            raise MembershipAdministrationError(
                code="IDEMPOTENCY_CONFLICT",
                status=409,
                title="Idempotency conflict",
                detail="The idempotency key was already used for another request.",
            )
        return previous[1]

    def accept_invitation(
        self, *, actor_id: UUID, verified_email: str, invitation_token: str
    ) -> MembershipSummaryValue:
        self.calls.append(
            ServiceCall(
                operation="accept_invitation",
                actor_id=actor_id,
                invitation_token_digest=sha256(invitation_token.encode()).hexdigest(),
                verified_email=verified_email,
            )
        )
        self._raise_scripted_problem("accept_invitation")
        if invitation_token == EXPIRED_TOKEN:
            raise MembershipAdministrationError(
                code="INVITATION_EXPIRED",
                status=410,
                title="Invitation unavailable",
                detail="The invitation cannot be accepted.",
            )
        if (
            invitation_token != ACTIVE_TOKEN
            or actor_id != ALPHA_ADMIN_ID
            or verified_email != ALPHA_ADMIN_EMAIL
        ):
            raise MembershipAdministrationError(
                code="INVITATION_INVALID",
                status=404,
                title="Invitation unavailable",
                detail="The invitation cannot be accepted.",
            )
        return self.membership

    def update_membership(
        self,
        *,
        actor_id: UUID,
        tenant_selector: UUID,
        membership_id: UUID,
        status: str | None,
        role_codes: tuple[str, ...] | None,
        row_version: int,
    ) -> MembershipSummaryValue:
        self.calls.append(
            ServiceCall(
                operation="update_membership",
                actor_id=actor_id,
                tenant_selector=tenant_selector,
                membership_id=membership_id,
                status=status,
                role_codes=role_codes,
                row_version=row_version,
            )
        )
        self._raise_scripted_problem("update_membership")
        if row_version != self.membership.row_version:
            raise MembershipAdministrationError(
                code="VERSION_CONFLICT",
                status=409,
                title="Version conflict",
                detail="The membership changed before this request completed.",
            )
        return MembershipSummaryValue(
            id=membership_id,
            tenant_id=tenant_selector,
            status=status or self.membership.status,
            row_version=row_version + 1,
            role_codes=role_codes or self.membership.role_codes,
        )

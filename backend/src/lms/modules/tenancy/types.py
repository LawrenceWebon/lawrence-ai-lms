from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrincipalSummary:
    user_id: UUID


@dataclass(frozen=True, slots=True)
class TenantSummary:
    id: UUID
    slug: str
    display_name: str


@dataclass(frozen=True, slots=True)
class TenantCandidate:
    id: UUID
    slug: str
    display_name: str
    membership_status: str


@dataclass(frozen=True, slots=True)
class MembershipSummary:
    id: UUID
    tenant_id: UUID
    status: str
    row_version: int
    role_codes: tuple[str, ...]
    permission_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntitlementSummary:
    status: str
    valid_until: datetime | None


@dataclass(frozen=True, slots=True)
class AuthenticationContextResult:
    principal: PrincipalSummary
    active_tenant: TenantSummary | None
    membership: MembershipSummary | None
    entitlement: EntitlementSummary | None
    available_tenants: tuple[TenantCandidate, ...]


@dataclass(frozen=True, slots=True)
class InvitationReceipt:
    id: UUID
    tenant_id: UUID
    status: str
    expires_at: datetime
    # Present only on the first creation response for the local delivery boundary.
    delivery_token: str | None = None

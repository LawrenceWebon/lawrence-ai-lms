from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, Protocol, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

RoleCode = Literal["tenant_admin", "instructor", "reviewer", "learner"]
MembershipMutationStatus = Literal["active", "inactive"]

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthenticationMembershipResult(Protocol):
    id: UUID
    status: str
    row_version: int
    role_codes: Sequence[str]
    permission_codes: Sequence[str]


class TenantSummaryResult(Protocol):
    id: UUID
    slug: str
    display_name: str


class TenantCandidateResult(TenantSummaryResult, Protocol):
    membership_status: str


class EntitlementResult(Protocol):
    status: str
    valid_until: datetime | None


class AuthenticationContextServiceResult(Protocol):
    @property
    def active_tenant(self) -> TenantSummaryResult | None: ...

    @property
    def membership(self) -> AuthenticationMembershipResult | None: ...

    @property
    def entitlement(self) -> EntitlementResult | None: ...

    @property
    def available_tenants(self) -> Sequence[TenantCandidateResult]: ...


class VerifiedActorResult(Protocol):
    @property
    def principal_id(self) -> UUID: ...

    @property
    def verified_email(self) -> str: ...

    @property
    def authentication_time(self) -> datetime: ...

    @property
    def assurance_level(self) -> Literal["aal1", "aal2"]: ...


class MembershipAdministrationServiceV1(Protocol):
    """Structural port shared by the HTTP and trusted Admin adapters."""

    def get_authentication_context(
        self, *, actor_id: UUID, tenant_selector: UUID | None
    ) -> object: ...

    def list_memberships(self, *, actor_id: UUID, tenant_selector: UUID) -> Sequence[object]: ...

    def create_invitation(
        self,
        *,
        actor_id: UUID,
        tenant_selector: UUID,
        email: str,
        role_codes: tuple[str, ...],
        idempotency_key: str,
    ) -> object: ...

    def accept_invitation(
        self, *, actor_id: UUID, verified_email: str, invitation_token: str
    ) -> object: ...

    def update_membership(
        self,
        *,
        actor_id: UUID,
        tenant_selector: UUID,
        membership_id: UUID,
        status: str | None,
        role_codes: tuple[str, ...] | None,
        row_version: int,
    ) -> object: ...


class MembershipAdministrationError(Exception):
    """Stable service failure safe for translation at adapter boundaries."""

    def __init__(self, *, code: str, status: int, title: str, detail: str) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.title = title
        self.detail = detail


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MembershipSummaryResponse(StrictSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    status: str = Field(min_length=1, max_length=32)
    row_version: int = Field(ge=1)
    role_codes: list[RoleCode]

    @field_validator("role_codes")
    @classmethod
    def require_canonical_role_codes(cls, value: list[RoleCode]) -> list[RoleCode]:
        if value != sorted(set(value)):
            raise ValueError("role_codes must be sorted and unique")
        return value


class InvitationReceiptResponse(StrictSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    status: str = Field(min_length=1, max_length=32)
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must include a timezone")
        return value


class CreateInvitationRequest(StrictSchema):
    email: str = Field(min_length=3, max_length=254)
    role_codes: list[RoleCode] = Field(min_length=1, max_length=4)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("email must be a valid address")
        return normalized

    @field_validator("role_codes")
    @classmethod
    def canonicalize_role_codes(cls, value: list[RoleCode]) -> list[RoleCode]:
        if len(value) != len(set(value)):
            raise ValueError("role_codes must be unique")
        return sorted(value)


class AcceptInvitationRequest(StrictSchema):
    invitation_token: SecretStr = Field(min_length=32, max_length=512)


class UpdateMembershipRequest(StrictSchema):
    status: MembershipMutationStatus | None = None
    role_codes: list[RoleCode] | None = Field(default=None, min_length=1, max_length=4)
    row_version: int = Field(ge=1)

    @field_validator("role_codes")
    @classmethod
    def canonicalize_optional_role_codes(
        cls, value: list[RoleCode] | None
    ) -> list[RoleCode] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("role_codes must be unique")
        return sorted(value) if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.status is None and self.role_codes is None:
            raise ValueError("status or role_codes is required")
        return self


class ProblemDetails(StrictSchema):
    type: str
    title: str = Field(min_length=1, max_length=120)
    status: int = Field(ge=400, le=599)
    detail: str = Field(max_length=1000)
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    request_id: str = Field(min_length=1, max_length=128)
    errors: list[dict[str, object]] = Field(default_factory=list, max_length=100)


class AuthenticationPrincipalResponse(StrictSchema):
    user_id: UUID
    authentication_time: datetime
    assurance_level: Literal["aal1", "aal2"]


class TenantSummaryResponse(StrictSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    slug: str = Field(min_length=1, max_length=63)
    display_name: str = Field(min_length=1, max_length=120)


class TenantCandidateResponse(TenantSummaryResponse):
    membership_status: Literal["active", "inactive"]


class AuthenticationMembershipResponse(StrictSchema):
    id: UUID
    status: Literal["active", "inactive"]
    row_version: int = Field(ge=1)
    role_codes: list[str]
    permission_codes: list[str]

    @field_validator("role_codes", "permission_codes")
    @classmethod
    def require_sorted_unique_codes(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("codes must be sorted and unique")
        return value


class EntitlementResponse(StrictSchema):
    status: Literal["active", "expired", "suspended"]
    valid_until: datetime | None


class AuthenticationContextResponse(StrictSchema):
    schema_uri: Literal["https://contracts.ai-lms.local/f001/auth-context.v1.schema.json"] = Field(
        default="https://contracts.ai-lms.local/f001/auth-context.v1.schema.json",
        alias="$schema",
    )
    principal: AuthenticationPrincipalResponse
    active_tenant: TenantSummaryResponse | None
    membership: AuthenticationMembershipResponse | None
    entitlement: EntitlementResponse | None
    available_tenants: list[TenantCandidateResponse] = Field(max_length=100)

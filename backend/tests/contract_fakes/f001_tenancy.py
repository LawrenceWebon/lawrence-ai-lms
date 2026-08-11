from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantCandidate:
    id: UUID
    slug: str
    display_name: str
    membership_status: str


@dataclass(frozen=True, slots=True)
class AuthenticationContextResult:
    principal_id: UUID
    active_tenant_id: UUID | None
    available_tenants: tuple[TenantCandidate, ...]


class TenancyServiceV1(Protocol):
    """Frozen adapter-facing fake contract; Lane B supplies the real service."""

    def get_authentication_context(
        self, *, principal_id: UUID, tenant_selector: UUID | None
    ) -> AuthenticationContextResult: ...


class StaticTenancyServiceFake:
    def __init__(self, result: AuthenticationContextResult) -> None:
        self._result = result

    def get_authentication_context(
        self, *, principal_id: UUID, tenant_selector: UUID | None
    ) -> AuthenticationContextResult:
        del principal_id, tenant_selector
        return self._result

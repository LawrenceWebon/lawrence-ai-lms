from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from django.db import connections, transaction

from .entities import IdentityCandidate
from .services import IdentityProfileReader

ActorType = Literal["user", "service", "privileged_operator"]


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    actor_type: ActorType
    actor_id: UUID
    tenant_id: UUID | None
    request_id: UUID

    def __post_init__(self) -> None:
        if self.actor_type not in ("user", "service", "privileged_operator"):
            raise ValueError("unsupported actor type")


class TenantAuthorizationResult(Protocol):
    principal_id: UUID
    active_tenant_id: UUID | None


class TenantAuthorizer(Protocol):
    def get_authentication_context(
        self, *, principal_id: UUID, tenant_selector: UUID | None
    ) -> TenantAuthorizationResult: ...


class TenantContextRejectedError(Exception):
    """The current database authority did not grant the requested context."""


class ExecutionContextContaminatedError(Exception):
    """A checked-out database connection already contained authorization state."""


class ExecutionContextTransactionError(Exception):
    """The execution-context wrapper must own the outer database transaction."""


@contextmanager
def transactional_execution_context(
    context: ExecutionContext, *, using: str = "default"
) -> Iterator[None]:
    """Set validated PostgreSQL context for exactly one local transaction."""

    connection = connections[using]
    if connection.in_atomic_block:
        raise ExecutionContextTransactionError
    with transaction.atomic(using=using):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT NULLIF(current_setting('app.current_actor_type', true), ''),
                       NULLIF(current_setting('app.current_actor_id', true), ''),
                       NULLIF(current_setting('app.current_tenant_id', true), ''),
                       NULLIF(current_setting('app.current_request_id', true), '')
                """
            )
            existing = cursor.fetchone()
            if existing is None or any(value is not None for value in existing):
                raise ExecutionContextContaminatedError
            cursor.execute(
                """
                SELECT set_config('app.current_actor_type', %s, true),
                       set_config('app.current_actor_id', %s, true),
                       set_config('app.current_tenant_id', %s, true),
                       set_config('app.current_request_id', %s, true)
                """,
                (
                    context.actor_type,
                    str(context.actor_id),
                    str(context.tenant_id) if context.tenant_id is not None else "",
                    str(context.request_id),
                ),
            )
        yield


class AuthorizedContextResolver:
    def __init__(
        self,
        authorizer: TenantAuthorizer,
        *,
        profiles: IdentityProfileReader,
    ) -> None:
        self._authorizer = authorizer
        self._profiles = profiles

    def resolve(
        self,
        *,
        identity: IdentityCandidate,
        tenant_selector: UUID | None,
        request_id: UUID,
        using: str = "default",
    ) -> TenantAuthorizationResult:
        candidate_context = ExecutionContext(
            actor_type="user",
            actor_id=identity.principal_id,
            tenant_id=tenant_selector,
            request_id=request_id,
        )
        with transactional_execution_context(candidate_context, using=using):
            profile = self._profiles.get_by_provider_subject(identity.principal_id)
            if (
                profile is None
                or profile.id != identity.profile_id
                or profile.provider_subject != identity.principal_id
                or profile.status != "active"
            ):
                raise TenantContextRejectedError
            result = self._authorizer.get_authentication_context(
                principal_id=identity.principal_id,
                tenant_selector=tenant_selector,
            )
            if result.principal_id != identity.principal_id:
                raise TenantContextRejectedError
            if result.active_tenant_id != tenant_selector:
                raise TenantContextRejectedError
        return result

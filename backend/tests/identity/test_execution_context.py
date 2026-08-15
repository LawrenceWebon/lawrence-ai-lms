from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from django.db import connection, transaction

from lms.modules.identity.context import (
    AuthorizedContextResolver,
    ExecutionContext,
    ExecutionContextContaminatedError,
    ExecutionContextTransactionError,
    TenantContextRejectedError,
    transactional_execution_context,
)
from lms.modules.identity.entities import IdentityCandidate, IdentityProfile
from tests.contract_fakes.f001_tenancy import (
    AuthenticationContextResult,
    StaticTenancyServiceFake,
)

PRINCIPAL_ID = UUID("00000000-0000-4000-8000-000000000102")
PROFILE_ID = UUID("20000000-0000-4000-8000-000000000102")
SESSION_ID = UUID("10000000-0000-4000-8000-000000000001")
TENANT_ID = UUID("00000000-0000-4000-8000-0000000000a1")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-0000000000b1")
REQUEST_ID = UUID("30000000-0000-4000-8000-000000000001")


class StaticProfiles:
    def __init__(self, status: str = "active") -> None:
        self.status = status

    def get_by_provider_subject(self, subject: UUID) -> IdentityProfile | None:
        assert subject == PRINCIPAL_ID
        return IdentityProfile(
            id=PROFILE_ID,
            provider_subject=PRINCIPAL_ID,
            status=self.status,
        )


def resolver(
    result: AuthenticationContextResult,
    *,
    profile_status: str = "active",
) -> AuthorizedContextResolver:
    return AuthorizedContextResolver(
        StaticTenancyServiceFake(result),
        profiles=StaticProfiles(profile_status),
    )


def database_context() -> tuple[str | None, str | None, str | None, str | None]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT NULLIF(current_setting('app.current_actor_type', true), ''),
                   NULLIF(current_setting('app.current_actor_id', true), ''),
                   NULLIF(current_setting('app.current_tenant_id', true), ''),
                   NULLIF(current_setting('app.current_request_id', true), '')
            """
        )
        row = cursor.fetchone()
    assert row is not None
    return row


def execution_context(*, tenant_id: UUID | None = TENANT_ID) -> ExecutionContext:
    return ExecutionContext(
        actor_type="user",
        actor_id=PRINCIPAL_ID,
        tenant_id=tenant_id,
        request_id=REQUEST_ID,
    )


@pytest.mark.django_db(transaction=True)
def test_context_is_transaction_local_and_resets_after_commit() -> None:
    with transactional_execution_context(execution_context()):
        assert database_context() == (
            "user",
            str(PRINCIPAL_ID),
            str(TENANT_ID),
            str(REQUEST_ID),
        )

    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_context_resets_after_explicit_rollback() -> None:
    with transactional_execution_context(execution_context()):
        transaction.set_rollback(True)

    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_context_resets_after_exception() -> None:
    with pytest.raises(RuntimeError, match="synthetic failure"):
        with transactional_execution_context(execution_context()):
            raise RuntimeError("synthetic failure")

    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_reused_connection_never_inherits_the_previous_context() -> None:
    with transactional_execution_context(execution_context()):
        first_connection = connection.connection

    with transactional_execution_context(execution_context(tenant_id=OTHER_TENANT_ID)):
        assert connection.connection is first_connection
        assert database_context()[2] == str(OTHER_TENANT_ID)

    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_session_scoped_pool_contamination_fails_closed() -> None:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_actor_id', %s, false)",
                (str(PRINCIPAL_ID),),
            )

        with pytest.raises(ExecutionContextContaminatedError):
            with transactional_execution_context(execution_context()):
                pytest.fail("contaminated context must not execute")
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_actor_id")

    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_nested_transaction_cannot_extend_context_lifetime() -> None:
    with transaction.atomic():
        with pytest.raises(ExecutionContextTransactionError):
            with transactional_execution_context(execution_context()):
                pytest.fail("a nested context transaction must not execute")

    assert database_context() == (None, None, None, None)


@pytest.mark.rls
@pytest.mark.django_db(transaction=True)
def test_context_resets_when_the_connection_uses_the_api_runtime_role() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SET ROLE lms_api_runtime")
    try:
        with transactional_execution_context(execution_context()):
            assert database_context()[1:] == (
                str(PRINCIPAL_ID),
                str(TENANT_ID),
                str(REQUEST_ID),
            )
        assert database_context() == (None, None, None, None)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")


def identity_candidate() -> IdentityCandidate:
    return IdentityCandidate(
        principal_id=PRINCIPAL_ID,
        profile_id=PROFILE_ID,
        session_id=SESSION_ID,
        authentication_time=datetime(2026, 8, 11, tzinfo=UTC),
        assurance_level="aal1",
        verified_email="synthetic-instructor@example.invalid",
    )


@pytest.mark.django_db(transaction=True)
def test_pre_tenant_resolution_cannot_gain_implicit_authority() -> None:
    authorizer = StaticTenancyServiceFake(
        AuthenticationContextResult(
            principal_id=PRINCIPAL_ID,
            active_tenant_id=TENANT_ID,
            available_tenants=(),
        )
    )

    with pytest.raises(TenantContextRejectedError):
        AuthorizedContextResolver(authorizer, profiles=StaticProfiles()).resolve(
            identity=identity_candidate(),
            tenant_selector=None,
            request_id=REQUEST_ID,
        )

    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_verified_identity_with_no_membership_receives_no_tenant_authority() -> None:
    authorizer = StaticTenancyServiceFake(
        AuthenticationContextResult(
            principal_id=PRINCIPAL_ID,
            active_tenant_id=None,
            available_tenants=(),
        )
    )

    result = AuthorizedContextResolver(authorizer, profiles=StaticProfiles()).resolve(
        identity=identity_candidate(),
        tenant_selector=None,
        request_id=REQUEST_ID,
    )

    assert result.active_tenant_id is None
    assert result.available_tenants == ()
    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_authorizer_cannot_return_a_different_principal_or_tenant() -> None:
    wrong_principal = AuthenticationContextResult(
        principal_id=UUID("00000000-0000-4000-8000-000000000105"),
        active_tenant_id=TENANT_ID,
        available_tenants=(),
    )
    wrong_tenant = AuthenticationContextResult(
        principal_id=PRINCIPAL_ID,
        active_tenant_id=OTHER_TENANT_ID,
        available_tenants=(),
    )

    for result in (wrong_principal, wrong_tenant):
        with pytest.raises(TenantContextRejectedError):
            resolver(result).resolve(
                identity=identity_candidate(),
                tenant_selector=TENANT_ID,
                request_id=REQUEST_ID,
            )

    assert database_context() == (None, None, None, None)


@pytest.mark.django_db(transaction=True)
def test_profile_is_rechecked_inside_the_authorized_transaction() -> None:
    result = AuthenticationContextResult(
        principal_id=PRINCIPAL_ID,
        active_tenant_id=TENANT_ID,
        available_tenants=(),
    )

    with pytest.raises(TenantContextRejectedError):
        resolver(result, profile_status="inactive").resolve(
            identity=identity_candidate(),
            tenant_selector=TENANT_ID,
            request_id=REQUEST_ID,
        )

    assert database_context() == (None, None, None, None)

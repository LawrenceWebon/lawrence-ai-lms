from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from lms.api.dependencies.authentication import AuthenticationDependency, AuthenticationProblem
from lms.modules.identity.entities import IdentityCandidate
from lms.modules.identity.services import IdentityAuthenticationRejectedError


class StubIdentityService:
    def __init__(self, *, reject: bool = False) -> None:
        self.reject = reject
        self.received_token: str | None = None

    def authenticate(self, *, token: str) -> IdentityCandidate:
        self.received_token = token
        if self.reject:
            raise IdentityAuthenticationRejectedError
        return IdentityCandidate(
            principal_id=UUID("00000000-0000-4000-8000-000000000102"),
            profile_id=UUID("20000000-0000-4000-8000-000000000102"),
            session_id=UUID("10000000-0000-4000-8000-000000000001"),
            authentication_time=datetime(2026, 8, 11, tzinfo=UTC),
            assurance_level="aal1",
            verified_email="synthetic-instructor@example.invalid",
        )


def test_bearer_dependency_returns_verified_candidate() -> None:
    service = StubIdentityService()

    candidate = AuthenticationDependency(service)("Bearer synthetic-token")

    assert service.received_token == "synthetic-token"  # noqa: S105
    assert str(candidate.principal_id) == "00000000-0000-4000-8000-000000000102"


@pytest.mark.parametrize(
    "authorization",
    [None, "", "Basic value", "Bearer", "Bearer   ", "Bearer one two"],
)
def test_missing_or_malformed_authorization_is_neutral(authorization: str | None) -> None:
    with pytest.raises(AuthenticationProblem) as caught:
        AuthenticationDependency(StubIdentityService())(authorization)

    assert caught.value.status_code == 401
    assert caught.value.code == "AUTHENTICATION_REQUIRED"
    assert caught.value.headers == {"WWW-Authenticate": "Bearer"}


def test_rejected_token_does_not_leak_token_or_identity_state() -> None:
    raw_token = "synthetic-sensitive-token"  # noqa: S105

    with pytest.raises(AuthenticationProblem) as caught:
        AuthenticationDependency(StubIdentityService(reject=True))(f"Bearer {raw_token}")

    assert caught.value.status_code == 401
    assert caught.value.code == "TOKEN_INVALID"
    assert raw_token not in str(caught.value)

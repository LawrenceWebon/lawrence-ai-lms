from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from lms.modules.identity.entities import IdentityProfile, VerifiedAccessToken
from lms.modules.identity.models import UserProfile
from lms.modules.identity.services import (
    DjangoIdentityProfileReader,
    IdentityAuthenticationRejectedError,
    IdentityService,
)

SUBJECT = UUID("00000000-0000-4000-8000-000000000102")
PROFILE_ID = UUID("20000000-0000-4000-8000-000000000102")
SESSION_ID = UUID("10000000-0000-4000-8000-000000000001")


class StaticVerifier:
    def verify(self, token: str) -> VerifiedAccessToken:
        assert token == "synthetic-token"  # noqa: S105
        return VerifiedAccessToken(
            subject=SUBJECT,
            session_id=SESSION_ID,
            authentication_time=datetime(2026, 8, 11, tzinfo=UTC),
            assurance_level="aal1",
        )


class StaticProfiles:
    def __init__(self, profile: IdentityProfile | None) -> None:
        self.profile = profile

    def get_by_provider_subject(self, subject: UUID) -> IdentityProfile | None:
        assert subject == SUBJECT
        return self.profile


class StaticSessions:
    def __init__(self, active: bool) -> None:
        self.active = active

    def is_active(self, *, subject: UUID, session_id: UUID) -> bool:
        assert subject == SUBJECT
        assert session_id == SESSION_ID
        return self.active


def service(*, status: str = "active", session_active: bool = True) -> IdentityService:
    return IdentityService(
        verifier=StaticVerifier(),
        profiles=StaticProfiles(
            IdentityProfile(id=PROFILE_ID, provider_subject=SUBJECT, status=status)
        ),
        sessions=StaticSessions(session_active),
    )


def test_active_profile_and_session_produce_identity_candidate() -> None:
    candidate = service().authenticate(token="synthetic-token")  # noqa: S106

    assert candidate.principal_id == SUBJECT
    assert candidate.profile_id == PROFILE_ID
    assert candidate.session_id == SESSION_ID
    assert candidate.assurance_level == "aal1"


@pytest.mark.parametrize(
    "profiles",
    [
        StaticProfiles(None),
        StaticProfiles(IdentityProfile(PROFILE_ID, SUBJECT, "inactive")),
        StaticProfiles(
            IdentityProfile(
                PROFILE_ID,
                UUID("00000000-0000-4000-8000-000000000105"),
                "active",
            )
        ),
    ],
)
def test_missing_or_disabled_profile_is_rejected(profiles: StaticProfiles) -> None:
    identity_service = IdentityService(
        verifier=StaticVerifier(),
        profiles=profiles,
        sessions=StaticSessions(True),
    )

    with pytest.raises(IdentityAuthenticationRejectedError):
        identity_service.authenticate(token="synthetic-token")  # noqa: S106


def test_revoked_session_is_rejected() -> None:
    with pytest.raises(IdentityAuthenticationRejectedError):
        service(session_active=False).authenticate(token="synthetic-token")  # noqa: S106


@pytest.mark.django_db
def test_django_profile_reader_returns_current_security_state() -> None:
    profile = UserProfile.objects.create(provider_subject=SUBJECT, status="inactive")

    result = DjangoIdentityProfileReader().get_by_provider_subject(SUBJECT)

    assert result == IdentityProfile(
        id=profile.id,
        provider_subject=SUBJECT,
        status="inactive",
    )

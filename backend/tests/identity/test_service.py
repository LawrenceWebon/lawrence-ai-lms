from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from django.db import DatabaseError, connection, transaction

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
            verified_email="synthetic-instructor@example.invalid",
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
    assert candidate.verified_email == "synthetic-instructor@example.invalid"


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


@pytest.mark.rls
@pytest.mark.django_db(transaction=True)
def test_runtime_profile_reader_uses_narrow_helper_without_table_select() -> None:
    profile = UserProfile.objects.create(provider_subject=SUBJECT, status="active")

    with connection.cursor() as cursor:
        cursor.execute("SET ROLE lms_api_runtime")
    try:
        assert DjangoIdentityProfileReader().get_by_provider_subject(SUBJECT) == IdentityProfile(
            id=profile.id,
            provider_subject=SUBJECT,
            status="active",
        )
        with pytest.raises(DatabaseError), transaction.atomic():
            UserProfile.objects.filter(provider_subject=SUBJECT).exists()
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")
        profile.delete()

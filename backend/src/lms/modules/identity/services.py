from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .entities import IdentityCandidate, IdentityProfile, VerifiedAccessToken
from .models import UserProfile
from .tokens import TokenInvalidError


class AccessTokenVerifier(Protocol):
    def verify(self, token: str) -> VerifiedAccessToken: ...


class IdentityProfileReader(Protocol):
    def get_by_provider_subject(self, subject: UUID) -> IdentityProfile | None: ...


class SessionStatusReader(Protocol):
    def is_active(self, *, subject: UUID, session_id: UUID) -> bool: ...


class IdentityAuthenticationRejectedError(Exception):
    """Neutral failure for invalid, disabled, or revoked identities."""


class DjangoIdentityProfileReader:
    def get_by_provider_subject(self, subject: UUID) -> IdentityProfile | None:
        row = (
            UserProfile.objects.filter(provider_subject=subject)
            .values("id", "provider_subject", "status")
            .first()
        )
        if row is None:
            return None
        return IdentityProfile(
            id=row["id"],
            provider_subject=row["provider_subject"],
            status=row["status"],
        )


class IdentityService:
    def __init__(
        self,
        *,
        verifier: AccessTokenVerifier,
        profiles: IdentityProfileReader,
        sessions: SessionStatusReader,
    ) -> None:
        self._verifier = verifier
        self._profiles = profiles
        self._sessions = sessions

    def authenticate(self, *, token: str) -> IdentityCandidate:
        try:
            verified = self._verifier.verify(token)
        except TokenInvalidError as error:
            raise IdentityAuthenticationRejectedError from error
        profile = self._profiles.get_by_provider_subject(verified.subject)
        if (
            profile is None
            or profile.provider_subject != verified.subject
            or profile.status != "active"
        ):
            raise IdentityAuthenticationRejectedError
        if not self._sessions.is_active(
            subject=verified.subject,
            session_id=verified.session_id,
        ):
            raise IdentityAuthenticationRejectedError
        return IdentityCandidate(
            principal_id=verified.subject,
            profile_id=profile.id,
            session_id=verified.session_id,
            authentication_time=verified.authentication_time,
            assurance_level=verified.assurance_level,
        )

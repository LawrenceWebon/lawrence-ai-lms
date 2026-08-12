from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

AssuranceLevel = Literal["aal1", "aal2"]


@dataclass(frozen=True, slots=True)
class VerifiedAccessToken:
    """Identity-only claims from a signature-verified provider access token."""

    subject: UUID
    session_id: UUID
    authentication_time: datetime
    assurance_level: AssuranceLevel
    verified_email: str


@dataclass(frozen=True, slots=True)
class IdentityProfile:
    id: UUID
    provider_subject: UUID
    status: str


@dataclass(frozen=True, slots=True)
class IdentityCandidate:
    """Verified actor candidate without tenant, role, or permission authority."""

    principal_id: UUID
    profile_id: UUID
    session_id: UUID
    authentication_time: datetime
    assurance_level: AssuranceLevel
    verified_email: str

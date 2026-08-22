# ruff: noqa: E402 -- this executable harness initializes Django before model imports.
from __future__ import annotations

import hmac
import time
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Final
from uuid import UUID

import django
import uvicorn
from django.conf import settings
from django.core.management import call_command
from django.db import connection, transaction
from django.utils import timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, SecretStr

django.setup()

from lms.api.composition import DjangoCourseAdministrationService, DjangoTenancyService
from lms.api.document_composition import DjangoSourceAdmissionService
from lms.api.main import create_application
from lms.modules.documents.storage import LocalQuarantineStorage
from lms.modules.identity.services import DjangoIdentityProfileReader, IdentityService
from lms.modules.identity.tokens import CachedJwks, JwtVerificationConfig, JwtVerifier
from lms.modules.tenancy.models import (
    EntitlementPeriod,
    MembershipRole,
    Role,
    Tenant,
    TenantInvitation,
    TenantInvitationRole,
    TenantMembership,
)
from lms.modules.tenancy.services import ensure_fixed_access_catalog
from tests.identity.jwt_test_support import PRIMARY_KEY, access_token

ALPHA_ID: Final = UUID("00000000-0000-4000-8000-0000000000a1")
BETA_ID: Final = UUID("00000000-0000-4000-8000-0000000000b1")
INVITATION_ID: Final = UUID("00000000-0000-4000-8000-000000000201")
ACTIVE_INVITATION: Final = "synthetic-active-token-000000000001"
SYNTHETIC_PASSWORD: Final = "synthetic-password"  # noqa: S105

SUBJECTS: Final = {
    "alpha-admin@example.invalid": UUID("00000000-0000-4000-8000-000000000101"),
    "instructor@example.invalid": UUID("00000000-0000-4000-8000-000000000102"),
    "learner@example.invalid": UUID("00000000-0000-4000-8000-000000000103"),
    "outsider@example.invalid": UUID("00000000-0000-4000-8000-000000000105"),
    "invitee@example.invalid": UUID("00000000-0000-4000-8000-000000000106"),
}
SESSIONS: Final = {
    subject: UUID(f"10000000-0000-4000-8000-{subject.hex[-12:]}") for subject in SUBJECTS.values()
}


class StaticJwksSource:
    def fetch(self) -> dict[str, object]:
        return {"keys": [PRIMARY_KEY.public_jwk()]}


class SyntheticSessionStatusReader:
    def is_active(self, *, subject: UUID, session_id: UUID) -> bool:
        return SESSIONS.get(subject) == session_id


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: SecretStr


class SessionResponse(BaseModel):
    access_token: str


def _identity_service() -> IdentityService:
    return IdentityService(
        verifier=JwtVerifier(
            config=JwtVerificationConfig(
                issuer="https://synthetic.supabase.co/auth/v1",
                audience="authenticated",
                role="authenticated",
                allowed_algorithms=("RS256",),
            ),
            keys=CachedJwks(source=StaticJwksSource()),
        ),
        profiles=DjangoIdentityProfileReader(),
        sessions=SyntheticSessionStatusReader(),
    )


source_storage = LocalQuarantineStorage(Path(settings.AI_LMS_LOCAL_QUARANTINE_ROOT))
source_service = DjangoSourceAdmissionService(storage=source_storage)
app = create_application(
    identity_authenticator=_identity_service(),
    tenancy_service=DjangoTenancyService(),
    course_service=DjangoCourseAdministrationService(),
    document_service=source_service,
)
fixture_router = APIRouter(prefix="/api/integration", include_in_schema=False)


def _digest(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        value.encode("utf-8"),
        sha256,
    ).hexdigest()


def _clear_source_quarantine() -> None:
    for locator in source_storage.locators():
        source_storage.delete(locator)


@transaction.atomic
def reset_fixture() -> None:
    from lms.modules.identity.models import UserProfile

    transaction.on_commit(_clear_source_quarantine)
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE app.tenants, app.permissions, app.user_profiles CASCADE")
    now = timezone.now()
    alpha = Tenant.objects.create(id=ALPHA_ID, slug="alpha", display_name="Alpha Academy")
    beta = Tenant.objects.create(id=BETA_ID, slug="beta", display_name="Beta Academy")
    EntitlementPeriod.objects.bulk_create(
        [
            EntitlementPeriod(
                tenant=alpha,
                status="active",
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=30),
            ),
            EntitlementPeriod(
                tenant=beta,
                status="active",
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=30),
            ),
        ]
    )
    ensure_fixed_access_catalog(alpha.id)
    ensure_fixed_access_catalog(beta.id)
    profiles = {
        email: UserProfile.objects.create(provider_subject=subject)
        for email, subject in SUBJECTS.items()
    }

    admin_membership = TenantMembership.objects.create(
        tenant=alpha,
        user_profile=profiles["alpha-admin@example.invalid"],
        status="active",
    )
    instructor_alpha = TenantMembership.objects.create(
        tenant=alpha,
        user_profile=profiles["instructor@example.invalid"],
        status="active",
        row_version=2,
    )
    instructor_beta = TenantMembership.objects.create(
        tenant=beta,
        user_profile=profiles["instructor@example.invalid"],
        status="active",
    )
    learner_alpha = TenantMembership.objects.create(
        tenant=alpha,
        user_profile=profiles["learner@example.invalid"],
        status="active",
    )
    for tenant, membership, role_code in (
        (alpha, admin_membership, "tenant_admin"),
        (alpha, instructor_alpha, "instructor"),
        (beta, instructor_beta, "instructor"),
        (alpha, learner_alpha, "learner"),
    ):
        MembershipRole.objects.create(
            tenant=tenant,
            membership=membership,
            role=Role.objects.get(tenant=tenant, code=role_code),
        )

    invitation = TenantInvitation.objects.create(
        id=INVITATION_ID,
        tenant=alpha,
        email="invitee@example.invalid",
        token_digest=_digest(ACTIVE_INVITATION),
        expires_at=now + timedelta(days=1),
    )
    TenantInvitationRole.objects.create(
        tenant=alpha,
        invitation=invitation,
        role=Role.objects.get(tenant=alpha, code="reviewer"),
    )


@fixture_router.post("/session", response_model=SessionResponse)
def create_synthetic_session(request: SessionRequest) -> SessionResponse:
    normalized_email = request.email.strip().casefold()
    subject = SUBJECTS.get(normalized_email)
    if subject is None or request.password.get_secret_value() != SYNTHETIC_PASSWORD:
        raise HTTPException(status_code=401, detail="Authentication failed")
    token = access_token(
        now=int(time.time()),
        claim_overrides={
            "sub": str(subject),
            "session_id": str(SESSIONS[subject]),
            "email": normalized_email,
        },
    )
    return SessionResponse(access_token=token)


@fixture_router.post("/reset", status_code=204)
def reset_synthetic_fixture() -> None:
    reset_fixture()


app.include_router(fixture_router)


def main() -> None:
    call_command("migrate", interactive=False, verbosity=1)
    reset_fixture()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")  # noqa: S104


if __name__ == "__main__":
    main()

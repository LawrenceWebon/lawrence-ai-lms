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
from django.db.models import F
from django.utils import timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, SecretStr

django.setup()

from lms.api.composition import DjangoCourseAdministrationService, DjangoTenancyService
from lms.api.document_composition import DjangoSourceAdmissionService
from lms.api.learning_composition import DjangoLearningService
from lms.api.main import create_application
from lms.modules.courses.models import (
    Course,
    CourseInstructor,
    CourseVersion,
    CurriculumSection,
    Lesson,
    LessonContentBlock,
)
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
    "learner-empty@example.invalid": UUID("00000000-0000-4000-8000-000000000104"),
    "outsider@example.invalid": UUID("00000000-0000-4000-8000-000000000105"),
    "invitee@example.invalid": UUID("00000000-0000-4000-8000-000000000106"),
}
SESSIONS: Final = {
    subject: UUID(f"10000000-0000-4000-8000-{subject.hex[-12:]}") for subject in SUBJECTS.values()
}
ADMIN_MEMBERSHIP_ID: Final = UUID("20000000-0000-4000-8000-000000000101")
INSTRUCTOR_ALPHA_MEMBERSHIP_ID: Final = UUID("20000000-0000-4000-8000-000000000102")
INSTRUCTOR_BETA_MEMBERSHIP_ID: Final = UUID("20000000-0000-4000-8000-000000000103")
LEARNER_MEMBERSHIP_ID: Final = UUID("20000000-0000-4000-8000-000000000104")
EMPTY_LEARNER_MEMBERSHIP_ID: Final = UUID("20000000-0000-4000-8000-000000000105")
COURSE_ID: Final = UUID("30000000-0000-4000-8000-000000000101")
COURSE_V1_ID: Final = UUID("30000000-0000-4000-8000-000000000201")
COURSE_V2_ID: Final = UUID("30000000-0000-4000-8000-000000000202")
SECTION_V1_ID: Final = UUID("30000000-0000-4000-8000-000000000301")
SECTION_V2_ID: Final = UUID("30000000-0000-4000-8000-000000000302")
LESSON_ONE_ID: Final = UUID("30000000-0000-4000-8000-000000000401")
LESSON_TWO_ID: Final = UUID("30000000-0000-4000-8000-000000000402")
LESSON_V2_ID: Final = UUID("30000000-0000-4000-8000-000000000403")
CONTENT_HASH_V1: Final = "sha256:" + "7" * 64
CONTENT_HASH_V2: Final = "sha256:" + "8" * 64


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
    learning_service=DjangoLearningService(),
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


def _rich_text(text: str) -> dict[str, object]:
    return {
        "type": "document",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text, "marks": []}],
            }
        ],
    }


def _create_f007_course(*, alpha: Tenant, instructor: TenantMembership) -> None:
    course = Course.objects.create(
        id=COURSE_ID,
        tenant=alpha,
        slug="private-learning-foundations",
    )
    CourseInstructor.objects.create(
        tenant=alpha,
        course=course,
        membership=instructor,
    )
    version_one = CourseVersion.objects.create(
        id=COURSE_V1_ID,
        tenant=alpha,
        course=course,
        version_number=1,
        primary_locale="en",
        title="Private learning foundations",
        description="An invented, rights-cleared learner playback fixture.",
        content_hash=CONTENT_HASH_V1,
    )
    section_one = CurriculumSection.objects.create(
        id=SECTION_V1_ID,
        tenant=alpha,
        course_version=version_one,
        title="Foundations",
        position=1,
    )
    lesson_one = Lesson.objects.create(
        id=LESSON_ONE_ID,
        tenant=alpha,
        course_version=version_one,
        section=section_one,
        title="A deliberate beginning",
        position=1,
        is_required=True,
    )
    lesson_two = Lesson.objects.create(
        id=LESSON_TWO_ID,
        tenant=alpha,
        course_version=version_one,
        section=section_one,
        title="Finish with intention",
        position=2,
        is_required=True,
    )
    LessonContentBlock.objects.create(
        tenant=alpha,
        course_version=version_one,
        lesson=lesson_one,
        position=1,
        document=_rich_text(
            "Welcome, learner — café. Safe <script>window.__f007Unsafe = true</script> text."
        ),
    )
    LessonContentBlock.objects.create(
        tenant=alpha,
        course_version=version_one,
        lesson=lesson_two,
        position=1,
        document=_rich_text("Complete this second synthetic lesson deliberately."),
    )

    version_two = CourseVersion.objects.create(
        id=COURSE_V2_ID,
        tenant=alpha,
        course=course,
        predecessor_version=version_one,
        version_number=2,
        primary_locale="en",
        title="Private learning foundations, version two",
        description="A later synthetic publication that must not replace an existing pin.",
        content_hash=CONTENT_HASH_V2,
    )
    section_two = CurriculumSection.objects.create(
        id=SECTION_V2_ID,
        tenant=alpha,
        course_version=version_two,
        title="Later foundations",
        position=1,
    )
    lesson_v2 = Lesson.objects.create(
        id=LESSON_V2_ID,
        tenant=alpha,
        course_version=version_two,
        section=section_two,
        title="A version two lesson",
        position=1,
        is_required=True,
    )
    LessonContentBlock.objects.create(
        tenant=alpha,
        course_version=version_two,
        lesson=lesson_v2,
        position=1,
        document=_rich_text("This later publication is not part of the original enrollment."),
    )
    CourseVersion.objects.filter(id__in=(COURSE_V1_ID, COURSE_V2_ID)).update(
        status="published",
        submitted_hash=F("content_hash"),
        approved_hash=F("content_hash"),
    )
    Course.objects.filter(id=COURSE_ID).update(current_published_version_id=COURSE_V1_ID)


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
        id=ADMIN_MEMBERSHIP_ID,
        tenant=alpha,
        user_profile=profiles["alpha-admin@example.invalid"],
        status="active",
    )
    instructor_alpha = TenantMembership.objects.create(
        id=INSTRUCTOR_ALPHA_MEMBERSHIP_ID,
        tenant=alpha,
        user_profile=profiles["instructor@example.invalid"],
        status="active",
        row_version=2,
    )
    instructor_beta = TenantMembership.objects.create(
        id=INSTRUCTOR_BETA_MEMBERSHIP_ID,
        tenant=beta,
        user_profile=profiles["instructor@example.invalid"],
        status="active",
    )
    learner_alpha = TenantMembership.objects.create(
        id=LEARNER_MEMBERSHIP_ID,
        tenant=alpha,
        user_profile=profiles["learner@example.invalid"],
        status="active",
    )
    empty_learner_alpha = TenantMembership.objects.create(
        id=EMPTY_LEARNER_MEMBERSHIP_ID,
        tenant=alpha,
        user_profile=profiles["learner-empty@example.invalid"],
        status="active",
    )
    for tenant, membership, role_code in (
        (alpha, admin_membership, "tenant_admin"),
        (alpha, instructor_alpha, "instructor"),
        (beta, instructor_beta, "instructor"),
        (alpha, learner_alpha, "learner"),
        (alpha, empty_learner_alpha, "learner"),
    ):
        MembershipRole.objects.create(
            tenant=tenant,
            membership=membership,
            role=Role.objects.get(tenant=tenant, code=role_code),
        )

    _create_f007_course(alpha=alpha, instructor=instructor_alpha)

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


@fixture_router.post("/f007/publish-successor", status_code=204)
@transaction.atomic
def publish_f007_successor() -> None:
    updated = Course.objects.filter(id=COURSE_ID, tenant_id=ALPHA_ID).update(
        current_published_version_id=COURSE_V2_ID,
        row_version=F("row_version") + 1,
    )
    if updated != 1:
        raise HTTPException(status_code=409, detail="F007 fixture is unavailable")


@fixture_router.post("/f007/withdraw-pinned", status_code=204)
@transaction.atomic
def withdraw_f007_pinned_version() -> None:
    Course.objects.filter(
        id=COURSE_ID,
        tenant_id=ALPHA_ID,
        current_published_version_id=COURSE_V1_ID,
    ).update(
        current_published_version_id=None,
        row_version=F("row_version") + 1,
    )
    updated = CourseVersion.objects.filter(
        id=COURSE_V1_ID,
        tenant_id=ALPHA_ID,
        status="published",
    ).update(status="withdrawn", row_version=F("row_version") + 1)
    if updated != 1:
        raise HTTPException(status_code=409, detail="F007 fixture is unavailable")


app.include_router(fixture_router)


def main() -> None:
    call_command("migrate", interactive=False, verbosity=1)
    reset_fixture()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")  # noqa: S104


if __name__ == "__main__":
    main()

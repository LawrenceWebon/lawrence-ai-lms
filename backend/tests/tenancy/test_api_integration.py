from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest

from lms.api.composition import DjangoTenancyService
from lms.api.main import create_application
from lms.modules.identity.entities import IdentityCandidate
from lms.modules.tenancy.services import create_invitation
from tests.contract_fakes.f002_course_administration import (
    RecordingCourseAdministrationServiceFake,
)

pytestmark = pytest.mark.django_db(transaction=True)


class StaticIdentityAuthenticator:
    def __init__(self, candidate: IdentityCandidate) -> None:
        self._candidate = candidate

    def authenticate(self, *, token: str) -> IdentityCandidate:
        assert token == "synthetic-api-token"  # noqa: S105
        return self._candidate


def candidate(*, principal_id: UUID, profile_id: UUID, email: str) -> IdentityCandidate:
    return IdentityCandidate(
        principal_id=principal_id,
        profile_id=profile_id,
        session_id=UUID("10000000-0000-4000-8000-000000000001"),
        authentication_time=datetime(2026, 8, 16, tzinfo=UTC),
        assurance_level="aal1",
        verified_email=email,
    )


def send(
    app: object,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    json: object | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, headers=headers, json=json)

    return asyncio.run(request())


def app_for(identity: IdentityCandidate) -> object:
    return create_application(
        identity_authenticator=StaticIdentityAuthenticator(identity),
        tenancy_service=DjangoTenancyService(),
        course_service=RecordingCourseAdministrationServiceFake(),
    )


def authorization(*, tenant_id: UUID | None = None) -> dict[str, str]:
    headers = {"Authorization": "Bearer synthetic-api-token"}
    if tenant_id is not None:
        headers["X-Tenant-ID"] = str(tenant_id)
    return headers


def test_real_auth_context_service_selects_explicit_tenant_and_denies_outsider(
    tenancy_seed: dict,
) -> None:
    instructor_profile = tenancy_seed["profiles"]["instructor"]
    instructor = candidate(
        principal_id=instructor_profile.provider_subject,
        profile_id=instructor_profile.id,
        email="synthetic-instructor@example.invalid",
    )
    outsider_profile = tenancy_seed["profiles"]["outsider"]
    outsider = candidate(
        principal_id=outsider_profile.provider_subject,
        profile_id=outsider_profile.id,
        email="outsider@example.invalid",
    )

    unselected = send(
        app_for(instructor),
        "GET",
        "/api/v1/auth-context",
        headers=authorization(),
    )
    selected = send(
        app_for(instructor),
        "GET",
        "/api/v1/auth-context",
        headers=authorization(tenant_id=tenancy_seed["alpha"].id),
    )
    denied = send(
        app_for(outsider),
        "GET",
        "/api/v1/auth-context",
        headers=authorization(tenant_id=tenancy_seed["alpha"].id),
    )

    assert unselected.status_code == 200
    assert unselected.json()["active_tenant"] is None
    assert [item["slug"] for item in unselected.json()["available_tenants"]] == [
        "alpha",
        "beta",
    ]
    assert selected.status_code == 200
    assert selected.json()["membership"]["role_codes"] == ["instructor"]
    assert selected.json()["membership"]["permission_codes"] == [
        "course_generation.blueprints.review",
        "course_generation.drafts.canonicalize",
        "course_generation.runs.create",
        "course_generation.runs.read",
        "courses.drafts.write",
        "courses.publish",
        "courses.read",
        "courses.review",
        "documents.ingestion.read",
        "documents.ingestion.start",
        "documents.sources.admit",
        "documents.sources.cancel",
        "documents.sources.read",
    ]
    assert denied.status_code == 404
    assert denied.headers["content-type"].startswith("application/problem+json")
    assert denied.json()["code"] == "TENANT_ACCESS_DENIED"


def test_real_invitation_replay_and_immediate_revocation_fail_closed(
    tenancy_seed: dict,
) -> None:
    alpha = tenancy_seed["alpha"]
    admin_profile = tenancy_seed["profiles"]["admin"]
    invitee_profile = tenancy_seed["profiles"]["invitee"]
    receipt = create_invitation(
        admin_profile.provider_subject,
        alpha.id,
        "invitee@example.invalid",
        ["reviewer"],
        "api-integration-invitation-0001",
    )
    assert receipt.delivery_token is not None
    invitee = candidate(
        principal_id=invitee_profile.provider_subject,
        profile_id=invitee_profile.id,
        email="invitee@example.invalid",
    )
    invitation_request = {"invitation_token": receipt.delivery_token}

    accepted = send(
        app_for(invitee),
        "POST",
        "/api/v1/tenant-invitations/accept",
        headers=authorization(),
        json=invitation_request,
    )
    replay = send(
        app_for(invitee),
        "POST",
        "/api/v1/tenant-invitations/accept",
        headers=authorization(),
        json=invitation_request,
    )

    assert accepted.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == accepted.json()
    assert accepted.json()["role_codes"] == ["reviewer"]
    assert receipt.delivery_token not in accepted.text

    admin = candidate(
        principal_id=admin_profile.provider_subject,
        profile_id=admin_profile.id,
        email="alpha-admin@example.invalid",
    )
    membership_id = accepted.json()["id"]
    revoked = send(
        app_for(admin),
        "PATCH",
        f"/api/v1/tenants/{alpha.id}/memberships/{membership_id}",
        headers=authorization(tenant_id=alpha.id),
        json={"status": "inactive", "row_version": accepted.json()["row_version"]},
    )
    denied = send(
        app_for(invitee),
        "GET",
        "/api/v1/auth-context",
        headers=authorization(tenant_id=alpha.id),
    )

    assert revoked.status_code == 200
    assert revoked.json()["status"] == "inactive"
    assert denied.status_code == 403
    assert denied.json()["code"] == "TENANT_ACCESS_INACTIVE"

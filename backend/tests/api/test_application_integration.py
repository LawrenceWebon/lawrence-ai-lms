from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import httpx

from lms.api.main import create_application
from lms.modules.identity.entities import IdentityCandidate
from tests.contract_fakes.f002_course_administration import (
    RecordingCourseAdministrationServiceFake,
)

ACTOR_ID = UUID("00000000-0000-4000-8000-000000000102")
PROFILE_ID = UUID("20000000-0000-4000-8000-000000000102")
SESSION_ID = UUID("10000000-0000-4000-8000-000000000001")
ALPHA_ID = UUID("00000000-0000-4000-8000-0000000000a1")
MEMBERSHIP_ID = UUID("00000000-0000-4000-8000-000000000301")


class StubIdentityAuthenticator:
    def authenticate(self, *, token: str) -> IdentityCandidate:
        assert token == "synthetic-access-token"  # noqa: S105
        return IdentityCandidate(
            principal_id=ACTOR_ID,
            profile_id=PROFILE_ID,
            session_id=SESSION_ID,
            authentication_time=datetime(2026, 8, 16, 1, 2, 3, tzinfo=UTC),
            assurance_level="aal1",
            verified_email="synthetic-instructor@example.invalid",
        )


class RecordingTenancyService:
    def __init__(self) -> None:
        self.selectors: list[UUID | None] = []

    def get_authentication_context(self, *, actor_id: UUID, tenant_selector: UUID | None) -> object:
        assert actor_id == ACTOR_ID
        self.selectors.append(tenant_selector)
        candidate = SimpleNamespace(
            id=ALPHA_ID,
            slug="alpha",
            display_name="Alpha Learning",
            membership_status="active",
        )
        if tenant_selector is None:
            return SimpleNamespace(
                principal=SimpleNamespace(user_id=ACTOR_ID),
                active_tenant=None,
                membership=None,
                entitlement=None,
                available_tenants=(candidate,),
            )
        assert tenant_selector == ALPHA_ID
        return SimpleNamespace(
            principal=SimpleNamespace(user_id=ACTOR_ID),
            active_tenant=SimpleNamespace(
                id=ALPHA_ID,
                slug="alpha",
                display_name="Alpha Learning",
            ),
            membership=SimpleNamespace(
                id=MEMBERSHIP_ID,
                tenant_id=ALPHA_ID,
                status="active",
                row_version=2,
                role_codes=("instructor",),
                permission_codes=("courses.drafts.write",),
            ),
            entitlement=SimpleNamespace(
                status="active",
                valid_until=datetime(2026, 9, 16, tzinfo=UTC),
            ),
            available_tenants=(candidate,),
        )

    def list_memberships(self, **_: object) -> tuple[object, ...]:
        return ()

    def create_invitation(self, **_: object) -> object:
        raise AssertionError("not called")

    def accept_invitation(self, **_: object) -> object:
        raise AssertionError("not called")

    def update_membership(self, **_: object) -> object:
        raise AssertionError("not called")


def send(app: object, path: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, headers=headers)

    return asyncio.run(request())


def test_composed_auth_context_requires_explicit_selection_and_matches_frozen_shape() -> None:
    service = RecordingTenancyService()
    app = create_application(
        identity_authenticator=StubIdentityAuthenticator(),
        tenancy_service=service,
        course_service=RecordingCourseAdministrationServiceFake(),
    )
    authorization = {"Authorization": "Bearer synthetic-access-token"}

    unselected = send(app, "/api/v1/auth-context", headers=authorization)
    selected = send(
        app,
        "/api/v1/auth-context",
        headers={**authorization, "X-Tenant-ID": str(ALPHA_ID)},
    )

    assert unselected.status_code == 200
    assert unselected.json() == {
        "$schema": "https://contracts.ai-lms.local/f001/auth-context.v1.schema.json",
        "principal": {
            "user_id": str(ACTOR_ID),
            "authentication_time": "2026-08-16T01:02:03Z",
            "assurance_level": "aal1",
        },
        "active_tenant": None,
        "membership": None,
        "entitlement": None,
        "available_tenants": [
            {
                "id": str(ALPHA_ID),
                "slug": "alpha",
                "display_name": "Alpha Learning",
                "membership_status": "active",
            }
        ],
    }
    assert selected.status_code == 200
    assert selected.json()["active_tenant"]["id"] == str(ALPHA_ID)
    assert selected.json()["membership"] == {
        "id": str(MEMBERSHIP_ID),
        "status": "active",
        "row_version": 2,
        "role_codes": ["instructor"],
        "permission_codes": ["courses.drafts.write"],
    }
    assert service.selectors == [None, ALPHA_ID]


def test_composed_routes_share_neutral_authentication_and_openapi_contract() -> None:
    app = create_application(
        identity_authenticator=StubIdentityAuthenticator(),
        tenancy_service=RecordingTenancyService(),
        course_service=RecordingCourseAdministrationServiceFake(),
    )

    response = send(app, "/api/v1/auth-context")
    paths = app.openapi()["paths"]

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert set(paths) == {
        "/health",
        "/api/v1/auth-context",
        "/api/v1/tenants/{tenant_id}/memberships",
        "/api/v1/tenants/{tenant_id}/invitations",
        "/api/v1/tenant-invitations/accept",
        "/api/v1/tenants/{tenant_id}/memberships/{membership_id}",
        "/api/v1/tenants/{tenant_id}/courses",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/approve",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/archive",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/curriculum",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/publish",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/request-changes",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/submit-review",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/successor-draft",
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/withdraw",
    }

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Final
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from jsonschema import Draft202012Validator, FormatChecker

from lms.api.routers.tenancy import create_tenancy_router
from lms.api.schemas.tenancy import MembershipAdministrationError
from tests.contract_fakes.f001_membership_admin import (
    ACTIVE_TOKEN,
    ALPHA_ADMIN_EMAIL,
    ALPHA_ADMIN_ID,
    ALPHA_TENANT_ID,
    BETA_TENANT_ID,
    CONSUMED_TOKEN,
    CROSS_TENANT_TOKEN,
    EXPIRED_TOKEN,
    MEMBERSHIP_ID,
    OUTSIDER_EMAIL,
    OUTSIDER_ID,
    REVOKED_TOKEN,
    RecordingMembershipAdministrationServiceFake,
    VerifiedActorValue,
)

IDEMPOTENCY_KEY: Final = "fixture-create-invitation-0001"


def make_app(
    service: RecordingMembershipAdministrationServiceFake,
    *,
    actor_dependency: Callable[[], VerifiedActorValue] | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_tenancy_router(
            service=service,
            actor_dependency=actor_dependency
            or (lambda: VerifiedActorValue(ALPHA_ADMIN_ID, ALPHA_ADMIN_EMAIL)),
        )
    )
    return app


def send(app: FastAPI, method: str, path: str, **kwargs: object) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(request())


def test_successful_api_operations_delegate_verified_actor_and_untrusted_selectors() -> None:
    service = RecordingMembershipAdministrationServiceFake()
    app = make_app(service)

    listed = send(app, "GET", f"/api/v1/tenants/{ALPHA_TENANT_ID}/memberships")
    invited = send(
        app,
        "POST",
        f"/api/v1/tenants/{ALPHA_TENANT_ID}/invitations",
        headers={"Idempotency-Key": IDEMPOTENCY_KEY},
        json={"email": "instructor@example.invalid", "role_codes": ["instructor"]},
    )
    accepted = send(
        app,
        "POST",
        "/api/v1/tenant-invitations/accept",
        json={"invitation_token": ACTIVE_TOKEN},
    )
    updated = send(
        app,
        "PATCH",
        f"/api/v1/tenants/{ALPHA_TENANT_ID}/memberships/{MEMBERSHIP_ID}",
        json={"status": "inactive", "role_codes": ["reviewer"], "row_version": 1},
    )

    assert listed.status_code == 200
    assert listed.json()[0]["role_codes"] == ["instructor", "reviewer"]
    assert invited.status_code == 201
    assert invited.json() == {
        "id": "00000000-0000-4000-8000-000000000201",
        "tenant_id": str(ALPHA_TENANT_ID),
        "status": "active",
        "expires_at": invited.json()["expires_at"],
    }
    assert ACTIVE_TOKEN not in json.dumps(invited.json())
    assert accepted.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["status"] == "inactive"
    assert [call.operation for call in service.calls] == [
        "list_memberships",
        "create_invitation",
        "accept_invitation",
        "update_membership",
    ]
    assert all(call.actor_id == ALPHA_ADMIN_ID for call in service.calls)
    assert service.calls[0].tenant_selector == ALPHA_TENANT_ID
    assert service.calls[2].verified_email == ALPHA_ADMIN_EMAIL


def test_same_invitation_idempotency_key_replays_and_changed_request_conflicts() -> None:
    service = RecordingMembershipAdministrationServiceFake()
    app = make_app(service)
    path = f"/api/v1/tenants/{ALPHA_TENANT_ID}/invitations"
    headers = {"Idempotency-Key": IDEMPOTENCY_KEY}
    request = {"email": "instructor@example.invalid", "role_codes": ["instructor"]}

    first = send(app, "POST", path, headers=headers, json=request)
    replay = send(app, "POST", path, headers=headers, json=request)
    changed = send(
        app,
        "POST",
        path,
        headers=headers,
        json={"email": "reviewer@example.invalid", "role_codes": ["reviewer"]},
    )

    assert first.json() == replay.json()
    assert changed.status_code == 409
    assert changed.json()["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize(
    ("operation", "method", "path", "kwargs", "code", "status"),
    [
        (
            "list_memberships",
            "GET",
            f"/api/v1/tenants/{ALPHA_TENANT_ID}/memberships",
            {},
            "TENANT_ACCESS_DENIED",
            404,
        ),
        (
            "list_memberships",
            "GET",
            f"/api/v1/tenants/{ALPHA_TENANT_ID}/memberships",
            {},
            "TENANT_ACCESS_INACTIVE",
            403,
        ),
        (
            "create_invitation",
            "POST",
            f"/api/v1/tenants/{ALPHA_TENANT_ID}/invitations",
            {
                "headers": {"Idempotency-Key": IDEMPOTENCY_KEY},
                "json": {"email": "learner@example.invalid", "role_codes": ["learner"]},
            },
            "TENANT_ACCESS_DENIED",
            404,
        ),
        (
            "accept_invitation",
            "POST",
            "/api/v1/tenant-invitations/accept",
            {"json": {"invitation_token": ACTIVE_TOKEN}},
            "INVITATION_EXPIRED",
            410,
        ),
        (
            "accept_invitation",
            "POST",
            "/api/v1/tenant-invitations/accept",
            {"json": {"invitation_token": ACTIVE_TOKEN}},
            "INVITATION_INVALID",
            404,
        ),
        (
            "update_membership",
            "PATCH",
            f"/api/v1/tenants/{ALPHA_TENANT_ID}/memberships/{MEMBERSHIP_ID}",
            {"json": {"status": "inactive", "row_version": 1}},
            "VERSION_CONFLICT",
            409,
        ),
    ],
)
def test_service_denials_are_neutral_problem_details(
    operation: str,
    method: str,
    path: str,
    kwargs: dict[str, object],
    code: str,
    status: int,
    problem_details_validator: Draft202012Validator,
) -> None:
    service = RecordingMembershipAdministrationServiceFake()
    service.problem_by_operation[operation] = MembershipAdministrationError(
        code=code,
        status=status,
        title="Request denied",
        detail="The requested operation is unavailable.",
    )
    response = send(make_app(service), method, path, **kwargs)

    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code
    assert ALPHA_TENANT_ID.hex not in response.text
    assert not list(problem_details_validator.iter_errors(response.json()))


def test_path_and_header_tenant_mismatch_is_denied_before_service_call() -> None:
    service = RecordingMembershipAdministrationServiceFake()

    response = send(
        make_app(service),
        "GET",
        f"/api/v1/tenants/{ALPHA_TENANT_ID}/memberships",
        headers={"X-Tenant-ID": str(BETA_TENANT_ID)},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "TENANT_ACCESS_DENIED"
    assert service.calls == []


def test_validation_error_uses_problem_details_instead_of_fastapi_default(
    problem_details_validator: Draft202012Validator,
) -> None:
    response = send(
        make_app(RecordingMembershipAdministrationServiceFake()),
        "POST",
        f"/api/v1/tenants/{ALPHA_TENANT_ID}/invitations",
        headers={"Idempotency-Key": "short"},
        json={"email": "not-an-email", "role_codes": ["owner"]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"
    assert not list(problem_details_validator.iter_errors(response.json()))


def test_service_error_detail_cannot_echo_an_invitation_token() -> None:
    service = RecordingMembershipAdministrationServiceFake()
    service.problem_by_operation["accept_invitation"] = MembershipAdministrationError(
        code="INVITATION_INVALID",
        status=404,
        title="Invitation unavailable",
        detail=f"Rejected invitation token {ACTIVE_TOKEN}",
    )

    response = send(
        make_app(service),
        "POST",
        "/api/v1/tenant-invitations/accept",
        json={"invitation_token": ACTIVE_TOKEN},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "INVITATION_INVALID"
    assert ACTIVE_TOKEN not in response.text


@pytest.mark.parametrize(
    ("token", "actor_id", "code", "status"),
    [
        (ACTIVE_TOKEN, OUTSIDER_ID, "INVITATION_INVALID", 404),
        (EXPIRED_TOKEN, ALPHA_ADMIN_ID, "INVITATION_EXPIRED", 410),
        (REVOKED_TOKEN, ALPHA_ADMIN_ID, "INVITATION_INVALID", 404),
        (CONSUMED_TOKEN, ALPHA_ADMIN_ID, "INVITATION_INVALID", 404),
        (CROSS_TENANT_TOKEN, ALPHA_ADMIN_ID, "INVITATION_INVALID", 404),
        ("synthetic-guessed-token-00000000001", ALPHA_ADMIN_ID, "INVITATION_INVALID", 404),
    ],
)
def test_unusable_invitations_fail_neutrally_without_echoing_token(
    token: str, actor_id: UUID, code: str, status: int
) -> None:
    response = send(
        make_app(
            RecordingMembershipAdministrationServiceFake(),
            actor_dependency=lambda: VerifiedActorValue(
                actor_id,
                OUTSIDER_EMAIL if actor_id == OUTSIDER_ID else ALPHA_ADMIN_EMAIL,
            ),
        ),
        "POST",
        "/api/v1/tenant-invitations/accept",
        json={"invitation_token": token},
    )

    assert response.status_code == status
    assert response.json()["code"] == code
    assert token not in response.text


def test_openapi_fragment_declares_problem_details_media_type() -> None:
    schema = make_app(RecordingMembershipAdministrationServiceFake()).openapi()

    operation = schema["paths"]["/api/v1/tenants/{tenant_id}/memberships"]["get"]
    denied_response = operation["responses"]["404"]

    assert "application/problem+json" in denied_response["content"]
    problem_schema = denied_response["content"]["application/problem+json"]["schema"]
    assert problem_schema == {"$ref": "#/components/schemas/ProblemDetails"}


def test_missing_authentication_is_problem_details() -> None:
    def unauthenticated() -> VerifiedActorValue:
        raise MembershipAdministrationError(
            code="AUTHENTICATION_REQUIRED",
            status=401,
            title="Authentication required",
            detail="Authentication is required.",
        )

    response = send(
        make_app(
            RecordingMembershipAdministrationServiceFake(),
            actor_dependency=unauthenticated,
        ),
        "GET",
        f"/api/v1/tenants/{ALPHA_TENANT_ID}/memberships",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"


@pytest.fixture
def problem_details_validator() -> Draft202012Validator:
    schema_path = "contracts/f001/problem-details.v1.schema.json"
    with open(schema_path, encoding="utf-8") as schema_file:
        return Draft202012Validator(json.load(schema_file), format_checker=FormatChecker())

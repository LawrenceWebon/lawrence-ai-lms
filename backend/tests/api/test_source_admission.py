from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import httpx
import pytest
from fastapi import FastAPI, Header

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.routers.documents import create_document_router
from lms.api.schemas.documents import SourceAdmissionContractError
from tests.contract_fakes.f003_source_admission import (
    ACTOR_ID,
    ALPHA_TENANT_ID,
    AUTHORIZATION_ID,
    BETA_TENANT_ID,
    IDEMPOTENCY_KEY,
    OPAQUE_TOKEN,
    SOURCE_DOCUMENT_ID,
    SOURCE_VERSION_ID,
    RecordingSourceAdmissionServiceFake,
    VerifiedActorValue,
    load_source_examples,
)

AUTHORIZATION = "Bearer synthetic-source-access-token"
PDF_BYTES = b"%PDF-1.4\nsynthetic browser-free fixture\n%%EOF\n"


@dataclass(frozen=True, slots=True)
class RouteCase:
    operation: str
    operation_id: str
    method: str
    path: str
    status: int
    body: object | None = None
    idempotent: bool = False
    authenticated: bool = True


def route_cases() -> tuple[RouteCase, ...]:
    examples = load_source_examples()
    base = (
        f"/api/v1/tenants/{ALPHA_TENANT_ID}/source-documents/{SOURCE_DOCUMENT_ID}"
        f"/versions/{SOURCE_VERSION_ID}"
    )
    return (
        RouteCase(
            "create_admission",
            "createSourceAdmission",
            "POST",
            f"/api/v1/tenants/{ALPHA_TENANT_ID}/source-documents/admissions",
            201,
            examples["CreateSourceAdmissionV1"],
            True,
        ),
        RouteCase(
            "review_authorization",
            "reviewSourceStoreAuthorization",
            "POST",
            f"{base}/rights-authorizations/{AUTHORIZATION_ID}/decisions",
            200,
            examples["ReviewSourceStoreAuthorizationV1"],
            True,
        ),
        RouteCase(
            "create_upload_intent",
            "createSourceUploadIntent",
            "POST",
            f"{base}/upload-intents",
            201,
            None,
            True,
        ),
        RouteCase(
            "upload_to_intent",
            "uploadSourceDocument",
            "PUT",
            f"/api/v1/source-upload-targets/{OPAQUE_TOKEN}",
            202,
            PDF_BYTES,
            False,
            False,
        ),
        RouteCase("get_admission", "getSourceAdmission", "GET", base, 200),
        RouteCase(
            "cancel_admission",
            "cancelSourceAdmission",
            "POST",
            f"{base}/cancel",
            200,
            examples["CancelSourceAdmissionV1"],
            True,
        ),
    )


def authenticated_actor(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> VerifiedActorValue:
    if authorization != AUTHORIZATION:
        raise AuthenticationProblem(code="AUTHENTICATION_REQUIRED")
    return VerifiedActorValue(ACTOR_ID)


def make_app(
    service: RecordingSourceAdmissionServiceFake,
    *,
    actor_dependency: Callable[..., VerifiedActorValue] = authenticated_actor,
) -> FastAPI:
    app = FastAPI()
    app.include_router(create_document_router(service=service, actor_dependency=actor_dependency))
    return app


def send(
    app: FastAPI,
    case: RouteCase,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        request_headers = {
            "Authorization": AUTHORIZATION,
            "X-Tenant-ID": str(ALPHA_TENANT_ID),
            **({"Idempotency-Key": IDEMPOTENCY_KEY} if case.idempotent else {}),
        }
        if case.operation == "upload_to_intent":
            request_headers = {"Content-Type": "application/pdf"}
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(
                case.method,
                case.path,
                headers=headers if headers is not None else request_headers,
                json=case.body if isinstance(case.body, dict) else None,
                content=case.body if isinstance(case.body, bytes) else None,
            )

    return asyncio.run(request())


def test_routes_delegate_only_verified_actor_and_explicit_selectors() -> None:
    service = RecordingSourceAdmissionServiceFake()
    responses = [send(make_app(service), case) for case in route_cases()]

    assert [response.status_code for response in responses] == [
        case.status for case in route_cases()
    ]
    assert [call.operation for call in service.calls] == [case.operation for case in route_cases()]
    assert all(
        call.actor_id == ACTOR_ID and call.tenant_id == ALPHA_TENANT_ID
        for call in service.calls
        if call.operation != "upload_to_intent"
    )
    upload = service.calls[3]
    assert upload.actor_id is None and upload.tenant_id is None
    assert upload.opaque_token == OPAQUE_TOKEN
    assert upload.content_type == "application/pdf"
    assert upload.body == PDF_BYTES
    assert responses[2].json() == service.intent
    assert all(
        response.json() == service.snapshot
        for response in responses
        if response.status_code in {200, 202}
    )


def test_openapi_has_frozen_paths_methods_statuses_and_binary_upload() -> None:
    schema = make_app(RecordingSourceAdmissionServiceFake()).openapi()
    for case in route_cases():
        path = (
            case.path.replace(str(ALPHA_TENANT_ID), "{tenant_id}")
            .replace(str(SOURCE_DOCUMENT_ID), "{source_document_id}")
            .replace(str(SOURCE_VERSION_ID), "{source_version_id}")
            .replace(str(AUTHORIZATION_ID), "{authorization_id}")
            .replace(OPAQUE_TOKEN, "{opaque_token}")
        )
        operation = schema["paths"][path][case.method.casefold()]
        assert operation["operationId"] == case.operation_id
        assert str(case.status) in operation["responses"]
        parameters = {item["name"]: item for item in operation.get("parameters", [])}
        assert ("X-Tenant-ID" in parameters) is case.authenticated
        assert ("Idempotency-Key" in parameters) is case.idempotent
        assert ("Authorization" in parameters) is case.authenticated

    upload = schema["paths"]["/api/v1/source-upload-targets/{opaque_token}"]["put"]
    assert upload["requestBody"] == {
        "required": True,
        "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
    }


@pytest.mark.parametrize("case", [case for case in route_cases() if case.authenticated])
def test_tenant_routes_require_authentication_and_matching_header(case: RouteCase) -> None:
    service = RecordingSourceAdmissionServiceFake()
    headers = {
        "X-Tenant-ID": str(ALPHA_TENANT_ID),
        **({"Idempotency-Key": IDEMPOTENCY_KEY} if case.idempotent else {}),
    }
    unauthenticated = send(make_app(service), case, headers=headers)
    headers["Authorization"] = AUTHORIZATION
    headers["X-Tenant-ID"] = str(BETA_TENANT_ID)
    mismatched = send(make_app(service), case, headers=headers)

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert mismatched.status_code == 404
    assert mismatched.json()["code"] == "RESOURCE_NOT_FOUND"
    assert str(ALPHA_TENANT_ID) not in mismatched.text
    assert str(BETA_TENANT_ID) not in mismatched.text
    assert service.calls == []


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED", 403),
        ("UPLOAD_INTENT_EXPIRED", 410),
        ("SOURCE_ADMISSION_STATE_CONFLICT", 409),
        ("UPLOAD_QUOTA_EXCEEDED", 429),
        ("SOURCE_ADMISSION_VALIDATION_UNAVAILABLE", 503),
    ],
)
def test_service_problems_use_bounded_problem_details(code: str, expected: int) -> None:
    case = route_cases()[0]
    service = RecordingSourceAdmissionServiceFake()
    service.problem_by_operation[case.operation] = SourceAdmissionContractError(code=code)

    response = send(make_app(service), case)

    assert response.status_code == expected
    assert response.json()["code"] == code
    assert response.headers["content-type"].startswith("application/problem+json")


def test_upload_route_reads_at_most_one_byte_beyond_the_frozen_cap() -> None:
    service = RecordingSourceAdmissionServiceFake()
    case = route_cases()[3]
    oversized = RouteCase(
        operation=case.operation,
        operation_id=case.operation_id,
        method=case.method,
        path=case.path,
        status=case.status,
        body=b"x" * (6_291_456 + 1024),
        authenticated=False,
    )

    response = send(make_app(service), oversized)

    assert response.status_code == 202
    assert len(service.calls[0].body) == 6_291_457

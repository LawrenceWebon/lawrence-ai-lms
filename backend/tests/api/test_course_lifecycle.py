from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final

import httpx
import pytest
from fastapi import FastAPI, Header
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.routers.courses import create_course_router
from lms.api.schemas.courses import (
    CourseAdministrationError,
    CourseSnapshotV1,
    CourseVersionHistoryV1,
    CreateCourseV1,
    CreateSuccessorDraftV1,
    ReplaceCurriculumV1,
    SuccessorDraftResultV1,
    TransitionCourseVersionV1,
    UpdateCourseVersionV1,
)
from tests.contract_fakes.f002_course_administration import (
    ACTOR_ID,
    ALPHA_TENANT_ID,
    BETA_TENANT_ID,
    COURSE_ID,
    IDEMPOTENCY_KEY,
    VERSION_ID,
    RecordingCourseAdministrationServiceFake,
    VerifiedActorValue,
    load_lifecycle_examples,
)

AUTHORIZATION: Final = "Bearer synthetic-course-token"
CURSOR: Final = "synthetic-opaque-cursor"
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class RouteCase:
    operation: str
    method: str
    path: str
    operation_id: str
    success_status: int
    body: dict[str, object] | None = None
    idempotent: bool = False
    query: dict[str, object] | None = None


def transition_body(transition: str) -> dict[str, object]:
    body: dict[str, object] = {
        "transition": transition,
        "expected_version_row_version": 2,
        "expected_content_hash": (
            "sha256:f4e7e98f5fe8199a25ba5293d4a7a58e1f45b649941de8c0935282ae5845ec31"
        ),
    }
    if transition == "request_changes":
        body["reason_codes"] = ["NEEDS_REVISION"]
    if transition in {"withdraw", "archive"}:
        body["reason_code"] = "SUPERSEDED"
    if transition in {"publish", "withdraw"}:
        body["expected_course_row_version"] = 1
    return body


def route_cases() -> tuple[RouteCase, ...]:
    examples = load_lifecycle_examples()
    base = f"/api/v1/tenants/{ALPHA_TENANT_ID}/courses"
    version = f"{base}/{COURSE_ID}/versions/{VERSION_ID}"
    return (
        RouteCase(
            "create_course",
            "POST",
            base,
            "createCourse",
            201,
            copy.deepcopy(examples["CreateCourseV1"]),
            True,
        ),
        RouteCase(
            "get_course_version",
            "GET",
            version,
            "getCourseVersion",
            200,
        ),
        RouteCase(
            "list_course_versions",
            "GET",
            f"{base}/{COURSE_ID}/versions",
            "listCourseVersions",
            200,
            query={"cursor": CURSOR, "limit": 25},
        ),
        RouteCase(
            "update_version",
            "PATCH",
            version,
            "updateCourseVersion",
            200,
            copy.deepcopy(examples["UpdateCourseVersionV1"]),
        ),
        RouteCase(
            "replace_curriculum",
            "PUT",
            f"{version}/curriculum",
            "replaceCourseCurriculum",
            200,
            copy.deepcopy(examples["ReplaceCurriculumV1"]),
        ),
        RouteCase(
            "transition_version",
            "POST",
            f"{version}/submit-review",
            "submitCourseReview",
            200,
            transition_body("submit_review"),
            True,
        ),
        RouteCase(
            "transition_version",
            "POST",
            f"{version}/request-changes",
            "requestCourseChanges",
            200,
            transition_body("request_changes"),
            True,
        ),
        RouteCase(
            "transition_version",
            "POST",
            f"{version}/approve",
            "approveCourseVersion",
            200,
            transition_body("approve"),
            True,
        ),
        RouteCase(
            "transition_version",
            "POST",
            f"{version}/publish",
            "publishCourseVersion",
            200,
            transition_body("publish"),
            True,
        ),
        RouteCase(
            "transition_version",
            "POST",
            f"{version}/withdraw",
            "withdrawCourseVersion",
            200,
            transition_body("withdraw"),
            True,
        ),
        RouteCase(
            "transition_version",
            "POST",
            f"{version}/archive",
            "archiveCourseVersion",
            200,
            transition_body("archive"),
            True,
        ),
        RouteCase(
            "create_successor_draft",
            "POST",
            f"{version}/successor-draft",
            "createSuccessorCourseDraft",
            200,
            copy.deepcopy(examples["CreateSuccessorDraftV1"]),
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
    service: RecordingCourseAdministrationServiceFake,
    *,
    actor_dependency: Callable[..., VerifiedActorValue] = authenticated_actor,
) -> FastAPI:
    app = FastAPI()
    app.include_router(create_course_router(service=service, actor_dependency=actor_dependency))
    return app


def request_headers(case: RouteCase) -> dict[str, str]:
    headers = {
        "Authorization": AUTHORIZATION,
        "X-Tenant-ID": str(ALPHA_TENANT_ID),
    }
    if case.idempotent:
        headers["Idempotency-Key"] = IDEMPOTENCY_KEY
    return headers


def send(app: FastAPI, case: RouteCase, *, headers: dict[str, str] | None = None) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(
                case.method,
                case.path,
                headers=headers if headers is not None else request_headers(case),
                json=case.body,
                params=case.query,
            )

    return asyncio.run(request())


def test_all_frozen_operations_delegate_only_verified_identity_and_selectors() -> None:
    service = RecordingCourseAdministrationServiceFake()
    app = make_app(service)

    responses = [send(app, case) for case in route_cases()]

    assert [response.status_code for response in responses] == [
        case.success_status for case in route_cases()
    ]
    assert [call.operation for call in service.calls] == [case.operation for case in route_cases()]
    assert all(call.actor_id == ACTOR_ID for call in service.calls)
    assert all(call.tenant_id == ALPHA_TENANT_ID for call in service.calls)
    assert service.calls[2].cursor == CURSOR
    assert service.calls[2].limit == 25
    assert all(
        call.idempotency_key == IDEMPOTENCY_KEY
        for call, case in zip(service.calls, route_cases(), strict=True)
        if case.idempotent
    )
    for response, case in zip(responses, route_cases(), strict=True):
        if case.operation == "list_course_versions":
            assert response.json() == service.history
        elif case.operation == "create_successor_draft":
            assert response.json() == service.successor
        else:
            assert response.json() == service.snapshot
    assert all(
        call.course_id == COURSE_ID for call in service.calls if call.operation != "create_course"
    )
    assert all(
        call.version_id == VERSION_ID
        for call in service.calls
        if call.operation
        in {"get_course_version", "update_version", "replace_curriculum", "transition_version"}
    )
    assert service.calls[-1].source_version_id == VERSION_ID


def test_openapi_fragment_has_exact_methods_operation_ids_statuses_and_headers() -> None:
    schema = make_app(RecordingCourseAdministrationServiceFake()).openapi()

    expected: dict[tuple[str, str], RouteCase] = {}
    tenant_token = str(ALPHA_TENANT_ID)
    course_token = str(COURSE_ID)
    version_token = str(VERSION_ID)
    for case in route_cases():
        path = (
            case.path.replace(tenant_token, "{tenant_id}")
            .replace(course_token, "{course_id}")
            .replace(version_token, "{version_id}")
        )
        expected[(path, case.method.casefold())] = case

    actual = {
        (path, method): operation
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if method in {"get", "post", "patch", "put"}
    }
    request_models = {
        "create_course": "CreateCourseV1",
        "update_version": "UpdateCourseVersionV1",
        "replace_curriculum": "ReplaceCurriculumV1",
        "transition_version": "TransitionCourseVersionV1",
        "create_successor_draft": "CreateSuccessorDraftV1",
    }
    response_models = {
        "list_course_versions": "CourseVersionHistoryV1",
        "create_successor_draft": "SuccessorDraftResultV1",
    }
    assert set(actual) == set(expected)
    for key, case in expected.items():
        operation = actual[key]
        assert operation["operationId"] == case.operation_id
        assert str(case.success_status) in operation["responses"]
        if case.body is None:
            assert "requestBody" not in operation
        else:
            request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
            assert request_schema == {
                "$ref": f"#/components/schemas/{request_models[case.operation]}"
            }
        response_schema = operation["responses"][str(case.success_status)]["content"][
            "application/json"
        ]["schema"]
        assert response_schema == {
            "$ref": (
                "#/components/schemas/" + response_models.get(case.operation, "CourseSnapshotV1")
            )
        }
        header_parameters = {
            parameter["name"]: parameter
            for parameter in operation.get("parameters", [])
            if parameter["in"] == "header"
        }
        assert "Authorization" in header_parameters
        assert header_parameters["X-Tenant-ID"]["required"] is True
        assert ("Idempotency-Key" in header_parameters) is case.idempotent
        if case.idempotent:
            assert header_parameters["Idempotency-Key"]["required"] is True
            idempotency_schema = header_parameters["Idempotency-Key"]["schema"]
            assert idempotency_schema["minLength"] == 16
            assert idempotency_schema["maxLength"] == 128

    list_operation = actual[("/api/v1/tenants/{tenant_id}/courses/{course_id}/versions", "get")]
    query_parameters = {
        parameter["name"]: parameter["schema"]
        for parameter in list_operation["parameters"]
        if parameter["in"] == "query"
    }
    assert query_parameters["limit"] == {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 50,
        "title": "Limit",
    }
    assert {
        "type": "string",
        "minLength": 1,
        "maxLength": 2048,
    } in query_parameters["cursor"]["anyOf"]


@pytest.mark.parametrize("case", route_cases(), ids=lambda case: case.operation_id)
def test_every_route_requires_authentication_before_service_call(case: RouteCase) -> None:
    service = RecordingCourseAdministrationServiceFake()
    headers = request_headers(case)
    headers.pop("Authorization")

    response = send(make_app(service), case, headers=headers)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["www-authenticate"] == "Bearer"
    assert service.calls == []


@pytest.mark.parametrize("case", route_cases(), ids=lambda case: case.operation_id)
def test_every_route_requires_explicit_matching_tenant_header(case: RouteCase) -> None:
    service = RecordingCourseAdministrationServiceFake()
    missing_headers = request_headers(case)
    missing_headers.pop("X-Tenant-ID")

    missing = send(make_app(service), case, headers=missing_headers)

    assert missing.status_code == 400
    assert missing.json()["code"] == "TENANT_CONTEXT_REQUIRED"
    assert service.calls == []

    mismatched_headers = request_headers(case)
    mismatched_headers["X-Tenant-ID"] = str(BETA_TENANT_ID)
    mismatched = send(make_app(service), case, headers=mismatched_headers)

    assert mismatched.status_code == 404
    assert mismatched.json()["code"] == "RESOURCE_NOT_FOUND"
    assert str(ALPHA_TENANT_ID) not in mismatched.text
    assert str(BETA_TENANT_ID) not in mismatched.text
    assert service.calls == []


@pytest.mark.parametrize("case", route_cases(), ids=lambda case: case.operation_id)
@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ("RESOURCE_NOT_FOUND", 404),
        ("TENANT_ACCESS_INACTIVE", 403),
        ("COURSE_PERMISSION_DENIED", 403),
    ],
)
def test_every_service_authorization_or_idor_denial_is_neutral(
    case: RouteCase,
    code: str,
    expected_status: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = RecordingCourseAdministrationServiceFake()
    sensitive_body = "Synthetic Safe Learning body must stay private"
    service.problem_by_operation[case.operation] = CourseAdministrationError(
        code=code,
        status=418,
        title=f"Leaked {ALPHA_TENANT_ID}",
        detail=sensitive_body,
    )

    response = send(make_app(service), case)

    assert response.status_code == expected_status
    assert response.json()["code"] == code
    assert response.headers["content-type"].startswith("application/problem+json")
    assert str(ALPHA_TENANT_ID) not in response.text
    assert str(COURSE_ID) not in response.text
    assert sensitive_body not in response.text
    assert str(ALPHA_TENANT_ID) not in caplog.text
    assert str(COURSE_ID) not in caplog.text
    assert sensitive_body not in caplog.text


@pytest.mark.parametrize(
    "case",
    [case for case in route_cases() if case.idempotent],
    ids=lambda case: case.operation_id,
)
def test_idempotency_header_is_required_and_never_accepted_in_body(case: RouteCase) -> None:
    service = RecordingCourseAdministrationServiceFake()
    headers = request_headers(case)
    headers.pop("Idempotency-Key")

    missing = send(make_app(service), case, headers=headers)
    assert missing.status_code == 422
    assert missing.json()["code"] == "COURSE_VALIDATION_FAILED"
    assert service.calls == []

    body_case = RouteCase(
        operation=case.operation,
        method=case.method,
        path=case.path,
        operation_id=case.operation_id,
        success_status=case.success_status,
        body={**(case.body or {}), "idempotency_key": IDEMPOTENCY_KEY},
        idempotent=True,
        query=case.query,
    )
    body_key = send(make_app(service), body_case)
    assert body_key.status_code == 422
    assert body_key.json()["code"] == "COURSE_VALIDATION_FAILED"
    assert service.calls == []


@pytest.mark.parametrize(
    "case",
    [case for case in route_cases() if case.operation == "transition_version"],
    ids=lambda case: case.operation_id,
)
def test_transition_discriminator_must_match_the_route(case: RouteCase) -> None:
    assert case.body is not None
    mismatched = copy.deepcopy(case.body)
    mismatched["transition"] = (
        "approve" if case.body["transition"] != "approve" else "submit_review"
    )
    invalid_case = RouteCase(
        case.operation,
        case.method,
        case.path,
        case.operation_id,
        case.success_status,
        mismatched,
        case.idempotent,
        case.query,
    )
    service = RecordingCourseAdministrationServiceFake()

    response = send(make_app(service), invalid_case)

    assert response.status_code == 422
    assert response.json()["code"] == "COURSE_VALIDATION_FAILED"
    assert service.calls == []


def test_request_validation_is_bounded_and_does_not_echo_course_body() -> None:
    sensitive_body = "private synthetic lesson body"
    body: dict[str, object] = {
        "slug": "safe-course",
        "primary_locale": "en",
        "title": "Safe course",
        "description": "Synthetic description.",
        **{f"unknown_{index}": sensitive_body for index in range(105)},
    }
    case = route_cases()[0]
    invalid_case = RouteCase(
        case.operation,
        case.method,
        case.path,
        case.operation_id,
        case.success_status,
        body,
        True,
    )

    response = send(make_app(RecordingCourseAdministrationServiceFake()), invalid_case)

    assert response.status_code == 422
    assert response.json()["code"] == "COURSE_VALIDATION_FAILED"
    assert len(response.json()["errors"]) == 100
    assert sensitive_body not in response.text


def test_strict_input_models_enforce_patch_curriculum_and_transition_semantics() -> None:
    examples = load_lifecycle_examples()
    with pytest.raises(ValidationError):
        UpdateCourseVersionV1(expected_version_row_version=1)
    with pytest.raises(ValidationError):
        UpdateCourseVersionV1(expected_version_row_version=1, title=None)
    with pytest.raises(ValidationError):
        UpdateCourseVersionV1.model_validate(
            {"expected_version_row_version": "1", "title": "Synthetic title"}
        )

    curriculum = copy.deepcopy(examples["ReplaceCurriculumV1"])
    section = curriculum["sections"][0]
    section.pop("expected_row_version")
    with pytest.raises(ValidationError):
        ReplaceCurriculumV1.model_validate(curriculum)

    curriculum = copy.deepcopy(examples["ReplaceCurriculumV1"])
    section = curriculum["sections"][0]
    section["id"] = None
    section["expected_row_version"] = None
    with pytest.raises(ValidationError):
        ReplaceCurriculumV1.model_validate(curriculum)

    curriculum = copy.deepcopy(examples["ReplaceCurriculumV1"])
    duplicate = copy.deepcopy(curriculum["sections"][0])
    duplicate["id"] = "00000000-0000-4000-8000-00000000c202"
    curriculum["sections"].append(duplicate)
    with pytest.raises(ValidationError):
        ReplaceCurriculumV1.model_validate(curriculum)

    with pytest.raises(ValidationError):
        TransitionCourseVersionV1.model_validate(
            transition_body("request_changes") | {"reason_codes": []}
        )
    with pytest.raises(ValidationError):
        TransitionCourseVersionV1.model_validate(
            transition_body("publish") | {"expected_course_row_version": None}
        )
    with pytest.raises(ValidationError):
        TransitionCourseVersionV1.model_validate(
            transition_body("submit_review") | {"reason_code": None}
        )


def test_all_committed_examples_round_trip_through_public_models() -> None:
    examples = load_lifecycle_examples()
    models = {
        "CreateCourseV1": CreateCourseV1,
        "UpdateCourseVersionV1": UpdateCourseVersionV1,
        "ReplaceCurriculumV1": ReplaceCurriculumV1,
        "TransitionCourseVersionV1": TransitionCourseVersionV1,
        "CourseSnapshotV1": CourseSnapshotV1,
        "CourseVersionHistoryV1": CourseVersionHistoryV1,
        "CreateSuccessorDraftV1": CreateSuccessorDraftV1,
        "SuccessorDraftResultV1": SuccessorDraftResultV1,
    }
    for name, model in models.items():
        parsed = model.model_validate(examples[name])
        assert parsed.model_dump(mode="json", by_alias=True, exclude_unset=True) == examples[name]


def test_generated_request_schemas_match_non_null_and_conditional_contracts() -> None:
    update_schema = UpdateCourseVersionV1.model_json_schema()
    for field in ("primary_locale", "title", "description"):
        property_schema = update_schema["properties"][field]
        assert "default" not in property_schema
        assert '"null"' not in json.dumps(property_schema)
    assert update_schema["minProperties"] == 2
    assert update_schema["anyOf"] == [
        {"required": ["primary_locale"]},
        {"required": ["title"]},
        {"required": ["description"]},
    ]

    curriculum_schema = ReplaceCurriculumV1.model_json_schema()
    section_schema = curriculum_schema["$defs"]["CurriculumSectionV1"]
    for field in ("id", "expected_row_version"):
        property_schema = section_schema["properties"][field]
        assert "default" not in property_schema
        assert '"null"' not in json.dumps(property_schema)
    assert "oneOf" in section_schema

    transition_schema = TransitionCourseVersionV1.model_json_schema()
    for field in ("expected_course_row_version", "reason_code", "reason_codes"):
        property_schema = transition_schema["properties"][field]
        assert "default" not in property_schema
        assert '"null"' not in json.dumps(property_schema)
    assert len(transition_schema["allOf"]) == 3


def test_response_models_require_schema_identity_but_allow_paged_history_pointer() -> None:
    examples = load_lifecycle_examples()
    snapshot = copy.deepcopy(examples["CourseSnapshotV1"])
    snapshot.pop("$schema")
    with pytest.raises(ValidationError):
        CourseSnapshotV1.model_validate(snapshot)

    missing_cursor = copy.deepcopy(examples["CourseVersionHistoryV1"])
    missing_cursor.pop("next_cursor")
    with pytest.raises(ValidationError):
        CourseVersionHistoryV1.model_validate(missing_cursor)

    history = copy.deepcopy(examples["CourseVersionHistoryV1"])
    history["versions"] = [history["versions"][0]]
    parsed = CourseVersionHistoryV1.model_validate(history)
    assert parsed.current_published_version_id == VERSION_ID
    assert all(not version.is_current_published for version in parsed.versions)

    history = copy.deepcopy(examples["CourseVersionHistoryV1"])
    history["current_published_version_id"] = history["versions"][0]["id"]
    history["versions"][0]["is_current_published"] = True
    history["versions"][1]["is_current_published"] = False
    with pytest.raises(ValidationError):
        CourseVersionHistoryV1.model_validate(history)


def test_invalid_service_response_and_unknown_service_error_fail_safely() -> None:
    service = RecordingCourseAdministrationServiceFake()
    invalid = copy.deepcopy(service.snapshot)
    assert isinstance(invalid, dict)
    invalid["version"]["tenant_id"] = str(BETA_TENANT_ID)
    invalid["version"]["title"] = "secret response title"
    service.response_by_operation["get_course_version"] = invalid

    invalid_response = send(make_app(service), route_cases()[1])
    assert invalid_response.status_code == 500
    assert invalid_response.json()["code"] == "SERVICE_CONTRACT_ERROR"
    assert "secret response title" not in invalid_response.text

    service = RecordingCourseAdministrationServiceFake()
    service.problem_by_operation["get_course_version"] = CourseAdministrationError(
        code="UNAPPROVED_SERVICE_CODE",
        status=418,
        title="Unapproved",
        detail="secret service detail",
    )
    unknown_problem = send(make_app(service), route_cases()[1])
    assert unknown_problem.status_code == 500
    assert unknown_problem.json()["code"] == "SERVICE_CONTRACT_ERROR"
    assert "secret service detail" not in unknown_problem.text


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ("AUTHENTICATION_REQUIRED", 401),
        ("TENANT_CONTEXT_REQUIRED", 400),
        ("RESOURCE_NOT_FOUND", 404),
        ("TENANT_ACCESS_INACTIVE", 403),
        ("COURSE_PERMISSION_DENIED", 403),
        ("COURSE_VALIDATION_FAILED", 422),
        ("VERSION_CONFLICT", 409),
        ("CONTENT_HASH_MISMATCH", 409),
        ("COURSE_VERSION_IMMUTABLE", 409),
        ("REVIEWER_SEPARATION_REQUIRED", 403),
        ("HUMAN_ACTION_REQUIRED", 403),
        ("IDEMPOTENCY_CONFLICT", 409),
        ("SERVICE_CONTRACT_ERROR", 500),
    ],
)
def test_all_frozen_service_problem_codes_have_safe_stable_http_translation(
    code: str,
    expected_status: int,
) -> None:
    service = RecordingCourseAdministrationServiceFake()
    sensitive_body = "synthetic private curriculum text"
    service.problem_by_operation["get_course_version"] = CourseAdministrationError(
        code=code,
        status=418,
        title="Untrusted title",
        detail=sensitive_body,
        errors=[
            {
                "location": ["version", "title"],
                "message": sensitive_body,
                "type": "value_error",
            }
        ],
    )

    response = send(make_app(service), route_cases()[1])

    assert response.status_code == expected_status
    assert response.json()["code"] == code
    assert sensitive_body not in response.text
    assert len(response.json()["errors"]) <= 100
    if code == "AUTHENTICATION_REQUIRED":
        assert response.headers["www-authenticate"] == "Bearer"


def test_problem_details_use_rfc_media_type_and_shared_schema() -> None:
    service = RecordingCourseAdministrationServiceFake()
    service.problem_by_operation["get_course_version"] = CourseAdministrationError(
        code="VERSION_CONFLICT",
        status=409,
        title="Version conflict",
        detail="Untrusted detail",
    )
    response = send(make_app(service), route_cases()[1])
    schema = json.loads(
        (REPO_ROOT / "contracts/f001/problem-details.v1.schema.json").read_text(encoding="utf-8")
    )

    assert response.headers["content-type"].startswith("application/problem+json")
    assert not list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(response.json())
    )
    operation = make_app(service).openapi()["paths"][
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}"
    ]["get"]
    assert "application/problem+json" in operation["responses"]["404"]["content"]


def test_history_pagination_is_bounded_before_service_call() -> None:
    case = route_cases()[2]
    service = RecordingCourseAdministrationServiceFake()
    invalid = RouteCase(
        case.operation,
        case.method,
        case.path,
        case.operation_id,
        case.success_status,
        query={"limit": 101, "cursor": "x" * 2049},
    )

    response = send(make_app(service), invalid)

    assert response.status_code == 422
    assert response.json()["code"] == "COURSE_VALIDATION_FAILED"
    assert service.calls == []

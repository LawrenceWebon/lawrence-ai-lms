from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Final

import httpx
import pytest
from fastapi import FastAPI, Header
from pydantic import ValidationError

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.routers.learning import create_learning_router
from lms.api.schemas.learning import (
    CreateEnrollmentV1,
    EnrollmentV1,
    LearnerDashboardV1,
    LearningAdministrationError,
    LessonPlaybackV1,
    PlaybackSnapshotV1,
    ProgressCommandV1,
    ProgressResultV1,
    RevokeEnrollmentV1,
)
from tests.contract_fakes.f007_learning import (
    ACTOR_ID,
    ALPHA_TENANT_ID,
    BETA_TENANT_ID,
    ENROLLMENT_ID,
    IDEMPOTENCY_KEY,
    LESSON_ID,
    RecordingLearningServiceFake,
    VerifiedActorValue,
    load_examples,
)

AUTHORIZATION: Final = "Bearer synthetic-learning-token"
CURSOR: Final = "synthetic_opaque_cursor_0001"


@dataclass(frozen=True, slots=True)
class RouteCase:
    operation: str
    method: str
    path: str
    operation_id: str
    status: int
    response_model: str
    body: dict[str, object] | None = None
    idempotent: bool = False
    query: dict[str, object] | None = None


def route_cases() -> tuple[RouteCase, ...]:
    examples = load_examples()
    base = f"/api/v1/tenants/{ALPHA_TENANT_ID}"
    playback = f"{base}/learner/enrollments/{ENROLLMENT_ID}"
    return (
        RouteCase(
            "create_enrollment",
            "POST",
            f"{base}/enrollments",
            "createEnrollment",
            201,
            "EnrollmentV1",
            copy.deepcopy(examples["CreateEnrollmentV1"]),
            True,
        ),
        RouteCase(
            "revoke_enrollment",
            "POST",
            f"{base}/enrollments/{ENROLLMENT_ID}/revoke",
            "revokeEnrollment",
            200,
            "EnrollmentV1",
            copy.deepcopy(examples["RevokeEnrollmentV1"]),
            True,
        ),
        RouteCase(
            "list_learner_courses",
            "GET",
            f"{base}/learner/courses",
            "listLearnerCourses",
            200,
            "LearnerDashboardV1",
            query={"cursor": CURSOR, "limit": 25},
        ),
        RouteCase(
            "get_learner_playback",
            "GET",
            f"{playback}/playback",
            "getLearnerPlayback",
            200,
            "PlaybackSnapshotV1",
        ),
        RouteCase(
            "get_learner_lesson",
            "GET",
            f"{playback}/lessons/{LESSON_ID}",
            "getLearnerLesson",
            200,
            "LessonPlaybackV1",
        ),
        *tuple(
            RouteCase(
                f"{command.split('_')[0]}_lesson",
                "POST",
                f"{playback}/progress/{command.replace('_', '-')}",
                operation_id,
                200,
                "ProgressResultV1",
                {
                    **copy.deepcopy(examples["ProgressCommandV1"]),
                    "command": command,
                },
                True,
            )
            for command, operation_id in (
                ("open_lesson", "openLearnerLesson"),
                ("complete_lesson", "completeLearnerLesson"),
                ("reopen_lesson", "reopenLearnerLesson"),
            )
        ),
    )


def actor(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> VerifiedActorValue:
    if authorization != AUTHORIZATION:
        raise AuthenticationProblem(code="AUTHENTICATION_REQUIRED")
    return VerifiedActorValue(ACTOR_ID)


def make_app(
    service: RecordingLearningServiceFake,
    dependency: Callable[..., VerifiedActorValue] = actor,
) -> FastAPI:
    app = FastAPI()
    app.include_router(create_learning_router(service=service, actor_dependency=dependency))
    return app


def send(
    app: FastAPI,
    case: RouteCase,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        request_headers = {
            "Authorization": AUTHORIZATION,
            "X-Tenant-ID": str(ALPHA_TENANT_ID),
        }
        if case.idempotent:
            request_headers["Idempotency-Key"] = IDEMPOTENCY_KEY
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(
                case.method,
                case.path,
                headers=request_headers if headers is None else headers,
                json=case.body if body is None else body,
                params=case.query,
            )

    return asyncio.run(request())


def test_frozen_examples_validate_through_the_transport_models() -> None:
    examples = load_examples()
    models = {
        "CreateEnrollmentV1": CreateEnrollmentV1,
        "RevokeEnrollmentV1": RevokeEnrollmentV1,
        "EnrollmentV1": EnrollmentV1,
        "LearnerDashboardV1": LearnerDashboardV1,
        "PlaybackSnapshotV1": PlaybackSnapshotV1,
        "LessonPlaybackV1": LessonPlaybackV1,
        "ProgressCommandV1": ProgressCommandV1,
        "ProgressResultV1": ProgressResultV1,
    }
    for name, model in models.items():
        assert model.model_validate(examples[name]).model_dump(mode="json") == examples[name]

    invalid = copy.deepcopy(examples["ProgressCommandV1"])
    invalid["tenant_id"] = str(ALPHA_TENANT_ID)
    with pytest.raises(ValidationError):
        ProgressCommandV1.model_validate(invalid)


def test_all_routes_delegate_verified_actor_and_only_frozen_selectors() -> None:
    service = RecordingLearningServiceFake()
    responses = [send(make_app(service), case) for case in route_cases()]

    assert [response.status_code for response in responses] == [
        case.status for case in route_cases()
    ]
    assert [call.operation for call in service.calls] == [case.operation for case in route_cases()]
    assert all(call.actor_id == ACTOR_ID for call in service.calls)
    assert all(call.tenant_id == ALPHA_TENANT_ID for call in service.calls)
    assert service.calls[2].cursor == CURSOR
    assert service.calls[2].limit == 25


def test_openapi_has_exact_learning_routes_operations_and_headers() -> None:
    schema = make_app(RecordingLearningServiceFake()).openapi()
    expected: dict[tuple[str, str], RouteCase] = {}
    for case in route_cases():
        path = (
            case.path.replace(str(ALPHA_TENANT_ID), "{tenant_id}")
            .replace(str(ENROLLMENT_ID), "{enrollment_id}")
            .replace(str(LESSON_ID), "{lesson_id}")
        )
        expected[(path, case.method.casefold())] = case
    actual = {
        (path, method): operation
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if method in {"get", "post"}
    }

    assert set(actual) == set(expected)
    for key, case in expected.items():
        operation = actual[key]
        assert operation["operationId"] == case.operation_id
        assert operation["responses"][str(case.status)]["content"]["application/json"][
            "schema"
        ] == {"$ref": f"#/components/schemas/{case.response_model}"}
        headers = {
            parameter["name"]: parameter
            for parameter in operation["parameters"]
            if parameter["in"] == "header"
        }
        assert headers["X-Tenant-ID"]["required"] is True
        assert ("Idempotency-Key" in headers) is case.idempotent


@pytest.mark.parametrize("case", route_cases(), ids=lambda item: item.operation_id)
def test_every_learning_route_requires_auth_and_matching_tenant(case: RouteCase) -> None:
    service = RecordingLearningServiceFake()
    missing = send(
        make_app(service),
        case,
        headers={"X-Tenant-ID": str(ALPHA_TENANT_ID)},
    )
    mismatch_headers = {
        "Authorization": AUTHORIZATION,
        "X-Tenant-ID": str(BETA_TENANT_ID),
    }
    if case.idempotent:
        mismatch_headers["Idempotency-Key"] = IDEMPOTENCY_KEY
    missing_tenant_headers = {"Authorization": AUTHORIZATION}
    if case.idempotent:
        missing_tenant_headers["Idempotency-Key"] = IDEMPOTENCY_KEY
    missing_tenant = send(make_app(service), case, headers=missing_tenant_headers)
    mismatched = send(make_app(service), case, headers=mismatch_headers)

    assert missing.status_code == 401
    assert missing.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert missing_tenant.status_code == 400
    assert missing_tenant.json()["code"] == "TENANT_CONTEXT_REQUIRED"
    assert mismatched.status_code == 404
    assert mismatched.json()["code"] == "LEARNING_RESOURCE_NOT_FOUND"
    assert service.calls == []


def test_route_command_discriminator_and_service_shape_fail_closed() -> None:
    service = RecordingLearningServiceFake()
    complete = route_cases()[6]
    wrong_command = copy.deepcopy(complete.body)
    assert wrong_command is not None
    wrong_command["command"] = "open_lesson"

    mismatch = send(make_app(service), complete, body=wrong_command)
    service.playback["source_document"] = "must never render"
    bad_shape = send(make_app(service), route_cases()[3])

    assert mismatch.status_code == 422
    assert mismatch.json()["code"] == "ENROLLMENT_VALIDATION_FAILED"
    assert bad_shape.status_code == 500
    assert bad_shape.json()["code"] == "SERVICE_CONTRACT_ERROR"
    assert "must never render" not in bad_shape.text


def test_service_problem_text_is_not_trusted_or_logged(caplog: pytest.LogCaptureFixture) -> None:
    service = RecordingLearningServiceFake()
    service.problem_by_operation["get_learner_lesson"] = LearningAdministrationError(
        code="LEARNING_RESOURCE_NOT_FOUND",
        status=418,
        errors=({"location": ("body", "private lesson text")},),
    )

    response = send(make_app(service), route_cases()[4])

    assert response.status_code == 404
    assert response.json()["code"] == "LEARNING_RESOURCE_NOT_FOUND"
    assert "private lesson text" not in response.text
    assert "private lesson text" not in caplog.text

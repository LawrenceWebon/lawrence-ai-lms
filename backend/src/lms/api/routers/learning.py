from __future__ import annotations

from collections.abc import Callable, Coroutine, Sequence
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.schemas.learning import (
    CreateEnrollmentV1,
    EnrollmentV1,
    LearnerDashboardV1,
    LearningAdministrationError,
    LearningServiceV1,
    LessonPlaybackV1,
    PlaybackSnapshotV1,
    ProgressCommandV1,
    ProgressResultV1,
    RevokeEnrollmentV1,
    VerifiedActorResult,
)
from lms.api.schemas.tenancy import ProblemDetails

ActorDependency = Callable[..., VerifiedActorResult]
RouteHandler = Callable[[Request], Coroutine[Any, Any, Response]]
TenantHeader = Annotated[UUID, Header(alias="X-Tenant-ID")]
IdempotencyHeader = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=128),
]
DashboardCursor = Annotated[
    str | None,
    Query(min_length=16, max_length=1024, pattern=r"^[A-Za-z0-9_-]+$"),
]
DashboardLimit = Annotated[int, Query(ge=1, le=50)]

_SAFE_PROBLEMS: dict[str, tuple[int, str, str]] = {
    "AUTHENTICATION_REQUIRED": (401, "Authentication required", "Authentication is required."),
    "TENANT_CONTEXT_REQUIRED": (400, "Tenant context required", "Select a tenant."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access inactive", "Tenant access is inactive."),
    "LEARNING_RESOURCE_NOT_FOUND": (
        404,
        "Learning resource unavailable",
        "The learning resource is unavailable.",
    ),
    "ENROLLMENT_VALIDATION_FAILED": (
        422,
        "Learning request invalid",
        "The request does not conform to the learning contract.",
    ),
    "PROGRESS_VERSION_CONFLICT": (
        409,
        "Progress version conflict",
        "Learner progress changed before this request completed.",
    ),
    "IDEMPOTENCY_CONFLICT": (
        409,
        "Idempotency conflict",
        "The request conflicts with an earlier request.",
    ),
    "SERVICE_CONTRACT_ERROR": (
        500,
        "Service contract error",
        "The service returned an invalid response.",
    ),
}
_SAFE_LOCATION_PARTS = frozenset(
    {
        "body",
        "path",
        "query",
        "header",
        "tenant_id",
        "enrollment_id",
        "lesson_id",
        "learner_membership_id",
        "course_id",
        "expected_enrollment_row_version",
        "expected_progress_row_version",
        "reason_code",
        "command",
        "cursor",
        "limit",
        "idempotency_key",
    }
)


def _problem_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {
        code: {
            "model": ProblemDetails,
            "description": "RFC Problem Details response",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetails"}
                }
            },
        }
        for code in codes
    }


def _request_id(request: Request) -> str:
    candidate = request.headers.get("X-Request-ID", "").strip()
    return candidate if 1 <= len(candidate) <= 128 else str(uuid4())


def _problem_response(
    request: Request,
    *,
    code: str,
    errors: list[dict[str, object]] | None = None,
) -> JSONResponse:
    status_code, title, detail = _SAFE_PROBLEMS[code]
    problem = ProblemDetails(
        type=f"https://api.ai-lms.local/problems/{code.casefold().replace('_', '-')}",
        title=title,
        status=status_code,
        detail=detail,
        code=code,
        request_id=_request_id(request),
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
        headers={"WWW-Authenticate": "Bearer"} if code == "AUTHENTICATION_REQUIRED" else None,
    )


def _safe_location(location: Sequence[object]) -> list[str]:
    result = []
    for part in location[:12]:
        value = str(part)
        result.append(value if value.isdecimal() or value in _SAFE_LOCATION_PARTS else "field")
    return result or ["body"]


def _validation_errors(errors: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for error in errors[:100]:
        location = error.get("loc", error.get("location", ("body",)))
        if isinstance(location, str) or not isinstance(location, Sequence):
            location = ("body",)
        result.append(
            {
                "location": _safe_location(location),
                "message": "The value is invalid.",
                "type": "value_error",
            }
        )
    return result


def _missing_tenant_header(problem: RequestValidationError) -> bool:
    return any(
        tuple(str(part).casefold() for part in error.get("loc", ())) == ("header", "x-tenant-id")
        and error.get("type") == "missing"
        for error in problem.errors()
    )


class LearningProblemDetailsRoute(APIRoute):
    def get_route_handler(self) -> RouteHandler:
        handler = super().get_route_handler()

        async def translate(request: Request) -> Response:
            try:
                return await handler(request)
            except LearningAdministrationError as problem:
                code = problem.code if problem.code in _SAFE_PROBLEMS else "SERVICE_CONTRACT_ERROR"
                errors = (
                    _validation_errors(problem.errors)
                    if code == "ENROLLMENT_VALIDATION_FAILED"
                    else []
                )
                return _problem_response(request, code=code, errors=errors)
            except AuthenticationProblem:
                return _problem_response(request, code="AUTHENTICATION_REQUIRED")
            except RequestValidationError as problem:
                code = (
                    "TENANT_CONTEXT_REQUIRED"
                    if _missing_tenant_header(problem)
                    else "ENROLLMENT_VALIDATION_FAILED"
                )
                return _problem_response(
                    request,
                    code=code,
                    errors=(
                        []
                        if code == "TENANT_CONTEXT_REQUIRED"
                        else _validation_errors(problem.errors())
                    ),
                )
            except ResponseValidationError, ValidationError:
                return _problem_response(request, code="SERVICE_CONTRACT_ERROR")

        return translate


def _matching_tenant(*, route_tenant_id: UUID, header_tenant_id: UUID) -> UUID:
    if route_tenant_id != header_tenant_id:
        raise LearningAdministrationError(code="LEARNING_RESOURCE_NOT_FOUND")
    return route_tenant_id


def create_learning_router(
    *,
    service: LearningServiceV1,
    actor_dependency: ActorDependency,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/tenants/{tenant_id}",
        route_class=LearningProblemDetailsRoute,
    )
    actor_requirement: Any = Depends(actor_dependency)

    @router.post(
        "/enrollments",
        operation_id="createEnrollment",
        status_code=status.HTTP_201_CREATED,
        response_model=EnrollmentV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def create_enrollment(
        tenant_id: UUID,
        command: CreateEnrollmentV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
    ) -> EnrollmentV1:
        return EnrollmentV1.model_validate(
            service.create_enrollment(
                actor_id=actor.principal_id,
                tenant_id=_matching_tenant(route_tenant_id=tenant_id, header_tenant_id=x_tenant_id),
                command=command,
                idempotency_key=idempotency_key,
            ),
            from_attributes=True,
        )

    @router.post(
        "/enrollments/{enrollment_id}/revoke",
        operation_id="revokeEnrollment",
        response_model=EnrollmentV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def revoke_enrollment(
        tenant_id: UUID,
        enrollment_id: UUID,
        command: RevokeEnrollmentV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
    ) -> EnrollmentV1:
        return EnrollmentV1.model_validate(
            service.revoke_enrollment(
                actor_id=actor.principal_id,
                tenant_id=_matching_tenant(route_tenant_id=tenant_id, header_tenant_id=x_tenant_id),
                enrollment_id=enrollment_id,
                command=command,
                idempotency_key=idempotency_key,
            ),
            from_attributes=True,
        )

    @router.get(
        "/learner/courses",
        operation_id="listLearnerCourses",
        response_model=LearnerDashboardV1,
        responses=_problem_responses(400, 401, 403, 404, 422, 500),
    )
    def list_learner_courses(
        tenant_id: UUID,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
        cursor: DashboardCursor = None,
        limit: DashboardLimit = 20,
    ) -> LearnerDashboardV1:
        return LearnerDashboardV1.model_validate(
            service.list_learner_courses(
                actor_id=actor.principal_id,
                tenant_id=_matching_tenant(route_tenant_id=tenant_id, header_tenant_id=x_tenant_id),
                cursor=cursor,
                limit=limit,
            ),
            from_attributes=True,
        )

    @router.get(
        "/learner/enrollments/{enrollment_id}/playback",
        operation_id="getLearnerPlayback",
        response_model=PlaybackSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 422, 500),
    )
    def get_learner_playback(
        tenant_id: UUID,
        enrollment_id: UUID,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
    ) -> PlaybackSnapshotV1:
        return PlaybackSnapshotV1.model_validate(
            service.get_learner_playback(
                actor_id=actor.principal_id,
                tenant_id=_matching_tenant(route_tenant_id=tenant_id, header_tenant_id=x_tenant_id),
                enrollment_id=enrollment_id,
            ),
            from_attributes=True,
        )

    @router.get(
        "/learner/enrollments/{enrollment_id}/lessons/{lesson_id}",
        operation_id="getLearnerLesson",
        response_model=LessonPlaybackV1,
        responses=_problem_responses(400, 401, 403, 404, 422, 500),
    )
    def get_learner_lesson(
        tenant_id: UUID,
        enrollment_id: UUID,
        lesson_id: UUID,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
    ) -> LessonPlaybackV1:
        return LessonPlaybackV1.model_validate(
            service.get_learner_lesson(
                actor_id=actor.principal_id,
                tenant_id=_matching_tenant(route_tenant_id=tenant_id, header_tenant_id=x_tenant_id),
                enrollment_id=enrollment_id,
                lesson_id=lesson_id,
            ),
            from_attributes=True,
        )

    def progress(
        *,
        expected: Literal["open_lesson", "complete_lesson", "reopen_lesson"],
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: str,
        x_tenant_id: UUID,
        actor: VerifiedActorResult,
    ) -> ProgressResultV1:
        if command.command != expected:
            raise LearningAdministrationError(
                code="ENROLLMENT_VALIDATION_FAILED",
                errors=({"location": ("body", "command")},),
            )
        operation = {
            "open_lesson": service.open_lesson,
            "complete_lesson": service.complete_lesson,
            "reopen_lesson": service.reopen_lesson,
        }[expected]
        return ProgressResultV1.model_validate(
            operation(
                actor_id=actor.principal_id,
                tenant_id=_matching_tenant(route_tenant_id=tenant_id, header_tenant_id=x_tenant_id),
                enrollment_id=enrollment_id,
                command=command,
                idempotency_key=idempotency_key,
            ),
            from_attributes=True,
        )

    @router.post(
        "/learner/enrollments/{enrollment_id}/progress/open-lesson",
        operation_id="openLearnerLesson",
        response_model=ProgressResultV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def open_lesson(
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
    ) -> ProgressResultV1:
        return progress(
            expected="open_lesson",
            tenant_id=tenant_id,
            enrollment_id=enrollment_id,
            command=command,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
            actor=actor,
        )

    @router.post(
        "/learner/enrollments/{enrollment_id}/progress/complete-lesson",
        operation_id="completeLearnerLesson",
        response_model=ProgressResultV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def complete_lesson(
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
    ) -> ProgressResultV1:
        return progress(
            expected="complete_lesson",
            tenant_id=tenant_id,
            enrollment_id=enrollment_id,
            command=command,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
            actor=actor,
        )

    @router.post(
        "/learner/enrollments/{enrollment_id}/progress/reopen-lesson",
        operation_id="reopenLearnerLesson",
        response_model=ProgressResultV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def reopen_lesson(
        tenant_id: UUID,
        enrollment_id: UUID,
        command: ProgressCommandV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        actor: VerifiedActorResult = actor_requirement,
    ) -> ProgressResultV1:
        return progress(
            expected="reopen_lesson",
            tenant_id=tenant_id,
            enrollment_id=enrollment_id,
            command=command,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
            actor=actor,
        )

    return router

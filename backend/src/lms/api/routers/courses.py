from __future__ import annotations

from collections.abc import Callable, Coroutine, Sequence
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.schemas.courses import (
    CourseAdministrationError,
    CourseAdministrationServiceV1,
    CourseSnapshotV1,
    CourseVersionHistoryV1,
    CreateCourseV1,
    CreateSuccessorDraftV1,
    ReplaceCurriculumV1,
    SuccessorDraftResultV1,
    TransitionCourseVersionV1,
    TransitionName,
    UpdateCourseVersionV1,
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
HistoryCursor = Annotated[str | None, Query(min_length=1, max_length=2048)]
HistoryLimit = Annotated[int, Query(ge=1, le=100)]
_SAFE_ERROR_LOCATION_PARTS = frozenset(
    {
        "body",
        "path",
        "query",
        "header",
        "tenant_id",
        "course_id",
        "version_id",
        "command",
        "slug",
        "primary_locale",
        "title",
        "description",
        "expected_version_row_version",
        "expected_course_row_version",
        "expected_source_version_row_version",
        "expected_content_hash",
        "expected_source_content_hash",
        "transition",
        "reason_code",
        "reason_codes",
        "sections",
        "lessons",
        "content_blocks",
        "id",
        "expected_row_version",
        "kind",
        "position",
        "is_required",
        "document",
        "content",
        "items",
        "type",
        "text",
        "marks",
        "level",
        "cursor",
        "limit",
        "idempotency_key",
    }
)

_SAFE_SERVICE_PROBLEMS: dict[str, tuple[int, str, str]] = {
    "AUTHENTICATION_REQUIRED": (
        status.HTTP_401_UNAUTHORIZED,
        "Authentication required",
        "Authentication is required.",
    ),
    "TENANT_CONTEXT_REQUIRED": (
        status.HTTP_400_BAD_REQUEST,
        "Tenant context required",
        "Select a tenant.",
    ),
    "RESOURCE_NOT_FOUND": (
        status.HTTP_404_NOT_FOUND,
        "Resource unavailable",
        "The resource is unavailable.",
    ),
    "TENANT_ACCESS_INACTIVE": (
        status.HTTP_403_FORBIDDEN,
        "Tenant access inactive",
        "Tenant access is inactive.",
    ),
    "COURSE_PERMISSION_DENIED": (
        status.HTTP_403_FORBIDDEN,
        "Course action unavailable",
        "The requested course action is unavailable.",
    ),
    "COURSE_VALIDATION_FAILED": (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Course validation failed",
        "The request does not conform to the course contract.",
    ),
    "VERSION_CONFLICT": (
        status.HTTP_409_CONFLICT,
        "Version conflict",
        "The resource changed before this request completed.",
    ),
    "CONTENT_HASH_MISMATCH": (
        status.HTTP_409_CONFLICT,
        "Content hash mismatch",
        "The selected course content no longer matches the expected hash.",
    ),
    "COURSE_VERSION_IMMUTABLE": (
        status.HTTP_409_CONFLICT,
        "Course version immutable",
        "The selected course version cannot be changed.",
    ),
    "REVIEWER_SEPARATION_REQUIRED": (
        status.HTTP_403_FORBIDDEN,
        "Separate reviewer required",
        "A separate qualified reviewer must perform this action.",
    ),
    "HUMAN_ACTION_REQUIRED": (
        status.HTTP_403_FORBIDDEN,
        "Human action required",
        "An authorized human must perform this action.",
    ),
    "IDEMPOTENCY_CONFLICT": (
        status.HTTP_409_CONFLICT,
        "Idempotency conflict",
        "The request conflicts with an earlier request.",
    ),
    "SERVICE_CONTRACT_ERROR": (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Service contract error",
        "The service returned an invalid response.",
    ),
}


def _problem_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {
        status_code: {
            "model": ProblemDetails,
            "description": "RFC Problem Details response",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetails"}
                }
            },
        }
        for status_code in status_codes
    }


def _request_id(request: Request) -> str:
    candidate = request.headers.get("X-Request-ID", "").strip()
    if 1 <= len(candidate) <= 128:
        return candidate
    return str(uuid4())


def _problem_response(
    request: Request,
    *,
    code: str,
    status_code: int,
    title: str,
    detail: str,
    errors: list[dict[str, object]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
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
        headers=headers,
    )


def _safe_error_location(location: Sequence[object]) -> list[str]:
    safe: list[str] = []
    for part in location[:12]:
        candidate = str(part)
        safe.append(
            candidate
            if candidate.isdecimal() or candidate in _SAFE_ERROR_LOCATION_PARTS
            else "field"
        )
    return safe or ["body"]


def _request_validation_errors(problem: RequestValidationError) -> list[dict[str, object]]:
    return [
        {
            "location": _safe_error_location(error.get("loc", ())),
            "message": "The value is invalid.",
            "type": str(error.get("type", "value_error"))[:64],
        }
        for error in problem.errors()[:100]
    ]


def _is_missing_tenant_header(problem: RequestValidationError) -> bool:
    for error in problem.errors():
        location = tuple(error.get("loc", ()))
        if (
            len(location) == 2
            and location[0] == "header"
            and str(location[1]).casefold() == "x-tenant-id"
            and error.get("type") == "missing"
        ):
            return True
    return False


def _service_validation_errors(
    errors: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    safe: list[dict[str, object]] = []
    for error in errors[:100]:
        location = error.get("location", ("body",))
        if isinstance(location, str) or not isinstance(location, Sequence):
            location = ("body",)
        safe.append(
            {
                "location": _safe_error_location(location),
                "message": "The value is invalid.",
                "type": "value_error",
            }
        )
    return safe


class CourseProblemDetailsRoute(APIRoute):
    """Translate course-service and validation failures without leaking input data."""

    def get_route_handler(self) -> RouteHandler:
        original_handler = super().get_route_handler()

        async def problem_details_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except CourseAdministrationError as problem:
                safe_problem = _SAFE_SERVICE_PROBLEMS.get(problem.code)
                if safe_problem is None:
                    safe_problem = _SAFE_SERVICE_PROBLEMS["SERVICE_CONTRACT_ERROR"]
                    code = "SERVICE_CONTRACT_ERROR"
                    errors: list[dict[str, object]] = []
                else:
                    code = problem.code
                    errors = (
                        _service_validation_errors(problem.errors)
                        if problem.code == "COURSE_VALIDATION_FAILED"
                        else []
                    )
                status_code, title, detail = safe_problem
                return _problem_response(
                    request,
                    code=code,
                    status_code=status_code,
                    title=title,
                    detail=detail,
                    errors=errors,
                    headers=(
                        {"WWW-Authenticate": "Bearer"}
                        if code == "AUTHENTICATION_REQUIRED"
                        else None
                    ),
                )
            except AuthenticationProblem:
                status_code, title, detail = _SAFE_SERVICE_PROBLEMS["AUTHENTICATION_REQUIRED"]
                return _problem_response(
                    request,
                    code="AUTHENTICATION_REQUIRED",
                    status_code=status_code,
                    title=title,
                    detail=detail,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except RequestValidationError as problem:
                code = (
                    "TENANT_CONTEXT_REQUIRED"
                    if _is_missing_tenant_header(problem)
                    else "COURSE_VALIDATION_FAILED"
                )
                status_code, title, detail = _SAFE_SERVICE_PROBLEMS[code]
                return _problem_response(
                    request,
                    code=code,
                    status_code=status_code,
                    title=title,
                    detail=detail,
                    errors=(
                        []
                        if code == "TENANT_CONTEXT_REQUIRED"
                        else _request_validation_errors(problem)
                    ),
                )
            except ResponseValidationError, ValidationError:
                status_code, title, detail = _SAFE_SERVICE_PROBLEMS["SERVICE_CONTRACT_ERROR"]
                return _problem_response(
                    request,
                    code="SERVICE_CONTRACT_ERROR",
                    status_code=status_code,
                    title=title,
                    detail=detail,
                )

        return problem_details_handler


def _require_matching_tenant(*, tenant_id: UUID, header_tenant_id: UUID) -> UUID:
    if header_tenant_id != tenant_id:
        raise CourseAdministrationError(code="RESOURCE_NOT_FOUND")
    return tenant_id


def _snapshot_response(result: object) -> CourseSnapshotV1:
    return CourseSnapshotV1.model_validate(result, from_attributes=True)


def _history_response(result: object) -> CourseVersionHistoryV1:
    return CourseVersionHistoryV1.model_validate(result, from_attributes=True)


def _successor_response(result: object) -> SuccessorDraftResultV1:
    return SuccessorDraftResultV1.model_validate(result, from_attributes=True)


def _require_transition(
    command: TransitionCourseVersionV1,
    *,
    expected: TransitionName,
) -> None:
    if command.transition != expected:
        raise CourseAdministrationError(code="COURSE_VALIDATION_FAILED")


def create_course_router(
    *,
    service: CourseAdministrationServiceV1,
    actor_dependency: ActorDependency,
) -> APIRouter:
    """Build the F-002 router without owning application composition."""

    router = APIRouter(
        prefix="/api/v1/tenants/{tenant_id}/courses",
        route_class=CourseProblemDetailsRoute,
    )
    actor_requirement: Any = Depends(actor_dependency)

    @router.post(
        "",
        operation_id="createCourse",
        status_code=status.HTTP_201_CREATED,
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def create_course(
        tenant_id: UUID,
        command: CreateCourseV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        result = service.create_course(
            actor_id=verified_actor.principal_id,
            tenant_id=_require_matching_tenant(
                tenant_id=tenant_id,
                header_tenant_id=x_tenant_id,
            ),
            command=command,
            idempotency_key=idempotency_key,
        )
        return _snapshot_response(result)

    @router.get(
        "/{course_id}/versions/{version_id}",
        operation_id="getCourseVersion",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 422, 500),
    )
    def get_course_version(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        result = service.get_course_version(
            actor_id=verified_actor.principal_id,
            tenant_id=_require_matching_tenant(
                tenant_id=tenant_id,
                header_tenant_id=x_tenant_id,
            ),
            course_id=course_id,
            version_id=version_id,
        )
        return _snapshot_response(result)

    @router.get(
        "/{course_id}/versions",
        operation_id="listCourseVersions",
        response_model=CourseVersionHistoryV1,
        responses=_problem_responses(400, 401, 403, 404, 422, 500),
    )
    def list_course_versions(
        tenant_id: UUID,
        course_id: UUID,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
        cursor: HistoryCursor = None,
        limit: HistoryLimit = 50,
    ) -> CourseVersionHistoryV1:
        result = service.list_course_versions(
            actor_id=verified_actor.principal_id,
            tenant_id=_require_matching_tenant(
                tenant_id=tenant_id,
                header_tenant_id=x_tenant_id,
            ),
            course_id=course_id,
            cursor=cursor,
            limit=limit,
        )
        return _history_response(result)

    @router.patch(
        "/{course_id}/versions/{version_id}",
        operation_id="updateCourseVersion",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def update_course_version(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: UpdateCourseVersionV1,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        result = service.update_version(
            actor_id=verified_actor.principal_id,
            tenant_id=_require_matching_tenant(
                tenant_id=tenant_id,
                header_tenant_id=x_tenant_id,
            ),
            course_id=course_id,
            version_id=version_id,
            command=command,
        )
        return _snapshot_response(result)

    @router.put(
        "/{course_id}/versions/{version_id}/curriculum",
        operation_id="replaceCourseCurriculum",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def replace_course_curriculum(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: ReplaceCurriculumV1,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        result = service.replace_curriculum(
            actor_id=verified_actor.principal_id,
            tenant_id=_require_matching_tenant(
                tenant_id=tenant_id,
                header_tenant_id=x_tenant_id,
            ),
            course_id=course_id,
            version_id=version_id,
            command=command,
        )
        return _snapshot_response(result)

    def transition(
        *,
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        expected: TransitionName,
        verified_actor: VerifiedActorResult,
        idempotency_key: str,
        x_tenant_id: UUID,
    ) -> CourseSnapshotV1:
        tenant_selector = _require_matching_tenant(
            tenant_id=tenant_id,
            header_tenant_id=x_tenant_id,
        )
        _require_transition(command, expected=expected)
        result = service.transition_version(
            actor_id=verified_actor.principal_id,
            tenant_id=tenant_selector,
            course_id=course_id,
            version_id=version_id,
            command=command,
            idempotency_key=idempotency_key,
        )
        return _snapshot_response(result)

    @router.post(
        "/{course_id}/versions/{version_id}/submit-review",
        operation_id="submitCourseReview",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def submit_course_review(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        return transition(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
            command=command,
            expected="submit_review",
            verified_actor=verified_actor,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
        )

    @router.post(
        "/{course_id}/versions/{version_id}/request-changes",
        operation_id="requestCourseChanges",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def request_course_changes(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        return transition(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
            command=command,
            expected="request_changes",
            verified_actor=verified_actor,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
        )

    @router.post(
        "/{course_id}/versions/{version_id}/approve",
        operation_id="approveCourseVersion",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def approve_course_version(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        return transition(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
            command=command,
            expected="approve",
            verified_actor=verified_actor,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
        )

    @router.post(
        "/{course_id}/versions/{version_id}/publish",
        operation_id="publishCourseVersion",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def publish_course_version(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        return transition(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
            command=command,
            expected="publish",
            verified_actor=verified_actor,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
        )

    @router.post(
        "/{course_id}/versions/{version_id}/withdraw",
        operation_id="withdrawCourseVersion",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def withdraw_course_version(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        return transition(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
            command=command,
            expected="withdraw",
            verified_actor=verified_actor,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
        )

    @router.post(
        "/{course_id}/versions/{version_id}/archive",
        operation_id="archiveCourseVersion",
        response_model=CourseSnapshotV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def archive_course_version(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: TransitionCourseVersionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseSnapshotV1:
        return transition(
            tenant_id=tenant_id,
            course_id=course_id,
            version_id=version_id,
            command=command,
            expected="archive",
            verified_actor=verified_actor,
            idempotency_key=idempotency_key,
            x_tenant_id=x_tenant_id,
        )

    @router.post(
        "/{course_id}/versions/{version_id}/successor-draft",
        operation_id="createSuccessorCourseDraft",
        response_model=SuccessorDraftResultV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def create_successor_course_draft(
        tenant_id: UUID,
        course_id: UUID,
        version_id: UUID,
        command: CreateSuccessorDraftV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> SuccessorDraftResultV1:
        result = service.create_successor_draft(
            actor_id=verified_actor.principal_id,
            tenant_id=_require_matching_tenant(
                tenant_id=tenant_id,
                header_tenant_id=x_tenant_id,
            ),
            course_id=course_id,
            source_version_id=version_id,
            command=command,
            idempotency_key=idempotency_key,
        )
        return _successor_response(result)

    return router

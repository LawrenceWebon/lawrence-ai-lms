from __future__ import annotations

from collections.abc import Callable, Coroutine, Sequence
from typing import Annotated, Any, Protocol
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.responses import Response

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.schemas.course_generation import (
    ApproveGenerationBlueprintV1,
    CourseGenerationReviewPackageV1,
    CourseGenerationRunV1,
    CourseGenerationServiceV1,
    GenerationContractError,
    RejectCourseGenerationV1,
    StartCourseGenerationV1,
)
from lms.api.schemas.tenancy import ProblemDetails


class VerifiedActorResult(Protocol):
    @property
    def principal_id(self) -> UUID: ...


ActorDependency = Callable[..., VerifiedActorResult]
RouteHandler = Callable[[Request], Coroutine[Any, Any, Response]]
TenantHeader = Annotated[UUID, Header(alias="X-Tenant-ID")]
IdempotencyHeader = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=128),
]

_SAFE_LOCATION_PARTS = frozenset(
    {
        "body",
        "path",
        "header",
        "tenant_id",
        "run_id",
        "source_document_id",
        "source_version_id",
        "ingestion_run_id",
        "target_level",
        "target_duration_minutes",
        "intended_audience",
        "teaching_style",
        "locale",
        "supersedes_run_id",
        "expected_run_row_version",
        "blueprint_id",
        "blueprint_revision",
        "expected_blueprint_content_sha256",
        "expected_review_content_sha256",
        "reason_code",
        "idempotency_key",
    }
)
_SAFE_PROBLEMS: dict[str, tuple[int, str, str]] = {
    "AUTHENTICATION_REQUIRED": (401, "Authentication required", "Authentication is required."),
    "TENANT_CONTEXT_REQUIRED": (400, "Tenant context required", "Select a tenant."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access inactive", "Tenant access is inactive."),
    "GENERATION_RESOURCE_NOT_FOUND": (
        404,
        "Generation unavailable",
        "The generation resource is unavailable.",
    ),
    "GENERATION_PERMISSION_DENIED": (
        403,
        "Generation action unavailable",
        "The requested generation action is unavailable.",
    ),
    "GENERATION_RIGHTS_REQUIRED": (
        403,
        "Generation rights required",
        "Active generation rights are required.",
    ),
    "GENERATION_RIGHTS_INACTIVE": (
        403,
        "Generation rights inactive",
        "Generation rights are inactive.",
    ),
    "GENERATION_VALIDATION_FAILED": (
        422,
        "Generation request invalid",
        "The request does not conform to the generation contract.",
    ),
    "GENERATION_SOURCE_INVALID": (
        422,
        "Normalized source invalid",
        "The normalized source is invalid.",
    ),
    "GENERATION_SOURCE_EDGE_INVALID": (
        422,
        "Source alignment invalid",
        "Generated source alignment is invalid.",
    ),
    "GENERATION_OUTPUT_INVALID": (
        422,
        "Generation output invalid",
        "The generated output is invalid.",
    ),
    "GENERATION_STATE_CONFLICT": (
        409,
        "Generation state conflict",
        "The generation state changed.",
    ),
    "GENERATION_VERSION_CONFLICT": (
        409,
        "Generation revision conflict",
        "The generation revision changed.",
    ),
    "GENERATION_LEASE_CONFLICT": (
        409,
        "Generation lease conflict",
        "The generation lease is unavailable.",
    ),
    "GENERATION_RETRY_EXHAUSTED": (
        409,
        "Generation retry exhausted",
        "The generation retry budget is exhausted.",
    ),
    "IDEMPOTENCY_CONFLICT": (
        409,
        "Idempotency conflict",
        "The request conflicts with an earlier request.",
    ),
    "SERVICE_CONTRACT_ERROR": (
        500,
        "Service contract error",
        "The generation service returned an invalid response.",
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
    return candidate if 1 <= len(candidate) <= 128 else str(uuid4())


def _safe_location(location: Sequence[object]) -> list[str]:
    safe: list[str] = []
    for part in location[:12]:
        candidate = str(part)
        safe.append(
            candidate if candidate.isdecimal() or candidate in _SAFE_LOCATION_PARTS else "field"
        )
    return safe or ["body"]


def _validation_errors(errors: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    safe: list[dict[str, object]] = []
    for error in errors[:100]:
        location = error.get("loc", error.get("location", ("body",)))
        if isinstance(location, str) or not isinstance(location, Sequence):
            location = ("body",)
        safe.append(
            {
                "location": _safe_location(location),
                "message": "The value is invalid.",
                "type": str(error.get("type", "value_error"))[:64],
            }
        )
    return safe


def _problem_response(
    request: Request,
    *,
    code: str,
    errors: list[dict[str, object]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    status_code, title, detail = _SAFE_PROBLEMS.get(code, _SAFE_PROBLEMS["SERVICE_CONTRACT_ERROR"])
    safe_code = code if code in _SAFE_PROBLEMS else "SERVICE_CONTRACT_ERROR"
    problem = ProblemDetails(
        type=f"https://api.ai-lms.local/problems/{safe_code.casefold().replace('_', '-')}",
        title=title,
        status=status_code,
        detail=detail,
        code=safe_code,
        request_id=_request_id(request),
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
        headers=headers,
    )


class CourseGenerationProblemDetailsRoute(APIRoute):
    def get_route_handler(self) -> RouteHandler:
        original_handler = super().get_route_handler()

        async def problem_details_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except GenerationContractError as problem:
                return _problem_response(
                    request,
                    code=problem.code,
                    errors=(
                        _validation_errors(problem.errors)
                        if problem.code == "GENERATION_VALIDATION_FAILED"
                        else []
                    ),
                )
            except AuthenticationProblem:
                return _problem_response(
                    request,
                    code="AUTHENTICATION_REQUIRED",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except RequestValidationError as problem:
                missing_tenant = any(
                    tuple(str(part).casefold() for part in error.get("loc", ()))
                    == ("header", "x-tenant-id")
                    for error in problem.errors()
                )
                return _problem_response(
                    request,
                    code=(
                        "TENANT_CONTEXT_REQUIRED"
                        if missing_tenant
                        else "GENERATION_VALIDATION_FAILED"
                    ),
                    errors=[] if missing_tenant else _validation_errors(problem.errors()),
                )
            except ResponseValidationError, ValidationError:
                return _problem_response(request, code="SERVICE_CONTRACT_ERROR")

        return problem_details_handler


def _tenant(tenant_id: UUID, header_tenant_id: UUID) -> UUID:
    if tenant_id != header_tenant_id:
        raise GenerationContractError(code="GENERATION_RESOURCE_NOT_FOUND")
    return tenant_id


def _run(result: object) -> CourseGenerationRunV1:
    return CourseGenerationRunV1.model_validate(result, from_attributes=True)


def _package(result: object) -> CourseGenerationReviewPackageV1:
    return CourseGenerationReviewPackageV1.model_validate(result, from_attributes=True)


def create_course_generation_router(
    *,
    service: CourseGenerationServiceV1,
    actor_dependency: ActorDependency,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", route_class=CourseGenerationProblemDetailsRoute)
    actor_requirement = Depends(actor_dependency)

    @router.post(
        "/tenants/{tenant_id}/course-generation-runs",
        operation_id="startCourseGeneration",
        response_model=CourseGenerationRunV1,
        status_code=status.HTTP_202_ACCEPTED,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def start_course_generation(
        tenant_id: UUID,
        command: StartCourseGenerationV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseGenerationRunV1:
        return _run(
            service.start_generation(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                command=command,
                idempotency_key=idempotency_key,
            )
        )

    @router.get(
        "/tenants/{tenant_id}/course-generation-runs/{run_id}",
        operation_id="getCourseGeneration",
        response_model=CourseGenerationReviewPackageV1,
        responses=_problem_responses(400, 401, 403, 404, 500),
    )
    def get_course_generation(
        tenant_id: UUID,
        run_id: UUID,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseGenerationReviewPackageV1:
        return _package(
            service.get_generation(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                run_id=run_id,
            )
        )

    @router.post(
        "/tenants/{tenant_id}/course-generation-runs/{run_id}/approve-blueprint",
        operation_id="approveCourseGenerationBlueprint",
        response_model=CourseGenerationRunV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def approve_course_generation_blueprint(
        tenant_id: UUID,
        run_id: UUID,
        command: ApproveGenerationBlueprintV1,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseGenerationRunV1:
        return _run(
            service.approve_blueprint(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                run_id=run_id,
                command=command,
            )
        )

    @router.post(
        "/tenants/{tenant_id}/course-generation-runs/{run_id}/reject",
        operation_id="rejectCourseGeneration",
        response_model=CourseGenerationRunV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def reject_course_generation(
        tenant_id: UUID,
        run_id: UUID,
        command: RejectCourseGenerationV1,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> CourseGenerationRunV1:
        return _run(
            service.reject_generation(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                run_id=run_id,
                command=command,
            )
        )

    return router

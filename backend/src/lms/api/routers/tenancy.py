from collections.abc import Callable, Coroutine
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.schemas.tenancy import (
    AcceptInvitationRequest,
    AuthenticationContextResponse,
    AuthenticationContextServiceResult,
    AuthenticationMembershipResponse,
    AuthenticationPrincipalResponse,
    CreateInvitationRequest,
    EntitlementResponse,
    InvitationReceiptResponse,
    MembershipAdministrationError,
    MembershipAdministrationServiceV1,
    MembershipSummaryResponse,
    ProblemDetails,
    TenantCandidateResponse,
    TenantSummaryResponse,
    UpdateMembershipRequest,
    VerifiedActorResult,
)

ActorDependency = Callable[..., VerifiedActorResult]
RouteHandler = Callable[[Request], Coroutine[Any, Any, Response]]

_SAFE_SERVICE_PROBLEMS: dict[str, tuple[int, str, str]] = {
    "AUTHENTICATION_REQUIRED": (401, "Authentication required", "Authentication is required."),
    "TOKEN_INVALID": (401, "Authentication failed", "Authentication could not be verified."),
    "TENANT_CONTEXT_REQUIRED": (400, "Tenant context required", "Select a tenant."),
    "TENANT_ACCESS_DENIED": (404, "Resource unavailable", "The resource is unavailable."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access inactive", "Tenant access is inactive."),
    "INVITATION_INVALID": (404, "Invitation unavailable", "The invitation is unavailable."),
    "INVITATION_EXPIRED": (410, "Invitation unavailable", "The invitation is unavailable."),
    "IDEMPOTENCY_CONFLICT": (
        409,
        "Idempotency conflict",
        "The request conflicts with an earlier request.",
    ),
    "VERSION_CONFLICT": (
        409,
        "Version conflict",
        "The resource changed before this request completed.",
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


class ProblemDetailsRoute(APIRoute):
    """Translate adapter-safe service and validation failures in one place."""

    def get_route_handler(self) -> RouteHandler:
        original_handler = super().get_route_handler()

        async def problem_details_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except MembershipAdministrationError as problem:
                safe_problem = _SAFE_SERVICE_PROBLEMS.get(problem.code)
                if safe_problem is None:
                    return _problem_response(
                        request,
                        code="SERVICE_CONTRACT_ERROR",
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        title="Service contract error",
                        detail="The service returned an unsupported problem code.",
                    )
                status_code, title, detail = safe_problem
                return _problem_response(
                    request,
                    code=problem.code,
                    status_code=status_code,
                    title=title,
                    detail=detail,
                )
            except AuthenticationProblem as problem:
                status_code, title, detail = _SAFE_SERVICE_PROBLEMS[problem.code]
                return _problem_response(
                    request,
                    code=problem.code,
                    status_code=status_code,
                    title=title,
                    detail=detail,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except RequestValidationError as problem:
                safe_errors = [
                    {
                        "location": [str(part) for part in error["loc"]],
                        "message": error["msg"],
                        "type": error["type"],
                    }
                    for error in problem.errors()
                ]
                return _problem_response(
                    request,
                    code="REQUEST_VALIDATION_ERROR",
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    title="Request validation failed",
                    detail="The request does not conform to the API contract.",
                    errors=safe_errors,
                )
            except ResponseValidationError:
                return _problem_response(
                    request,
                    code="SERVICE_CONTRACT_ERROR",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    title="Service contract error",
                    detail="The service returned an invalid response.",
                )

        return problem_details_handler


def _require_matching_selector(*, tenant_id: UUID, header_tenant_id: UUID | None) -> UUID:
    if header_tenant_id is not None and header_tenant_id != tenant_id:
        raise MembershipAdministrationError(
            code="TENANT_ACCESS_DENIED",
            status=404,
            title="Resource unavailable",
            detail="The requested resource is unavailable.",
        )
    return tenant_id


def _membership_response(result: object) -> MembershipSummaryResponse:
    return MembershipSummaryResponse.model_validate(result, from_attributes=True)


def _invitation_response(result: object) -> InvitationReceiptResponse:
    return InvitationReceiptResponse.model_validate(result, from_attributes=True)


def _authentication_context_response(
    result: AuthenticationContextServiceResult, *, verified_actor: VerifiedActorResult
) -> AuthenticationContextResponse:
    active_tenant = result.active_tenant
    membership = result.membership
    entitlement = result.entitlement
    return AuthenticationContextResponse(
        principal=AuthenticationPrincipalResponse(
            user_id=verified_actor.principal_id,
            authentication_time=verified_actor.authentication_time,
            assurance_level=verified_actor.assurance_level,
        ),
        active_tenant=(
            TenantSummaryResponse.model_validate(active_tenant, from_attributes=True)
            if active_tenant is not None
            else None
        ),
        membership=(
            AuthenticationMembershipResponse.model_validate(
                membership,
                from_attributes=True,
            )
            if membership is not None
            else None
        ),
        entitlement=(
            EntitlementResponse.model_validate(entitlement, from_attributes=True)
            if entitlement is not None
            else None
        ),
        available_tenants=[
            TenantCandidateResponse.model_validate(candidate, from_attributes=True)
            for candidate in result.available_tenants
        ],
    )


def create_tenancy_router(
    *,
    service: MembershipAdministrationServiceV1,
    actor_dependency: ActorDependency,
) -> APIRouter:
    """Build the Lane C router without owning application composition."""

    router = APIRouter(prefix="/api/v1", route_class=ProblemDetailsRoute)
    actor = Annotated[VerifiedActorResult, Depends(actor_dependency)]
    header_selector = Annotated[UUID | None, Header(alias="X-Tenant-ID")]

    @router.get(
        "/auth-context",
        operation_id="getAuthenticationContext",
        response_model=AuthenticationContextResponse,
        responses=_problem_responses(401, 403, 404, 422, 500),
    )
    def get_authentication_context(
        verified_actor: actor,
        x_tenant_id: header_selector = None,
    ) -> AuthenticationContextResponse:
        result = cast(
            AuthenticationContextServiceResult,
            service.get_authentication_context(
                actor_id=verified_actor.principal_id,
                tenant_selector=x_tenant_id,
            ),
        )
        return _authentication_context_response(result, verified_actor=verified_actor)

    @router.get(
        "/tenants/{tenant_id}/memberships",
        operation_id="listTenantMemberships",
        response_model=list[MembershipSummaryResponse],
        responses=_problem_responses(400, 401, 403, 404, 422, 500),
    )
    def list_memberships(
        tenant_id: UUID,
        verified_actor: actor,
        x_tenant_id: header_selector = None,
    ) -> list[MembershipSummaryResponse]:
        tenant_selector = _require_matching_selector(
            tenant_id=tenant_id, header_tenant_id=x_tenant_id
        )
        return [
            _membership_response(result)
            for result in service.list_memberships(
                actor_id=verified_actor.principal_id, tenant_selector=tenant_selector
            )
        ]

    @router.post(
        "/tenants/{tenant_id}/invitations",
        operation_id="createTenantInvitation",
        status_code=status.HTTP_201_CREATED,
        response_model=InvitationReceiptResponse,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def create_invitation(
        tenant_id: UUID,
        request: CreateInvitationRequest,
        verified_actor: actor,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=16, max_length=128),
        ],
        x_tenant_id: header_selector = None,
    ) -> InvitationReceiptResponse:
        tenant_selector = _require_matching_selector(
            tenant_id=tenant_id, header_tenant_id=x_tenant_id
        )
        result = service.create_invitation(
            actor_id=verified_actor.principal_id,
            tenant_selector=tenant_selector,
            email=request.email,
            role_codes=tuple(request.role_codes),
            idempotency_key=idempotency_key,
        )
        return _invitation_response(result)

    @router.post(
        "/tenant-invitations/accept",
        operation_id="acceptTenantInvitation",
        response_model=MembershipSummaryResponse,
        responses=_problem_responses(401, 404, 410, 422, 500),
    )
    def accept_invitation(
        request: AcceptInvitationRequest,
        verified_actor: actor,
    ) -> MembershipSummaryResponse:
        result = service.accept_invitation(
            actor_id=verified_actor.principal_id,
            verified_email=verified_actor.verified_email,
            invitation_token=request.invitation_token.get_secret_value(),
        )
        return _membership_response(result)

    @router.patch(
        "/tenants/{tenant_id}/memberships/{membership_id}",
        operation_id="updateTenantMembership",
        response_model=MembershipSummaryResponse,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def update_membership(
        tenant_id: UUID,
        membership_id: UUID,
        request: UpdateMembershipRequest,
        verified_actor: actor,
        x_tenant_id: header_selector = None,
    ) -> MembershipSummaryResponse:
        tenant_selector = _require_matching_selector(
            tenant_id=tenant_id, header_tenant_id=x_tenant_id
        )
        result = service.update_membership(
            actor_id=verified_actor.principal_id,
            tenant_selector=tenant_selector,
            membership_id=membership_id,
            status=request.status,
            role_codes=(tuple(request.role_codes) if request.role_codes is not None else None),
            row_version=request.row_version,
        )
        return _membership_response(result)

    return router

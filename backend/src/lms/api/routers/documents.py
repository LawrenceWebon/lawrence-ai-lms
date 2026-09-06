from __future__ import annotations

from collections.abc import Callable, Coroutine, Sequence
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from lms.api.dependencies.authentication import AuthenticationProblem
from lms.api.schemas.documents import (
    CancelSourceAdmissionV1,
    CreateSourceAdmissionV1,
    DocumentIngestionRunV1,
    RequestedSourceOperation,
    ReviewSourceOperationAuthorizationV1,
    ReviewSourceStoreAuthorizationV1,
    SourceAdmissionContractError,
    SourceAdmissionServiceV1,
    SourceAdmissionV1,
    SourceOperationAuthorizationV1,
    UploadIntentV1,
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
_MAX_UPLOAD_READ_BYTES = 6_291_457
_SAFE_LOCATION_PARTS = frozenset(
    {
        "body",
        "path",
        "header",
        "tenant_id",
        "source_document_id",
        "source_version_id",
        "authorization_id",
        "operation",
        "run_id",
        "display_name",
        "declared_filename",
        "rights_declaration",
        "basis",
        "attestation_version",
        "attested",
        "rights_holder_name",
        "evidence_reference",
        "valid_until",
        "decision",
        "expected_authorization_row_version",
        "decision_code",
        "expected_source_version_row_version",
        "reason_code",
        "idempotency_key",
    }
)
_SAFE_PROBLEMS: dict[str, tuple[int, str, str]] = {
    "AUTHENTICATION_REQUIRED": (401, "Authentication required", "Authentication is required."),
    "TENANT_CONTEXT_REQUIRED": (400, "Tenant context required", "Select a tenant."),
    "RESOURCE_NOT_FOUND": (404, "Resource unavailable", "The resource is unavailable."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access inactive", "Tenant access is inactive."),
    "SOURCE_PERMISSION_DENIED": (
        403,
        "Source action unavailable",
        "The requested source action is unavailable.",
    ),
    "SOURCE_RIGHTS_AUTHORIZATION_REQUIRED": (
        403,
        "Source rights required",
        "Active source rights are required.",
    ),
    "SOURCE_RIGHTS_AUTHORIZATION_DENIED": (
        403,
        "Source rights denied",
        "Source rights were denied.",
    ),
    "SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED": (
        403,
        "Separate reviewer required",
        "A separate source-rights reviewer is required.",
    ),
    "SOURCE_OPERATION_AUTHORIZATION_REQUIRED": (
        403,
        "Operation rights required",
        "Active operation rights are required.",
    ),
    "SOURCE_OPERATION_AUTHORIZATION_INACTIVE": (
        403,
        "Operation rights inactive",
        "Operation rights are inactive.",
    ),
    "INGESTION_RESOURCE_NOT_FOUND": (
        404,
        "Ingestion unavailable",
        "The ingestion resource is unavailable.",
    ),
    "INGESTION_STATE_CONFLICT": (
        409,
        "Ingestion state conflict",
        "The ingestion state changed.",
    ),
    "INGESTION_LEASE_CONFLICT": (
        409,
        "Ingestion lease conflict",
        "The ingestion lease is unavailable.",
    ),
    "INGESTION_RETRY_EXHAUSTED": (
        409,
        "Ingestion retry exhausted",
        "The ingestion retry budget is exhausted.",
    ),
    "EXTRACTION_PARSER_FAILED": (
        422,
        "Extraction failed",
        "The admitted PDF could not be extracted.",
    ),
    "OCR_REQUIRED": (422, "OCR required", "The admitted PDF requires OCR."),
    "OCR_ADAPTER_UNAVAILABLE": (
        503,
        "OCR unavailable",
        "The OCR adapter is unavailable.",
    ),
    "DOCUMENT_QUALITY_INSUFFICIENT": (
        422,
        "Document quality insufficient",
        "The normalized document is insufficient.",
    ),
    "UPLOAD_INTENT_EXPIRED": (410, "Upload target expired", "The upload target expired."),
    "UPLOAD_QUOTA_EXCEEDED": (
        429,
        "Upload quota reached",
        "The local upload quota was reached.",
    ),
    "SOURCE_ADMISSION_STATE_CONFLICT": (
        409,
        "Admission state conflict",
        "The source admission state changed.",
    ),
    "SOURCE_ADMISSION_VERSION_CONFLICT": (
        409,
        "Source version conflict",
        "The source version changed.",
    ),
    "IDEMPOTENCY_CONFLICT": (
        409,
        "Idempotency conflict",
        "The request conflicts with an earlier request.",
    ),
    "SOURCE_ADMISSION_REJECTED": (
        422,
        "Source rejected",
        "The PDF was rejected by admission validation.",
    ),
    "SOURCE_ADMISSION_VALIDATION_FAILED": (
        422,
        "Source request invalid",
        "The request does not conform to the source-admission contract.",
    ),
    "SOURCE_ADMISSION_VALIDATION_UNAVAILABLE": (
        503,
        "Source validation unavailable",
        "PDF validation is temporarily unavailable.",
    ),
    "SERVICE_CONTRACT_ERROR": (
        500,
        "Service contract error",
        "The source service returned an invalid response.",
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


def _problem_response(
    request: Request,
    *,
    code: str,
    errors: list[dict[str, object]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    status_code, title, detail = _SAFE_PROBLEMS.get(
        code,
        _SAFE_PROBLEMS["SERVICE_CONTRACT_ERROR"],
    )
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


def _missing_tenant_header(problem: RequestValidationError) -> bool:
    return any(
        tuple(error.get("loc", ())) == ("header", "X-Tenant-ID")
        or tuple(str(part).casefold() for part in error.get("loc", ())) == ("header", "x-tenant-id")
        for error in problem.errors()
    )


class SourceAdmissionProblemDetailsRoute(APIRoute):
    """Translate bounded source failures without reflecting private input."""

    def get_route_handler(self) -> RouteHandler:
        original_handler = super().get_route_handler()

        async def problem_details_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except SourceAdmissionContractError as problem:
                errors = (
                    _validation_errors(problem.errors)
                    if problem.code == "SOURCE_ADMISSION_VALIDATION_FAILED"
                    else []
                )
                return _problem_response(request, code=problem.code, errors=errors)
            except AuthenticationProblem:
                return _problem_response(
                    request,
                    code="AUTHENTICATION_REQUIRED",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except RequestValidationError as problem:
                code = (
                    "TENANT_CONTEXT_REQUIRED"
                    if _missing_tenant_header(problem)
                    else "SOURCE_ADMISSION_VALIDATION_FAILED"
                )
                return _problem_response(
                    request,
                    code=code,
                    errors=[]
                    if code == "TENANT_CONTEXT_REQUIRED"
                    else _validation_errors(problem.errors()),
                )
            except ResponseValidationError, ValidationError:
                return _problem_response(request, code="SERVICE_CONTRACT_ERROR")

        return problem_details_handler


def _tenant(tenant_id: UUID, header_tenant_id: UUID) -> UUID:
    if tenant_id != header_tenant_id:
        raise SourceAdmissionContractError(code="RESOURCE_NOT_FOUND")
    return tenant_id


def _snapshot(result: object) -> SourceAdmissionV1:
    return SourceAdmissionV1.model_validate(result, from_attributes=True)


def _operation_authorization(result: object) -> SourceOperationAuthorizationV1:
    return SourceOperationAuthorizationV1.model_validate(result, from_attributes=True)


def _ingestion_run(result: object) -> DocumentIngestionRunV1:
    return DocumentIngestionRunV1.model_validate(result, from_attributes=True)


async def _bounded_upload_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        remaining = _MAX_UPLOAD_READ_BYTES - len(body)
        if remaining <= 0:
            break
        body.extend(chunk[:remaining])
        if len(body) >= _MAX_UPLOAD_READ_BYTES:
            break
    return bytes(body)


def create_document_router(
    *,
    service: SourceAdmissionServiceV1,
    actor_dependency: ActorDependency,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", route_class=SourceAdmissionProblemDetailsRoute)
    actor_requirement = Depends(actor_dependency)

    @router.post(
        "/tenants/{tenant_id}/source-documents/admissions",
        operation_id="createSourceAdmission",
        response_model=SourceAdmissionV1,
        status_code=status.HTTP_201_CREATED,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def create_source_admission(
        tenant_id: UUID,
        command: CreateSourceAdmissionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> SourceAdmissionV1:
        return _snapshot(
            service.create_admission(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                command=command,
                idempotency_key=idempotency_key,
            )
        )

    @router.post(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/rights-authorizations/{authorization_id}/decisions",
        operation_id="reviewSourceStoreAuthorization",
        response_model=SourceAdmissionV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def review_source_store_authorization(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        authorization_id: UUID,
        command: ReviewSourceStoreAuthorizationV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> SourceAdmissionV1:
        return _snapshot(
            service.review_authorization(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                authorization_id=authorization_id,
                command=command,
                idempotency_key=idempotency_key,
            )
        )

    @router.post(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/upload-intents",
        operation_id="createSourceUploadIntent",
        response_model=UploadIntentV1,
        status_code=status.HTTP_201_CREATED,
        responses=_problem_responses(400, 401, 403, 404, 409, 429, 500),
    )
    def create_source_upload_intent(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> UploadIntentV1:
        result = service.create_upload_intent(
            actor_id=verified_actor.principal_id,
            tenant_id=_tenant(tenant_id, x_tenant_id),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
            idempotency_key=idempotency_key,
        )
        return UploadIntentV1.model_validate(result, from_attributes=True)

    @router.put(
        "/source-upload-targets/{opaque_token}",
        operation_id="uploadSourceDocument",
        response_model=SourceAdmissionV1,
        status_code=status.HTTP_202_ACCEPTED,
        responses=_problem_responses(404, 409, 410, 422, 503, 500),
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
            }
        },
    )
    async def upload_source_document(opaque_token: str, request: Request) -> SourceAdmissionV1:
        body = await _bounded_upload_body(request)
        return _snapshot(
            await run_in_threadpool(
                service.upload_to_intent,
                opaque_token=opaque_token,
                content_type=request.headers.get("content-type", ""),
                body=body,
            )
        )

    @router.get(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}",
        operation_id="getSourceAdmission",
        response_model=SourceAdmissionV1,
        responses=_problem_responses(400, 401, 403, 404, 500),
    )
    def get_source_admission(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> SourceAdmissionV1:
        return _snapshot(
            service.get_admission(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                source_document_id=source_document_id,
                source_version_id=source_version_id,
            )
        )

    @router.post(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/cancel",
        operation_id="cancelSourceAdmission",
        response_model=SourceAdmissionV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def cancel_source_admission(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        command: CancelSourceAdmissionV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> SourceAdmissionV1:
        return _snapshot(
            service.cancel_admission(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                command=command,
                idempotency_key=idempotency_key,
            )
        )

    @router.get(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/authorizations",
        operation_id="listSourceOperationAuthorizations",
        response_model=list[SourceOperationAuthorizationV1],
        responses=_problem_responses(400, 401, 403, 404, 500),
    )
    def list_source_operation_authorizations(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> list[SourceOperationAuthorizationV1]:
        result = service.list_operation_authorizations(
            actor_id=verified_actor.principal_id,
            tenant_id=_tenant(tenant_id, x_tenant_id),
            source_document_id=source_document_id,
            source_version_id=source_version_id,
        )
        if not isinstance(result, Sequence):
            raise SourceAdmissionContractError(code="SERVICE_CONTRACT_ERROR")
        return [_operation_authorization(item) for item in result]

    @router.post(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/authorizations/{operation}",
        operation_id="requestSourceOperationAuthorization",
        response_model=SourceOperationAuthorizationV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def request_source_operation_authorization(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> SourceOperationAuthorizationV1:
        return _operation_authorization(
            service.request_operation_authorization(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                operation=operation,
                idempotency_key=idempotency_key,
            )
        )

    @router.post(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/authorizations/{operation}/review",
        operation_id="reviewSourceOperationAuthorization",
        response_model=SourceOperationAuthorizationV1,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def review_source_operation_authorization(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        operation: RequestedSourceOperation,
        command: ReviewSourceOperationAuthorizationV1,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> SourceOperationAuthorizationV1:
        return _operation_authorization(
            service.review_operation_authorization(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                operation=operation,
                command=command,
                idempotency_key=idempotency_key,
            )
        )

    @router.post(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/ingestion-runs",
        operation_id="startDocumentIngestion",
        response_model=DocumentIngestionRunV1,
        status_code=status.HTTP_202_ACCEPTED,
        responses=_problem_responses(400, 401, 403, 404, 409, 422, 500),
    )
    def start_document_ingestion(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        idempotency_key: IdempotencyHeader,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> DocumentIngestionRunV1:
        return _ingestion_run(
            service.start_ingestion(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                idempotency_key=idempotency_key,
            )
        )

    @router.get(
        "/tenants/{tenant_id}/source-documents/{source_document_id}/versions/"
        "{source_version_id}/ingestion-runs/{run_id}",
        operation_id="getDocumentIngestion",
        response_model=DocumentIngestionRunV1,
        responses=_problem_responses(400, 401, 403, 404, 500),
    )
    def get_document_ingestion(
        tenant_id: UUID,
        source_document_id: UUID,
        source_version_id: UUID,
        run_id: UUID,
        x_tenant_id: TenantHeader,
        verified_actor: VerifiedActorResult = actor_requirement,
    ) -> DocumentIngestionRunV1:
        return _ingestion_run(
            service.get_ingestion(
                actor_id=verified_actor.principal_id,
                tenant_id=_tenant(tenant_id, x_tenant_id),
                source_document_id=source_document_id,
                source_version_id=source_version_id,
                run_id=run_id,
            )
        )

    return router

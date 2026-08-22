from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldError:
    path: str
    code: str


_PROBLEMS: dict[str, tuple[int, str]] = {
    "AUTHENTICATION_REQUIRED": (401, "Authentication is required."),
    "TENANT_CONTEXT_REQUIRED": (400, "An active tenant context is required."),
    "RESOURCE_NOT_FOUND": (404, "The requested resource was not found."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access is inactive."),
    "SOURCE_PERMISSION_DENIED": (403, "The source action is unavailable."),
    "SOURCE_RIGHTS_AUTHORIZATION_REQUIRED": (403, "Active source rights are required."),
    "SOURCE_RIGHTS_AUTHORIZATION_DENIED": (403, "Source rights were denied."),
    "SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED": (
        403,
        "A separate source-rights reviewer is required.",
    ),
    "SOURCE_ADMISSION_REJECTED": (422, "The PDF was rejected by admission validation."),
    "SOURCE_ADMISSION_VALIDATION_UNAVAILABLE": (503, "PDF validation is unavailable."),
    "UPLOAD_INTENT_EXPIRED": (410, "The upload target expired."),
    "UPLOAD_QUOTA_EXCEEDED": (429, "The local upload quota was reached."),
    "SOURCE_ADMISSION_STATE_CONFLICT": (409, "The source admission state changed."),
    "SOURCE_ADMISSION_VERSION_CONFLICT": (409, "The source version changed."),
    "IDEMPOTENCY_CONFLICT": (409, "The idempotency key was used for another request."),
    "SOURCE_ADMISSION_VALIDATION_FAILED": (422, "The source request is invalid."),
    "SERVICE_CONTRACT_ERROR": (500, "The source service contract could not be satisfied."),
}


class SourceAdmissionError(Exception):
    """Bounded application error safe for HTTP and trusted Admin adapters."""

    def __init__(
        self,
        code: str,
        *,
        field_errors: tuple[FieldError, ...] = (),
    ) -> None:
        status, detail = _PROBLEMS.get(code, _PROBLEMS["SERVICE_CONTRACT_ERROR"])
        self.code = code if code in _PROBLEMS else "SERVICE_CONTRACT_ERROR"
        self.status = status
        self.detail = detail
        self.field_errors = field_errors[:100]
        super().__init__(f"{self.code}: {self.detail}")

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldError:
    path: str
    code: str


_PROBLEMS: dict[str, tuple[int, str]] = {
    "GENERATION_RESOURCE_NOT_FOUND": (404, "The generation resource was not found."),
    "GENERATION_PERMISSION_DENIED": (403, "The generation action is unavailable."),
    "GENERATION_RIGHTS_REQUIRED": (403, "Active generation rights are required."),
    "GENERATION_RIGHTS_INACTIVE": (403, "Generation rights are inactive."),
    "GENERATION_VALIDATION_FAILED": (422, "The generation request is invalid."),
    "GENERATION_SOURCE_INVALID": (422, "The normalized source is invalid."),
    "GENERATION_SOURCE_EDGE_INVALID": (422, "A generated source edge is invalid."),
    "GENERATION_OUTPUT_INVALID": (422, "The generated output is invalid."),
    "GENERATION_STATE_CONFLICT": (409, "The generation state changed."),
    "GENERATION_VERSION_CONFLICT": (409, "The generation revision changed."),
    "GENERATION_LEASE_CONFLICT": (409, "The generation lease is unavailable."),
    "GENERATION_RETRY_EXHAUSTED": (409, "The generation retry budget is exhausted."),
    "IDEMPOTENCY_CONFLICT": (409, "The idempotency key was used for another request."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access is inactive."),
    "SERVICE_CONTRACT_ERROR": (500, "The generation service contract failed."),
}


class CourseGenerationError(Exception):
    def __init__(self, code: str, *, field_errors: tuple[FieldError, ...] = ()) -> None:
        status, detail = _PROBLEMS.get(code, _PROBLEMS["SERVICE_CONTRACT_ERROR"])
        self.code = code if code in _PROBLEMS else "SERVICE_CONTRACT_ERROR"
        self.status = status
        self.detail = detail
        self.field_errors = field_errors[:100]
        super().__init__(f"{self.code}: {self.detail}")

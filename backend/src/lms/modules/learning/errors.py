from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldError:
    path: str
    code: str
    detail: str


_PROBLEMS: dict[str, tuple[int, str]] = {
    "AUTHENTICATION_REQUIRED": (401, "Authentication is required."),
    "TENANT_CONTEXT_REQUIRED": (400, "An active tenant context is required."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access is inactive."),
    "LEARNING_RESOURCE_NOT_FOUND": (404, "The learning resource is unavailable."),
    "ENROLLMENT_VALIDATION_FAILED": (422, "Enrollment validation failed."),
    "PROGRESS_VERSION_CONFLICT": (409, "Learner progress changed before this command."),
    "IDEMPOTENCY_CONFLICT": (409, "The idempotency key was used for another request."),
    "SERVICE_CONTRACT_ERROR": (500, "The learning service contract could not be satisfied."),
}


class LearningError(Exception):
    """Bounded learning-domain failure safe for transport translation."""

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


def validation_failed(*errors: FieldError) -> LearningError:
    bounded = tuple(errors[:100]) or (
        FieldError(path="$", code="invalid", detail="The learning request is invalid."),
    )
    return LearningError("ENROLLMENT_VALIDATION_FAILED", field_errors=bounded)

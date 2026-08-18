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
    "RESOURCE_NOT_FOUND": (404, "The requested resource was not found."),
    "TENANT_ACCESS_INACTIVE": (403, "Tenant access is inactive."),
    "COURSE_PERMISSION_DENIED": (403, "Course access is denied."),
    "COURSE_VALIDATION_FAILED": (422, "Course validation failed."),
    "VERSION_CONFLICT": (409, "The course changed before this command completed."),
    "CONTENT_HASH_MISMATCH": (409, "The course content no longer matches the expected hash."),
    "COURSE_VERSION_IMMUTABLE": (409, "This course version is immutable."),
    "REVIEWER_SEPARATION_REQUIRED": (403, "A separate reviewer is required."),
    "HUMAN_ACTION_REQUIRED": (403, "This action requires an authorized human."),
    "IDEMPOTENCY_CONFLICT": (409, "The idempotency key was used for another request."),
    "SERVICE_CONTRACT_ERROR": (500, "The course service contract could not be satisfied."),
}


class CourseLifecycleError(Exception):
    """Bounded application error safe for transport adapters."""

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


def validation_failed(errors: tuple[FieldError, ...]) -> CourseLifecycleError:
    bounded = errors[:100] or (
        FieldError(path="$", code="invalid", detail="The course input is invalid."),
    )
    return CourseLifecycleError("COURSE_VALIDATION_FAILED", field_errors=bounded)


def service_error(code: str) -> CourseLifecycleError:
    return CourseLifecycleError(code)

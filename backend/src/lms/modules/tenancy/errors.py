from __future__ import annotations


class TenancyError(Exception):
    """Stable application error consumed by the HTTP/Admin adapters."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail or code
        super().__init__(f"{code}: {self.detail}")


def denied(detail: str = "Tenant access is denied.") -> TenancyError:
    return TenancyError("TENANT_ACCESS_DENIED", detail)

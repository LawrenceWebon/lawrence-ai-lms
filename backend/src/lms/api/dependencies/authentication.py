from __future__ import annotations

from typing import Annotated, Protocol

from fastapi import Header, HTTPException

from lms.modules.identity.entities import IdentityCandidate
from lms.modules.identity.services import IdentityAuthenticationRejectedError

AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]


class IdentityAuthenticator(Protocol):
    def authenticate(self, *, token: str) -> IdentityCandidate: ...


class AuthenticationProblem(HTTPException):
    def __init__(self, *, code: str) -> None:
        self.code = code
        super().__init__(
            status_code=401,
            detail={
                "code": code,
                "title": "Authentication required",
                "status": 401,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthenticationDependency:
    """Extract a bearer token and return identity data without tenant authority."""

    def __init__(self, identity_service: IdentityAuthenticator) -> None:
        self._identity_service = identity_service

    def __call__(self, authorization: AuthorizationHeader = None) -> IdentityCandidate:
        if authorization is None:
            raise AuthenticationProblem(code="AUTHENTICATION_REQUIRED")
        scheme, separator, token = authorization.partition(" ")
        if (
            not separator
            or scheme.casefold() != "bearer"
            or not token
            or token != token.strip()
            or any(character.isspace() for character in token)
        ):
            raise AuthenticationProblem(code="AUTHENTICATION_REQUIRED")
        try:
            return self._identity_service.authenticate(token=token)
        except IdentityAuthenticationRejectedError as error:
            raise AuthenticationProblem(code="TOKEN_INVALID") from error

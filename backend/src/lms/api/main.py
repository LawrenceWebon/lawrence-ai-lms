from __future__ import annotations

from typing import TypedDict

import django
from django.apps import apps
from fastapi import FastAPI

from lms.api.dependencies.authentication import AuthenticationDependency, IdentityAuthenticator
from lms.api.routers.courses import create_course_router
from lms.api.routers.tenancy import create_tenancy_router
from lms.api.schemas.courses import CourseAdministrationServiceV1
from lms.api.schemas.tenancy import MembershipAdministrationServiceV1
from lms.modules.identity.entities import IdentityCandidate
from lms.modules.identity.services import IdentityAuthenticationRejectedError

if not apps.ready:
    django.setup()

from lms.api.composition import DjangoCourseAdministrationService, DjangoTenancyService


class HealthResponse(TypedDict):
    service: str
    status: str
    capabilities: list[str]


class FailClosedIdentityAuthenticator:
    """Production-safe placeholder until an approved provider adapter is configured."""

    def authenticate(self, *, token: str) -> IdentityCandidate:
        del token
        raise IdentityAuthenticationRejectedError


def create_application(
    *,
    identity_authenticator: IdentityAuthenticator,
    tenancy_service: MembershipAdministrationServiceV1,
    course_service: CourseAdministrationServiceV1,
) -> FastAPI:
    application = FastAPI(
        title="AI LMS API",
        version="0.1.0",
        openapi_version="3.1.0",
        docs_url=None,
        redoc_url=None,
    )

    @application.get("/health", operation_id="healthCheck", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        return {
            "service": "ai-lms-api",
            "status": "ok",
            "capabilities": ["f001-identity-tenancy", "f002-course-lifecycle"],
        }

    application.include_router(
        create_tenancy_router(
            service=tenancy_service,
            actor_dependency=AuthenticationDependency(identity_authenticator),
        )
    )
    application.include_router(
        create_course_router(
            service=course_service,
            actor_dependency=AuthenticationDependency(identity_authenticator),
        )
    )
    return application


app = create_application(
    identity_authenticator=FailClosedIdentityAuthenticator(),
    tenancy_service=DjangoTenancyService(),
    course_service=DjangoCourseAdministrationService(),
)

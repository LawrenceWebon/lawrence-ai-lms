from __future__ import annotations

from typing import TypedDict

import django
from django.apps import apps
from fastapi import FastAPI

from lms.api.dependencies.authentication import AuthenticationDependency, IdentityAuthenticator
from lms.api.routers.courses import create_course_router
from lms.api.routers.documents import create_document_router
from lms.api.routers.learning import create_learning_router
from lms.api.routers.tenancy import create_tenancy_router
from lms.api.schemas.courses import CourseAdministrationServiceV1
from lms.api.schemas.documents import SourceAdmissionServiceV1
from lms.api.schemas.learning import LearningServiceV1
from lms.api.schemas.tenancy import MembershipAdministrationServiceV1
from lms.modules.identity.entities import IdentityCandidate
from lms.modules.identity.services import IdentityAuthenticationRejectedError

if not apps.ready:
    django.setup()

from lms.api.composition import DjangoCourseAdministrationService, DjangoTenancyService
from lms.api.document_composition import DjangoSourceAdmissionService
from lms.api.learning_composition import DjangoLearningService


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
    document_service: SourceAdmissionServiceV1 | None = None,
    learning_service: LearningServiceV1 | None = None,
) -> FastAPI:
    capabilities = ["f001-identity-tenancy", "f002-course-lifecycle"]
    if document_service is not None:
        capabilities.append("f003-pdf-source-admission")
    if learning_service is not None:
        capabilities.append("f007-private-learner-playback")
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
            "capabilities": capabilities,
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
    if document_service is not None:
        application.include_router(
            create_document_router(
                service=document_service,
                actor_dependency=AuthenticationDependency(identity_authenticator),
            )
        )
    if learning_service is not None:
        application.include_router(
            create_learning_router(
                service=learning_service,
                actor_dependency=AuthenticationDependency(identity_authenticator),
            )
        )
    return application


app = create_application(
    identity_authenticator=FailClosedIdentityAuthenticator(),
    tenancy_service=DjangoTenancyService(),
    course_service=DjangoCourseAdministrationService(),
    document_service=DjangoSourceAdmissionService(),
    learning_service=DjangoLearningService(),
)

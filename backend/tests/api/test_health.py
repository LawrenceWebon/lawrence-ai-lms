import asyncio

import httpx

from lms.api.main import app


def test_health_endpoint_reports_f001_integration_readiness() -> None:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request())

    assert response.status_code == 200
    assert response.json() == {
        "service": "ai-lms-api",
        "status": "ok",
        "capabilities": [
            "f001-identity-tenancy",
            "f002-course-lifecycle",
            "f003-pdf-source-admission",
            "f007-private-learner-playback",
        ],
    }


def test_openapi_is_31_and_contains_f001_business_routes() -> None:
    schema = app.openapi()

    assert schema["openapi"].startswith("3.1.")
    assert "/api/v1/auth-context" in schema["paths"]
    assert "/api/v1/tenant-invitations/accept" in schema["paths"]
    assert "/api/v1/source-upload-targets/{opaque_token}" in schema["paths"]
    assert schema["paths"]["/health"]["get"]["operationId"] == "healthCheck"

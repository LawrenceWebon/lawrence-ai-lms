import asyncio

import httpx

from lms.api.main import app


def test_health_endpoint_reports_only_foundation_readiness() -> None:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request())

    assert response.status_code == 200
    assert response.json() == {
        "service": "ai-lms-api",
        "status": "ok",
        "capabilities": [],
    }


def test_openapi_is_31_and_contains_no_f001_business_routes() -> None:
    schema = app.openapi()

    assert schema["openapi"].startswith("3.1.")
    assert schema["paths"] == {"/health": schema["paths"]["/health"]}
    assert schema["paths"]["/health"]["get"]["operationId"] == "healthCheck"

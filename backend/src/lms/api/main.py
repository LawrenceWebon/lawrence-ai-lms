from __future__ import annotations

from typing import TypedDict

from fastapi import FastAPI


class HealthResponse(TypedDict):
    service: str
    status: str
    capabilities: list[str]


app = FastAPI(
    title="AI LMS API",
    version="0.0.0",
    openapi_version="3.1.0",
    docs_url=None,
    redoc_url=None,
)


@app.get("/health", operation_id="healthCheck", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return {
        "service": "ai-lms-api",
        "status": "ok",
        "capabilities": [],
    }

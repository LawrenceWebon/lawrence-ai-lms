from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

from lms.adapters.admin.course_generation import (
    COURSE_GENERATION_READONLY_FIELDS,
    CourseGenerationAdminActions,
)
from lms.adapters.admin.documents import AdminActorContext
from lms.api.routers.course_generation import create_course_generation_router
from lms.api.schemas.course_generation import (
    ApproveGenerationBlueprintV1,
    CanonicalizeCourseGenerationV1,
    GenerationContractError,
    RejectCourseGenerationV1,
    StartCourseGenerationV1,
)

TENANT_ID = UUID("00000000-0000-4000-8000-0000000000a1")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000102")
RUN_ID = UUID("00000000-0000-4000-8000-0000000005a1")
DOCUMENT_ID = UUID("00000000-0000-4000-8000-0000000005a2")
VERSION_ID = UUID("00000000-0000-4000-8000-0000000005a3")
INGESTION_ID = UUID("00000000-0000-4000-8000-0000000005a4")
BLUEPRINT_ID = UUID("00000000-0000-4000-8000-0000000005a5")
MODULE_ID = UUID("00000000-0000-4000-8000-0000000005a6")
LESSON_ID = UUID("00000000-0000-4000-8000-0000000005a7")
SECTION_ID = UUID("00000000-0000-4000-8000-0000000005a8")
CANONICALIZATION_ID = UUID("00000000-0000-4000-8000-0000000005a9")
COURSE_ID = UUID("00000000-0000-4000-8000-0000000005aa")
COURSE_VERSION_ID = UUID("00000000-0000-4000-8000-0000000005ab")
HASH = "sha256:" + "1" * 64
NOW = datetime(2026, 8, 31, tzinfo=UTC)


def _run(status: str, *, blueprint: bool, output: bool, reason: str | None = None) -> Any:
    return SimpleNamespace(
        id=RUN_ID,
        tenant_id=TENANT_ID,
        source_document_id=DOCUMENT_ID,
        source_version_id=VERSION_ID,
        ingestion_run_id=INGESTION_ID,
        supersedes_run_id=None,
        status=status,
        target_level="beginner",
        target_duration_minutes=45,
        intended_audience="Synthetic adult learners",
        teaching_style="guided",
        locale="en",
        adapter="deterministic-source-course-v1",
        provider="local_deterministic",
        model="none",
        input_manifest_sha256=HASH,
        blueprint_content_sha256=HASH if blueprint else None,
        output_manifest_sha256=HASH if output else None,
        attempt_count=2 if output else 1 if blueprint else 0,
        max_attempts=3,
        checkpoint=status,
        reason_code=reason,
        row_version=3,
        created_at=NOW,
        updated_at=NOW,
    )


def _blueprint() -> Any:
    module = SimpleNamespace(
        id=MODULE_ID,
        kind="module",
        parent_id=None,
        position=1,
        title="Synthetic module",
        description="Source-linked module",
        source_section_id=SECTION_ID,
    )
    lesson = SimpleNamespace(
        id=LESSON_ID,
        kind="lesson",
        parent_id=MODULE_ID,
        position=1,
        title="Synthetic lesson",
        description="Source-linked lesson",
        source_section_id=SECTION_ID,
    )
    return SimpleNamespace(
        id=BLUEPRINT_ID,
        schema_version="course-blueprint.v1",
        title="Synthetic course",
        description="A deterministic course",
        intended_audience="Synthetic adult learners",
        prerequisites=(),
        learning_outcomes=("Explain the synthetic source",),
        items=(module, lesson),
        projection={"schema_version": "course-blueprint.v1"},
        content_sha256=HASH,
    )


class RecordingGenerationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID, UUID]] = []

    def start_generation(self, *, actor_id: UUID, tenant_id: UUID, **_: object) -> object:
        self.calls.append(("start", actor_id, tenant_id))
        return _run("queued", blueprint=False, output=False)

    def get_generation(self, *, actor_id: UUID, tenant_id: UUID, **_: object) -> object:
        self.calls.append(("get", actor_id, tenant_id))
        return SimpleNamespace(
            run=_run("blueprint_review", blueprint=True, output=False),
            blueprint=_blueprint(),
            lessons=(),
        )

    def approve_blueprint(self, *, actor_id: UUID, tenant_id: UUID, **_: object) -> object:
        self.calls.append(("approve", actor_id, tenant_id))
        return _run("generation_queued", blueprint=True, output=False)

    def reject_generation(self, *, actor_id: UUID, tenant_id: UUID, **_: object) -> object:
        self.calls.append(("reject", actor_id, tenant_id))
        return _run(
            "rejected",
            blueprint=True,
            output=False,
            reason="GENERATION_CONTENT_REJECTED",
        )

    def canonicalize_generation(self, *, actor_id: UUID, tenant_id: UUID, **_: object) -> object:
        self.calls.append(("canonicalize", actor_id, tenant_id))
        return SimpleNamespace(
            id=CANONICALIZATION_ID,
            tenant_id=tenant_id,
            generation_run_id=RUN_ID,
            course_id=COURSE_ID,
            course_version_id=COURSE_VERSION_ID,
            reviewed_output_sha256=HASH,
            canonical_content_sha256=HASH,
            canonicalization_sha256=HASH,
            canonicalized_by_actor_id=actor_id,
            created_at=NOW,
        )


def _start_request() -> dict[str, object]:
    return {
        "source_document_id": str(DOCUMENT_ID),
        "source_version_id": str(VERSION_ID),
        "ingestion_run_id": str(INGESTION_ID),
        "target_level": "beginner",
        "target_duration_minutes": 45,
        "intended_audience": "Synthetic adult learners",
        "teaching_style": "guided",
        "locale": "en",
        "supersedes_run_id": None,
    }


def _send(
    app: object,
    method: str,
    path: str,
    *,
    tenant_id: UUID = TENANT_ID,
    body: object | None = None,
    idempotency: bool = False,
) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        headers = {"X-Tenant-ID": str(tenant_id)}
        if idempotency:
            headers["Idempotency-Key"] = "generation-contract-idempotency-0001"
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, headers=headers, json=body)

    return asyncio.run(request())


def _app(service: RecordingGenerationService) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_course_generation_router(
            service=service,
            actor_dependency=lambda: SimpleNamespace(principal_id=ACTOR_ID),
        )
    )
    return app


def test_generation_http_contract_delegates_all_human_actions_and_is_tenant_bound() -> None:
    service = RecordingGenerationService()
    app = _app(service)
    base = f"/api/v1/tenants/{TENANT_ID}/course-generation-runs"

    started = _send(app, "POST", base, body=_start_request(), idempotency=True)
    reviewed = _send(app, "GET", f"{base}/{RUN_ID}")
    approved = _send(
        app,
        "POST",
        f"{base}/{RUN_ID}/approve-blueprint",
        body={
            "expected_run_row_version": 3,
            "blueprint_id": str(BLUEPRINT_ID),
            "blueprint_revision": 1,
            "expected_blueprint_content_sha256": HASH,
        },
        idempotency=True,
    )
    rejected = _send(
        app,
        "POST",
        f"{base}/{RUN_ID}/reject",
        body={
            "expected_run_row_version": 3,
            "expected_review_content_sha256": HASH,
            "reason_code": "GENERATION_CONTENT_REJECTED",
        },
        idempotency=True,
    )
    canonicalized = _send(
        app,
        "POST",
        f"{base}/{RUN_ID}/canonicalize",
        body={
            "expected_run_row_version": 3,
            "expected_output_manifest_sha256": HASH,
            "course_slug": "synthetic-course",
        },
        idempotency=True,
    )

    statuses = [
        started.status_code,
        reviewed.status_code,
        approved.status_code,
        rejected.status_code,
        canonicalized.status_code,
    ]
    assert statuses == [
        202,
        200,
        200,
        200,
        201,
    ]
    assert reviewed.json()["blueprint"]["items"][1]["parent_id"] == str(MODULE_ID)
    assert [call[0] for call in service.calls] == [
        "start",
        "get",
        "approve",
        "reject",
        "canonicalize",
    ]
    assert all(call[1:] == (ACTOR_ID, TENANT_ID) for call in service.calls)

    mismatched = _send(
        app,
        "POST",
        base,
        tenant_id=UUID("00000000-0000-4000-8000-0000000000b1"),
        body=_start_request(),
        idempotency=True,
    )
    assert mismatched.status_code == 404
    assert mismatched.json()["code"] == "GENERATION_RESOURCE_NOT_FOUND"
    assert len(service.calls) == 5


def test_generation_admin_delegates_without_an_orm_escape_hatch() -> None:
    service = RecordingGenerationService()
    actions = CourseGenerationAdminActions(service=service)
    context = AdminActorContext(actor_id=ACTOR_ID, tenant_id=TENANT_ID)
    request = StartCourseGenerationV1.model_validate(_start_request())

    actions.start_generation(
        context=context,
        request=request,
        idempotency_key="generation-admin-idempotency-0001",
    )
    actions.get_generation(context=context, run_id=RUN_ID)
    actions.approve_blueprint(
        context=context,
        run_id=RUN_ID,
        request=ApproveGenerationBlueprintV1(
            expected_run_row_version=3,
            blueprint_id=BLUEPRINT_ID,
            blueprint_revision=1,
            expected_blueprint_content_sha256=HASH,
        ),
        idempotency_key="generation-admin-approve-0001",
    )
    actions.reject_generation(
        context=context,
        run_id=RUN_ID,
        request=RejectCourseGenerationV1(
            expected_run_row_version=3,
            expected_review_content_sha256=HASH,
            reason_code="GENERATION_CONTENT_REJECTED",
        ),
        idempotency_key="generation-admin-reject-0001",
    )
    actions.canonicalize_generation(
        context=context,
        run_id=RUN_ID,
        request=CanonicalizeCourseGenerationV1(
            expected_run_row_version=3,
            expected_output_manifest_sha256=HASH,
            course_slug="synthetic-course",
        ),
        idempotency_key="generation-admin-canonicalize-0001",
    )

    assert [call[0] for call in service.calls] == [
        "start",
        "get",
        "approve",
        "reject",
        "canonicalize",
    ]
    assert {"status", "provider", "model", "source_edges", "row_version"} <= (
        COURSE_GENERATION_READONLY_FIELDS
    )
    with pytest.raises(GenerationContractError) as missing:
        actions.start_generation(
            context=AdminActorContext(actor_id=ACTOR_ID, tenant_id=None),
            request=request,
            idempotency_key="generation-admin-idempotency-0002",
        )
    assert missing.value.code == "TENANT_CONTEXT_REQUIRED"

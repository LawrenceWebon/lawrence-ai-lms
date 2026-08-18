from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest
from django.db import connection, transaction

from lms.adapters.admin.courses import AdminActorContext, CourseAdminActions
from lms.api.composition import DjangoCourseAdministrationService, DjangoTenancyService
from lms.api.main import create_application
from lms.api.schemas.courses import CreateCourseV1
from lms.modules.identity.entities import IdentityCandidate
from lms.modules.tenancy.models import AuditFact, OutboxFact
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

ALPHA_ID = UUID("00000000-0000-4000-8000-0000000000a1")
BETA_ID = UUID("00000000-0000-4000-8000-0000000000b1")
SESSION_ID = UUID("10000000-0000-4000-8000-000000000031")


class FixtureIdentityAuthenticator:
    def __init__(self, subjects: dict[str, UUID]) -> None:
        self._subjects = subjects

    def authenticate(self, *, token: str) -> IdentityCandidate:
        subject = self._subjects[token]
        return IdentityCandidate(
            principal_id=subject,
            profile_id=subject,
            session_id=SESSION_ID,
            authentication_time=datetime(2026, 8, 18, tzinfo=UTC),
            assurance_level="aal1",
            verified_email=f"{token}@example.invalid",
        )


def send(
    app: object,
    method: str,
    path: str,
    *,
    actor_key: str = "instructor",
    tenant_id: UUID = ALPHA_ID,
    body: dict[str, object] | None = None,
    idempotency_key: str | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {actor_key}",
            "X-Tenant-ID": str(tenant_id),
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, headers=headers, json=body)

    return asyncio.run(request())


def transition(snapshot: dict[str, Any], name: str) -> dict[str, object]:
    body: dict[str, object] = {
        "transition": name,
        "expected_version_row_version": snapshot["version"]["row_version"],
        "expected_content_hash": snapshot["version"]["content_hash"],
    }
    if name == "publish":
        body["expected_course_row_version"] = snapshot["course"]["row_version"]
    return body


@pytest.mark.django_db(transaction=True)
def test_real_composition_publishes_one_immutable_version_and_creates_a_successor(
    tenancy_seed: dict[str, Any],
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    outsider = tenancy_seed["profiles"]["outsider"].provider_subject
    service = DjangoCourseAdministrationService()
    app = create_application(
        identity_authenticator=FixtureIdentityAuthenticator(
            {"instructor": instructor, "outsider": outsider}
        ),
        tenancy_service=DjangoTenancyService(),
        course_service=service,
    )
    collection = f"/api/v1/tenants/{ALPHA_ID}/courses"

    created_response = send(
        app,
        "POST",
        collection,
        body={
            "slug": "synthetic-integration-course",
            "primary_locale": "en",
            "title": "Synthetic integration course",
            "description": "Invented text for the F-002 integration journey.",
        },
        idempotency_key="create-course-00000031",
    )
    assert created_response.status_code == 201
    created = created_response.json()
    course_id = created["course"]["id"]
    version_id = created["version"]["id"]
    version_path = f"{collection}/{course_id}/versions/{version_id}"

    edited_response = send(
        app,
        "PATCH",
        version_path,
        body={
            "expected_version_row_version": created["version"]["row_version"],
            "title": "Synthetic integration course, reviewed",
        },
    )
    assert edited_response.status_code == 200
    edited = edited_response.json()
    stale_edit = send(
        app,
        "PATCH",
        version_path,
        body={
            "expected_version_row_version": created["version"]["row_version"],
            "title": "Stale title must not win",
        },
    )
    assert stale_edit.status_code == 409
    assert stale_edit.json()["code"] == "VERSION_CONFLICT"

    curriculum_response = send(
        app,
        "PUT",
        f"{version_path}/curriculum",
        body={
            "expected_version_row_version": edited["version"]["row_version"],
            "sections": [
                {
                    "title": "Safe foundations",
                    "position": 1,
                    "lessons": [
                        {
                            "title": "A deterministic lesson",
                            "position": 1,
                            "is_required": True,
                            "content_blocks": [
                                {
                                    "kind": "rich_text",
                                    "position": 1,
                                    "document": {
                                        "type": "document",
                                        "content": [
                                            {
                                                "type": "heading",
                                                "level": 2,
                                                "content": [
                                                    {
                                                        "type": "text",
                                                        "text": "Learning safely",
                                                        "marks": [],
                                                    }
                                                ],
                                            },
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {
                                                        "type": "text",
                                                        "text": (
                                                            "Only reviewed synthetic text is "
                                                            "published."
                                                        ),
                                                        "marks": ["strong"],
                                                    }
                                                ],
                                            },
                                        ],
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    )
    assert curriculum_response.status_code == 200
    draft = curriculum_response.json()

    section = draft["sections"][0]
    lesson = section["lessons"][0]
    block = lesson["content_blocks"][0]
    unchanged_curriculum = send(
        app,
        "PUT",
        f"{version_path}/curriculum",
        body={
            "expected_version_row_version": draft["version"]["row_version"],
            "sections": [
                {
                    "id": section["id"],
                    "expected_row_version": section["row_version"],
                    "title": section["title"],
                    "position": section["position"],
                    "lessons": [
                        {
                            "id": lesson["id"],
                            "expected_row_version": lesson["row_version"],
                            "title": lesson["title"],
                            "position": lesson["position"],
                            "is_required": lesson["is_required"],
                            "content_blocks": [
                                {
                                    "id": block["id"],
                                    "expected_row_version": block["row_version"],
                                    "kind": block["kind"],
                                    "position": block["position"],
                                    "document": block["document"],
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    )
    assert unchanged_curriculum.status_code == 200
    unchanged = unchanged_curriculum.json()
    assert unchanged["version"]["row_version"] == draft["version"]["row_version"] + 1
    assert unchanged["sections"][0]["row_version"] == section["row_version"]
    assert unchanged["sections"][0]["lessons"][0]["row_version"] == lesson["row_version"]
    draft = unchanged

    stale_hash_command = transition(draft, "submit_review")
    stale_hash_command["expected_content_hash"] = f"sha256:{'0' * 64}"
    stale_hash = send(
        app,
        "POST",
        f"{version_path}/submit-review",
        body=stale_hash_command,
        idempotency_key="stale-hash-course-000031",
    )
    assert stale_hash.status_code == 409
    assert stale_hash.json()["code"] == "CONTENT_HASH_MISMATCH"

    submitted_response = send(
        app,
        "POST",
        f"{version_path}/submit-review",
        body=transition(draft, "submit_review"),
        idempotency_key="submit-course-00000031",
    )
    assert submitted_response.status_code == 200
    submitted = submitted_response.json()
    assert submitted["version"]["status"] == "under_review"

    replay = send(
        app,
        "POST",
        f"{version_path}/submit-review",
        body=transition(draft, "submit_review"),
        idempotency_key="submit-course-00000031",
    )
    assert replay.status_code == 200
    assert replay.json() == submitted

    approved_response = send(
        app,
        "POST",
        f"{version_path}/approve",
        body=transition(submitted, "approve"),
        idempotency_key="approve-course-00000031",
    )
    assert approved_response.status_code == 200
    approved = approved_response.json()
    assert approved["latest_review"]["self_review"] is True

    published_response = send(
        app,
        "POST",
        f"{version_path}/publish",
        body=transition(approved, "publish"),
        idempotency_key="publish-course-00000031",
    )
    assert published_response.status_code == 200
    published = published_response.json()
    assert published["version"]["status"] == "published"
    assert published["course"]["current_published_version_id"] == version_id

    immutable = send(
        app,
        "PATCH",
        version_path,
        body={
            "expected_version_row_version": published["version"]["row_version"],
            "title": "Forbidden in-place edit",
        },
    )
    assert immutable.status_code == 409
    assert immutable.json()["code"] == "COURSE_VERSION_IMMUTABLE"

    successor_body = {
        "expected_course_row_version": published["course"]["row_version"],
        "expected_source_version_row_version": published["version"]["row_version"],
        "expected_source_content_hash": published["version"]["content_hash"],
    }
    successor_response = send(
        app,
        "POST",
        f"{version_path}/successor-draft",
        body=successor_body,
        idempotency_key="successor-course-000031",
    )
    assert successor_response.status_code == 200
    successor = successor_response.json()
    assert successor["snapshot"]["version"]["status"] == "draft"
    assert successor["snapshot"]["version"]["predecessor_version_id"] == version_id
    assert successor["snapshot"]["sections"][0]["id"] != published["sections"][0]["id"]
    successor_replay = send(
        app,
        "POST",
        f"{version_path}/successor-draft",
        body=successor_body,
        idempotency_key="successor-course-000031",
    )
    assert successor_replay.status_code == 200
    assert successor_replay.json() == successor

    history_response = send(app, "GET", f"{collection}/{course_id}/versions")
    assert history_response.status_code == 200
    history = history_response.json()
    assert [item["version_number"] for item in history["versions"]] == [2, 1]
    assert history["versions"][1]["is_current_published"] is True

    admin_history = CourseAdminActions(service=service).list_course_versions(
        context=AdminActorContext(actor_id=instructor, tenant_id=ALPHA_ID),
        course_id=UUID(course_id),
    )
    assert [item.version_number for item in admin_history.versions] == [2, 1]

    beta_denied = send(
        app,
        "GET",
        f"/api/v1/tenants/{BETA_ID}/courses/{course_id}/versions/{version_id}",
        tenant_id=BETA_ID,
    )
    outsider_denied = send(app, "GET", version_path, actor_key="outsider")
    assert beta_denied.status_code == 404
    assert outsider_denied.status_code == 404
    assert "Synthetic integration" not in beta_denied.text + outsider_denied.text

    assert (
        AuditFact.objects.filter(
            tenant_id=ALPHA_ID,
            subject_id=version_id,
        ).count()
        == 3
    )
    assert (
        OutboxFact.objects.filter(
            tenant_id=ALPHA_ID,
            aggregate_id=version_id,
        ).count()
        == 3
    )
    assert (
        AuditFact.objects.filter(tenant_id=ALPHA_ID, event_type__startswith="course.").count() == 4
    )
    assert (
        OutboxFact.objects.filter(tenant_id=ALPHA_ID, event_type__startswith="course.").count() == 4
    )
    serialized_facts = " ".join(
        str(payload)
        for payload in OutboxFact.objects.filter(tenant_id=ALPHA_ID).values_list(
            "payload", flat=True
        )
    )
    assert "Only reviewed synthetic text" not in serialized_facts


def test_openapi_composes_the_frozen_f002_operations() -> None:
    service = DjangoCourseAdministrationService()
    app = create_application(
        identity_authenticator=FixtureIdentityAuthenticator({}),
        tenancy_service=DjangoTenancyService(),
        course_service=service,
    )
    paths = app.openapi()["paths"]

    assert paths["/api/v1/tenants/{tenant_id}/courses"]["post"]["operationId"] == "createCourse"
    assert (
        paths["/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/publish"][
            "post"
        ]["operationId"]
        == "publishCourseVersion"
    )
    assert "CourseSnapshotV1" in app.openapi()["components"]["schemas"]


@pytest.mark.rls
@pytest.mark.django_db(transaction=True)
def test_real_admin_service_composition_operates_as_the_non_owner_runtime_role(
    tenancy_seed: dict[str, Any],
) -> None:
    actor_id = tenancy_seed["profiles"]["instructor"].provider_subject
    actions = CourseAdminActions(service=DjangoCourseAdministrationService())

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE lms_api_runtime")
        created = actions.create_course(
            context=AdminActorContext(actor_id=actor_id, tenant_id=ALPHA_ID),
            request=CreateCourseV1(
                slug="runtime-composed-course",
                primary_locale="en",
                title="Runtime composed course",
                description="Rights-cleared synthetic runtime-role fixture.",
            ),
            idempotency_key="runtime-composition-000031",
        )
        history = actions.list_course_versions(
            context=AdminActorContext(actor_id=actor_id, tenant_id=ALPHA_ID),
            course_id=created.course.id,
        )

    assert created.version.status == "draft"
    assert [version.id for version in history.versions] == [created.version.id]

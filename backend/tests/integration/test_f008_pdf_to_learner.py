from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from lms.api.composition import DjangoTenancyService
from lms.api.course_composition import DjangoCourseAdministrationService
from lms.api.document_composition import DjangoSourceAdmissionService
from lms.api.generation_composition import DjangoCourseGenerationService
from lms.api.learning_composition import DjangoLearningService
from lms.api.main import create_application
from lms.modules.course_generation.models import GenerationCanonicalization
from lms.modules.course_generation.services import CourseGenerationService
from lms.modules.documents.storage import LocalQuarantineStorage
from lms.modules.tenancy.models import OutboxFact
from tests.documents.conftest import valid_pdf_bytes as valid_pdf_bytes
from tests.integration.test_f002_course_composition import transition
from tests.integration.test_f003_source_admission import (
    FixtureIdentityAuthenticator,
    approve_and_intent,
    create_admission,
    headers,
    send,
)
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

pytestmark = pytest.mark.django_db(transaction=True)


def test_private_pdf_to_reviewed_publication_and_resumable_learner_playback(
    tenancy_seed: dict[str, Any], valid_pdf_bytes: bytes, tmp_path: Path
) -> None:
    tenant_id = tenancy_seed["alpha"].id
    courses = DjangoCourseAdministrationService()
    documents = DjangoSourceAdmissionService(storage=LocalQuarantineStorage(tmp_path / "source"))
    generation = CourseGenerationService(course_drafts=courses)
    app = create_application(
        identity_authenticator=FixtureIdentityAuthenticator(tenancy_seed["profiles"]),
        tenancy_service=DjangoTenancyService(),
        course_service=courses,
        document_service=documents,
        generation_service=DjangoCourseGenerationService(service=generation),
        learning_service=DjangoLearningService(),
    )
    base = f"/api/v1/tenants/{tenant_id}"
    sequence = 0

    def call(
        method: str,
        path: str,
        *,
        body: Any = None,
        actor: str = "instructor",
        expected: int = 200,
        key: str | None = None,
    ) -> Any:
        nonlocal sequence
        sequence += 1
        response = send(
            app,
            method,
            path,
            request_headers=headers(
                actor, tenant_id, idempotency=key or f"f008-command-{sequence:016d}"
            ),
            json=body,
        )
        assert response.status_code == expected, response.text
        return response.json()

    declaration = create_admission(app, tenant_id, suffix="f008")
    _rights, intent = approve_and_intent(app, tenant_id, declaration, suffix="f008")
    upload_headers = headers("instructor", tenant_id)
    upload_headers["Content-Type"] = "application/pdf"
    uploaded = send(
        app,
        "PUT",
        str(intent["target_url"]),
        request_headers=upload_headers,
        content=valid_pdf_bytes,
    )
    assert uploaded.status_code == 202, uploaded.text
    source = uploaded.json()
    assert source["source_version"]["admission_status"] == "admitted"
    document_id = source["source_document"]["id"]
    source_version_id = source["source_version"]["id"]
    source_path = f"{base}/source-documents/{document_id}/versions/{source_version_id}"

    for operation in ("extract", "generate"):
        operation_path = f"{source_path}/authorizations/{operation}"
        requested = call("POST", operation_path)
        active = call(
            "POST",
            f"{operation_path}/review",
            actor="admin",
            body={
                "decision": "activate",
                "decision_code": "RIGHTS_EVIDENCE_ACCEPTED",
                "expected_authorization_row_version": requested["row_version"],
            },
        )
        assert active["status"] == "active"
    ingestion = call("POST", f"{source_path}/ingestion-runs", expected=202)
    extracted = documents.run_ingestion(
        tenant_id=tenant_id, run_id=UUID(ingestion["id"]), worker_id="f008-extraction-worker"
    )
    assert extracted.run.status == "ready_for_generation"
    normalized = call("GET", f"{source_path}/ingestion-runs/{ingestion['id']}")
    assert normalized["status"] == "ready_for_generation"

    queued = call(
        "POST",
        f"{base}/course-generation-runs",
        expected=202,
        body={
            "source_document_id": document_id,
            "source_version_id": source_version_id,
            "ingestion_run_id": ingestion["id"],
            "target_level": "beginner",
            "target_duration_minutes": 30,
            "intended_audience": "Synthetic adult learners",
            "teaching_style": "guided",
            "locale": "en",
        },
    )
    run_id = UUID(queued["id"])
    run_path = f"{base}/course-generation-runs/{run_id}"
    planned = generation.run_generation(
        tenant_id=tenant_id, run_id=run_id, worker_id="f008-generator"
    )
    assert planned.run.status == "blueprint_review"
    package = call("GET", run_path)
    blueprint = package["blueprint"]
    approved = call(
        "POST",
        f"{run_path}/approve-blueprint",
        body={
            "expected_run_row_version": package["run"]["row_version"],
            "blueprint_id": blueprint["id"],
            "blueprint_revision": 1,
            "expected_blueprint_content_sha256": blueprint["content_sha256"],
        },
    )
    assert approved["status"] == "generation_queued"
    generated = generation.run_generation(
        tenant_id=tenant_id, run_id=run_id, worker_id="f008-generator"
    )
    assert generated.run.status == "review_ready"
    canonical_body = {
        "expected_run_row_version": generated.run.row_version,
        "expected_output_manifest_sha256": generated.run.output_manifest_sha256,
        "course_slug": "f008-synthetic-course",
    }
    canonical = call(
        "POST",
        f"{run_path}/canonicalize",
        body=canonical_body,
        expected=201,
        key="f008-canonicalization-0001",
    )
    assert (
        call(
            "POST",
            f"{run_path}/canonicalize",
            body=canonical_body,
            expected=201,
            key="f008-canonicalization-0001",
        )
        == canonical
    )
    assert GenerationCanonicalization.objects.filter(generation_run_id=run_id).count() == 1
    version_path = (
        f"{base}/courses/{canonical['course_id']}/versions/{canonical['course_version_id']}"
    )
    snapshot = call("GET", version_path)
    assert snapshot["version"]["origin_type"] == "ai_assisted"
    assert snapshot["course"]["current_published_version_id"] is None
    snapshot = call(
        "PATCH",
        version_path,
        body={
            "expected_version_row_version": snapshot["version"]["row_version"],
            "title": "Human-reviewed synthetic course",
        },
    )
    assert snapshot["version"]["content_hash"] != canonical["canonical_content_sha256"]
    for action in ("submit_review", "approve", "publish"):
        snapshot = call(
            "POST",
            f"{version_path}/{action.replace('_', '-')}",
            body=transition(snapshot, action),
        )
    assert snapshot["version"]["status"] == "published"
    enrollment = call(
        "POST",
        f"{base}/enrollments",
        actor="admin",
        expected=201,
        body={
            "learner_membership_id": str(tenancy_seed["memberships"]["learner"].id),
            "course_id": canonical["course_id"],
        },
    )
    learner_path = f"{base}/learner/enrollments/{enrollment['id']}"
    playback = call("GET", f"{learner_path}/playback", actor="learner")
    assert playback["course_version_id"] == canonical["course_version_id"]
    lesson_id = snapshot["sections"][0]["lessons"][0]["id"]
    lesson = call("GET", f"{learner_path}/lessons/{lesson_id}", actor="learner")
    assert lesson["lesson"]["content_blocks"][0]["document"]["type"] == "document"
    for forbidden in ("source_version_id", "ingestion_run_id", "generation_run_id", "provider"):
        assert forbidden not in str(playback)
        assert forbidden not in str(lesson)
    completed = call(
        "POST",
        f"{learner_path}/progress/complete-lesson",
        actor="learner",
        body={
            "command": "complete_lesson",
            "lesson_id": lesson_id,
            "expected_progress_row_version": 0,
        },
        key="f008-complete-lesson-0001",
    )
    assert completed["course_state"] == "completed"
    resumed = call("GET", f"{learner_path}/playback", actor="learner")
    assert resumed["course_version_id"] == canonical["course_version_id"]
    assert resumed["progress"]["state"] == "completed"
    assert resumed["progress"]["row_version"] == completed["progress_row_version"]
    assert call("GET", source_path, actor="learner", expected=403)["code"]
    assert call("GET", run_path, actor="learner", expected=403)["code"]
    assert call("GET", version_path, actor="learner", expected=403)["code"]
    assert call("GET", f"{learner_path}/playback", actor="outsider", expected=404)["code"]
    events = set(OutboxFact.objects.values_list("event_type", flat=True))
    assert {
        "document.ingestion.ready.v1",
        "course_generation.canonicalized.v1",
        "course.version.published.v1",
        "learning.enrollment.created.v1",
        "learning.course.completed.v1",
    } <= events

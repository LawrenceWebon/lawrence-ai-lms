from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from django.db import DatabaseError, connection, transaction

from lms.api.course_composition import DjangoCourseAdministrationService
from lms.api.schemas.courses import (
    CourseAdministrationError,
    CreateSuccessorDraftV1,
    ReplaceCurriculumV1,
    TransitionCourseVersionV1,
)
from lms.modules.course_generation.errors import CourseGenerationError
from lms.modules.course_generation.models import (
    CanonicalizationSourceEdge,
    CourseGenerationRun,
    GenerationCanonicalization,
)
from lms.modules.course_generation.types import CanonicalizeGenerationCommand
from lms.modules.courses.models import Course, CourseVersion
from lms.modules.documents.types import ReviewAuthorizationCommand
from lms.modules.tenancy.models import OutboxFact
from tests.course_generation.test_service import _review_ready_generation

pytestmark = pytest.mark.django_db


@pytest.fixture
def ready_generation(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    generation_service: Any,
    valid_pdf_bytes: bytes,
) -> Any:
    return _review_ready_generation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        ingestion_service=ingestion_service,
        generation_service=generation_service,
        valid_pdf_bytes=valid_pdf_bytes,
        suffix="canonical-gates",
    )


def canonicalize(tenancy_seed: Any, generation_service: Any, run: Any) -> Any:
    return generation_service.canonicalize_generation(
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        run_id=run.id,
        command=CanonicalizeGenerationCommand(
            expected_run_row_version=run.row_version,
            expected_output_manifest_sha256=run.output_manifest_sha256,
            course_slug="canonical-gates-course",
        ),
        idempotency_key="canonical-gates-create-0001",
    )


def transition(service: Any, seed: Any, snapshot: Any, name: str) -> Any:
    values = {
        "transition": name,
        "expected_version_row_version": snapshot.version.row_version,
        "expected_content_hash": snapshot.version.content_hash,
    }
    if name == "publish":
        values["expected_course_row_version"] = snapshot.course.row_version
    return service.transition_version(
        actor_id=seed["profiles"]["admin"].provider_subject,
        tenant_id=seed["alpha"].id,
        course_id=snapshot.course.id,
        version_id=snapshot.version.id,
        command=TransitionCourseVersionV1.model_validate(values),
        idempotency_key=f"canonical-gates-{name}-{snapshot.version.row_version}",
    )


def test_generated_curriculum_can_be_removed_without_losing_origin_evidence(
    tenancy_seed: Any, generation_service: Any, ready_generation: Any
) -> None:
    _source, _ingestion, run = ready_generation
    result = canonicalize(tenancy_seed, generation_service, run)
    evidence = CanonicalizationSourceEdge.objects.get(canonicalization_id=result.id)
    original_targets = (
        evidence.curriculum_section_id,
        evidence.lesson_id,
        evidence.content_block_id,
    )
    service = DjangoCourseAdministrationService()
    snapshot = service.get_course_version(
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        course_id=result.course_id,
        version_id=result.course_version_id,
    )
    edited = service.replace_curriculum(
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        course_id=result.course_id,
        version_id=result.course_version_id,
        command=ReplaceCurriculumV1(
            expected_version_row_version=snapshot.version.row_version,
            sections=[],
        ),
    )
    assert edited.sections == ()
    assert edited.version.content_hash != result.canonical_content_sha256
    evidence.refresh_from_db()
    assert original_targets == (
        evidence.curriculum_section_id,
        evidence.lesson_id,
        evidence.content_block_id,
    )
    assert GenerationCanonicalization.objects.get(id=result.id).canonicalization_sha256 == (
        result.canonicalization_sha256
    )


def test_revoking_generate_right_after_approval_blocks_publication(
    tenancy_seed: Any, documents_service: Any, generation_service: Any, ready_generation: Any
) -> None:
    source, _ingestion, run = ready_generation
    result = canonicalize(tenancy_seed, generation_service, run)
    service = DjangoCourseAdministrationService()
    snapshot = service.get_course_version(
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        course_id=result.course_id,
        version_id=result.course_version_id,
    )
    submitted = transition(service, tenancy_seed, snapshot, "submit_review")
    approved = transition(service, tenancy_seed, submitted, "approve")
    documents_service.review_operation_authorization(
        actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
        tenant_id=tenancy_seed["alpha"].id,
        source_document_id=source.source_document.id,
        source_version_id=source.source_version.id,
        operation="generate",
        command=ReviewAuthorizationCommand(
            decision="revoke",
            expected_authorization_row_version=2,
            decision_code="RIGHTS_REVOKED",
        ),
        idempotency_key="canonical-gates-revoke-rights",
    )
    with pytest.raises(CourseAdministrationError) as caught:
        transition(service, tenancy_seed, approved, "publish")
    assert caught.value.status in {403, 409, 422}
    assert Course.objects.get(id=result.course_id).current_published_version_id is None
    assert CourseVersion.objects.get(id=result.course_version_id).status == "approved"
    assert not OutboxFact.objects.filter(event_type="course.version.published.v1").exists()


def test_canonicalization_rejects_stale_hash_and_rolls_back_fact_failure(
    tenancy_seed: Any, generation_service: Any, ready_generation: Any, monkeypatch: Any
) -> None:
    _source, _ingestion, run = ready_generation
    command = CanonicalizeGenerationCommand(
        expected_run_row_version=run.row_version,
        expected_output_manifest_sha256=run.output_manifest_sha256,
        course_slug="canonical-gates-course",
    )
    for changed in (
        replace(command, expected_run_row_version=run.row_version + 1),
        replace(command, expected_output_manifest_sha256="sha256:" + "0" * 64),
    ):
        with pytest.raises(CourseGenerationError, match="GENERATION_OUTPUT_HASH_MISMATCH"):
            generation_service.canonicalize_generation(
                actor_id=tenancy_seed["profiles"]["admin"].provider_subject,
                tenant_id=tenancy_seed["alpha"].id,
                run_id=run.id,
                command=changed,
                idempotency_key="canonical-gates-stale-input",
            )

    def fail_fact(**_: Any) -> None:
        raise RuntimeError("synthetic canonicalization fact failure")

    monkeypatch.setattr(generation_service, "_record_canonicalization_fact", fail_fact)
    with pytest.raises(RuntimeError, match="synthetic canonicalization fact failure"):
        canonicalize(tenancy_seed, generation_service, run)
    assert not Course.objects.exists()
    assert not GenerationCanonicalization.objects.exists()
    assert not CanonicalizationSourceEdge.objects.exists()
    assert CourseGenerationRun.objects.get(id=run.id).status == "review_ready"


@pytest.mark.rls
@pytest.mark.django_db(transaction=True)
def test_successor_keeps_rights_and_database_denies_publication_bypass(
    tenancy_seed: Any, documents_service: Any, generation_service: Any, ready_generation: Any
) -> None:
    source, _ingestion, run = ready_generation
    service = DjangoCourseAdministrationService()
    common = {
        "actor_id": tenancy_seed["profiles"]["admin"].provider_subject,
        "tenant_id": tenancy_seed["alpha"].id,
    }
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE lms_api_runtime")
        result = canonicalize(tenancy_seed, generation_service, run)
        snapshot = service.get_course_version(
            **common, course_id=result.course_id, version_id=result.course_version_id
        )
        submitted = transition(service, tenancy_seed, snapshot, "submit_review")
        approved = transition(service, tenancy_seed, submitted, "approve")
        published = transition(service, tenancy_seed, approved, "publish")
        successor = service.create_successor_draft(
            **common,
            course_id=result.course_id,
            source_version_id=result.course_version_id,
            command=CreateSuccessorDraftV1(
                expected_course_row_version=published.course.row_version,
                expected_source_version_row_version=published.version.row_version,
                expected_source_content_hash=published.version.content_hash,
            ),
            idempotency_key="canonical-gates-successor-0001",
        )
        submitted_successor = transition(service, tenancy_seed, successor.snapshot, "submit_review")
        approved_successor = transition(service, tenancy_seed, submitted_successor, "approve")
        documents_service.review_operation_authorization(
            **common,
            source_document_id=source.source_document.id,
            source_version_id=source.source_version.id,
            operation="generate",
            command=ReviewAuthorizationCommand(
                decision="revoke",
                expected_authorization_row_version=2,
                decision_code="RIGHTS_REVOKED",
            ),
            idempotency_key="canonical-gates-successor-revoke",
        )
        with pytest.raises(CourseAdministrationError, match="COURSE_VALIDATION_FAILED"):
            transition(service, tenancy_seed, approved_successor, "publish")
        with pytest.raises(DatabaseError, match="generated course source rights unavailable"):
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.course_versions SET status = 'published', "
                    "row_version = row_version + 1 "
                    "WHERE tenant_id = %s AND id = %s",
                    [str(common["tenant_id"]), str(approved_successor.version.id)],
                )
    assert Course.objects.get(id=result.course_id).current_published_version_id == (
        result.course_version_id
    )
    assert CourseVersion.objects.get(id=approved_successor.version.id).status == "approved"

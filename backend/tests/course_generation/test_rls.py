from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, connection, transaction

from lms.modules.course_generation.models import (
    BlueprintReviewDecision,
    CourseBlueprint,
    CourseBlueprintItem,
    CourseGenerationAttempt,
    CourseGenerationRun,
    GeneratedLessonArtifact,
    GenerationRunSnapshot,
    GenerationSourceEdge,
)
from lms.modules.course_generation.types import ApproveBlueprintCommand
from lms.modules.documents.models import DocumentSection
from tests.course_generation.test_service import _intent, _ready_source
from tests.documents.test_ingestion_service import _activate_operation

pytestmark = [pytest.mark.rls, pytest.mark.django_db(transaction=True)]

GENERATION_TABLES = {
    "course_generation_runs",
    "course_generation_attempts",
    "course_generation_snapshots",
    "course_generation_blueprints",
    "course_generation_blueprint_items",
    "generated_lesson_artifacts",
    "course_generation_source_edges",
    "course_generation_blueprint_decisions",
    "course_generation_rejections",
}


def _set_user_context(actor_id: object, tenant_id: object) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_actor_id', %s, true)", [str(actor_id)])
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, true)", [str(tenant_id)])


def _set_job_context(run_id: object, stage: str, tenant_id: object) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_job_id', %s, true)", [str(run_id)])
        cursor.execute("SELECT set_config('app.current_job_stage', %s, true)", [stage])
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, true)", [str(tenant_id)])


def _set_role(role: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL ROLE {role}")


def test_generation_tables_are_non_runtime_owned_with_forced_rls() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT namespace.nspname, class.relname, role.rolname,
                   class.relrowsecurity, class.relforcerowsecurity
              FROM pg_class class
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              JOIN pg_roles role ON role.oid = class.relowner
             WHERE (namespace.nspname, class.relname) IN (
                    ('integration', 'course_generation_runs'),
                    ('integration', 'course_generation_attempts'),
                    ('integration', 'course_generation_snapshots'),
                    ('app', 'course_generation_blueprints'),
                    ('app', 'course_generation_blueprint_items'),
                    ('app', 'generated_lesson_artifacts'),
                    ('app', 'course_generation_source_edges'),
                    ('audit', 'course_generation_blueprint_decisions'),
                    ('audit', 'course_generation_rejections')
             )
            """
        )
        rows = cursor.fetchall()
        cursor.execute(
            """
            SELECT
                has_table_privilege(
                    'lms_api_runtime', 'app.generated_lesson_artifacts', 'INSERT'
                ),
                has_table_privilege(
                    'lms_worker_runtime', 'integration.course_generation_runs', 'DELETE'
                ),
                has_table_privilege(
                    'lms_worker_runtime',
                    'audit.course_generation_blueprint_decisions', 'INSERT'
                )
            """
        )
        privileges = cursor.fetchone()
    assert {row[1] for row in rows} == GENERATION_TABLES
    assert all(row[2] == "lms_object_owner" for row in rows)
    assert all(row[3] and row[4] for row in rows)
    assert privileges == (False, False, False)


def test_generation_api_and_worker_services_succeed_through_production_roles(
    tenancy_seed: dict[str, Any],
    documents_service: Any,
    ingestion_service: Any,
    generation_service: Any,
    valid_pdf_bytes: bytes,
) -> None:
    instructor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    learner = tenancy_seed["profiles"]["learner"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    admitted, ingestion = _ready_source(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        ingestion_service=ingestion_service,
        valid_pdf_bytes=valid_pdf_bytes,
        suffix="production-role-0001",
    )
    _activate_operation(
        tenancy_seed=tenancy_seed,
        documents_service=documents_service,
        admitted=admitted,
        operation="generate",
        key_suffix="generation-production-role-0001",
    )

    with transaction.atomic():
        _set_user_context(instructor, tenant_id)
        _set_role("lms_api_runtime")
        run = generation_service.start_generation(
            actor_id=instructor,
            tenant_id=tenant_id,
            source_document_id=admitted.source_document.id,
            source_version_id=admitted.source_version.id,
            ingestion_run_id=ingestion.id,
            intent=_intent(),
            idempotency_key="generation-runtime-start-0001",
        )
        assert GenerationRunSnapshot.objects.filter(generation_run_id=run.id).exists()

    with transaction.atomic():
        _set_job_context(run.id, "generation_claim", tenant_id)
        _set_role("lms_worker_runtime")
        planned = generation_service.run_generation(
            tenant_id=tenant_id,
            run_id=run.id,
            worker_id="generation-production-worker",
        )
        assert planned.run.status == "blueprint_review"
        assert CourseGenerationAttempt.objects.filter(generation_run_id=run.id).count() == 1
        assert CourseBlueprintItem.objects.filter(generation_run_id=run.id).count() == 2
        assert DocumentSection.objects.filter(source_version_id=admitted.source_version.id).exists()

    with transaction.atomic():
        _set_user_context(admin, tenant_id)
        _set_role("lms_api_runtime")
        package = generation_service.get_generation(
            actor_id=admin,
            tenant_id=tenant_id,
            run_id=run.id,
        )
        assert package.blueprint is not None
        approved = generation_service.approve_blueprint(
            actor_id=admin,
            tenant_id=tenant_id,
            run_id=run.id,
            command=ApproveBlueprintCommand(
                expected_run_row_version=package.run.row_version,
                blueprint_id=package.blueprint.id,
                blueprint_revision=1,
                expected_blueprint_content_sha256=package.blueprint.content_sha256,
            ),
        )
        assert approved.status == "generation_queued"
        assert BlueprintReviewDecision.objects.filter(generation_run_id=run.id).exists()

    with transaction.atomic():
        _set_job_context(run.id, "generation_claim", tenant_id)
        _set_role("lms_worker_runtime")
        generated = generation_service.run_generation(
            tenant_id=tenant_id,
            run_id=run.id,
            worker_id="generation-production-worker",
        )
        assert generated.run.status == "review_ready"
        artifact = GeneratedLessonArtifact.objects.get(generation_run_id=run.id)
        assert GenerationSourceEdge.objects.filter(
            generation_run_id=run.id, generated_artifact_id=artifact.id
        ).exists()
        with pytest.raises(DatabaseError), transaction.atomic():
            GeneratedLessonArtifact.objects.filter(id=artifact.id).update(
                title="forbidden mutation"
            )

    with transaction.atomic():
        _set_user_context(learner, tenant_id)
        _set_role("lms_api_runtime")
        assert CourseGenerationRun.objects.count() == 0
        assert CourseBlueprint.objects.count() == 0
        assert GeneratedLessonArtifact.objects.count() == 0

    with transaction.atomic():
        _set_job_context(run.id, "unrelated_stage", tenant_id)
        _set_role("lms_worker_runtime")
        assert CourseGenerationRun.objects.count() == 0
        assert DocumentSection.objects.count() == 0

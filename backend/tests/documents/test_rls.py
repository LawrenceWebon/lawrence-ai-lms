from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, connection, transaction

from lms.modules.documents.models import (
    DocumentJob,
    DocumentJobAttempt,
    SourceDocument,
    SourceVersion,
    UploadIntent,
)
from lms.modules.documents.types import (
    CreateAdmissionCommand,
    ReviewAuthorizationCommand,
    RightsDeclarationInput,
)
from tests.tenancy.conftest import tenancy_seed as tenancy_seed

pytestmark = [pytest.mark.rls, pytest.mark.django_db(transaction=True)]

DOCUMENT_TABLES = {
    "source_documents",
    "source_document_versions",
    "source_rights_declarations",
    "source_use_authorizations",
    "source_upload_intents",
    "source_storage_objects",
    "document_jobs",
    "document_job_attempts",
}


def _mutated_digest(digest: str) -> str:
    replacement = "1" if digest.startswith("0") else "0"
    return f"{replacement}{digest[1:]}"


def test_mutated_upload_digest_is_always_distinct() -> None:
    assert _mutated_digest("0" * 64) != "0" * 64
    assert _mutated_digest("f" * 64) != "f" * 64


def command(name: str) -> CreateAdmissionCommand:
    return CreateAdmissionCommand(
        display_name=name,
        declared_filename="synthetic-rls.pdf",
        rights_declaration=RightsDeclarationInput(
            basis="owned",
            attestation_version="f003-source-rights-attestation-v1",
            attested=True,
        ),
    )


def set_user_context(actor_id: object | None, tenant_id: object | None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_actor_id', %s, true)",
            ["" if actor_id is None else str(actor_id)],
        )
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            ["" if tenant_id is None else str(tenant_id)],
        )


def set_job_context(job_id: object, stage: str, tenant_id: object | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_job_id', %s, true)",
            [str(job_id)],
        )
        cursor.execute(
            "SELECT set_config('app.current_job_stage', %s, true)",
            [stage],
        )
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            ["" if tenant_id is None else str(tenant_id)],
        )


def set_upload_context(token_digest: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_actor_id', '', true)")
        cursor.execute("SELECT set_config('app.current_tenant_id', '', true)")
        cursor.execute(
            "SELECT set_config('app.current_upload_token_digest', %s, true)",
            [token_digest],
        )


def set_role(role: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL ROLE {role}")


def test_document_tables_are_non_runtime_owned_with_forced_rls() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT namespace.nspname, class.relname, role.rolname,
                   class.relrowsecurity, class.relforcerowsecurity
              FROM pg_class class
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              JOIN pg_roles role ON role.oid = class.relowner
             WHERE (namespace.nspname, class.relname) IN (
                    ('app', 'source_documents'),
                    ('app', 'source_document_versions'),
                    ('app', 'source_rights_declarations'),
                    ('app', 'source_use_authorizations'),
                    ('app', 'source_upload_intents'),
                    ('app', 'source_storage_objects'),
                    ('integration', 'document_jobs'),
                    ('integration', 'document_job_attempts')
             )
            """
        )
        rows = cursor.fetchall()
        cursor.execute(
            """
            SELECT rolname, rolsuper, rolbypassrls
              FROM pg_roles
             WHERE rolname IN ('lms_api_runtime', 'lms_worker_runtime')
             ORDER BY rolname
            """
        )
        roles = cursor.fetchall()
    assert {row[1] for row in rows} == DOCUMENT_TABLES
    assert all(row[2] == "lms_object_owner" for row in rows)
    assert all(row[3] and row[4] for row in rows)
    assert roles == [
        ("lms_api_runtime", False, False),
        ("lms_worker_runtime", False, False),
    ]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                has_table_privilege('lms_api_runtime', 'app.source_documents', 'DELETE'),
                has_table_privilege(
                    'lms_worker_runtime', 'app.source_storage_objects', 'INSERT'
                ),
                has_table_privilege(
                    'lms_worker_runtime', 'integration.document_jobs', 'DELETE'
                )
            """
        )
        assert cursor.fetchone() == (False, False, False)


def test_api_runtime_is_tenant_scoped_and_context_resets(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    alpha = documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenancy_seed["alpha"].id,
        command=command("Alpha synthetic source"),
        idempotency_key="rls-alpha-source-create",
    )
    documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenancy_seed["beta"].id,
        command=command("Beta synthetic source"),
        idempotency_key="rls-beta-source-create",
    )

    with transaction.atomic():
        set_user_context(actor, tenancy_seed["alpha"].id)
        set_role("lms_api_runtime")
        assert list(SourceDocument.objects.values_list("id", flat=True)) == [
            alpha.source_document.id
        ]

    with transaction.atomic():
        set_role("lms_api_runtime")
        assert SourceDocument.objects.count() == 0

    with transaction.atomic():
        set_user_context(
            tenancy_seed["profiles"]["outsider"].provider_subject,
            tenancy_seed["alpha"].id,
        )
        set_role("lms_api_runtime")
        assert SourceDocument.objects.count() == 0


def test_api_runtime_rejects_cross_tenant_insert(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenancy_seed["alpha"].id,
        command=command("Tenant edge source"),
        idempotency_key="rls-source-edge-create",
    )
    with transaction.atomic():
        set_user_context(actor, tenancy_seed["alpha"].id)
        set_role("lms_api_runtime")
        with pytest.raises(DatabaseError), transaction.atomic():
            SourceDocument.objects.create(
                tenant=tenancy_seed["beta"],
                display_name="Forbidden cross-tenant source",
                owner_actor_id=actor,
            )


def test_upload_token_scope_is_exact_and_mutated_digest_is_neutral(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenant_id,
        command=command("Opaque upload RLS source"),
        idempotency_key="rls-upload-token-create",
    )
    documents_service.review_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=ReviewAuthorizationCommand(
            decision="activate",
            expected_authorization_row_version=1,
            decision_code="RIGHTS_EVIDENCE_ACCEPTED",
        ),
        idempotency_key="rls-upload-token-review",
    )
    intent = documents_service.create_upload_intent(
        actor_id=actor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="rls-upload-token-intent",
    )
    digest = UploadIntent.objects.get(id=intent.id).token_digest

    with transaction.atomic():
        set_upload_context(digest)
        set_role("lms_api_runtime")
        assert list(SourceDocument.objects.values_list("id", flat=True)) == [
            created.source_document.id
        ]
        assert list(UploadIntent.objects.values_list("id", flat=True)) == [intent.id]

    with transaction.atomic():
        set_upload_context(_mutated_digest(digest))
        set_role("lms_api_runtime")
        assert SourceDocument.objects.count() == 0
        assert UploadIntent.objects.count() == 0


def test_runtime_direct_evidence_token_mutation_and_delete_fail_closed(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenant_id,
        command=command("Direct mutation guard source"),
        idempotency_key="rls-direct-guard-create",
    )
    documents_service.review_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=ReviewAuthorizationCommand(
            decision="activate",
            expected_authorization_row_version=1,
            decision_code="RIGHTS_EVIDENCE_ACCEPTED",
        ),
        idempotency_key="rls-direct-guard-review",
    )
    intent = documents_service.create_upload_intent(
        actor_id=actor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="rls-direct-guard-intent",
    )

    with transaction.atomic():
        set_user_context(actor, tenant_id)
        set_role("lms_api_runtime")
        with pytest.raises(DatabaseError), transaction.atomic():
            SourceVersion.objects.filter(id=created.source_version.id).update(derived_page_count=2)
        with pytest.raises(DatabaseError), transaction.atomic():
            UploadIntent.objects.filter(id=intent.id).update(token_digest="0" * 64)
        with pytest.raises(DatabaseError), transaction.atomic():
            SourceDocument.objects.filter(id=created.source_document.id).delete()


def test_inactive_membership_invalidates_existing_runtime_context(
    tenancy_seed: dict[str, Any], documents_service: Any
) -> None:
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenant_id,
        command=command("Stale membership source"),
        idempotency_key="rls-stale-member-create",
    )
    tenancy_seed["memberships"]["instructor_alpha"].status = "inactive"
    tenancy_seed["memberships"]["instructor_alpha"].save(update_fields=("status",))

    with transaction.atomic():
        set_user_context(actor, tenant_id)
        set_role("lms_api_runtime")
        assert SourceDocument.objects.count() == 0


def test_worker_can_claim_only_its_exact_job_scope(
    tenancy_seed: dict[str, Any], documents_service: Any, valid_pdf_bytes: bytes
) -> None:
    actor = tenancy_seed["profiles"]["instructor"].provider_subject
    admin = tenancy_seed["profiles"]["admin"].provider_subject
    tenant_id = tenancy_seed["alpha"].id
    created = documents_service.create_admission(
        actor_id=actor,
        tenant_id=tenant_id,
        command=command("Worker-scoped source"),
        idempotency_key="rls-worker-source-create",
    )
    documents_service.review_authorization(
        actor_id=admin,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        authorization_id=created.store_authorization.id,
        command=ReviewAuthorizationCommand(
            decision="activate",
            expected_authorization_row_version=1,
            decision_code="RIGHTS_EVIDENCE_ACCEPTED",
        ),
        idempotency_key="rls-worker-source-review",
    )
    intent = documents_service.create_upload_intent(
        actor_id=actor,
        tenant_id=tenant_id,
        source_document_id=created.source_document.id,
        source_version_id=created.source_version.id,
        idempotency_key="rls-worker-source-intent",
    )
    documents_service.upload_to_intent(
        opaque_token=intent.opaque_token,
        content_type="application/pdf",
        body=valid_pdf_bytes,
    )
    job = DocumentJob.objects.get(stage="validate_admission")

    with transaction.atomic():
        set_job_context(job.id, job.stage, tenant_id)
        set_role("lms_worker_runtime")
        assert list(DocumentJob.objects.values_list("id", flat=True)) == [job.id]
        assert SourceDocument.objects.filter(id=created.source_document.id).exists()
        assert DocumentJobAttempt.objects.filter(job_id=job.id).count() == 1

    with transaction.atomic():
        set_job_context(job.id, "remove_quarantine_object", tenant_id)
        set_role("lms_worker_runtime")
        assert DocumentJob.objects.count() == 0
        assert SourceDocument.objects.count() == 0
        assert DocumentJobAttempt.objects.count() == 0

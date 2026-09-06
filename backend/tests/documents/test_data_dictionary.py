from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from django.db import connection

DICTIONARY_PATH = Path("backend/src/lms/modules/documents/migrations/document_schema_v1.json")
DOCUMENT_TABLES = (
    ("app", "source_documents"),
    ("app", "source_document_versions"),
    ("app", "source_rights_declarations"),
    ("app", "source_use_authorizations"),
    ("app", "source_upload_intents"),
    ("app", "source_storage_objects"),
    ("app", "source_artifacts"),
    ("app", "document_pages"),
    ("app", "document_elements"),
    ("app", "document_sections"),
    ("app", "document_section_elements"),
    ("integration", "document_jobs"),
    ("integration", "document_job_attempts"),
    ("integration", "document_ingestion_runs"),
    ("integration", "document_ingestion_attempts"),
)

INGESTION_TABLES = {
    "source_artifacts",
    "document_pages",
    "document_elements",
    "document_sections",
    "document_section_elements",
    "document_ingestion_runs",
    "document_ingestion_attempts",
}


def database_fingerprint() -> str:
    catalog: dict[str, object] = {}
    schemas = sorted({schema for schema, _table in DOCUMENT_TABLES})
    tables = sorted({table for _schema, table in DOCUMENT_TABLES})
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT namespace.nspname, class.relname, attribute.attnum, attribute.attname,
                   format_type(attribute.atttypid, attribute.atttypmod),
                   attribute.attnotnull,
                   pg_get_expr(default_value.adbin, default_value.adrelid)
              FROM pg_attribute attribute
              JOIN pg_class class ON class.oid = attribute.attrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              LEFT JOIN pg_attrdef default_value
                ON default_value.adrelid = attribute.attrelid
               AND default_value.adnum = attribute.attnum
             WHERE namespace.nspname = ANY(%s)
               AND class.relname = ANY(%s)
               AND attribute.attnum > 0
               AND NOT attribute.attisdropped
             ORDER BY namespace.nspname, class.relname, attribute.attnum
            """,
            [schemas, tables],
        )
        catalog["columns"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT namespace.nspname, class.relname, constraint_row.conname,
                   constraint_row.contype,
                   pg_get_constraintdef(constraint_row.oid, true)
              FROM pg_constraint constraint_row
              JOIN pg_class class ON class.oid = constraint_row.conrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE namespace.nspname = ANY(%s) AND class.relname = ANY(%s)
             ORDER BY namespace.nspname, class.relname, constraint_row.conname
            """,
            [schemas, tables],
        )
        catalog["constraints"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT schemaname, tablename, indexname, indexdef
              FROM pg_indexes
             WHERE schemaname = ANY(%s) AND tablename = ANY(%s)
             ORDER BY schemaname, tablename, indexname
            """,
            [schemas, tables],
        )
        catalog["indexes"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT schemaname, tablename, policyname, cmd, roles::text, qual, with_check
              FROM pg_policies
             WHERE schemaname = ANY(%s) AND tablename = ANY(%s)
             ORDER BY schemaname, tablename, policyname
            """,
            [schemas, tables],
        )
        catalog["policies"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT namespace.nspname, class.relname, trigger_row.tgname,
                   pg_get_triggerdef(trigger_row.oid, true)
              FROM pg_trigger trigger_row
              JOIN pg_class class ON class.oid = trigger_row.tgrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE namespace.nspname = ANY(%s)
               AND class.relname = ANY(%s)
               AND NOT trigger_row.tgisinternal
             ORDER BY namespace.nspname, class.relname, trigger_row.tgname
            """,
            [schemas, tables],
        )
        catalog["triggers"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT namespace.nspname, class.relname, role.rolname,
                   class.relrowsecurity, class.relforcerowsecurity
              FROM pg_class class
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              JOIN pg_roles role ON role.oid = class.relowner
             WHERE namespace.nspname = ANY(%s) AND class.relname = ANY(%s)
             ORDER BY namespace.nspname, class.relname
            """,
            [schemas, tables],
        )
        catalog["security"] = cursor.fetchall()
    encoded = json.dumps(catalog, sort_keys=True, separators=(",", ":"), default=str).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def test_document_dictionary_has_a_reproducible_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    encoded = json.dumps(dictionary["objects"], sort_keys=True, separators=(",", ":")).encode()
    assert dictionary["schema_fingerprint"] == f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    assert {(item["schema"], item["table"]) for item in dictionary["objects"]} == set(
        DOCUMENT_TABLES
    )
    for item in dictionary["objects"]:
        expected_migration = (
            "documents.0003_ingestion_schema"
            if item["table"] in INGESTION_TABLES
            else "documents.0001_initial"
        )
        expected_security = (
            "documents.0005_ingestion_security"
            if item["table"] in INGESTION_TABLES or item["table"] == "source_use_authorizations"
            else "documents.0002_document_security"
        )
        assert item["migration"] == expected_migration
        assert item["security_migration"] == expected_security


@pytest.mark.django_db
def test_migrated_document_schema_matches_catalog_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    assert database_fingerprint() == dictionary["database_fingerprint"]
    assert all(item["rls"] == "ENABLE + FORCE" for item in dictionary["objects"])


@pytest.mark.django_db
def test_catalog_contains_named_tenant_edges_checks_and_active_intent_guard() -> None:
    expected = {
        "fk_source_versions_same_tenant_document",
        "fk_source_documents_current_version",
        "fk_source_rights_same_tenant_document",
        "fk_source_rights_same_tenant_version",
        "fk_source_auth_same_tenant_document",
        "fk_source_auth_same_tenant_version",
        "fk_source_auth_same_tenant_declaration",
        "fk_source_intents_same_tenant_document",
        "fk_source_intents_same_tenant_version",
        "fk_source_intents_same_tenant_authorization",
        "fk_source_objects_same_tenant_document",
        "fk_source_objects_same_tenant_version",
        "fk_source_objects_same_tenant_intent",
        "fk_document_jobs_same_tenant_document",
        "fk_document_jobs_same_tenant_version",
        "fk_document_jobs_same_tenant_object",
        "fk_document_attempts_same_tenant_job",
        "fk_ingestion_runs_same_tenant_document",
        "fk_ingestion_runs_same_tenant_version",
        "fk_ingestion_runs_same_tenant_object",
        "fk_ingestion_runs_same_tenant_authorization",
        "fk_ingestion_attempts_same_tenant_run",
        "fk_source_artifacts_same_tenant_run",
        "fk_document_pages_same_tenant_run",
        "fk_document_elements_same_tenant_page",
        "fk_document_sections_same_tenant_run",
        "fk_section_elements_same_tenant_section",
        "fk_section_elements_same_tenant_element",
        "ck_source_versions_admitted_evidence",
        "ck_document_jobs_attempt_bounds",
        "ck_ingestion_runs_lease_shape",
        "ck_ingestion_runs_result_shape",
        "uq_source_intents_active_version",
        "uq_ingestion_runs_active_version",
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT constraint_row.conname
              FROM pg_constraint constraint_row
              JOIN pg_class class ON class.oid = constraint_row.conrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE (namespace.nspname, class.relname) IN (
                ('app', 'source_documents'),
                ('app', 'source_document_versions'),
                ('app', 'source_rights_declarations'),
                ('app', 'source_use_authorizations'),
                ('app', 'source_upload_intents'),
                ('app', 'source_storage_objects'),
                ('app', 'source_artifacts'),
                ('app', 'document_pages'),
                ('app', 'document_elements'),
                ('app', 'document_sections'),
                ('app', 'document_section_elements'),
                ('integration', 'document_jobs'),
                ('integration', 'document_job_attempts'),
                ('integration', 'document_ingestion_runs'),
                ('integration', 'document_ingestion_attempts')
             )
            """
        )
        constraints = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT indexname
              FROM pg_indexes
             WHERE (schemaname, tablename) IN (
                ('app', 'source_upload_intents'),
                ('integration', 'document_ingestion_runs')
             )
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}
    assert expected <= constraints | indexes

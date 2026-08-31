from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from django.db import connection

DICTIONARY_PATH = Path(
    "backend/src/lms/modules/course_generation/migrations/course_generation_schema_v1.json"
)
GENERATION_TABLES = (
    ("integration", "course_generation_runs"),
    ("integration", "course_generation_attempts"),
    ("integration", "course_generation_snapshots"),
    ("app", "course_generation_blueprints"),
    ("app", "course_generation_blueprint_items"),
    ("app", "generated_lesson_artifacts"),
    ("app", "course_generation_source_edges"),
    ("audit", "course_generation_blueprint_decisions"),
    ("audit", "course_generation_rejections"),
)


def database_fingerprint() -> str:
    catalog: dict[str, object] = {}
    schemas = sorted({schema for schema, _table in GENERATION_TABLES})
    tables = sorted({table for _schema, table in GENERATION_TABLES})
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


def test_generation_dictionary_has_a_reproducible_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    encoded = json.dumps(dictionary["objects"], sort_keys=True, separators=(",", ":")).encode()
    assert dictionary["schema_fingerprint"] == f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    assert {(item["schema"], item["table"]) for item in dictionary["objects"]} == set(
        GENERATION_TABLES
    )
    assert all(
        item["security_migration"] == "course_generation.0004_generation_security"
        for item in dictionary["objects"]
    )


@pytest.mark.django_db
def test_migrated_generation_schema_matches_catalog_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    assert database_fingerprint() == dictionary["database_fingerprint"]
    assert all(item["rls"] == "ENABLE + FORCE" for item in dictionary["objects"])


@pytest.mark.django_db
def test_catalog_contains_generation_tenant_edges_checks_and_human_guards() -> None:
    expected = {
        "fk_generation_runs_same_tenant_document",
        "fk_generation_runs_same_tenant_version",
        "fk_generation_runs_same_tenant_ingestion",
        "fk_generation_runs_same_tenant_authorization",
        "fk_generation_attempts_same_tenant_run",
        "fk_generation_snapshots_same_tenant_run",
        "fk_generation_blueprints_same_tenant_run",
        "fk_generation_items_same_tenant_blueprint",
        "fk_generation_items_same_tenant_parent",
        "fk_generated_lessons_same_tenant_item",
        "fk_generation_edges_same_tenant_section",
        "fk_generation_decisions_same_tenant_blueprint",
        "fk_generation_rejections_same_tenant_run",
        "ck_generation_runs_lease_shape",
        "ck_generation_runs_result_shape",
        "uq_generation_runs_active_ingestion",
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT constraint_row.conname
              FROM pg_constraint constraint_row
              JOIN pg_class class ON class.oid = constraint_row.conrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE namespace.nspname = ANY(%s) AND class.relname = ANY(%s)
            """,
            [
                sorted({schema for schema, _table in GENERATION_TABLES}),
                sorted({table for _schema, table in GENERATION_TABLES}),
            ],
        )
        constraints = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
             WHERE schemaname = ANY(%s) AND tablename = ANY(%s)
            """,
            [
                sorted({schema for schema, _table in GENERATION_TABLES}),
                sorted({table for _schema, table in GENERATION_TABLES}),
            ],
        )
        indexes = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT trigger_row.tgname
              FROM pg_trigger trigger_row
              JOIN pg_class class ON class.oid = trigger_row.tgrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE namespace.nspname = ANY(%s) AND class.relname = ANY(%s)
               AND NOT trigger_row.tgisinternal
            """,
            [
                sorted({schema for schema, _table in GENERATION_TABLES}),
                sorted({table for _schema, table in GENERATION_TABLES}),
            ],
        )
        triggers = {row[0] for row in cursor.fetchall()}
    assert expected <= constraints | indexes
    assert {"trg_generation_runs_guard", "trg_generation_decisions_immutable"} <= triggers

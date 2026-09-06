from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from django.db import connection

DICTIONARY_PATH = Path("backend/src/lms/modules/learning/migrations/learning_schema_v1.json")
LEARNING_TABLES = ("course_progress", "enrollments", "lesson_progress")


def database_fingerprint() -> str:
    catalog: dict[str, object] = {}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT class.relname, attribute.attnum, attribute.attname,
                   format_type(attribute.atttypid, attribute.atttypmod),
                   attribute.attnotnull,
                   pg_get_expr(default_value.adbin, default_value.adrelid)
              FROM pg_attribute attribute
              JOIN pg_class class ON class.oid = attribute.attrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              LEFT JOIN pg_attrdef default_value
                ON default_value.adrelid = attribute.attrelid
               AND default_value.adnum = attribute.attnum
             WHERE namespace.nspname = 'app'
               AND class.relname = ANY(%s)
               AND attribute.attnum > 0
               AND NOT attribute.attisdropped
             ORDER BY class.relname, attribute.attnum
            """,
            [list(LEARNING_TABLES)],
        )
        catalog["columns"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT class.relname, constraint_row.conname, constraint_row.contype,
                   pg_get_constraintdef(constraint_row.oid, true)
              FROM pg_constraint constraint_row
              JOIN pg_class class ON class.oid = constraint_row.conrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE namespace.nspname = 'app' AND class.relname = ANY(%s)
             ORDER BY class.relname, constraint_row.conname
            """,
            [list(LEARNING_TABLES)],
        )
        catalog["constraints"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT tablename, indexname, indexdef
              FROM pg_indexes
             WHERE schemaname = 'app' AND tablename = ANY(%s)
             ORDER BY tablename, indexname
            """,
            [list(LEARNING_TABLES)],
        )
        catalog["indexes"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT tablename, policyname, cmd, roles::text, qual, with_check
              FROM pg_policies
             WHERE schemaname = 'app' AND tablename = ANY(%s)
             ORDER BY tablename, policyname
            """,
            [list(LEARNING_TABLES)],
        )
        catalog["policies"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT class.relname, trigger_row.tgname,
                   pg_get_triggerdef(trigger_row.oid, true)
              FROM pg_trigger trigger_row
              JOIN pg_class class ON class.oid = trigger_row.tgrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE namespace.nspname = 'app'
               AND class.relname = ANY(%s)
               AND NOT trigger_row.tgisinternal
             ORDER BY class.relname, trigger_row.tgname
            """,
            [list(LEARNING_TABLES)],
        )
        catalog["triggers"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT class.relname, role.rolname,
                   class.relrowsecurity, class.relforcerowsecurity
              FROM pg_class class
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
              JOIN pg_roles role ON role.oid = class.relowner
             WHERE namespace.nspname = 'app' AND class.relname = ANY(%s)
             ORDER BY class.relname
            """,
            [list(LEARNING_TABLES)],
        )
        catalog["security"] = cursor.fetchall()
    encoded = json.dumps(catalog, sort_keys=True, separators=(",", ":"), default=str).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def test_learning_dictionary_has_a_reproducible_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    encoded = json.dumps(dictionary["objects"], sort_keys=True, separators=(",", ":")).encode()
    assert dictionary["schema_fingerprint"] == f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    assert {item["table"] for item in dictionary["objects"]} == set(LEARNING_TABLES)
    assert all(item["migration"] == "learning.0001_initial" for item in dictionary["objects"])
    security_migrations = {
        item["table"]: item["security_migration"] for item in dictionary["objects"]
    }
    assert security_migrations == {
        "enrollments": "learning.0003_enrollment_management_only",
        "course_progress": "learning.0002_learning_security",
        "lesson_progress": "learning.0002_learning_security",
    }


@pytest.mark.django_db
def test_migrated_learning_schema_matches_catalog_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    assert database_fingerprint() == dictionary["database_fingerprint"]
    assert all(item["rls"] == "ENABLE + FORCE" for item in dictionary["objects"])


@pytest.mark.django_db
def test_database_catalog_contains_named_learning_constraints_indexes_and_helpers() -> None:
    expected = {
        "fk_enrollments_same_tenant_membership",
        "fk_enrollments_same_tenant_course",
        "fk_enrollments_same_course_version",
        "fk_course_progress_same_tenant_enrollment",
        "fk_course_progress_same_tenant_version",
        "fk_course_progress_same_version_resume",
        "fk_lesson_progress_same_tenant_enrollment",
        "fk_lesson_progress_same_version_lesson",
        "uq_enrollments_active_learner_course",
        "uq_course_progress_enrollment",
        "uq_lesson_progress_enrollment_lesson",
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT constraint_name
              FROM information_schema.table_constraints
             WHERE constraint_schema = 'app' AND table_name = ANY(%s)
            """,
            [list(LEARNING_TABLES)],
        )
        constraints = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
             WHERE schemaname = 'app' AND tablename = ANY(%s)
            """,
            [list(LEARNING_TABLES)],
        )
        indexes = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT proname FROM pg_proc procedure
              JOIN pg_namespace namespace ON namespace.oid = procedure.pronamespace
             WHERE namespace.nspname = 'app' AND proname LIKE '%%learning%%'
            """
        )
        helpers = {row[0] for row in cursor.fetchall()}
    assert expected <= constraints | indexes
    assert {
        "has_active_learning_enrollment",
        "has_learning_version_access",
        "has_learning_course_access",
        "lock_active_learning_membership",
    } <= helpers

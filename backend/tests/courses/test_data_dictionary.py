from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from django.db import connection

DICTIONARY_PATH = Path("backend/src/lms/modules/courses/migrations/course_schema_v1.json")
COURSE_TABLES = (
    "course_instructors",
    "course_publication_reviews",
    "course_versions",
    "courses",
    "curriculum_sections",
    "lesson_content_blocks",
    "lessons",
)


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
            [list(COURSE_TABLES)],
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
            [list(COURSE_TABLES)],
        )
        catalog["constraints"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT tablename, indexname, indexdef
              FROM pg_indexes
             WHERE schemaname = 'app' AND tablename = ANY(%s)
             ORDER BY tablename, indexname
            """,
            [list(COURSE_TABLES)],
        )
        catalog["indexes"] = cursor.fetchall()
        cursor.execute(
            """
            SELECT tablename, policyname, cmd, roles::text, qual, with_check
              FROM pg_policies
             WHERE schemaname = 'app' AND tablename = ANY(%s)
             ORDER BY tablename, policyname
            """,
            [list(COURSE_TABLES)],
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
            [list(COURSE_TABLES)],
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
            [list(COURSE_TABLES)],
        )
        catalog["security"] = cursor.fetchall()
    encoded = json.dumps(catalog, sort_keys=True, separators=(",", ":"), default=str).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def test_course_dictionary_has_a_reproducible_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    encoded = json.dumps(dictionary["objects"], sort_keys=True, separators=(",", ":")).encode()
    assert dictionary["schema_fingerprint"] == f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    assert {item["table"] for item in dictionary["objects"]} == {
        "courses",
        "course_versions",
        "course_instructors",
        "curriculum_sections",
        "lessons",
        "lesson_content_blocks",
        "course_publication_reviews",
    }
    assert all(item["migration"] == "courses.0001_initial" for item in dictionary["objects"])
    assert all(
        item["security_migration"] == "courses.0002_course_security"
        for item in dictionary["objects"]
    )
    versions = next(item for item in dictionary["objects"] if item["table"] == "course_versions")
    assert versions["successor_migration"] == "courses.0003_one_successor"


@pytest.mark.django_db
def test_migrated_course_schema_matches_catalog_fingerprint() -> None:
    dictionary = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    assert database_fingerprint() == dictionary["database_fingerprint"]
    assert all(item["rls"] == "ENABLE + FORCE" for item in dictionary["objects"])


@pytest.mark.django_db
def test_database_catalog_contains_named_course_constraints_and_indexes() -> None:
    expected_constraints = {
        "fk_versions_same_tenant_course",
        "fk_versions_same_course_predecessor",
        "fk_courses_current_version",
        "fk_instructors_same_tenant_course",
        "fk_instructors_same_tenant_member",
        "fk_sections_same_tenant_version",
        "fk_lessons_same_version_section",
        "fk_blocks_same_version_lesson",
        "fk_reviews_same_tenant_version",
        "ck_blocks_document_object",
        "ck_reviews_reason_codes_array",
        "uq_versions_one_successor",
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT constraint_name
              FROM information_schema.table_constraints
             WHERE constraint_schema = 'app'
               AND table_name IN (
                    'courses', 'course_versions', 'course_instructors',
                    'curriculum_sections', 'lessons', 'lesson_content_blocks',
                    'course_publication_reviews'
               )
            """
        )
        constraints = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT indexname
              FROM pg_indexes
             WHERE schemaname = 'app'
               AND tablename IN (
                    'courses', 'course_versions', 'course_instructors',
                    'curriculum_sections', 'lessons', 'lesson_content_blocks',
                    'course_publication_reviews'
               )
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}
    assert expected_constraints <= constraints | indexes

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT class.relname, pg_get_constraintdef(constraint_row.oid, true)
              FROM pg_constraint constraint_row
              JOIN pg_class class ON class.oid = constraint_row.conrelid
              JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
             WHERE namespace.nspname = 'app'
               AND class.relname = ANY(%s)
               AND constraint_row.contype = 'u'
            """,
            [list(COURSE_TABLES)],
        )
        unique_definitions: dict[str, set[str]] = {}
        for table, definition in cursor.fetchall():
            unique_definitions.setdefault(table, set()).add(definition)
        cursor.execute(
            """
            SELECT tablename, indexdef
              FROM pg_indexes
             WHERE schemaname = 'app' AND tablename = ANY(%s)
            """,
            [list(COURSE_TABLES)],
        )
        tenant_first_indexes = {
            table for table, definition in cursor.fetchall() if "(tenant_id" in definition
        }
    assert all("UNIQUE (tenant_id, id)" in unique_definitions[table] for table in COURSE_TABLES)
    assert tenant_first_indexes == set(COURSE_TABLES)

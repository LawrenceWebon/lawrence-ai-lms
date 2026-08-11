from __future__ import annotations

import os

import psycopg
import pytest

pytestmark = pytest.mark.rls


def database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:55432/postgres",
    )


def test_api_runtime_role_is_non_owner_and_cannot_bypass_rls() -> None:
    with psycopg.connect(database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT rolsuper, rolcreatedb, rolcreaterole, rolcanlogin,
                       rolreplication, rolbypassrls
                  FROM pg_roles
                 WHERE rolname = 'lms_api_runtime'
                """
            )
            assert cursor.fetchone() == (False, False, False, True, False, False)

            cursor.execute(
                """
                SELECT tableowner
                  FROM pg_tables
                 WHERE schemaname = 'app' AND tablename = 'user_profiles'
                """
            )
            assert cursor.fetchone() == ("lms_object_owner",)


def test_api_runtime_role_has_no_ddl_or_owner_shortcut() -> None:
    with psycopg.connect(database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT has_table_privilege(%s, %s, %s)",
                ("lms_api_runtime", "app.user_profiles", "SELECT"),
            )
            assert cursor.fetchone() == (False,)

            cursor.execute("SET LOCAL ROLE lms_api_runtime")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("CREATE TABLE app.role_escape (id integer)")
        connection.rollback()

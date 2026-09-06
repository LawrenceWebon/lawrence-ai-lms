from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_learning_migrations_reverse_and_roll_forward() -> None:
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([("learning", None)])
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('app.enrollments')")
            assert cursor.fetchone() == (None,)
            cursor.execute("SELECT count(*) FROM app.permissions WHERE code LIKE 'learning.%%'")
            assert cursor.fetchone() == (0,)

        executor = MigrationExecutor(connection)
        executor.migrate([("learning", "0003_enrollment_management_only")])
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT class.relrowsecurity, class.relforcerowsecurity
                  FROM pg_class class
                  JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
                 WHERE namespace.nspname = 'app' AND class.relname = 'enrollments'
                """
            )
            assert cursor.fetchone() == (True, True)
            cursor.execute("SELECT count(*) FROM app.permissions WHERE code LIKE 'learning.%%'")
            assert cursor.fetchone() == (2,)
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate([("learning", "0003_enrollment_management_only")])

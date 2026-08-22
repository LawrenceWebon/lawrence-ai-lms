from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_document_migrations_reverse_and_roll_forward() -> None:
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([("documents", None)])
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('app.source_documents')")
            assert cursor.fetchone() == (None,)

        executor = MigrationExecutor(connection)
        executor.migrate([("documents", "0002_document_security")])
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT class.relrowsecurity, class.relforcerowsecurity
                  FROM pg_class class
                  JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
                 WHERE namespace.nspname = 'app' AND class.relname = 'source_documents'
                """
            )
            assert cursor.fetchone() == (True, True)
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate([("documents", "0002_document_security")])

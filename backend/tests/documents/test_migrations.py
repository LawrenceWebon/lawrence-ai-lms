from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_document_migrations_reverse_and_roll_forward() -> None:
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("documents", None)])
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('app.source_documents')")
            assert cursor.fetchone() == (None,)

        executor = MigrationExecutor(connection)
        executor.migrate([("documents", "0005_ingestion_security")])
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT namespace.nspname, class.relname,
                       class.relrowsecurity, class.relforcerowsecurity
                  FROM pg_class class
                  JOIN pg_namespace namespace ON namespace.oid = class.relnamespace
                 WHERE (namespace.nspname, class.relname) IN (
                    ('app', 'source_documents'),
                    ('app', 'document_pages'),
                    ('integration', 'document_ingestion_runs')
                 )
                 ORDER BY namespace.nspname, class.relname
                """
            )
            assert cursor.fetchall() == [
                ("app", "document_pages", True, True),
                ("app", "source_documents", True, True),
                ("integration", "document_ingestion_runs", True, True),
            ]
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(targets)

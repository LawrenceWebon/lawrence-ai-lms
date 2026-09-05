from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.course_generation.test_data_dictionary import database_fingerprint


@pytest.mark.django_db(transaction=True)
def test_generation_migrations_reverse_and_restore_the_complete_graph() -> None:
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    before = database_fingerprint()
    try:
        executor.migrate([("course_generation", None)])
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('integration.course_generation_runs')")
            assert cursor.fetchone() == (None,)
            cursor.execute(
                "SELECT to_regprocedure('app.lock_generated_course_publication(uuid,uuid,uuid)')"
            )
            assert cursor.fetchone() == (None,)
        MigrationExecutor(connection).migrate(targets)
        assert database_fingerprint() == before
    finally:
        MigrationExecutor(connection).migrate(targets)

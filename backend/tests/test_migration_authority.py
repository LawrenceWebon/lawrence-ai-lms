from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_migration_authority_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_migration_authority.py"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.django_db
def test_f001_migration_graph_orders_platform_identity_and_tenancy() -> None:
    graph = MigrationLoader(connection, ignore_no_migrations=True).graph

    assert ("platform_database", "0001_platform_baseline") in graph.node_map
    assert ("lms_identity", "0002_runtime_profile_lookup") in graph.node_map
    secure_invitation = graph.node_map[("tenancy", "0002_secure_invitation_bootstrap")]
    assert {node.key for node in secure_invitation.parents} == {
        ("lms_identity", "0002_runtime_profile_lookup"),
        ("tenancy", "0001_initial"),
    }

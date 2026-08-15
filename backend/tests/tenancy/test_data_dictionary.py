from __future__ import annotations

import json
from pathlib import Path


def test_executable_dictionary_covers_lane_b_migration() -> None:
    path = Path("database/generated/data-dictionary.json")
    dictionary = json.loads(path.read_text(encoding="utf-8"))
    assert dictionary["schema_version"] == 2
    objects = {(item["schema"], item["table"]): item for item in dictionary["objects"]}
    expected = {
        ("app", "tenants"),
        ("app", "entitlement_periods"),
        ("app", "tenant_memberships"),
        ("app", "roles"),
        ("app", "permissions"),
        ("app", "role_permissions"),
        ("app", "membership_roles"),
        ("app", "tenant_invitations"),
        ("app", "tenant_invitation_roles"),
        ("audit", "tenant_audit_facts"),
        ("integration", "idempotency_reservations"),
        ("integration", "tenant_outbox_facts"),
    }
    assert expected <= objects.keys()

    for key in expected:
        item = objects[key]
        assert item["authority"] == "Django"
        assert item["verification"]["migration"] == "tenancy.0001_initial"
        assert item["columns"]
        assert item["keys"]
        assert item["invariants"]
        assert item["access"]
        assert item["performance"]
        assert item["lifecycle"]
        if item["tenant_classification"].startswith("tenant_owned"):
            tenant_column = next(
                column for column in item["columns"] if column["name"] == "tenant_id"
            )
            assert tenant_column["nullable"] is False
            assert "UNIQUE (tenant_id,id)" in item["keys"]
            assert "FORCE" in item["access"]["rls"]

    assert (
        objects[("app", "tenant_invitations")]["verification"]["security_migration"]
        == "tenancy.0002_secure_invitation_bootstrap"
    )

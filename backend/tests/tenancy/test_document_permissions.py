from __future__ import annotations

from typing import Any

import pytest

from lms.modules.tenancy.models import RolePermission


@pytest.mark.django_db
def test_f003_permission_matrix_is_exact_and_grants_no_inferred_operation(
    tenancy_seed: dict[str, Any],
) -> None:
    rows = RolePermission.objects.filter(
        tenant_id=tenancy_seed["alpha"].id,
        permission__code__startswith="documents.",
    ).values_list("role__code", "permission__code")
    actual: dict[str, set[str]] = {
        "tenant_admin": set(),
        "instructor": set(),
        "reviewer": set(),
        "learner": set(),
    }
    for role, permission in rows:
        actual[role].add(permission)

    all_permissions = {
        "documents.sources.read",
        "documents.sources.admit",
        "documents.sources.cancel",
        "documents.source_rights.review",
    }
    assert actual == {
        "tenant_admin": all_permissions,
        "instructor": {
            "documents.sources.read",
            "documents.sources.admit",
            "documents.sources.cancel",
        },
        "reviewer": set(),
        "learner": set(),
    }
    assert not any("extract" in permission or "ocr" in permission for _, permission in rows)

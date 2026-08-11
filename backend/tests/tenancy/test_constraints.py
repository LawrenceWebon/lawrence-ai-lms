from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from lms.modules.tenancy.models import MembershipRole, Role


def test_composite_foreign_keys_reject_cross_tenant_edges(tenancy_seed: dict) -> None:
    beta_role = Role.objects.get(tenant=tenancy_seed["beta"], code="instructor")
    with pytest.raises(IntegrityError), transaction.atomic():
        MembershipRole.objects.create(
            tenant=tenancy_seed["alpha"],
            membership=tenancy_seed["memberships"]["instructor_alpha"],
            role=beta_role,
        )


def test_fixed_role_codes_reject_undeclared_roles(tenancy_seed: dict) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Role.objects.create(
            tenant=tenancy_seed["alpha"],
            code="owner",
            display_name="Owner",
        )

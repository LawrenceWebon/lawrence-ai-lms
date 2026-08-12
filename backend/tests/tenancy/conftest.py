from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from django.apps import apps
from django.conf import settings
from django.utils import timezone

# Lane B owns the app, while common application registration remains an integration
# hotspot. Register it only in this lane's focused test process.
if "lms.modules.tenancy.apps.TenancyConfig" not in settings.INSTALLED_APPS:
    settings.INSTALLED_APPS.append("lms.modules.tenancy.apps.TenancyConfig")
    apps.set_installed_apps(settings.INSTALLED_APPS)


@pytest.fixture
def tenancy_seed(db: Any) -> Iterator[dict[str, Any]]:
    from lms.modules.identity.models import UserProfile
    from lms.modules.tenancy.models import EntitlementPeriod, Tenant, TenantMembership
    from lms.modules.tenancy.services import ensure_fixed_access_catalog

    del db
    now = timezone.now()
    alpha = Tenant.objects.create(
        id=UUID("00000000-0000-4000-8000-0000000000a1"),
        slug="alpha",
        display_name="Alpha Academy",
    )
    beta = Tenant.objects.create(
        id=UUID("00000000-0000-4000-8000-0000000000b1"),
        slug="beta",
        display_name="Beta Academy",
    )
    EntitlementPeriod.objects.bulk_create(
        [
            EntitlementPeriod(
                tenant=alpha,
                status="active",
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=30),
            ),
            EntitlementPeriod(
                tenant=beta,
                status="active",
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=30),
            ),
        ]
    )
    ensure_fixed_access_catalog(alpha.id)
    ensure_fixed_access_catalog(beta.id)

    profiles = {
        "admin": UserProfile.objects.create(
            provider_subject=UUID("00000000-0000-4000-8000-000000000101")
        ),
        "instructor": UserProfile.objects.create(
            provider_subject=UUID("00000000-0000-4000-8000-000000000102")
        ),
        "learner": UserProfile.objects.create(
            provider_subject=UUID("00000000-0000-4000-8000-000000000103")
        ),
        "inactive": UserProfile.objects.create(
            provider_subject=UUID("00000000-0000-4000-8000-000000000104")
        ),
        "outsider": UserProfile.objects.create(
            provider_subject=UUID("00000000-0000-4000-8000-000000000105")
        ),
        "invitee": UserProfile.objects.create(
            provider_subject=UUID("00000000-0000-4000-8000-000000000106")
        ),
    }

    memberships = {
        "admin": TenantMembership.objects.create(
            tenant=alpha, user_profile=profiles["admin"], status="active"
        ),
        "instructor_alpha": TenantMembership.objects.create(
            tenant=alpha,
            user_profile=profiles["instructor"],
            status="active",
            row_version=2,
        ),
        "instructor_beta": TenantMembership.objects.create(
            tenant=beta, user_profile=profiles["instructor"], status="active"
        ),
        "learner": TenantMembership.objects.create(
            tenant=alpha, user_profile=profiles["learner"], status="active"
        ),
        "inactive": TenantMembership.objects.create(
            tenant=alpha,
            user_profile=profiles["inactive"],
            status="inactive",
            row_version=3,
        ),
    }

    from lms.modules.tenancy.models import MembershipRole, Role

    for name, tenant, code in (
        ("admin", alpha, "tenant_admin"),
        ("instructor_alpha", alpha, "instructor"),
        ("instructor_beta", beta, "instructor"),
        ("learner", alpha, "learner"),
        ("inactive", alpha, "learner"),
    ):
        MembershipRole.objects.create(
            tenant=tenant,
            membership=memberships[name],
            role=Role.objects.get(tenant=tenant, code=code),
        )

    yield {
        "alpha": alpha,
        "beta": beta,
        "profiles": profiles,
        "memberships": memberships,
    }
    from django.db import connection

    # Normal db tests are rolled back by pytest-django. Transactional/RLS tests
    # need explicit cleanup because common app registration is integration-owned.
    if not connection.in_atomic_block:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE app.tenants, app.permissions, app.user_profiles CASCADE")


@pytest.fixture
def runtime_role() -> Iterator[None]:
    from django.db import connection, transaction

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE lms_api_runtime")
        try:
            yield
        finally:
            transaction.set_rollback(True)

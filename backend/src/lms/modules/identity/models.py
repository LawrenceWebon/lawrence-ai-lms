from __future__ import annotations

import uuid

from django.db import models


class UserProfile(models.Model):
    """Minimal global profile anchor; credentials and sessions remain provider-owned."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_subject = models.UUIDField(unique=True, editable=False)
    status = models.CharField(max_length=16, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."user_profiles'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=("active", "inactive")),
                name="ck_user_profiles_status",
            )
        ]

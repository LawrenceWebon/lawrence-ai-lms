from __future__ import annotations

import uuid
from uuid import UUID

from django.db import models

ROLE_CODES = ("tenant_admin", "instructor", "reviewer", "learner")
MEMBERSHIP_STATUSES = ("active", "inactive")
TENANT_STATUSES = ("active", "inactive", "suspended")
ENTITLEMENT_STATUSES = ("active", "expired", "suspended")
INVITATION_STATUSES = ("active", "accepted", "expired", "revoked")


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tenant(TimestampedModel):
    objects: models.Manager[Tenant] = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=63, unique=True)
    display_name = models.CharField(max_length=120)
    status = models.CharField(max_length=16, default="active")
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."tenants'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=TENANT_STATUSES),
                name="ck_tenants_status",
            )
        ]


class EntitlementPeriod(TimestampedModel):
    objects: models.Manager[EntitlementPeriod] = models.Manager()
    tenant_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT, related_name="entitlements")
    status = models.CharField(max_length=16, default="active")
    starts_at = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."entitlement_periods'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_entitlements_tenant_id"),
            models.CheckConstraint(
                condition=models.Q(status__in=ENTITLEMENT_STATUSES),
                name="ck_entitlements_status",
            ),
            models.CheckConstraint(
                condition=models.Q(valid_until__isnull=True)
                | models.Q(valid_until__gt=models.F("starts_at")),
                name="ck_entitlements_time_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "status", "starts_at", "valid_until"),
                name="ix_entitlements_access",
            )
        ]


class TenantMembership(TimestampedModel):
    objects: models.Manager[TenantMembership] = models.Manager()
    tenant_id: UUID
    user_profile_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT, related_name="memberships")
    user_profile = models.ForeignKey(
        "lms_identity.UserProfile",
        on_delete=models.RESTRICT,
        related_name="tenant_memberships",
    )
    status = models.CharField(max_length=16, default="active")
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."tenant_memberships'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_memberships_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "user_profile"), name="uq_memberships_tenant_user"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=MEMBERSHIP_STATUSES),
                name="ck_memberships_status",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "user_profile"), name="ix_memberships_access")
        ]


class Permission(models.Model):
    objects: models.Manager[Permission] = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=96, unique=True)
    description = models.CharField(max_length=200)

    class Meta:
        db_table = 'app"."permissions'


class Role(TimestampedModel):
    objects: models.Manager[Role] = models.Manager()
    tenant_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT, related_name="roles")
    code = models.CharField(max_length=32)
    display_name = models.CharField(max_length=80)

    class Meta:
        db_table = 'app"."roles'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_roles_tenant_id"),
            models.UniqueConstraint(fields=("tenant", "code"), name="uq_roles_tenant_code"),
            models.CheckConstraint(
                condition=models.Q(code__in=ROLE_CODES), name="ck_roles_fixed_code"
            ),
        ]
        indexes = [models.Index(fields=("tenant", "code"), name="ix_roles_tenant_code")]


class RolePermission(models.Model):
    objects: models.Manager[RolePermission] = models.Manager()
    tenant_id: UUID
    role_id: UUID
    permission_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT)
    role = models.ForeignKey(Role, on_delete=models.RESTRICT, related_name="permission_links")
    permission = models.ForeignKey(Permission, on_delete=models.RESTRICT)

    class Meta:
        db_table = 'app"."role_permissions'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_role_permissions_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "role", "permission"), name="uq_role_permissions_edge"
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "role", "permission"), name="ix_role_permissions_lookup")
        ]


class MembershipRole(models.Model):
    objects: models.Manager[MembershipRole] = models.Manager()
    tenant_id: UUID
    membership_id: UUID
    role_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT)
    membership = models.ForeignKey(
        TenantMembership, on_delete=models.CASCADE, related_name="role_links"
    )
    role = models.ForeignKey(Role, on_delete=models.RESTRICT, related_name="membership_links")

    class Meta:
        db_table = 'app"."membership_roles'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_membership_roles_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "membership", "role"), name="uq_membership_roles_edge"
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "membership", "role"), name="ix_membership_roles_lookup")
        ]


class TenantInvitation(TimestampedModel):
    objects: models.Manager[TenantInvitation] = models.Manager()
    role_links: models.Manager[TenantInvitationRole]
    tenant_id: UUID
    accepted_by_id: UUID | None
    accepted_membership_id: UUID | None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT, related_name="invitations")
    email = models.EmailField(max_length=254)
    token_digest = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(max_length=16, default="active")
    expires_at = models.DateTimeField()
    accepted_by = models.ForeignKey(
        "lms_identity.UserProfile",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="accepted_tenant_invitations",
    )
    accepted_membership = models.ForeignKey(
        TenantMembership,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = 'app"."tenant_invitations'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_invitations_tenant_id"),
            models.CheckConstraint(
                condition=models.Q(status__in=INVITATION_STATUSES),
                name="ck_invitations_status",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "expires_at"), name="ix_invites_active"),
        ]


class TenantInvitationRole(models.Model):
    objects: models.Manager[TenantInvitationRole] = models.Manager()
    tenant_id: UUID
    invitation_id: UUID
    role_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT)
    invitation = models.ForeignKey(
        TenantInvitation, on_delete=models.CASCADE, related_name="role_links"
    )
    role = models.ForeignKey(Role, on_delete=models.RESTRICT)

    class Meta:
        db_table = 'app"."tenant_invitation_roles'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_invitation_roles_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "invitation", "role"), name="uq_invitation_roles_edge"
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "invitation", "role"), name="ix_invitation_roles_lookup")
        ]


class AuditFact(models.Model):
    objects: models.Manager[AuditFact] = models.Manager()
    tenant_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT)
    event_type = models.CharField(max_length=96)
    actor_id = models.UUIDField()
    subject_type = models.CharField(max_length=64)
    subject_id = models.UUIDField()
    request_id = models.UUIDField(default=uuid.uuid4)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit"."tenant_audit_facts'
        constraints = [models.UniqueConstraint(fields=("tenant", "id"), name="uq_audit_tenant_id")]
        indexes = [models.Index(fields=("tenant", "occurred_at"), name="ix_audit_tenant_time")]


class IdempotencyReservation(TimestampedModel):
    objects: models.Manager[IdempotencyReservation] = models.Manager()
    tenant_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT)
    actor_id = models.UUIDField()
    operation = models.CharField(max_length=64)
    key_digest = models.CharField(max_length=64)
    request_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default="reserved")
    response_payload = models.JSONField(default=dict)

    class Meta:
        db_table = 'integration"."idempotency_reservations'
        constraints = [
            models.UniqueConstraint(fields=("tenant", "id"), name="uq_idempotency_tenant_id"),
            models.UniqueConstraint(
                fields=("tenant", "actor_id", "operation", "key_digest"),
                name="uq_idempotency_operation_key",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("reserved", "completed")),
                name="ck_idempotency_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=("tenant", "actor_id", "operation", "key_digest"),
                name="ix_idempotency_lookup",
            )
        ]


class OutboxFact(models.Model):
    objects: models.Manager[OutboxFact] = models.Manager()
    tenant_id: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.RESTRICT)
    event_type = models.CharField(max_length=96)
    aggregate_type = models.CharField(max_length=64)
    aggregate_id = models.UUIDField()
    actor_id = models.UUIDField()
    request_id = models.UUIDField(default=uuid.uuid4)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'integration"."tenant_outbox_facts'
        constraints = [models.UniqueConstraint(fields=("tenant", "id"), name="uq_outbox_tenant_id")]
        indexes = [models.Index(fields=("tenant", "occurred_at"), name="ix_outbox_tenant_time")]

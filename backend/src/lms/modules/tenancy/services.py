from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import uuid
from collections.abc import Iterable
from datetime import timedelta
from typing import cast
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from .errors import TenancyError, denied
from .models import (
    ROLE_CODES,
    AuditFact,
    EntitlementPeriod,
    IdempotencyReservation,
    MembershipRole,
    OutboxFact,
    Permission,
    Role,
    RolePermission,
    Tenant,
    TenantInvitation,
    TenantInvitationRole,
    TenantMembership,
)
from .types import (
    AuthenticationContextResult,
    EntitlementSummary,
    InvitationReceipt,
    MembershipSummary,
    PrincipalSummary,
    TenantCandidate,
    TenantSummary,
)

PERMISSION_MEMBERSHIPS_READ = "tenancy.memberships.read"
PERMISSION_INVITATIONS_CREATE = "tenancy.invitations.create"
PERMISSION_MEMBERSHIPS_UPDATE = "tenancy.memberships.update"
PERMISSION_COURSES_READ = "courses.read"
PERMISSION_COURSE_DRAFTS_WRITE = "courses.drafts.write"
PERMISSION_COURSES_REVIEW = "courses.review"
PERMISSION_COURSES_PUBLISH = "courses.publish"
FIXED_PERMISSIONS = {
    PERMISSION_MEMBERSHIPS_READ: "List tenant memberships",
    PERMISSION_INVITATIONS_CREATE: "Create tenant invitations",
    PERMISSION_MEMBERSHIPS_UPDATE: "Update membership state and fixed roles",
    PERMISSION_COURSES_READ: "Read tenant courses",
    PERMISSION_COURSE_DRAFTS_WRITE: "Create and edit tenant course drafts",
    PERMISSION_COURSES_REVIEW: "Review tenant course versions",
    PERMISSION_COURSES_PUBLISH: "Publish and withdraw tenant course versions",
}
ROLE_DISPLAY_NAMES = {
    "tenant_admin": "Tenant administrator",
    "instructor": "Instructor",
    "reviewer": "Reviewer",
    "learner": "Learner",
}
ROLE_PERMISSION_CODES = {
    "tenant_admin": tuple(sorted(FIXED_PERMISSIONS)),
    "instructor": tuple(
        sorted(
            (
                PERMISSION_COURSES_READ,
                PERMISSION_COURSE_DRAFTS_WRITE,
                PERMISSION_COURSES_REVIEW,
                PERMISSION_COURSES_PUBLISH,
            )
        )
    ),
    "reviewer": tuple(sorted((PERMISSION_COURSES_READ, PERMISSION_COURSES_REVIEW))),
    "learner": (),
}
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class _InvitationNeedsExpiryError(Exception):
    pass


def _digest(value: str) -> str:
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _request_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _set_transaction_context(
    *,
    actor_id: UUID,
    tenant_id: UUID | None,
    invitation_digest: str = "",
    verified_email: str = "",
) -> None:
    request_id = uuid.uuid4()
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_actor_id', %s, true)", [str(actor_id)])
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, true)",
            ["" if tenant_id is None else str(tenant_id)],
        )
        cursor.execute("SELECT set_config('app.current_request_id', %s, true)", [str(request_id)])
        cursor.execute(
            "SELECT set_config('app.current_invitation_digest', %s, true)",
            [invitation_digest],
        )
        cursor.execute(
            "SELECT set_config('app.current_verified_email', %s, true)",
            [verified_email],
        )


def _actor_profile_id(actor_id: UUID) -> UUID:
    del actor_id  # The verified actor has already been installed transaction-locally.
    with connection.cursor() as cursor:
        cursor.execute("SELECT app.current_user_profile_id()")
        row = cursor.fetchone()
    if row is None or row[0] is None:
        raise denied()
    return cast(UUID, row[0])


def _current_entitlement(tenant_id: UUID) -> EntitlementPeriod | None:
    now = timezone.now()
    return (
        EntitlementPeriod.objects.filter(
            tenant_id=tenant_id,
            status="active",
            starts_at__lte=now,
        )
        .filter(models_valid_until(now))
        .order_by("-starts_at")
        .first()
    )


def _has_current_invitation_access(tenant_id: UUID) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT app.has_invitation_access(%s)", [tenant_id])
        row = cursor.fetchone()
    return row is not None and row[0] is True


def _has_current_invitation_identity_match(tenant_id: UUID) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT app.has_invitation_identity_match(%s)", [tenant_id])
        row = cursor.fetchone()
    return row is not None and row[0] is True


def models_valid_until(now: object) -> Q:
    # Kept as a tiny helper so every authorization read uses the same validity rule.
    return Q(valid_until__isnull=True) | Q(valid_until__gt=now)


def _role_codes(membership: TenantMembership) -> tuple[str, ...]:
    return tuple(
        MembershipRole.objects.filter(tenant_id=membership.tenant_id, membership_id=membership.id)
        .order_by("role__code")
        .values_list("role__code", flat=True)
    )


def _permission_codes(membership: TenantMembership) -> tuple[str, ...]:
    return tuple(
        RolePermission.objects.filter(
            tenant_id=membership.tenant_id,
            role__membership_links__membership_id=membership.id,
        )
        .order_by("permission__code")
        .values_list("permission__code", flat=True)
        .distinct()
    )


def _membership_summary(membership: TenantMembership) -> MembershipSummary:
    return MembershipSummary(
        id=membership.id,
        tenant_id=membership.tenant_id,
        status=membership.status,
        row_version=membership.row_version,
        role_codes=_role_codes(membership),
        permission_codes=_permission_codes(membership),
    )


def _active_membership(actor_id: UUID, tenant_id: UUID) -> TenantMembership:
    profile_id = _actor_profile_id(actor_id)
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        membership = TenantMembership.objects.get(tenant_id=tenant_id, user_profile_id=profile_id)
    except (Tenant.DoesNotExist, TenantMembership.DoesNotExist) as error:
        raise denied() from error
    if tenant.status != "active" or membership.status != "active":
        raise TenancyError("TENANT_ACCESS_INACTIVE", "Tenant membership is inactive.")
    if _current_entitlement(tenant_id) is None:
        raise TenancyError("TENANT_ACCESS_INACTIVE", "Tenant entitlement is inactive.")
    return membership


def _has_permission(membership: TenantMembership, permission_code: str) -> bool:
    return RolePermission.objects.filter(
        tenant_id=membership.tenant_id,
        role__membership_links__membership_id=membership.id,
        permission__code=permission_code,
    ).exists()


def _authorize(actor_id: UUID, tenant_id: UUID, permission_code: str) -> TenantMembership:
    membership = _active_membership(actor_id, tenant_id)
    if not _has_permission(membership, permission_code):
        raise denied()
    return membership


def _normalized_role_codes(role_codes: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted(set(role_codes)))
    if not normalized or any(code not in ROLE_CODES for code in normalized):
        raise denied("Only declared fixed tenant roles may be assigned.")
    return normalized


def _normalized_verified_email(email: str) -> str:
    normalized = email.strip().casefold()
    if len(normalized) > 254 or _EMAIL_PATTERN.fullmatch(normalized) is None:
        raise TenancyError("INVITATION_INVALID")
    return normalized


def ensure_fixed_access_catalog(tenant_id: UUID) -> None:
    """Provision the fixed F-001 catalog for a newly created tenant."""

    tenant = Tenant.objects.get(id=tenant_id)
    permissions: dict[str, Permission] = {}
    for code, description in FIXED_PERMISSIONS.items():
        permission_id = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-lms:permission:{code}")
        permission, _ = Permission.objects.get_or_create(
            id=permission_id, defaults={"code": code, "description": description}
        )
        permissions[code] = permission

    for role_code in ROLE_CODES:
        role_id = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-lms:{tenant_id}:role:{role_code}")
        role, _ = Role.objects.get_or_create(
            id=role_id,
            defaults={
                "tenant": tenant,
                "code": role_code,
                "display_name": ROLE_DISPLAY_NAMES[role_code],
            },
        )
        for permission_code in ROLE_PERMISSION_CODES[role_code]:
            RolePermission.objects.get_or_create(
                tenant=tenant, role=role, permission=permissions[permission_code]
            )


def get_authentication_context(
    actor_id: UUID, tenant_selector: UUID | None = None
) -> AuthenticationContextResult:
    with transaction.atomic():
        # Candidate discovery is the frozen narrow actor-only bootstrap boundary.
        _set_transaction_context(actor_id=actor_id, tenant_id=None)
        profile_id = _actor_profile_id(actor_id)
        memberships = (
            TenantMembership.objects.filter(
                user_profile_id=profile_id,
                status="active",
                tenant__status="active",
                tenant__entitlements__status="active",
                tenant__entitlements__starts_at__lte=timezone.now(),
            )
            .filter(tenant__entitlements__in=_valid_entitlements())
            .select_related("tenant")
            .distinct()
            .order_by("tenant__slug")[:100]
        )
        available = tuple(
            TenantCandidate(
                id=item.tenant_id,
                slug=item.tenant.slug,
                display_name=item.tenant.display_name,
                membership_status=item.status,
            )
            for item in memberships
        )
        if tenant_selector is None:
            return AuthenticationContextResult(
                principal=PrincipalSummary(actor_id),
                active_tenant=None,
                membership=None,
                entitlement=None,
                available_tenants=available,
            )

        # Install the untrusted selector only after discovery, then re-authorize
        # current membership and entitlement in the same transaction.
        _set_transaction_context(actor_id=actor_id, tenant_id=tenant_selector)
        membership = _active_membership(actor_id, tenant_selector)
        entitlement = _current_entitlement(tenant_selector)
        if entitlement is None:  # Defensive; _active_membership already rejects this.
            raise TenancyError("TENANT_ACCESS_INACTIVE")
        tenant = membership.tenant
        return AuthenticationContextResult(
            principal=PrincipalSummary(actor_id),
            active_tenant=TenantSummary(tenant.id, tenant.slug, tenant.display_name),
            membership=_membership_summary(membership),
            entitlement=EntitlementSummary(entitlement.status, entitlement.valid_until),
            available_tenants=available,
        )


def _valid_entitlements() -> QuerySet[EntitlementPeriod]:
    now = timezone.now()
    return EntitlementPeriod.objects.filter(status="active", starts_at__lte=now).filter(
        models_valid_until(now)
    )


def list_memberships(actor_id: UUID, tenant_selector: UUID) -> tuple[MembershipSummary, ...]:
    with transaction.atomic():
        _set_transaction_context(actor_id=actor_id, tenant_id=tenant_selector)
        _authorize(actor_id, tenant_selector, PERMISSION_MEMBERSHIPS_READ)
        memberships = TenantMembership.objects.filter(tenant_id=tenant_selector).order_by(
            "created_at", "id"
        )
        return tuple(_membership_summary(item) for item in memberships)


def _fact_payload(
    *, status: str, role_codes: tuple[str, ...], row_version: int
) -> dict[str, object]:
    return {"status": status, "role_codes": list(role_codes), "row_version": row_version}


def _record_facts(
    *,
    actor_id: UUID,
    tenant_id: UUID,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: dict[str, object],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.current_request_id')")
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Missing transaction request context")
    request_id = uuid.UUID(str(row[0]))
    AuditFact.objects.create(
        tenant_id=tenant_id,
        event_type=event_type,
        actor_id=actor_id,
        subject_type=aggregate_type,
        subject_id=aggregate_id,
        request_id=request_id,
        payload=payload,
    )
    OutboxFact.objects.create(
        tenant_id=tenant_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        actor_id=actor_id,
        request_id=request_id,
        payload=payload,
    )


def create_invitation(
    actor_id: UUID,
    tenant_selector: UUID,
    email: str,
    role_codes: Iterable[str],
    idempotency_key: str,
) -> InvitationReceipt:
    normalized_email = email.strip().casefold()
    normalized_roles = _normalized_role_codes(role_codes)
    if not (16 <= len(idempotency_key) <= 128) or "@" not in normalized_email:
        raise denied("Invitation input is invalid.")
    request_hash = _request_hash({"email": normalized_email, "role_codes": normalized_roles})
    key_digest = _digest(idempotency_key)

    with transaction.atomic():
        _set_transaction_context(actor_id=actor_id, tenant_id=tenant_selector)
        _authorize(actor_id, tenant_selector, PERMISSION_INVITATIONS_CREATE)
        reservation, _ = IdempotencyReservation.objects.get_or_create(
            tenant_id=tenant_selector,
            actor_id=actor_id,
            operation="create_invitation",
            key_digest=key_digest,
            defaults={"request_hash": request_hash},
        )
        reservation = IdempotencyReservation.objects.select_for_update().get(id=reservation.id)
        if reservation.request_hash != request_hash:
            raise TenancyError("IDEMPOTENCY_CONFLICT")
        if reservation.status == "completed":
            invitation = TenantInvitation.objects.get(
                id=UUID(str(reservation.response_payload["invitation_id"])),
                tenant_id=tenant_selector,
            )
            return InvitationReceipt(
                invitation.id,
                invitation.tenant_id,
                invitation.status,
                invitation.expires_at,
            )

        roles = list(
            Role.objects.filter(tenant_id=tenant_selector, code__in=normalized_roles).order_by(
                "code"
            )
        )
        if len(roles) != len(normalized_roles):
            raise denied("Only declared fixed tenant roles may be assigned.")

        raw_token = secrets.token_urlsafe(32)
        invitation = TenantInvitation.objects.create(
            tenant_id=tenant_selector,
            email=normalized_email,
            token_digest=_digest(raw_token),
            expires_at=timezone.now() + timedelta(hours=24),
        )
        TenantInvitationRole.objects.bulk_create(
            [
                TenantInvitationRole(tenant_id=tenant_selector, invitation=invitation, role=role)
                for role in roles
            ]
        )
        payload: dict[str, object] = {
            "status": invitation.status,
            "role_codes": list(normalized_roles),
        }
        _record_facts(
            actor_id=actor_id,
            tenant_id=tenant_selector,
            event_type="tenant.invitation.created.v1",
            aggregate_type="tenant_invitation",
            aggregate_id=invitation.id,
            payload=payload,
        )
        reservation.status = "completed"
        reservation.response_payload = {"invitation_id": str(invitation.id)}
        reservation.save(update_fields=("status", "response_payload", "updated_at"))
        return InvitationReceipt(
            invitation.id,
            invitation.tenant_id,
            invitation.status,
            invitation.expires_at,
            raw_token,
        )


def accept_invitation(
    actor_id: UUID, verified_email: str, invitation_token: str
) -> MembershipSummary:
    if not (32 <= len(invitation_token) <= 512):
        raise TenancyError("INVITATION_INVALID")
    normalized_email = _normalized_verified_email(verified_email)
    token_digest = _digest(invitation_token)
    try:
        with transaction.atomic():
            _set_transaction_context(
                actor_id=actor_id,
                tenant_id=None,
                invitation_digest=token_digest,
                verified_email=normalized_email,
            )
            profile_id = _actor_profile_id(actor_id)
            try:
                invitation = TenantInvitation.objects.get(token_digest=token_digest)
            except TenantInvitation.DoesNotExist as error:
                raise TenancyError("INVITATION_INVALID") from error

            _set_transaction_context(
                actor_id=actor_id,
                tenant_id=invitation.tenant_id,
                invitation_digest=token_digest,
                verified_email=normalized_email,
            )
            if invitation.email != normalized_email:
                raise TenancyError("INVITATION_INVALID")
            if invitation.status == "expired":
                if not _has_current_invitation_identity_match(invitation.tenant_id):
                    raise TenancyError("INVITATION_INVALID")
                raise TenancyError("INVITATION_EXPIRED")
            try:
                invitation = TenantInvitation.objects.select_for_update().get(id=invitation.id)
            except TenantInvitation.DoesNotExist as error:
                raise TenancyError("INVITATION_INVALID") from error
            if invitation.email != normalized_email:
                raise TenancyError("INVITATION_INVALID")
            if not _has_current_invitation_access(invitation.tenant_id):
                raise TenancyError("INVITATION_INVALID")
            if invitation.status == "accepted":
                if (
                    invitation.accepted_by_id != profile_id
                    or invitation.accepted_membership is None
                ):
                    raise TenancyError("INVITATION_INVALID")
                return _membership_summary(invitation.accepted_membership)
            if invitation.expires_at <= timezone.now():
                raise _InvitationNeedsExpiryError
            if invitation.status != "active":
                raise TenancyError("INVITATION_INVALID")

            membership, created = TenantMembership.objects.get_or_create(
                tenant_id=invitation.tenant_id,
                user_profile_id=profile_id,
                defaults={"status": "active"},
            )
            if not created and membership.status != "active":
                membership.status = "active"
                membership.row_version += 1
                membership.save(update_fields=("status", "row_version", "updated_at"))

            invited_role_ids = invitation.role_links.values_list("role_id", flat=True)
            roles = list(
                Role.objects.filter(
                    tenant_id=invitation.tenant_id,
                    id__in=invited_role_ids,
                ).order_by("code")
            )
            MembershipRole.objects.filter(
                tenant_id=invitation.tenant_id, membership=membership
            ).delete()
            MembershipRole.objects.bulk_create(
                [
                    MembershipRole(tenant_id=invitation.tenant_id, membership=membership, role=role)
                    for role in roles
                ]
            )
            invitation.status = "accepted"
            invitation.accepted_by_id = profile_id
            invitation.accepted_membership = membership
            invitation.accepted_at = timezone.now()
            invitation.row_version += 1
            invitation.save(
                update_fields=(
                    "status",
                    "accepted_by",
                    "accepted_membership",
                    "accepted_at",
                    "row_version",
                    "updated_at",
                )
            )
            summary = _membership_summary(membership)
            _record_facts(
                actor_id=actor_id,
                tenant_id=invitation.tenant_id,
                event_type="tenant.membership.activated.v1",
                aggregate_type="tenant_membership",
                aggregate_id=membership.id,
                payload=_fact_payload(
                    status=summary.status,
                    role_codes=summary.role_codes,
                    row_version=summary.row_version,
                ),
            )
            return summary
    except _InvitationNeedsExpiryError:
        with transaction.atomic():
            _set_transaction_context(
                actor_id=actor_id,
                tenant_id=None,
                invitation_digest=token_digest,
                verified_email=normalized_email,
            )
            invitation = TenantInvitation.objects.select_for_update().get(token_digest=token_digest)
            if invitation.email != normalized_email:
                raise TenancyError("INVITATION_INVALID") from None
            if invitation.status == "active" and invitation.expires_at <= timezone.now():
                invitation.status = "expired"
                invitation.row_version += 1
                invitation.save(update_fields=("status", "row_version", "updated_at"))
        raise TenancyError("INVITATION_EXPIRED") from None


def update_membership(
    actor_id: UUID,
    tenant_selector: UUID,
    membership_id: UUID,
    *,
    status: str | None = None,
    role_codes: Iterable[str] | None = None,
    row_version: int,
) -> MembershipSummary:
    if status is not None and status not in ("active", "inactive"):
        raise denied("Membership status is invalid.")
    normalized_roles = None if role_codes is None else _normalized_role_codes(role_codes)
    if status is None and normalized_roles is None:
        raise denied("No membership change was supplied.")

    with transaction.atomic():
        _set_transaction_context(actor_id=actor_id, tenant_id=tenant_selector)
        _authorize(actor_id, tenant_selector, PERMISSION_MEMBERSHIPS_UPDATE)
        try:
            current = TenantMembership.objects.get(id=membership_id, tenant_id=tenant_selector)
        except TenantMembership.DoesNotExist as error:
            raise denied() from error
        new_status = current.status if status is None else status
        updated = TenantMembership.objects.filter(
            id=membership_id,
            tenant_id=tenant_selector,
            row_version=row_version,
        ).update(status=new_status, row_version=row_version + 1, updated_at=timezone.now())
        if updated != 1:
            raise TenancyError("VERSION_CONFLICT")

        if normalized_roles is not None:
            roles = list(
                Role.objects.filter(tenant_id=tenant_selector, code__in=normalized_roles).order_by(
                    "code"
                )
            )
            if len(roles) != len(normalized_roles):
                raise denied("Only declared fixed tenant roles may be assigned.")
            MembershipRole.objects.filter(
                tenant_id=tenant_selector, membership_id=membership_id
            ).delete()
            MembershipRole.objects.bulk_create(
                [
                    MembershipRole(
                        tenant_id=tenant_selector,
                        membership_id=membership_id,
                        role=role,
                    )
                    for role in roles
                ]
            )

        membership = TenantMembership.objects.get(id=membership_id, tenant_id=tenant_selector)
        summary = _membership_summary(membership)
        if status == "inactive":
            event_type = "tenant.membership.deactivated.v1"
        elif status == "active" and current.status != "active":
            event_type = "tenant.membership.activated.v1"
        else:
            event_type = "tenant.membership.roles_changed.v1"
        _record_facts(
            actor_id=actor_id,
            tenant_id=tenant_selector,
            event_type=event_type,
            aggregate_type="tenant_membership",
            aggregate_id=membership.id,
            payload=_fact_payload(
                status=summary.status,
                role_codes=summary.role_codes,
                row_version=summary.row_version,
            ),
        )
        return summary

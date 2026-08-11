# Technical Decisions — F-001 Minimal Identity and Tenant Context

## Existing architecture to reuse

- Modular monolith and adapter → application service → policy/model direction.
- Django-only schema/migration authority; FastAPI-only HTTP/OpenAPI authority.
- Supabase Auth for identity/session, PostgreSQL for authorization.
- One transaction-bound execution context under non-owner forced-RLS roles.
- RFC Problem Details, `/api/v1`, stable operation IDs, generated TypeScript client.

## Frozen contracts

### Authentication context v1

`GET /api/v1/auth-context` accepts an optional `X-Tenant-ID` selector and returns:

```text
principal: { user_id, authentication_time, assurance_level }
active_tenant: null | { id, slug, display_name }
membership: null | { id, status, row_version, role_codes[], permission_codes[] }
entitlement: null | { status, valid_until }
available_tenants[]: { id, slug, display_name, membership_status }
```

The selector and returned codes are presentation data; every protected command repeats
database authorization. Multiple memberships never produce an implicit active tenant.

### Membership administration v1

- `GET /api/v1/tenants/{tenant_id}/memberships`
- `POST /api/v1/tenants/{tenant_id}/invitations` with idempotency key
- `POST /api/v1/tenant-invitations/accept` with token in the body
- `PATCH /api/v1/tenants/{tenant_id}/memberships/{membership_id}` with `row_version`

Problem codes: `AUTHENTICATION_REQUIRED`, `TOKEN_INVALID`,
`TENANT_CONTEXT_REQUIRED`, `TENANT_ACCESS_DENIED`, `TENANT_ACCESS_INACTIVE`,
`INVITATION_INVALID`, `INVITATION_EXPIRED`, `IDEMPOTENCY_CONFLICT`, and
`VERSION_CONFLICT`.

### Event facts v1

- `tenant.invitation.created.v1`
- `tenant.membership.activated.v1`
- `tenant.membership.roles_changed.v1`
- `tenant.membership.deactivated.v1`

Events contain opaque identifiers and classifications, never invitation tokens or email bodies.

### Synthetic fixtures v1

- tenants Alpha and Beta with active local entitlements;
- users: Alpha admin, multi-tenant instructor, Alpha learner, inactive member, outsider;
- active/expired/revoked invitations and stale role/membership versions;
- production-equivalent API runtime role with forced RLS.

## Data contract to complete before migration

Minimum objects: `user_profiles`, `tenants`, `entitlement_periods`,
`tenant_memberships`, `roles`, `permissions`, `role_permissions`, `membership_roles`,
`tenant_invitations`, immutable audit facts, idempotency reservations, and outbox facts.
Every tenant-owned object has non-null `tenant_id`, `UNIQUE (tenant_id,id)`, composite
same-tenant foreign keys, tenant-first indexes, explicit retention/delete behavior,
and one owning Django migration.

## Decisions

### TD-001 — Provider identity is not authorization

- Status: approved.
- Decision: verified Supabase subject identifies the principal; application membership,
  entitlement, role, permission, and scope are re-read from PostgreSQL per transaction.
- Tradeoff: more database reads in exchange for immediate revocation and one authority.

### TD-002 — Explicit tenant selector

- Status: approved.
- Decision: use optional `X-Tenant-ID` as an untrusted selector for v1; no default is
  chosen when multiple memberships exist.
- Alternatives: tenant in JWT rejected as authority; custom domains deferred.
- Revisit: when custom routing is separately approved.

### TD-003 — Fixed initial tenant roles

- Status: approved.
- Decision: seed `tenant_admin`, `instructor`, `reviewer`, and `learner`; permissions are
  normalized and feature-owned. No custom-role editor in F-001.
- Tradeoff: less flexibility, smaller auditable permission surface.

### TD-004 — Private idempotent invitation acceptance

- Status: approved.
- Decision: store only a keyed token digest, expiry, intended tenant/email/role request,
  status, and audit lineage. Acceptance binds only to the verified identity and locks
  the invitation/membership result.
- Tradeoff: delivery/reissue needs explicit state but replay and token leakage are controlled.

### TD-005 — No asynchronous business job

- Status: approved.
- Decision: identity/context and membership changes are short local transactions.
  Invitation delivery is an optional outbox consumer using a local sink; provider email
  is not required.

### TD-006 — Phase 0 toolchain selection is a controlled prerequisite

- Status: approved and evidenced by merged PR #4 and the pinned toolchain record.
- Decision: use the approved Python/Node stacks and expose repository scripts for lint,
  typecheck, tests, migration drift, OpenAPI compatibility, and Playwright. Do not pin
  versions in this document or copy historical examples.

### TD-008 — Local project dependencies execute only in Docker Compose

- Status: approved by the project owner on 2026-08-11.
- Decision: AI LMS worktrees live under the exact
  `/home/lawrence/Project Neo/worktrees/ai-lms/` root. Each issue starts an isolated
  Compose project with `docker compose up -d --build`; Python, Node, and Playwright
  project dependencies remain in pinned images/containers and are reused. Host
  `.venv` and host project dependency installation are prohibited.
- Tradeoff: the first image build is larger, while later commands share exact runtime
  layers and avoid worktree-specific dependency installation.

### TD-007 — Narrow pre-tenant bootstrap boundary

- Status: approved.
- Decision: only two authenticated operations may run before a tenant context exists:
  list the current principal's minimal membership candidates, and accept a presented
  invitation. They set actor/request context, use narrowly granted services/functions,
  return no tenant content, and establish/re-derive the tenant before any tenant write.
- Alternatives: tenant claims as authority rejected; implicit tenant selection rejected.
- Tradeoff: one explicit bootstrap boundary requires its own grants/RLS tests but avoids
  a broad cross-tenant runtime role.
- Revisit: if the identity provider gains an approved, strongly consistent membership authority.

## Shared hotspots and owner

The integration owner exclusively owns root manifests/lockfiles, common settings and
composition, base/user-profile and platform-database migrations, CI, OpenAPI source and
generated client, event baselines, and `manifest.json`. Lane agents consume the frozen
contracts and do not edit those paths.

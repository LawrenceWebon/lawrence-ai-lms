# Test Plan — F-001 Minimal Identity and Tenant Context

## Strategy

Tests lead each lane. Deterministic software tests use synthetic Alpha/Beta tenants and
production-equivalent PostgreSQL roles. There is no AI evaluation for F-001.

## Step 0 foundation

- Reproducible install and documented command smoke tests.
- Architecture imports reject router/Admin direct model writes and duplicate migration authority.
- Generated OpenAPI/client baseline and schema fingerprint reproduce without drift.
- Test runtime proves API role is non-owner and lacks `BYPASSRLS`.

## Lane A identity/JWT

- Missing, malformed, expired, future, wrong issuer/project/audience/role/algorithm/key tokens.
- Unknown `kid` refresh-once, key cache outage, rotation overlap, revoked/disabled user.
- Verified identity with absent/inactive membership still receives no tenant authority.
- Pre-tenant discovery returns only the actor's minimal candidate descriptors and cannot access tenant content or accept a token for another verified identity.
- Transaction-local actor/tenant context resets after commit, rollback, exception, and pool reuse.

## Lane B tenancy/RLS

- Active tenant + membership + entitlement + declared permission allows context.
- Missing/inactive/suspended tenant, membership, entitlement, role, or permission denies.
- Cross-tenant select/insert/update/delete and guessed IDs fail under API role.
- Conflicting path/header selectors fail without revealing which tenant exists.
- Composite FK rejects tenant changes and cross-tenant role/membership edges.
- Concurrent role/status update yields one success and one `VERSION_CONFLICT`.
- Audit and outbox commit atomically; rollback leaves neither partial mutation nor event.

## Lane C invitation/API/Admin

- Tenant admin creates an invitation only for own tenant and allowed fixed role.
- Same idempotency key/request returns the same result; changed request conflicts.
- Raw token is absent from database, logs, errors, events, and snapshots.
- Valid matching identity accepts once; repeat is idempotent; wrong identity, expired,
  revoked, consumed, cross-tenant, or guessed token fails neutrally.
- Non-admin cannot invite, change roles, activate/deactivate, or bypass through Admin.
- API returns OpenAPI-conformant RFC Problem Details for every error class.

## Lane D web

- Sign-in, invitation, tenant list, explicit selection, loading, empty, error, denied,
  and session-expired states render from fixtures.
- Multiple memberships never auto-select; single membership behavior follows the same explicit contract.
- Keyboard order, visible focus, labels, error association, live status, zoom/reflow, and locale-safe text pass.
- No core-table browser client or authorization based on hidden controls.

## Integration and E2E

1. Admin invites instructor; instructor authenticates, accepts, selects Alpha, and reads context.
2. Multi-tenant instructor switches Alpha/Beta and receives only current authorized context.
3. Outsider supplies Alpha selector and receives no tenant data.
4. Admin revokes membership; the next request and open UI session fail closed.
5. Concurrent invitation acceptance and role changes remain single-effect and auditable.

## Failure/recovery

- JWKS unavailable, PostgreSQL unavailable, and pool/context reset failure all fail closed.
- Duplicate submit/retry is safe; no async job is introduced.
- Local email sink failure does not revoke a created invitation; retry uses the same outbox fact.

## Explicitly not required

- OCR, upload, AI, RAG, payment, course, enrollment, quiz, worker, real email, analytics,
  load/capacity, provider sandbox, or production deployment tests.

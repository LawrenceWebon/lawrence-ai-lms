# F-001 — Minimal Identity and Tenant Context

## Status

Planning complete. Step 0 merged in PR #4 and the Docker-only workflow amendment
merged in PR #6. The readiness audit passes against `develop` at
`b34ba7ac377a6a12363b036ece3d682d0b0ecdd8`; lanes A-D are ready for issue creation
and independently isolated implementation.

## Product reference

- Feature ID: F-001
- Product: `docs/product/spec.md`
- Inventory: `docs/product/features.md`
- Decisions: P-003, P-005, P-006, P-007, P-009
- Prerequisite: F-000 documentation/Codex setup; engineering scaffold is Step 0 below

## Summary

An invited member signs in, selects an active tenant they belong to, and receives only
the permissions authorized by current PostgreSQL membership and entitlement state.
This establishes the authority boundary required by every later PDF and course action.

## Actors

- Tenant administrator: invites members and manages their minimal tenant roles.
- Instructor/reviewer: enters an authorized tenant context for later authoring work.
- Learner: enters an authorized tenant context for later enrollment and playback.
- Platform operator: can manage platform lifecycle without standing tenant-content access.

## Goals

- Authenticate a user through the approved Supabase identity/session boundary.
- Resolve an active tenant from current database membership and entitlement state.
- Return a stable authorization context for API and web consumers.
- Permit tenant administrators to invite, activate/deactivate, and assign minimal roles.
- Deny missing, stale, inactive, revoked, and cross-tenant access consistently.
- Record immutable security/audit facts for membership and role changes.

## Non-goals

- Public registration or tenant self-service purchase.
- Course, PDF, generation, enrollment, learner-content, billing, or RAG behavior.
- Custom domains, social login, enterprise SSO, broad profile management, or real email.
- Standing support impersonation or a privileged tenant-content UI.
- Production data, deployment, provider procurement, or analytics.

## User flow

1. A tenant administrator creates a single-use, expiring invitation for an email and
   approved tenant role.
2. The recipient authenticates and submits the invitation token; the server binds the
   verified identity to one active tenant membership without trusting token role data.
3. The signed-in member requests authentication context. With no tenant selector, the
   response lists only their active tenant memberships.
4. The member selects a tenant. Every tenant-scoped request supplies that untrusted
   selector and the server re-derives active user, membership, entitlement, roles,
   permissions, and resource scope inside the database transaction.
5. The web UI shows the active tenant and only permitted actions. Hidden controls are
   not authorization.
6. If membership, role, entitlement, or session state changes, the next protected
   request fails closed or returns the updated context.

## Functional requirements

- The system is private: only provisioned/invited identities can obtain membership.
- Supabase Auth owns credentials/session identity; PostgreSQL owns profile, tenant,
  membership, entitlement, role, permission, invitation, audit, and authorization state.
- Tenant selectors from path/header/browser/JWT are never authority.
- The API uses one non-owner, non-`BYPASSRLS` transaction and transaction-local context.
- Before tenant selection, only minimal self-membership discovery and invitation
  acceptance are allowed through the narrowly granted bootstrap boundary; they expose
  no tenant content and cannot authorize any other command.
- Tenant-owned relationships use composite same-tenant integrity and forced RLS.
- Invitation creation and acceptance are idempotent; token values are never stored or logged in plaintext.
- Role/membership changes use version comparison and cannot grant undeclared permissions.
- No tenant context is silently selected when more than one active membership exists.
- Operators have no tenant-content path in this feature; future privileged access must use the approved JIT design.

## Acceptance criteria

- A valid invited user can authenticate, accept one invitation, and resolve its tenant context.
- Repeating the same acceptance returns the same membership result without duplication.
- A user with two memberships sees only those tenants and must explicitly select one.
- Missing/invalid authentication returns RFC Problem Details with `401`.
- Missing tenant selection on a tenant-scoped request returns `TENANT_CONTEXT_REQUIRED`.
- Unknown, inactive, revoked, expired-entitlement, or wrong-tenant access fails closed with no protected data.
- A path/header tenant mismatch is denied rather than choosing either selector.
- A tenant administrator can invite and change allowed roles only inside their tenant.
- Instructor, reviewer, learner, and tenant administrator cannot grant permissions they do not possess.
- Role/membership changes are effective on the next request and produce audit/outbox facts atomically.
- Production-role RLS, pool-reset, IDOR, stale-membership, duplicate, and concurrent-change tests pass.
- Keyboard, focus, label, validation-error, loading, empty, and access-denied states pass the applicable WCAG checks.

## Dependencies

- Approved modular-monolith and Django/FastAPI boundary ADRs.
- Supabase Auth/JWT contract and local synthetic Supabase project.
- Phase 0 web/API/Django/test/OpenAPI scaffold and exact lockfiles.
- Executable identity/tenancy data dictionary before migrations.

## Constraints

- Synthetic users and tenant data only until documents 25/26 are approved.
- No browser core-table CRUD; Next.js consumes the generated API client.
- No session-scoped tenant database setting and no alternate Admin authorization path.
- Authentication and authorization errors avoid account/tenant enumeration.
- No provider secret, bearer token, email, or sensitive profile data in logs/fixtures.

## Assumptions

- Email/password plus verification is sufficient for the local first slice.
- Invitation delivery uses a local test sink or displayed fixture token; real email is separate.
- One membership can hold multiple seeded tenant roles; feature permissions are added by their owning future features.

## Open questions

None blocks feature design. Exact supported framework/tool versions are selected and
recorded during the Phase 0 scaffold from current supported releases, not copied from
historical examples.

## Existing architecture relevant to this feature

- Verified: Step 0 provides pinned manifests, a minimal scaffold, migrations, routes,
  contracts, and tests; PR #6 adds the owner-required Docker-only execution workflow
  at `b34ba7ac377a6a12363b036ece3d682d0b0ecdd8`.
- Approved target: Next.js web, FastAPI HTTP/OpenAPI, Django models/services/migrations/Admin, PostgreSQL RLS, Supabase Auth.
- Approved boundaries: ADR-0001, ADR-0002, plan documents 01, 03–05, 11–12, 15, 19–20, 22–24.
- Existing external dependency: none configured; `SOURCES.md` entries S-01–S-15 remain within their 2026-09-01 recheck window.
- Conflict resolved by plan: JWT and browser claims are selectors; database membership is authority.
- Known toolchain: exact supported versions, locks, images, and stable commands were
  recorded by Step 0; local Supabase remains outside this foundation amendment.

## Explicitly out of scope

- Generic IAM/policy engines, organization graphs, bulk import/export, custom roles UI,
  notification center, user directory search, profile avatars, account deletion, and SSO.
- Course permissions beyond stable placeholder role identities needed by later features.
- QStash, Redis, worker, OCR, storage, AI, Pinecone, payment, PostHog, or production Sentry setup.

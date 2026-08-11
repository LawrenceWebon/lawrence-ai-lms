# Implementation Plan — F-001 Minimal Identity and Tenant Context

Status: **Step 0 implementation in progress; lanes not started**

GitHub issue #1 and its linked branch are active for Step 0. Lane and integration issue
IDs remain local until the Step 0 PR merges and this feature passes a new readiness
audit.

## Dependency graph

```text
Step 0 foundation/contracts
        |
        +--> Lane A JWT/execution context ----+
        +--> Lane B tenancy domain/RLS -------+--> Step 5 integration
        +--> Lane C membership API/Admin -----+
        +--> Lane D web UX/E2E fixtures -------+
```

At most four lanes are active after Step 0. They target the owner-approved `develop`
branch, use frozen fixtures, and do not import sibling branches. Step 5 starts only
after lane PRs merge.

| Step | Local issue | Owner | Branch template | Owned paths | Depends on | PR order |
|---|---|---|---|---|---|---|
| 0 | [#1](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/1) | Integration owner | `chore/LMS-1-foundation-contracts` | root manifests/locks, scaffold/composition, CI, base profile/platform migrations, contracts and fixtures | docs | 1 |
| A | LOCAL-F001-A | Agent A | `feature/LMS-<issue>-jwt-context` | identity module, JWT/API auth dependency, identity tests | Step 0 contracts | 2–5 |
| B | LOCAL-F001-B | Agent B | `feature/LMS-<issue>-tenant-membership` | tenancy domain/services/policies/migrations/RLS and tests | Step 0 contracts | 2–5 |
| C | LOCAL-F001-C | Agent C | `feature/LMS-<issue>-membership-api-admin` | membership/invitation FastAPI routers/schemas and adapter-only Admin plus tests | Step 0 service fakes | 2–5 |
| D | LOCAL-F001-D | Agent D | `feature/LMS-<issue>-tenant-context-web` | web auth/tenant-context features and isolated E2E fixture/spec paths | Step 0 TS fixtures | 2–5 |
| 5 | LOCAL-F001-I | Integration owner | `feature/LMS-<issue>-identity-integration` | composition, OpenAPI/client regeneration, shared migration order, full E2E/evidence | A–D merged | 6 |

## Isolation contract

- One issue, owner, branch, worktree, local database/schema, ports, and PR.
- Agents stage only owned paths and never edit root locks, common settings, OpenAPI,
  generated client, CI, or the documentation manifest.
- Each lane tests against committed v1 schemas/fakes; no cherry-picking sibling work.
- A changed frozen contract returns to Step 0 or becomes an explicit versioned change.

## Step 0 — Engineering foundation and contract baseline

- Objective: create the minimum runnable web/API/Django/test scaffold and freeze the v1 contracts above.
- Behavior: authenticated health/context fixtures can execute without feature behavior.
- Data: base schemas/runtime roles plus minimal global user-profile ownership only.
- Security: no production secrets/data; API test role is non-owner/non-`BYPASSRLS`.
- Non-scope: membership behavior, real provider email, PDF/AI/worker implementation.
- Tests: reproducible install, health flow, architecture/import boundaries, migration
  authority, empty OpenAPI generation/client compile, documentation drift.
- Acceptance: exact supported versions and repository commands are committed; all four lane fixture suites can run.

## Lane A — JWT identity and authorized execution context

- Objective: verify the pinned token contract and construct identity candidates for the shared UoW.
- Behavior: valid local Supabase tokens authenticate; malformed/wrong-project/stale tokens fail closed.
- Data: read global profile status; no tenant mutation.
- Security: allowlisted algorithm/key/issuer/audience/time; unknown-key refresh once; no JWT permission authority.
- Non-scope: membership management and frontend.
- Tests: token matrix, key rotation/cache failure, revoked user, missing context, pool reset.
- Acceptance: identity service/API dependency passes using frozen tenant-authorizer fake.

## Lane B — Tenant membership, entitlement, role policy, and RLS

- Objective: make PostgreSQL the current tenant-authorization authority.
- Behavior: create/activate/deactivate membership, assign fixed roles, resolve context, deny stale/inactive/cross-tenant access.
- Data: complete dictionary and Django migrations for tenancy objects owned by this lane.
- Security: forced RLS, composite tenant FKs, least grants, atomic audit/outbox, version conflict.
- Non-scope: HTTP/UI and custom roles.
- Tests: production-role RLS matrix, same-tenant constraints, policy transitions, concurrency and rollback/outbox.
- Acceptance: public service/selectors satisfy frozen fixtures without API imports.

## Lane C — Membership/invitation API and Admin adapters

- Objective: expose the frozen v1 HTTP contract and trusted adapter-only Admin actions.
- Behavior: list memberships, create/accept invitations, update membership roles/status, return Problem Details.
- Data: no direct ORM writes and no new migration.
- Security: tenant admin permission, idempotency, hashed tokens, neutral denial, CSRF where cookie-authenticated.
- Non-scope: email provider and business logic in routers/Admin forms.
- Tests: API contract, IDOR, permission escalation, replay, expiry, idempotency conflict, service-call parity.
- Acceptance: routers/Admin pass against the committed fake service contract.

## Lane D — Web sign-in and active-tenant experience

- Objective: implement accessible session/tenant selection UI against the frozen TypeScript fixture.
- Behavior: sign in, show memberships, require explicit selection, show loading/empty/denied states, accept invitation.
- Data: generated-client boundary only; no Supabase core-table reads.
- Security: hidden controls never authorize; selector is untrusted; tokens and invitation values are not logged.
- Non-scope: course dashboards, general member directory, analytics, real email.
- Tests: component states, keyboard/focus/errors, wrong-tenant denial fixture, Playwright journey against mock transport.
- Acceptance: web build/type/lint and isolated browser fixture journey pass without backend branch code.

## Step 5 — Integration, regeneration, and critical journey

- Objective: wire merged lanes, order migrations, regenerate contracts/client, and prove the full F-001 journey.
- Behavior: invitation → authentication → explicit tenant selection → allowed request → immediate revocation denial.
- Shared ownership: integration owner only.
- Tests: full backend, schema/RLS, OpenAPI compatibility/client compile, web, Playwright, accessibility, secret scan.
- Acceptance: exact evidence is attached to the integration PR; no deferred capability artifacts appear.

## Planned commands

Step 0 must expose these stable repository commands before lane implementation:

```text
make lint
make typecheck
make test
make test-rls
make openapi-check
make web-build
make e2e-f001
make docs-check
```

The Make targets wrap pinned tools; agents do not replace them with ad hoc commands.

## Dry-run result

The predicted implementation follows existing planned boundaries and does not require
a new provider or architecture. Issue #1 and its server-side linked branch exist. The
remaining material prerequisite is its reviewed runnable scaffold/contracts PR.

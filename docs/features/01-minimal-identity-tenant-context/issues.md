# GitHub Issues — F-001

Step 0 [GitHub issue #1](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/1)
merged through PR #4 at `ec4006fcfe45a1c9832f80704581fb1289dcde7f`.
[GitHub issue #5](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/5) and PR
#6 merged the owner-required Docker-only workflow at
`b34ba7ac377a6a12363b036ece3d682d0b0ecdd8`. The readiness audit passes at that exact
base. Backend lanes A-C merged through PRs #16, #15, and #14. Lane D merged through
PR #24. The Step 5 integration is provisioned as GitHub issue #25 and remains pending
independent review.

## #1 — Foundation and frozen contracts

- Outcome: runnable minimum scaffold, exact lockfiles/commands, v1 schemas and fixtures.
- Owner/paths: integration owner; shared manifests, composition, CI, base migrations,
  OpenAPI/event/fixture baselines.
- Base/branch: `develop` -> `chore/LMS-1-foundation-contracts`.
- Acceptance: all Step 0 checks and four isolated fixture suites run.
- Non-goals: F-001 business behavior, external providers, real data.

## #5 — Docker-only development workflow

- Outcome: reusable pinned backend/web tooling services and PostgreSQL start with
  `docker compose up -d --build`; no host project dependency install is required.
- Owner/paths: integration owner; Compose/Docker/Make/CI and workflow/readiness hotspots.
- Base/branch: `develop` -> `chore/LMS-5-docker-workflow`.
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/integration-LMS-5`.
- Acceptance: all stable commands execute through healthy isolated containers; no host
  `.venv` or `node_modules`; second build reuses dependency layers.
- Non-goals: F-001 business behavior, dependency upgrades, providers, schema changes.

## #9 — JWT identity and execution context

- Outcome: verified identity candidate and transaction-local context fail closed.
- Owner/paths: Agent A; identity module, API authentication dependency, identity tests.
- Base/branch: `develop` -> `feature/LMS-9-jwt-context`.
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/agent-a-LMS-9`.
- Compose: `ai-lms-lms-9`; PostgreSQL host port `55109`.
- Contract: auth-context v1 plus tenant-authorizer fake.
- Acceptance: JWT/key/revocation/context-reset matrix passes.

## #10 — Tenancy membership, roles, entitlement and RLS

- Outcome: PostgreSQL-authoritative tenant access and role policy.
- Owner/paths: Agent B; tenancy domain/services/policies/migrations/RLS/tests.
- Base/branch: `develop` -> `feature/LMS-10-tenant-membership`.
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/agent-b-LMS-10`.
- Compose: `ai-lms-lms-10`; PostgreSQL host port `55110`.
- Contract: tenancy public service/selectors and synthetic Alpha/Beta fixtures.
- Acceptance: dictionary, migration, constraints, production-role RLS, concurrency,
  audit/outbox and rollback tests pass.

## #11 — Membership/invitation API and Admin

- Outcome: frozen HTTP contract and adapter-only trusted Admin actions.
- Owner/paths: Agent C; membership/invitation FastAPI schemas/routers, Admin adapters,
  contract tests.
- Base/branch: `develop` -> `feature/LMS-11-membership-api-admin`.
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/agent-c-LMS-11`.
- Compose: `ai-lms-lms-11`; PostgreSQL host port `55111`.
- Contract: tenancy service fake and Problem Details codes.
- Acceptance: IDOR/permissions/replay/idempotency/version/API/Admin parity pass.

## #23 — Web tenant-context journey

- Outcome: accessible sign-in, invitation, tenant selection and denial states.
- Owner/paths: Agent D; web auth/tenant-context features and isolated E2E fixtures.
- Base/branch: `develop` -> `feature/LMS-23-f001-web-tenant-context`.
- Delivery: merged through PR #24 at `465a3ba6370179927e5db72505ffb34d656fa34a`.
- Contract: TypeScript auth-context v1 fixture; generated client is read-only.
- Acceptance: lint/type/build/component and mock-transport Playwright checks pass.

## #25 — Integration and regeneration

- Outcome: merged lanes wired with ordered migrations, generated client and critical E2E.
- Owner/paths: integration owner; shared hotspots only after A–D merge.
- Base/branch: `develop` -> `feature/LMS-25-f001-integration`.
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/integration-LMS-25`.
- Compose: `ai-lms-lms-25`; PostgreSQL host port `55225`.
- Acceptance: all Make targets, production-role matrix, compatibility, accessibility,
  secret scan and evidence checks pass at the reviewed SHA.
- Non-goals: deploy, real data, email provider, course/PDF/AI behavior.

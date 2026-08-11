# GitHub Issues — F-001

Step 0 [GitHub issue #1](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/1)
merged through PR #4 at `ec4006fcfe45a1c9832f80704581fb1289dcde7f`.
[GitHub issue #5](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/5)
implements the owner-required Docker-only workflow amendment. Create lanes A-D only
after issue #5 merges and the readiness audit passes. Their bodies remain local plans
until then; replace each local ID with its returned GitHub issue number.

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

## LOCAL-F001-A — JWT identity and execution context

- Outcome: verified identity candidate and transaction-local context fail closed.
- Owner/paths: Agent A; identity module, API authentication dependency, identity tests.
- Contract: auth-context v1 plus tenant-authorizer fake.
- Acceptance: JWT/key/revocation/context-reset matrix passes.

## LOCAL-F001-B — Tenancy membership, roles, entitlement and RLS

- Outcome: PostgreSQL-authoritative tenant access and role policy.
- Owner/paths: Agent B; tenancy domain/services/policies/migrations/RLS/tests.
- Contract: tenancy public service/selectors and synthetic Alpha/Beta fixtures.
- Acceptance: dictionary, migration, constraints, production-role RLS, concurrency,
  audit/outbox and rollback tests pass.

## LOCAL-F001-C — Membership/invitation API and Admin

- Outcome: frozen HTTP contract and adapter-only trusted Admin actions.
- Owner/paths: Agent C; membership/invitation FastAPI schemas/routers, Admin adapters,
  contract tests.
- Contract: tenancy service fake and Problem Details codes.
- Acceptance: IDOR/permissions/replay/idempotency/version/API/Admin parity pass.

## LOCAL-F001-D — Web tenant-context journey

- Outcome: accessible sign-in, invitation, tenant selection and denial states.
- Owner/paths: Agent D; web auth/tenant-context features and isolated E2E fixtures.
- Contract: TypeScript auth-context v1 fixture; generated client is read-only.
- Acceptance: lint/type/build/component and mock-transport Playwright checks pass.

## LOCAL-F001-I — Integration and regeneration

- Outcome: merged lanes wired with ordered migrations, generated client and critical E2E.
- Owner/paths: integration owner; shared hotspots only after A–D merge.
- Acceptance: all Make targets, production-role matrix, compatibility, accessibility,
  secret scan and evidence checks pass at the reviewed SHA.
- Non-goals: deploy, real data, email provider, course/PDF/AI behavior.

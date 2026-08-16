# Implementation Plan — F-002 Canonical Course Lifecycle

Status: **issues provisioned; implementation blocked until planning PR merges**

## Dependency graph

```text
planning #27 merged
       |
       +--> Lane A persistence/RLS --------+
       +--> Lane B lifecycle services -----+--> integration/web
       +--> Lane C API/Admin adapters -----+
```

Lanes A–C start together from the first `develop` SHA containing planning #27. They
consume `contracts/f002/canonical-course.v1.*` and may not import an unmerged sibling
branch. Integration starts only after A–C merge in the declared order.

| Issue | Agent | Objective | Primary owned paths | Contracts/fixtures | Depends on | Merge order |
|---|---|---|---|---|---|---|
| [#28](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/28) | A | Course/curriculum persistence, migrations, permissions, constraints, RLS | course models/apps/migrations/repository plus DB tests | F-002 JSON schema/example; frozen repository method table | #27 merged | 1 |
| [#29](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/29) | B | Lifecycle policies/services, hashing, validation, concurrency/idempotency ports | course types/errors/policies/services plus unit/service tests | F-002 JSON schema/example; fake repository/fact writer | #27 merged | 2 |
| [#30](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/30) | C | Thin FastAPI and Admin adapters against a structural service fake | course API/Admin files and adapter tests | frozen HTTP/Problem Details contract | #27 merged | 3 |
| [#31](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/31) | Integration | Compose real lanes, OpenAPI/client, minimal editor and critical E2E | shared composition/generated/web/e2e/docs hotspots | merged A–C plus F-002 fixture | A–C merged | 4 |

## Isolation and shared ownership

| Lane | Branch | Worktree | Compose project | PostgreSQL port |
|---|---|---|---|---|
| A | `feature/LMS-28-f002-course-persistence` | `/home/lawrence/Project Neo/worktrees/ai-lms/agent-a-LMS-28` | `ai-lms-lms-28` | `55228` |
| B | `feature/LMS-29-f002-course-lifecycle` | `/home/lawrence/Project Neo/worktrees/ai-lms/agent-b-LMS-29` | `ai-lms-lms-29` | `55229` |
| C | `feature/LMS-30-f002-course-adapters` | `/home/lawrence/Project Neo/worktrees/ai-lms/agent-c-LMS-30` | `ai-lms-lms-30` | `55230` |
| I | `feature/LMS-31-f002-integration` | `/home/lawrence/Project Neo/worktrees/ai-lms/integration-LMS-31` | `ai-lms-lms-31` | `55231` |

- Lane A is sole owner of F-002 migrations, models, RLS/grants, permission seeds, and
  executable data dictionary.
- Lane B owns domain/application behavior and defines its ports locally from the frozen
  method contract; it uses fakes and does not import Lane A.
- Lane C owns only adapters and structural service fakes; it does not import Lane B or
  compose routes into the application.
- Integration is sole owner of settings/application composition, OpenAPI/generated
  client, root scripts/CI, shared event schemas, web/e2e wiring, documentation manifest,
  and cross-lane compatibility fixes.
- No lane changes dependencies or lockfiles. A required change stops and transfers to
  integration ownership.

## Frozen public service and persistence boundaries

Lane B exposes the public application-service behavior below. Lane C consumes a
structurally matching port and supplies fakes in focused tests:

```text
create_course(actor_id, tenant_id, command, idempotency_key) -> CourseSnapshotV1
get_course(actor_id, tenant_id, course_id) -> CourseSnapshotV1
update_version(actor_id, tenant_id, course_id, version_id, command) -> CourseSnapshotV1
replace_curriculum(actor_id, tenant_id, course_id, version_id, command) -> CourseSnapshotV1
transition_version(actor_id, tenant_id, course_id, version_id, command, idempotency_key) -> CourseSnapshotV1
create_successor_draft(actor_id, tenant_id, course_id, source_version_id, idempotency_key) -> CourseSnapshotV1
```

Lane A implements storage behavior for: load one tenant-scoped aggregate/snapshot;
atomically insert course plus v1; compare and replace mutable version/curriculum;
append an immutable review; compare and transition state/publication pointer; create a
successor draft; and reserve/complete idempotency plus audit/outbox facts in the calling
transaction. Lane B models that behavior as a port and fake without importing Lane A.

The real integration may split repository and command-service classes internally, but
the public adapter behavior, transaction semantics, and DTOs cannot change without
updating the contract and all consumer tests in one integration-owned change.

## Lane A — persistence, permissions, migrations, and RLS

- Objective: make the frozen aggregate enforceable under real PostgreSQL production
  roles without implementing lifecycle decisions in model callbacks.
- Owned paths:
  - `backend/src/lms/modules/courses/apps.py`
  - `backend/src/lms/modules/courses/__init__.py`
  - `backend/src/lms/modules/courses/models.py`
  - `backend/src/lms/modules/courses/repositories.py`
  - `backend/src/lms/modules/courses/migrations/**`
  - narrowly declared permission-catalog and settings paths required to install the app
  - `backend/tests/courses/test_models.py`, `test_constraints.py`, `test_data_dictionary.py`, `test_rls.py`, and repository tests
  - `backend/tests/test_migration_authority.py` additions
- Must not edit: services/policies/types/errors, FastAPI/Admin, OpenAPI/client, web/e2e,
  dependencies, CI, F-002 planning contracts, or manifest.
- Acceptance: exact tables/dictionary, tenant-composite edges, positions, versions,
  publication pointer, published immutability, permission seeds, rollback, repository
  shape, and production-role matrix pass.
- Focused commands: migration authority, `pytest backend/tests/courses -m rls`,
  constraints/data-dictionary/repository suites, Ruff, mypy.

## Lane B — lifecycle policies and application services

- Objective: implement the canonical hash, validation, permission/state policy, review,
  idempotency, concurrency, and atomic fact orchestration against in-memory ports.
- Owned paths:
  - `backend/src/lms/modules/courses/types.py`
  - `backend/src/lms/modules/courses/errors.py`
  - `backend/src/lms/modules/courses/hashing.py`
  - `backend/src/lms/modules/courses/validation.py`
  - `backend/src/lms/modules/courses/policies.py`
  - `backend/src/lms/modules/courses/services.py`
  - `backend/tests/courses/test_hashing.py`, `test_validation.py`, `test_policies.py`, `test_services.py`
  - `backend/tests/contract_fakes/f002_courses.py`
- Must not edit: models/migrations/repositories/settings, FastAPI/Admin, OpenAPI/client,
  web/e2e, dependencies, CI, contracts, or manifest.
- Acceptance: transition matrix, human-only decisions, reviewer separation, canonical
  hash, immutable-state denial, stale/concurrent results, idempotent replay/conflict,
  audit/outbox rollback, and successor-version behavior pass with fakes.
- Focused commands: F-002 unit/service tests, architecture boundary, Ruff, mypy, full
  non-RLS regression.

## Lane C — FastAPI and trusted Admin adapters

- Objective: expose the frozen HTTP behavior and trusted Admin actions through one
  structural service port without owning composition or domain mutation.
- Owned paths:
  - `backend/src/lms/api/schemas/courses.py`
  - `backend/src/lms/api/routers/courses.py`
  - `backend/src/lms/adapters/admin/courses.py`
  - `backend/tests/api/test_course_lifecycle.py`
  - `backend/tests/adapters/test_course_admin.py`
  - `backend/tests/contract_fakes/f002_course_administration.py`
- Must not edit: course model/service files, migrations/settings/composition,
  `contracts/openapi`, generated client, web/e2e, dependencies, CI, planning contracts,
  or manifest.
- Acceptance: exact operations/schemas/problems, auth/tenant/IDOR matrix, strict input,
  bounded safe validation errors, neutral denials, Admin/service parity, and direct
  model-write prevention pass using fakes.
- Focused commands: API/Admin tests, contract test, Ruff, mypy, architecture boundary,
  full non-RLS regression.

## Integration — real composition, generated artifacts, web, and E2E

- Objective: integrate A–C after ordered merges and prove the minimal human course
  journey against real PostgreSQL and the generated client.
- Owned paths: explicit shared composition/settings fixes, `contracts/openapi/**`,
  `packages/api-client/**`, generation scripts, `apps/web/src/features/course-editor/**`,
  course routes/pages/styles, F-002 Playwright fixtures/specs, Compose integration
  harness, event schemas, F-002 status docs, and `manifest.json`.
- Acceptance: migration order, real service/API/Admin parity, OpenAPI/client parity,
  create/edit/submit/approve/publish/new-draft browser journey, immediate revocation,
  Alpha/Beta/outsider denial, immutable published version, accessibility, secret/log
  checks, full regressions, and protected GitHub checks pass.
- Non-goal: merge, deployment, provider configuration, PDF/AI/learning features.

## Launch gate for three terminals

Start Agents A–C only when all are true:

1. the planning PR for #27 is independently approved and merged into `develop`;
2. issues A–C say `READY FOR IMPLEMENTATION` and link the merge SHA;
3. their linked branches are created from that exact `develop` SHA;
4. each worktree path is absent before provisioning and each Compose resource is unique;
5. the F-002 JSON schema/example and contract test pass on the shared base.

Until then, implementation is blocked. Integration starts only after A–C merge and
must merge the latest base, rerun all gates, and obtain a new exact-SHA review.

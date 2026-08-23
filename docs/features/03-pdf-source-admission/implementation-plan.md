# Implementation Plan — F-003 PDF Source Admission

Status: **#43/PR #56 merged; independent post-merge audit returned CHANGES REQUIRED; parser remediation #61 blocks F-004**

## Dependency graph

```text
F-001 merged + P-013 local envelope
                |
                v
planning #42 (contracts, fixture, test plan)
                |
                v
       merged PR #44 + correction #51/PR #53
                |
       owner disposition + merged PR #55
                |
       #43 local implementation candidate
                |
       exact-head review + protected checks --> F-004 contract consumers
```

F-003 intentionally has one implementation issue, one branch, one worktree, and one
PR. It is the integration owner because splitting migrations, storage-admission state,
OpenAPI/client, and the browser flow would create shared-hotspot conflicts without
meaningful independent delivery.

| Issue | Agent | Objective | Primary owned paths | Consumes | Depends on | Merge order |
|---|---|---|---|---|---|---|
| [#42](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/42) | Planning | Freeze local-only DTO/job/event/fixture, Q-P03 envelope, boundaries, and test plan | `docs/features/03-pdf-source-admission/**`, `contracts/f003/**`, contract test, product decision/question, feature index, manifest | F-001/F-002 architecture patterns and plan documents | none | 1 |
| [#51](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51) | Review-evidence correction owner | Record the exact audit, correct its three blocking contract findings, and document the one-time temporal exception | Narrow F-003 contract/test/status/evidence and serialized manifest paths | exact PR #44 head plus frozen product/plan behavior | #42/PR #44 merged | 2 |
| [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43) | F-003 integration owner | Implement the complete private local admission slice and evidence | Documents module/migrations/RLS, API/Admin/composition, contracts/OpenAPI/client/events, web/E2E, F-003 tests/docs/manifest | frozen #42 contract and synthetic fixtures | #51 merged; owner launch disposition recorded | 3 |

## Launch gate — satisfied 2026-08-22

Issue #43 remained blocked until all conditions were true:

1. #42's planning contract, merged as PR #44 at
   `83a0c487ff782192d4c18e08cfebd86eb4cf626f`, has its missing review order resolved
   by correction #51. PR #53 merged as
   `5b89c6a8e62140f8032492b5454a12b2ef063bce`, but its merge head
   `57bb2692eebfc81c6198589bfdd4fb7afeb17286` lacks an independent exact-head verdict
   and a distinct authorized GitHub approval. The project owner's narrow
   [launch disposition](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43#issuecomment-5379136978)
   closed that historical hold without claiming retroactive approval;
2. P-013 is present on that merged base, and its local-only values are copied without
   reinterpretation into the executable admission-policy fixture;
3. `contracts/f003` and `backend/tests/contracts/test_f003_contracts.py` pass on the
   exact merged base;
4. no uncommitted change exists in the coordinator checkout and the target branch/path
   is absent; and
5. F-003's implementation branch is created from that exact `origin/develop` SHA.

The disposition was accepted only because it is the latest explicit project-owner
instruction after PR #55 merged at
`b733f94718826d7c7f98e08e44285639ece07813`. It applies only to #43's launch and does
not weaken this implementation's exact-head review, distinct approval, protected-check,
or merge requirements.

F-002's missing pre-merge review record is separately tracked by #40/#41. F-003
depends only on merged F-001 and the frozen F-003 contract; this plan does not disguise
or resolve the F-002 review gate.

## Issue #43 — private PDF source-admission vertical slice

- Objective: implement F-003 without selecting an external storage, scanner, OCR,
  persistent-worker, queue, provider, or production environment.
- Branch: `feature/LMS-43-f003-source-admission`
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/source-admission-LMS-43`
- Host scratch: `/home/lawrence/Project Neo/tmp/LMS-43`
- Compose project: `ai-lms-lms-43`
- PostgreSQL host port: `55243`
- Base: exact `origin/develop` SHA
  `b733f94718826d7c7f98e08e44285639ece07813` after the recorded owner disposition.

The application implementation is pinned at
`f4b3af0b7d4595617f4effcba1b263a02f04e540`; complete local results and limitations are
in the [implementation evidence](../../evidence/f003-source-admission-implementation.md).
The later documentation commit, protected checks, and independent exact-head verdict
remain part of the PR handoff gate.

### Exclusive ownership

- `backend/src/lms/modules/documents/**`, including its Django app, models,
  migrations, repositories, types, policies, services, local quarantine/inspector
  ports, worker/reconciler entrypoints, and executable data dictionary;
- `backend/tests/documents/**`, F-003 contract fakes, documents API/Admin/integration
  tests, F-003 migration/RLS/data-dictionary tests, and narrowly scoped F-003 changes
  to shared test harnesses;
- fixed F-003 permission additions in `backend/src/lms/modules/tenancy/services.py`
  plus their exact tenancy tests;
- Documents FastAPI schemas/router/composition and trusted Django Admin adapter;
- necessary app/settings/main registration, the generated OpenAPI/client, event
  schemas, and F-003-only architecture/CI/Make wiring;
- `apps/web/src/app/source-documents/**`,
  `apps/web/src/features/source-admission/**`, F-003 Playwright fixture/spec and
  necessary local test-server wiring; and
- F-003 status records and `manifest.json`.

### Must not change

- Existing identity, tenancy, and course implementation except the declared additive
  permission catalog and narrowly required application registration;
- dependency manifests/lockfiles unless a separate approved integration decision
  transfers that hotspot (the current plan requires no new dependency);
- external provider credentials/configuration, real data, retention periods, worker
  provider/region, OCR/generation/vector code, public source access, or deployment.

### Required behavior

1. Create a rights declaration plus requested `store` authorization and immutable
   source/version under F-001 tenant authority.
2. Require a separate active human source-rights reviewer to decide the authorization;
   only activation can issue a short-lived opaque local upload target.
3. Accept only byte-derived local PDF observations within P-013, then record private
   quarantine inventory and a durable validation job after storage returns.
4. Validate/reconcile in a claimed job/stage scope with lease, checkpoint, bounded
   retry, deterministic result, safe rejection, and no transaction around I/O.
5. Expose only the frozen tenant-safe status/decision/cancel/read operations and
   generated-client browser flow; no raw storage path or source bytes are returned.
6. Cancel, deny, expire, revoke, or dispute by immediately blocking new use and
   completing durable object-removal reconciliation after commit.

### Required tests and evidence

| Area | Minimum proof |
|---|---|
| Frozen contract | All F-003 schemas/examples/fixture manifest validate; P-013 limits and no-content job/event rule are asserted |
| Domain/service | Rights separation, operation scope, state table, idempotency, stale/concurrent command, audit/outbox rollback, validator retry/lease/checkpoint, cancel/revoke race |
| Migration/data/RLS | Django-only migration authority; dictionary; composite tenant edges; forced RLS/grants; API/worker production-role, absent/wrong/stale context, guessed IDs, pool reset, object inventory and immutable evidence |
| Admission security | MIME/signature/polyglot, encrypted/corrupt, bytes/pages/pixels/decoded limits, expired/tampered/replayed target, quota, absent inspector, no raw source/token/path in logs/events |
| Reconciliation/removal | orphan object, missing object, checksum mismatch, duplicate body, failed delete/retry, cancellation/revocation/expiry blocks before removal completes |
| API/Admin | strict schemas and media type, Problem Details, idempotency headers, neutral denials, service-only Admin actions, OpenAPI/client drift |
| Browser/accessibility | active tenant, declaration, pending-review, approved upload, validating/admitted/rejected/cancelled/blocked states; keyboard/focus/status live region, labels, errors, 200% reflow; no direct database/storage client |
| Regressions | F-001/F-002 tests, OpenAPI/client, architecture, migrations, docs/manifest, secret/log checks, required CI checks |

Start and reuse only the issue's isolated services:

```text
COMPOSE_PROJECT_NAME=ai-lms-lms-43 AI_LMS_POSTGRES_PORT=55243 \
AI_LMS_UID=$(id -u) AI_LMS_GID=$(id -g) docker compose up -d --build --wait
```

The exact evidence command set is finalized with implementation-owned targets, and at
minimum includes focused F-003 pytest/API/RLS/contract suites, `make lint`,
`make typecheck`, `make test`, `make test-rls`, `make openapi-check`, `make web-build`,
the F-003 Playwright spec plus existing F-001/F-002 specs, `make docs-check`, and
`git diff --check`. No host virtual environment or host Node installation is allowed.

### Handoff / PR gate

#43 may report `READY FOR CODE REVIEW` only with its exact head SHA, base SHA, complete
path diff, local command results, protected check results, relevant synthetic fixture
checksums, migration/RLS evidence, known limitations, and a statement that no external
provider/real-data/production action occurred. An independent agent/context reviews
that exact SHA; the author does not approve or merge it.

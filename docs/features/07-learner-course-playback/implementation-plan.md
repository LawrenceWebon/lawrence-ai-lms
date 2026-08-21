# Implementation Plan — F-007 Learner Course Playback and Progress

Status: **BLOCKED — owner decisions and planning review/merge required**

## Dependency graph

```text
F-001 merged + F-002 implementation merged
                    |
                    v
        planning #45 + F007-Q01–Q04
                    |
          independent review + merge
                    |
                    v
     one vertical F-007 implementation issue
```

F-007 depends on the completed F-001 tenant context and F-002 canonical publication
base. It does not depend on F-003–F-006 and may be implemented independently after its
own planning contract and owner decisions merge.

| Issue | Agent | Objective | Primary owned paths | Contracts/fixtures | Depends on | Merge order |
|---|---|---|---|---|---|---|
| [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45) | Planning | Resolve private enrollment/playback/progress scope and freeze executable contracts | F-007 feature docs/contracts/test/index/manifest only | F-007 schemas/examples/synthetic fixtures | F-001/F-002 merged | 1 |
| [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) | Vertical integration owner | Implement enrollment, pinned playback, explicit progress, generated client, minimal learner UI, and evidence | All declared F-007 code/migration/generated/web/test/status hotspots | Merged F-007 contract package | #45 approved and merged; F007-Q01–Q04 closed | 2 |

Splitting this slice into concurrent persistence/service/adapter lanes would create
avoidable contention in the permission catalog, migration graph, learning domain,
application composition, OpenAPI/client, and player E2E journey. One bounded vertical
issue is the smallest safe delivery unit.

## Isolation and resources

| Lane | Branch | Worktree | Compose project | PostgreSQL port |
|---|---|---|---|---|
| Planning | `chore/LMS-45-f007-playback-contracts` | `/home/lawrence/Project Neo/worktrees/ai-lms/planning-LMS-45` | `ai-lms-lms-45` | `55245` |
| Implementation | `feature/LMS-46-f007-learner-playback` | `/home/lawrence/Project Neo/worktrees/ai-lms/learner-playback-LMS-46` | `ai-lms-lms-46` | `55246` |

Issue #46 exists in an explicitly blocked state. Its branch and worktree must not be
provisioned before the launch gate closes.

## Implementation issue ownership

### Objective

Deliver the smallest private learner journey: a tenant administrator manually assigns
an active learner to a currently published course; the enrollment pins that immutable
version; the learner lists, opens, reads, explicitly progresses, completes/reopens,
and resumes it; revocation and the accepted withdrawal policy take effect on the next
request.

### Owned paths

- `backend/src/lms/modules/learning/**`
- `backend/tests/learning/**`
- the narrowly declared F-007 additions to the tenancy permission catalog and its
  focused permission/migration tests
- `backend/src/lms/api/schemas/learning.py`
- `backend/src/lms/api/routers/learning.py`
- `backend/src/lms/adapters/admin/learning.py`
- F-007 API/Admin/contract-fake/integration/RLS tests
- the narrow settings, application-composition, and main-router changes required to
  install and expose Learning
- `contracts/openapi/**` and `packages/api-client/**`
- `contracts/events/learning.*/**` or the repository's equivalent generated event
  registry paths, using the frozen F-007 event schema
- `apps/web/src/app/learner-courses/**`
- `apps/web/src/features/learner-playback/**`
- F-007 Playwright fixtures/specs and their narrow scripts/configuration entry
- F-007 status/evidence updates and `manifest.json`

### Read-only dependencies

- F-001 identity/tenancy services, schemas, and tests
- F-002 Courses public service/read boundary, models, rich-text schema, lifecycle
  fixtures, renderer conventions, and publication tests
- F-003–F-006 branches, contracts, source data, and AI artifacts

The issue may not edit F-001/F-002 behavior or broaden their public contracts. If a
necessary shared change is discovered, stop, document it, and create a separately
approved corrective issue rather than silently absorbing it.

### Shared hotspots

The implementation issue is the sole F-007 integration owner for:

- Learning Django migrations, RLS/grants, and executable data dictionary;
- permission seed additions;
- application settings/composition and root router wiring;
- OpenAPI and generated TypeScript client;
- learner routes/player and Playwright integration;
- learning event schemas/registry;
- documentation status/evidence and authoritative manifest.

No other feature lane may edit these F-007 hotspots concurrently. F-003–F-006 retain
their own declared paths and must coordinate any genuinely shared root artifact through
their integration owner and dependency merge order.

## Required implementation behavior

### Persistence and RLS

- Add only the minimum learning tables needed for enrollment, enrollment history,
  lesson/course progress, idempotency/audit/outbox linkage, with names confirmed by the
  executable data dictionary.
- Enforce `UNIQUE (tenant_id, id)` and composite same-tenant foreign keys on every
  tenant edge, including the learner membership, course, pinned course version,
  section/lesson references, and progress parent.
- Enforce one active enrollment per tenant/learner membership/course and preserve
  immutable revoked enrollment history.
- Force RLS and run production-role positive/negative matrices for missing context,
  wrong tenant, other learner, guessed IDs, inactive membership/entitlement, revoked
  enrollment, tenant mutation, and pool reuse.
- Make Django migrations the only DDL/grant/RLS authority; add no Supabase application
  migration history.

### Services and selectors

- Expose one Learning public application boundary used by FastAPI and Admin.
- Re-derive authorization and current course publication state inside each create or
  revoke transaction; never trust browser-supplied tenant, learner, or version
  authority.
- Keep playback selectors read-only and primary-backed for authorization and
  progress read-after-write.
- Apply optimistic concurrency and durable idempotency to every state-changing POST.
- Commit learning state, audit, and outbox facts atomically and perform no provider or
  network call inside the transaction.

### API and Admin

- Implement exactly the frozen operation IDs, methods, headers, DTOs, success statuses,
  and stable RFC Problem Details codes.
- Validate responses against the contract and return neutral learner-resource denials.
- Admin create/revoke actions call the shared service; critical pin/status/progress
  fields are read-only and generic model writes cannot perform lifecycle transitions.

### Web and accessibility

- Use only the generated API client for core LMS data.
- Render only the allowlisted F-002 rich-text tree with escaped text.
- Provide private dashboard empty/error/loading states; player outline, lesson,
  previous/next, resume, complete, and reopen controls.
- Clear rendered content on access loss; never persist tenant/course authorization in
  browser storage.
- Meet keyboard, focus, semantic heading/landmark, live status/error, 200% zoom, 400%
  reflow, contrast, reduced-motion, and accepted locale/RTL test requirements.

## Non-goals

- Self-enrollment, public catalog, checkout, commerce, invitations, cohorts, groups,
  rules, bulk assignment, notifications, analytics, notes, bookmarks, discussions,
  prerequisites, assessments, grades, certificates, assets, downloads, links, media,
  or learner source/provenance views.
- PDF upload/extraction/OCR, structured generation/review, AI/provider/vector behavior,
  real data, staging/production storage, or deployment.
- Dependency/lockfile changes, new providers/queues/caches, CI redesign, or unrelated
  cleanup.

## Launch gate

Do not create the implementation branch/worktree or write application code until all
conditions are true:

1. the project owner resolves F007-Q01, F007-Q02, F007-Q03, and Q-P08/F007-Q04 in an
   approved repository decision;
2. planning issue #45 contains the resulting exact contract changes and no hidden
   product decision remains;
3. the planning PR receives independent exact-SHA review, the required distinct
   authorized approval, all protected checks pass, and it merges to `develop`;
4. the implementation issue says `READY FOR IMPLEMENTATION` and links that merge SHA;
5. its worktree path is absent, branch starts from the approved merge, and Compose
   resources are unique; and
6. F-001/F-002 regressions plus the F-007 contract suite pass on that shared base.

## Verification for the future implementation

The implementation issue runs its dedicated Compose stack and records exact results:

```text
make lint
make typecheck
make test
make test-rls
make openapi-check
make web-build
make e2e-f001
make e2e-f002
make docs-check
```

It also runs the focused F-007 contract/unit/service/database/RLS/API/Admin/browser,
concurrency/idempotency, architecture-boundary, migration-drift, event-compatibility,
accessibility, secret/log-redaction, and `git diff --check` suites described in
`test-plan.md`. No production or recovery claim is made by local implementation.

# Technical Decisions — F-007 Learner Course Playback and Progress

Status: **owner-approved and frozen; implementation merged; independent post-merge audit requires RLS remediation #60**

Local implementation evidence is recorded in
[F007-LOCAL-IMPLEMENTATION-2026-08-22](../../evidence/f007-learner-playback-implementation.md)
at application commit `dd758909e3060032ecbe28f8175d3849a4c26208`.

## Existing architecture to reuse

- F-001 verified identity, explicit tenant selection, active membership/entitlement
  checks, fixed permission catalog, and production-role PostgreSQL RLS helpers.
- F-002 canonical course identity, immutable course versions, ordered curriculum,
  provider-neutral rich text, publication pointer, and human publication service.
- The modular-monolith service/adapter boundary in ADR-0001 and ADR-0002.
- Django-only migration authority and FastAPI-owned HTTP/OpenAPI boundary.
- RFC Problem Details, transaction-local authorization, optimistic row versions,
  command idempotency, atomic audit/outbox facts, and deterministic synthetic fixtures.
- The learning-domain version-pin invariant in documents 05, 07, and 20.

## Owner-approved decisions

These decisions change persisted lifecycle or acceptance behavior and are approved
under P-014. Implementation must consume them exactly.

### F007-Q01 — Private enrollment and re-enrollment policy

Approved decision:

- the first slice permits manual assignment by a tenant administrator with
  `learning.enrollments.manage`;
- there is no learner self-enrollment, public catalog, checkout, invitation, cohort,
  group, or rule-driven enrollment;
- revocation is terminal for that enrollment record; and
- a later re-enrollment creates a new record and pins the then-current published
  version. Historical progress is not copied automatically.

### F007-Q02 — Withdrawn or archived pinned version

Approved decision:

- a withdrawn or archived pinned version becomes immediately unavailable for new
  playback and progress operations;
- selectors return the same neutral `404 LEARNING_RESOURCE_NOT_FOUND` used for an
  inaccessible enrollment;
- the service does not auto-migrate the enrollment to another version; and
- progress, enrollment, audit, and outbox history remain durable under the future
  approved retention/legal-hold policy but are not learner-readable while unavailable.

### F007-Q03 — Completion and reopen semantics

Approved decision:

- `open_lesson` explicitly records the resume lesson and starts an unstarted lesson;
- `complete_lesson` explicitly marks a lesson complete;
- `reopen_lesson` explicitly returns a completed lesson to in-progress;
- a course is complete exactly when every required lesson in the pinned version is
  complete, and reopens when a required lesson reopens; and
- scroll, dwell time, media telemetry, browser navigation, and GET requests never
  infer or mutate completion.

### F007-Q04 — Initial locale acceptance

Approved decision:

This closes product question Q-P08 for the focused pilot: the accepted initial locale
is exactly `en`. The implementation preserves the F-002 `primary_locale`, Unicode,
language/fallback metadata, and repository localization boundaries and remains
structurally ready for RTL without claiming another supported pilot locale.

## Frozen technical decisions

### F007-TD-001 — Enrollment is private and pins one immutable course version

- Status: accepted under P-014.
- `Enrollment` is tenant-owned and relates one active learner membership to one course
  and one immutable course version.
- The create request accepts `course_id` only. Inside one transaction, the service
  re-derives the learner membership, locks/rechecks the course, and copies its current
  published version ID into the enrollment. A browser cannot select a version.
- An active-enrollment partial unique constraint covers
  `(tenant_id, learner_membership_id, course_id)`; revoked rows remain historical and
  immutable except for append-only related facts.
- A publication-pointer advance never changes an existing enrollment pin. A later
  enrollment pins the then-current published version.
- The initial `admission_source` is exactly `manual_assignment`.

### F007-TD-002 — Playback is enrollment-scoped and version-stable

- Status: accepted under P-014.
- Every dashboard, outline, and lesson selector re-derives the actor's current tenant,
  membership, permission, enrollment ownership, enrollment status, and pinned version.
- The dashboard lists only the current learner's active enrollments, ordered by
  `(enrolled_at DESC, id DESC)` with a maximum page size of 50 and an opaque cursor.
- A playback snapshot returns learner-safe course/version metadata, ordered sections
  and lessons, progress summaries, and a resume lesson. A lesson response returns one
  lesson's F-002 rich-text blocks plus previous/next lesson IDs.
- Raw HTML, source documents, generation/review/provenance data, author/reviewer
  identities, and unrestricted audit data are never returned.
- A current publication-pointer change cannot alter the enrollment's title, outline,
  lesson IDs, content hash, or content. Withdrawal does not silently fall forward.

### F007-TD-003 — Progress changes only through explicit optimistic commands

- Status: accepted under P-014.
- GET operations are selectors and have no business-state side effect.
- `open_lesson`, `complete_lesson`, and `reopen_lesson` require an HTTP
  `Idempotency-Key`, a route-matching command discriminator, `lesson_id`, and the
  expected progress row version. Zero means the learner expects no progress row yet.
- The server validates that the lesson belongs to the pinned version, locks or
  compare-and-swaps the progress aggregate, derives lesson/course state, and commits
  progress, audit, idempotency, and outbox facts atomically.
- Same key and canonical request returns the recorded result. Same key with a changed
  request returns `IDEMPOTENCY_CONFLICT`. A stale expected version returns
  `PROGRESS_VERSION_CONFLICT` without a partial change.
- Resume position is the most recently successful explicit `open_lesson` or lesson
  transition, with deterministic server time and identifier tie-breaking.

### F007-TD-004 — The learner surface is minimal and private

- Status: accepted under P-014.
- The web surface contains a private learner-course list, an enrollment playback page,
  one rich-text lesson renderer, previous/next navigation, resume, complete, and reopen
  controls, and safe empty/loading/error states.
- It consumes the generated API client. Browser-supplied tenant, learner, enrollment,
  course, version, lesson, and progress IDs are selectors only.
- The rich-text response directly references
  `contracts/f002/canonical-course.v1.schema.json#/$defs/rich_text_document`; F-007
  cannot broaden its node/mark set or add fallback HTML.
- Inaccessible, guessed, revoked, wrong-tenant, and unavailable enrollment resources
  use neutral `LEARNING_RESOURCE_NOT_FOUND` behavior.

### F007-TD-005 — Learning owns authorization, transactions, and RLS

- Status: accepted.
- The Learning module owns enrollment and progress invariants. It reads published
  course/curriculum state through the Courses public boundary and never mutates F-002
  models directly.
- `learner` receives `learning.playback.read`; `tenant_admin` receives
  `learning.enrollments.manage`. Instructor/reviewer roles do not imply either grant.
- User requests require current active tenant, entitlement, membership, and resource
  relationship. Service/worker identities have no F-007 authority.
- Tenant-owned learning tables repeat `tenant_id`, use composite same-tenant foreign
  keys, force RLS, and are tested as non-owner API roles. Current membership and
  enrollment state are re-read inside the command/selector transaction.
- Django Admin enrollment actions call the same application service; generic field
  editing cannot create, revoke, or repin an enrollment or mutate progress.

### F007-TD-006 — One vertical issue owns shared integration hotspots

- Status: accepted.
- F-007 is implemented in issue
  [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46). The
  [project-owner disposition](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46#issuecomment-5380754610)
  closed decision correction [#50](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/50)'s
  already-merged launch hold without claiming retroactive approval. Issue #46 is the
  sole F-007 owner for learning migrations/RLS, permission
  additions, services, API/Admin, composition, OpenAPI/client generation, web/player,
  events, tests, and documentation manifest.
- F-001/F-002 paths and contracts remain read-only inputs except for narrow,
  issue-declared permission/composition integration owned by the F-007 issue.
- No provider, queue, storage, dependency, lockfile, CI, analytics, notification, or
  production configuration is added.

## Frozen executable DTO contract

The schema and examples are
`contracts/f007/learner-playback.v1.schema.json` and
`contracts/f007/learner-playback.v1.examples.json`.

| DTO | Direction | Required content |
|---|---|---|
| `CreateEnrollmentV1` | request | `learner_membership_id`, `course_id` |
| `RevokeEnrollmentV1` | request | expected enrollment row version and bounded reason code |
| `EnrollmentV1` | response | enrollment/course/version pin, source, state, timestamps, row version |
| `LearnerDashboardV1` | response | bounded own-enrollment cards and opaque next cursor |
| `PlaybackSnapshotV1` | response | pinned metadata, ordered outline, progress summary, resume lesson |
| `LessonPlaybackV1` | response | one pinned lesson, F-002 rich-text blocks, progress, previous/next IDs |
| `ProgressCommandV1` | request | route-matching command, lesson ID, expected progress row version |
| `ProgressResultV1` | response | lesson/course progress states, counts, resume lesson, row version |

Bodies never accept tenant authority, actor ID, authoritative course-version ID,
status timestamps, or idempotency keys. Request schemas reject unknown properties.

## Frozen HTTP contract

All paths are under `/api/v1/tenants/{tenant_id}` and require `Authorization` plus a
matching `X-Tenant-ID`.

| Method/path | Operation ID | Request | Success | Idempotency |
|---|---|---|---|---|
| `POST /enrollments` | `createEnrollment` | `CreateEnrollmentV1` | `201 EnrollmentV1` | header required |
| `POST /enrollments/{enrollment_id}/revoke` | `revokeEnrollment` | `RevokeEnrollmentV1` | `200 EnrollmentV1` | header required |
| `GET /learner/courses` | `listLearnerCourses` | cursor/limit | `200 LearnerDashboardV1` | none |
| `GET /learner/enrollments/{enrollment_id}/playback` | `getLearnerPlayback` | none | `200 PlaybackSnapshotV1` | none |
| `GET /learner/enrollments/{enrollment_id}/lessons/{lesson_id}` | `getLearnerLesson` | none | `200 LessonPlaybackV1` | none |
| `POST /learner/enrollments/{enrollment_id}/progress/open-lesson` | `openLearnerLesson` | `ProgressCommandV1:open_lesson` | `200 ProgressResultV1` | header required |
| `POST /learner/enrollments/{enrollment_id}/progress/complete-lesson` | `completeLearnerLesson` | `ProgressCommandV1:complete_lesson` | `200 ProgressResultV1` | header required |
| `POST /learner/enrollments/{enrollment_id}/progress/reopen-lesson` | `reopenLearnerLesson` | `ProgressCommandV1:reopen_lesson` | `200 ProgressResultV1` | header required |

The dashboard accepts `limit` (default 20, maximum 50) and an opaque cursor. It
re-authorizes every page and never treats the cursor as authority.

## Stable problem codes

`AUTHENTICATION_REQUIRED`, `TENANT_CONTEXT_REQUIRED`, `TENANT_ACCESS_INACTIVE`,
`LEARNING_RESOURCE_NOT_FOUND`, `ENROLLMENT_VALIDATION_FAILED`,
`PROGRESS_VERSION_CONFLICT`, `IDEMPOTENCY_CONFLICT`, and
`SERVICE_CONTRACT_ERROR`.

Withdrawn/archived pins use neutral `404 LEARNING_RESOURCE_NOT_FOUND`; the schemas do
not expose a separate existence oracle and the service never auto-migrates the pin.

## Frozen event facts

The executable event schema/example pair is
`contracts/f007/learner-events.v1.schema.json` and
`contracts/f007/learner-events.v1.examples.json`. Events use the repository v1
envelope and contain identifiers, state, versions, counts, reason codes, and the
admission source only—never title, description, lesson text, source/provenance,
tokens, or unrestricted actor data.

| Event type | Minimum payload |
|---|---|
| `learning.enrollment.created.v1` | enrollment, learner membership, course/version IDs, source, aggregate version |
| `learning.enrollment.revoked.v1` | same IDs, reason code, aggregate version |
| `learning.lesson.progressed.v1` | enrollment/version/lesson IDs, prior/new lesson state, aggregate version |
| `learning.course.completed.v1` | enrollment/version IDs, required/completed counts, aggregate version |
| `learning.course.reopened.v1` | enrollment/version/lesson IDs, required/completed counts, aggregate version |

## Shared hotspots and owner

F-007 implementation issue #46 is the only owner of learning migrations,
permissions, application composition/settings, OpenAPI/client regeneration, web
playback routes, F-007 events, integration/E2E fixtures, status documentation, and
`manifest.json`. Its owner-approved launch disposition is recorded above, and its local
candidate is pinned by the implementation evidence; this does not supply the still
required independent review or approval of the final PR head.

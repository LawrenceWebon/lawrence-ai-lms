# Test Plan — F-007 Learner Course Playback and Progress

Status: **planning proposal; implementation evidence does not exist**

## Software correctness

### Contract

- Check every F-007 schema as Draft 2020-12 and validate every named DTO/event example
  with the F-002 rich-text schema registered at its exact `$id`.
- Reject unknown properties, malformed UUID/timestamp/hash/cursor values, unsupported
  states/sources/commands, missing conditional fields, and request bodies containing
  tenant, actor, authoritative course-version, or idempotency authority.
- Prove lesson content is accepted only through the exact F-002
  `rich_text_document` reference; reject raw HTML, URL, image, embed, source,
  provenance, generation, or review fields.
- Validate synthetic fixtures for active pin, empty dashboard, revoked enrollment,
  revoked membership, wrong tenant, guessed lesson, publication-pointer advance, and
  withdrawn pinned version.
- Prove event payloads contain only the allowlisted identifiers/state/version/count/
  reason/source fields and reject lesson/course text or source/provider content.

### Unit and policy

- Tenant administrator create/revoke permission versus learner/instructor/reviewer/
  service denial.
- Learner playback permission plus own active enrollment relationship; permission alone
  never grants an enrollment-less or other learner's read.
- Current active tenant, entitlement, membership, enrollment, course/version, and
  lesson relationship checks for every selector and command.
- F007-Q01 accepted re-enrollment behavior and terminal old enrollment.
- F007-Q02 accepted withdrawal/archive behavior and no auto-migration.
- F007-Q03 transition table for unstarted/in-progress/completed lesson and course
  progress, including repeated/no-op/forbidden transitions.
- Required-versus-optional lesson completion and reopen derivation.
- Publication-pointer advance leaves an existing pin and all progress semantics
  unchanged.
- Cursor encoding/binding, maximum/default page size, filter/endpoint mismatch,
  tamper/expiry, duplicate sort values, and empty/end pages.

### Database and migration

- Forward migration, clean rollback/roll-forward plan, graph order, schema fingerprint,
  executable data dictionary, named constraints/indexes, and
  `makemigrations --check`.
- Composite same-tenant FK negatives for learner membership, course, pinned course
  version, section/lesson, enrollment/progress, audit, and outbox edges on insert and
  update.
- One active enrollment per tenant/learner/course; multiple historical revoked rows
  allowed only under the accepted re-enrollment policy.
- Browser cannot repin an enrollment; publication-pointer updates cannot rewrite it;
  revoked enrollment facts cannot be deleted or reused as a new active row.
- Forced RLS as the non-owner API role: absent/malformed/wrong/stale context,
  cross-tenant CRUD, other learner, guessed ID, tenant mutation, inactive membership/
  entitlement, revoked enrollment, helper/view access, and connection-pool reset.
- Expected row-version constraints, unique progress parent/lesson rows, deterministic
  counts/resume selection, and indexes for the dashboard and player query shapes.

### Service and transaction

- Create enrollment locks/rechecks the course pointer and pins exactly one currently
  published version; no current publication fails atomically.
- Revoke validates current state/version and commits enrollment, audit, idempotency,
  and outbox facts together.
- Playback selectors perform no insert/update, including first open or missing progress.
- Explicit open/complete/reopen validates the pinned lesson and atomically changes
  lesson/course progress, resume state, audit, idempotency, and outbox facts.
- Same key/same canonical request returns one result; same key/changed request conflicts;
  an injected failure rolls back all facts.
- Two simultaneous assignment attempts produce one active enrollment; two progress
  commands with the same expected version produce one winner and one stable conflict.
- Immediate read-after-write uses primary authority and returns the winning progress.
- Membership or enrollment revocation between authorization and write cannot commit a
  progress change.

### API and Admin

- Exact methods, operation IDs, headers, strict DTOs, success statuses, RFC Problem
  Details media type/codes, response validation, and generated OpenAPI compatibility.
- Missing/malformed authentication, missing/mismatched tenant header/route, inactive
  access, permission denial, other learner, wrong tenant, guessed enrollment/lesson,
  unavailable pin, stale version, and idempotency conflict matrices for every route.
- Neutral denials do not reveal whether an enrollment, course, version, or lesson
  exists and do not include titles/content in errors or logs.
- Admin uses the shared service; generic save cannot create/revoke/repin enrollment or
  write progress, and current actor/tenant context is mandatory.

### Integration and browser

- Alpha admin assigns an active Alpha learner to published v1; the learner dashboard
  lists exactly that private enrollment and an un-enrolled learner sees a safe empty
  state with no catalog/self-enroll control.
- Alpha opens v1 outline and lesson, explicitly records resume, completes and reopens a
  required lesson, refreshes, and resumes at the recorded lesson.
- Publishing v2 changes the course pointer but not Alpha's pinned v1 title, content
  hash, outline, lesson IDs, content, or progress.
- Beta, outsider, another Alpha learner, and an inactive/revoked member cannot discover
  or retrieve Alpha's enrollment/content/progress.
- Enrollment revocation and the accepted withdrawn-pin policy clear rendered browser
  content and show one accessible neutral unavailable state on the next request.
- Two browser sessions exercising stale progress yield one winner and a recoverable
  conflict without silently overwriting completion.
- No core LMS data is read directly from Supabase or stored as authorization state in
  local/session storage.

## Security and privacy

- Rich-text rendering escapes content and has no raw HTML/URL/embed execution path.
- IDOR/cross-tenant matrix covers every route, production role, parent-child edge, and
  browser navigation selector.
- Architecture tests reject router/Admin direct model writes and Learning mutation of
  Course-owned models.
- Secret/log capture proves no token, lesson body, course description, source content,
  review/provenance data, or private learner identity enters general logs/events.
- Only synthetic `.invalid` identities and invented course text are used. No private
  PDF, production data, provider payload, prompt, or chat is introduced.

## Accessibility and localization

- Automated axe checks supplement keyboard-only operation, logical focus order,
  visible focus, skip/navigation landmarks, semantic headings, labelled progress
  controls, and announced loading/success/conflict/unavailable states.
- Test 200% text zoom, 400% reflow, forced colors/high contrast, reduced motion, and
  responsive orientation for dashboard and player.
- Verify the owner-approved initial locale, fallback chain, language metadata, and
  preserved F-002 course primary locale. Run an RTL structural interaction check
  without claiming an unapproved pilot locale.
- Record browser/OS/assistive-technology versions, tester, result, defects, and retest
  evidence for the critical learner journey.

## Performance and resilience

- Assert bounded dashboard page size, query count, deterministic keyset order, and
  indexed `EXPLAIN` evidence for the approved workload shape.
- Exercise duplicate/stale progress bursts and concurrent assignment without lost
  updates, duplicate active enrollments, or authorization bypass.
- No cache is required. If later measurement justifies one, it needs a separate
  approved cache-matrix decision; authorization, enrollment, and progress remain
  PostgreSQL authority.
- Local implementation may prove restart/retry and transaction rollback behavior but
  cannot claim production SLO, capacity, recovery, retention, or real-data readiness.

## Not applicable

- PDF upload/extraction/OCR, AI generation/evaluation/provenance, prompt injection,
  vector/RAG, commerce/payment, assessments/grades/certificates, notifications,
  analytics, provider sandboxes, and production object recovery are absent and
  disabled by F-007.
- F-001 tenant isolation, F-002 immutable publication, learner relationship
  authorization, progress correctness, accessibility, and event minimization remain
  applicable and non-waivable.

## Commands and pass criteria

Planning verifies the executable contract package in the dedicated Compose stack:

```text
docker compose up -d --build --wait
docker compose exec -T backend pytest backend/tests/contracts/test_f007_contracts.py
docker compose exec -T backend ruff check backend/tests/contracts/test_f007_contracts.py
pwsh -NoProfile -File ./scripts/generate-document-manifest.ps1 -Check
pwsh -NoProfile -File ./scripts/validate-markdown-links.ps1
git diff --check
```

The future implementation adds the complete repository gates:

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

It must also run the focused F-007 migration/RLS/service/API/Admin/event/client/player/
accessibility/concurrency suites. All applicable checks pass with zero lint/type errors;
protected GitHub checks and an independent exact-head review remain required before
merge.

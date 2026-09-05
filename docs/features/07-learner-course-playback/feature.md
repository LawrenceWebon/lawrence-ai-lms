# F-007 — Learner Course Playback and Progress

Status: **implementation merged; independent post-merge audit requires enrollment-RLS remediation #60**

Feature ID: `F-007`

Planning issue: [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45)

Implementation issue: [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46)

Local implementation evidence:
[F007-LOCAL-IMPLEMENTATION-2026-08-22](../../evidence/f007-learner-playback-implementation.md)

## Outcome

An active, enrolled learner can enter their tenant, open the exact published course
version pinned to their enrollment, read the supported rich-text lessons, save a
deliberate learning position, and resume it later without gaining visibility of draft,
source, generation, review, or another tenant's data.

## Actors and permissions

| Actor | Allowed behavior | Never implied |
|---|---|---|
| Learner | Read only their own active enrollment/playback records and issue explicit progress commands with `learning.playback.read` | Self-enrollment, access to a different learner's enrollment, source/generation/review data, unpublished content, or an enrollment-less course read |
| Tenant administrator | Create or revoke a manual enrollment with `learning.enrollments.manage` | Automatic playback access, learner impersonation, cross-tenant assignment, or a public catalog |
| Instructor/reviewer | Continue to use F-002 authoring/review permissions; may play only when separately holding the learner role and an active enrollment | Implicit learner access from author/reviewer status |
| Worker, AI, provider, or service identity | No learner playback or progress authority | Creating/revoking enrollment or acting as a learner |
| Platform operator | No standing learner-content access | Broad support browsing or tenant impersonation |

The initial role grants are deliberately least-privilege: `learner` receives
`learning.playback.read`; `tenant_admin` receives
`learning.enrollments.manage`; no other F-007 permission is implied. A current,
tenant-scoped enrollment remains mandatory after the role check.

## User flow

1. A tenant administrator manually assigns an active learner to a course. The
   service—not the browser—locks the course's current published version and records
   that immutable version as the enrollment pin. Revocation is terminal; a later
   re-enrollment creates a new record, pins the then-current published version, and
   copies no historical progress.
2. The learner authenticates and explicitly selects an active tenant.
3. The learner dashboard lists only the learner's active enrollments in that tenant;
   an active learner with none sees an empty state instead of a catalog or self-enroll
   control.
4. The learner opens an enrollment. The server re-derives membership, permission,
   enrollment ownership, and the pinned course version before returning a navigable
   playback outline.
5. The learner opens a lesson and sends an explicit, idempotent progress command to
   record the resume position. A read request never mutates progress.
6. The learner explicitly marks a lesson complete or reopens it. The server marks the
   course complete exactly when all required pinned-version lessons are complete and
   reopens it when a required lesson reopens.
7. On a later visit, the server returns the pinned version and the recorded resume
   lesson. A later publication pointer never rewrites that enrollment.
8. Revoked membership/enrollment or a withdrawn/archived pinned version fails closed
   for new reads and commands with neutral `404 LEARNING_RESOURCE_NOT_FOUND`; the
   durable audit/progress history remains available only to its authorized operational
   policy and no enrollment is automatically migrated.

## Requirements

- F-007 consumes the F-002 canonical rich-text contract and immutable published
  versions. It does not duplicate, reinterpret, or mutate course/curriculum records.
- An enrollment has one tenant, learner membership, course, immutable pinned course
  version, admission source, lifecycle status, row version, and audit/outbox lineage.
- A browser never supplies the authoritative tenant, learner, course version, or
  entitlement. Each command re-derives current state inside the same transaction.
- The learner dashboard and playback routes are enrollment-scoped, cursor-bounded,
  tenant-isolated, and return only learner-safe course metadata/content.
- The initial content renderer accepts the F-002 allowlisted rich-text tree only;
  raw HTML, source PDFs, generation artifacts, author/reviewer identities, and
  unrestricted provenance are absent.
- Progress is an explicit server command with an idempotency key and expected progress
  row version. Duplicate replay returns the original result; stale concurrent writes
  return a stable conflict without losing recorded completion.
- A course-publication-pointer change does not modify an existing enrollment pin. A
  new enrollment can only pin the then-current published version.
- The initial design introduces no provider, queue, storage, notification, commerce,
  assessment, note/bookmark, analytics, real data, or production capability.

## Failure behavior

| Condition | Required result |
|---|---|
| Missing/invalid authentication | `401 AUTHENTICATION_REQUIRED`; no learner/course disclosure |
| Missing tenant selector | `400 TENANT_CONTEXT_REQUIRED` |
| Inactive tenant, membership, or entitlement | Existing tenant-access failure; no cached playback remains authoritative |
| Guessed/wrong-tenant enrollment, lesson, course, or version | Neutral `404 LEARNING_RESOURCE_NOT_FOUND` |
| Active membership without learner playback permission or enrollment | Neutral `404 LEARNING_RESOURCE_NOT_FOUND`; dashboard may still return an empty own-enrollment list |
| Browser requests a lesson outside the enrollment's pinned version | Neutral `404 LEARNING_RESOURCE_NOT_FOUND` |
| Pinned version is withdrawn/archived, or enrollment is revoked | Neutral `404 LEARNING_RESOURCE_NOT_FOUND`; no new playback/progress succeeds and no version auto-migration occurs |
| Stale progress row version | `409 PROGRESS_VERSION_CONFLICT`; no partial state change |
| Duplicate idempotency key with a different command hash | `409 IDEMPOTENCY_CONFLICT`; same hash replays the stored result |
| Invalid/unrecognized content block or response shape | Fail closed as `500 SERVICE_CONTRACT_ERROR`; do not render fallback HTML |

## Acceptance criteria

- A synthetic Alpha learner with an active manual enrollment can list one private
  course, open its pinned v1 outline and lesson, deliberately record a resume lesson,
  complete/reopen a lesson, and resume after a refresh.
- A later v2 publication pointer does not alter Alpha's v1 enrollment, lesson IDs,
  content hash, ordered curriculum, or progress record.
- Beta, an outsider, a different Alpha learner, and an un-enrolled Alpha learner cannot
  discover or retrieve Alpha's enrollment, pinned version, lesson body, or progress;
  the own empty dashboard is distinguishable from a guessed resource only by safe UI
  state, not by a resource oracle.
- Membership/enrollment revocation and the approved withdrawn-course policy take effect
  on the next request. The browser clears rendered learner content and reports a safe,
  actionable unavailable state.
- Replayed create/revoke/open/complete/reopen commands have one durable effect; changed
  same-key requests conflict; stale multi-device writes preserve one recorded winner.
- The player is keyboard-operable, has a visible focus order, semantic course/section/
  lesson headings and navigation, labelled progress controls, a live status/error
  region, and reflows at 200% zoom. Initial pilot acceptance is exactly `en`; Unicode,
  fallback/language metadata, and RTL-ready structure are preserved without claiming
  another supported locale.

## Explicit non-goals

- PDF upload, extraction, OCR, source inspection, generation, provenance panels, or
  source-reference access;
- learner self-enrollment, public course discovery/catalog, checkout, entitlement from
  payment, coupons, invitations, or cohort/group rules;
- quizzes, assessments, grading, certificates, prerequisites, notes, bookmarks,
  discussion, messaging, downloads, media, links, assets, or adaptive learning;
- background progress capture from scroll/time/video telemetry, notifications,
  analytics, broad dashboards, and production-recovery claims; and
- a decision about real-data retention, legal hold, or production access policy.

## References

- Product: `docs/product/spec.md`
- Inventory: `docs/product/features.md`
- Decisions: P-001, P-002, P-003, P-005, P-007, P-009, P-010, P-011, P-012,
  P-014
- Existing contracts: `contracts/f002/canonical-course.v1.schema.json` and
  `contracts/f002/course-lifecycle.v1.schema.json`
- Plans: `docs/plan/04-domain-module-design.md`,
  `docs/plan/05-database-schema-plan.md`,
  `docs/plan/07-manual-course-authoring.md`,
  `docs/plan/11-api-and-event-contracts.md`,
  `docs/plan/12-security-and-multitenancy.md`,
  `docs/plan/13-performance-scalability-availability.md`,
  `docs/plan/15-testing-quality-gates.md`, and
  `docs/plan/18-localization-accessibility.md`
- ADRs: ADR-0001, ADR-0002, ADR-0004

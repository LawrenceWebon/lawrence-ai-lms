# F-002 — Canonical Course Lifecycle

Status: **corrective contract freeze pending independent review and merge**

Feature ID: `F-002`

Planning issue: [#27](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/27)

## Outcome

An authorized human can create a tenant-owned course draft, edit its ordered text
curriculum, submit an exact immutable content hash for review, approve that same hash,
and explicitly publish an immutable version through the one canonical course model.

## Actors and permissions

| Actor | Allowed in this slice | Never implied |
|---|---|---|
| Tenant administrator | Read, author, review, and publish through explicit permissions | Standing cross-tenant or model-bypass access |
| Instructor/course author | Read, create/edit drafts, submit review, review, and publish in the first pilot | Editing a submitted/approved/published snapshot in place |
| Reviewer | Read submitted versions, request changes, and approve the reviewed hash | Draft mutation or publication unless separately granted |
| Learner | No F-002 course access | Draft, review, or publication access |
| AI, worker, or service identity | No approval or publication | Acting as the accountable human |
| Platform operator | No standing course-content access | Impersonation or broad tenant access |

The fixed permission codes are `courses.read`, `courses.drafts.write`,
`courses.review`, and `courses.publish`. Default role grants are:

- `tenant_admin`: all four;
- `instructor`: all four for the first pilot under P-010;
- `reviewer`: `courses.read` and `courses.review`;
- `learner`: none in F-002.

Every command still re-derives the active tenant, membership, entitlement, permission,
course ownership, and current version state inside the transaction. A role or visible UI
control is not authorization authority.

## User flow

1. An authenticated instructor explicitly selects an active tenant.
2. The instructor creates a stable course and its first draft version.
3. The instructor adds ordered sections, lessons, and structured rich-text blocks.
4. Each draft mutation supplies the expected `row_version`; stale writes fail without
   changing the draft.
5. The instructor submits the draft. The service validates it, computes the canonical
   content hash, and records the immutable submitted hash.
6. A qualified human reviews that exact hash and either requests changes or approves
   it. A tenant policy may require a separate reviewer; the first pilot otherwise
   permits an authorized instructor to review their own draft with an audit fact.
7. An authorized human publishes the exact approved hash. One transaction freezes the
   version, updates the course publication pointer, and records audit/outbox facts.
8. The instructor opens tenant-scoped version history and explicitly creates a
   successor draft from the immutable version. The successor records its predecessor,
   starts with new child identities and review state, and leaves the predecessor
   unchanged.

## Requirements

- One stable `Course` owns ordered immutable/mutable `CourseVersion` records.
- A version owns ordered `CurriculumSection`, `Lesson`, and `RichTextBlock` records.
- F-002 supports one provider-neutral rich-text document tree: paragraphs, headings
  levels 2–4, bullet/ordered lists, list items, text, and `strong`, `emphasis`, or
  `code` marks. It stores no HTML, URL, embed, script, asset, or provider payload.
- Canonical states remain `draft`, `under_review`, `changes_requested`, `approved`,
  `scheduled`, `published`, `withdrawn`, and `archived`. The first vertical slice
  exposes immediate human publication; scheduled publication UI/execution is not
  enabled, but the canonical value is reserved against incompatible aliases.
- Only `draft` and `changes_requested` content is mutable. Submission, approval, and
  publication compare the exact canonical content hash.
- Published content and its curriculum children are immutable at service and database
  boundaries. A new version is required for material change.
- Snapshot reads select an exact course/version pair. Version history is ordered by
  descending `version_number`, cursor-paginated, tenant/course scoped, and never
  treats a cursor or path tenant as authorization authority.
- Successor creation compares the course row, source-version row, and source content
  hash; it deep-copies product content into a mutable `draft`, resets review fields and
  child row versions, and records `predecessor_version_id` without changing the source.
- Every tenant-owned table has `UNIQUE (tenant_id, id)`, composite same-tenant foreign
  keys, forced RLS, explicit grants, named constraints/indexes, and rollback evidence.
- Section, lesson, and block positions are positive and unique inside their parent.
  Reorder uses expected versions and one atomic operation.
- The publication pointer and publish/audit/outbox facts commit atomically. No network
  call occurs inside the transaction.
- API and Admin adapters call the same application service and return neutral RFC
  Problem Details for denied or stale selectors.

## Failure behavior

| Failure | Required result |
|---|---|
| Missing/stale identity, membership, entitlement, or permission | Fail closed without tenant/course disclosure |
| Wrong-tenant or guessed course/version/child ID | Neutral `404 RESOURCE_NOT_FOUND` |
| Missing active tenant selector | `400 TENANT_CONTEXT_REQUIRED` |
| Stale expected version | `409 VERSION_CONFLICT`; no partial mutation |
| Invalid structure, empty required content, or duplicate positions | `422 COURSE_VALIDATION_FAILED` with bounded field errors |
| Existing curriculum ID without its row version, unknown parent, or wrong-parent edge | `422 COURSE_VALIDATION_FAILED` for shape; otherwise neutral `404 RESOURCE_NOT_FOUND` |
| Submit/approve/publish hash mismatch | `409 CONTENT_HASH_MISMATCH`; approval is not reused |
| Separate reviewer required but same actor reviews | `403 REVIEWER_SEPARATION_REQUIRED` |
| AI/service actor attempts approval/publication | `403 HUMAN_ACTION_REQUIRED` |
| Edit of immutable state | `409 COURSE_VERSION_IMMUTABLE` |
| Simultaneous publication | Exactly one publication pointer wins; the stale command receives `409 VERSION_CONFLICT` |
| Publish transaction fails | Version, pointer, audit, and outbox all roll back |

## Acceptance criteria

- The synthetic Alpha instructor creates and edits a draft containing the frozen
  rich-text example; Beta and outsider selectors learn no Alpha course details.
- Stale draft updates and concurrent reorder attempts leave the winning snapshot intact.
- Submission records a deterministic hash; request-changes reopens only that version;
  approval records the exact reviewed hash.
- Human publication atomically updates one pointer and produces one idempotent result;
  AI/service principals cannot approve or publish.
- Published rows reject direct and service-level mutation. A new draft version can be
  created without altering the published snapshot.
- Exact snapshot and descending cursor history reads expose only authorized versions;
  successor creation is idempotent and preserves its immutable predecessor byte for byte.
- API and Admin contract tests prove parity through fakes; the integration issue proves
  real service/database composition and the critical browser journey.
- Production-role RLS and composite-FK tests cover missing context, wrong tenant,
  guessed IDs, insert/update tenant changes, pool reset, and immutable publication.

## Explicit non-goals

- PDF/source admission, extraction, OCR, AI generation, provenance, or provider setup;
- enrollment, playback, progress, learner catalog, or public discovery;
- quizzes, assignments, assessments, certificates, grading, or completion rules;
- downloadable files, approved-PDF blocks, links, images, media, embeds, HTML, or scripts;
- broad standalone authoring, collaboration, comments, templates, duplication, or autosave transport;
- scheduled-publication UI/worker, notifications, commerce, pricing, analytics, or deployment;
- real customer data or production activation.

## References

- Product: `docs/product/spec.md`
- Inventory: `docs/product/features.md`
- Decisions: P-002, P-003, P-005, P-007, P-010, P-011, P-012
- Plans: `docs/plan/04-domain-module-design.md`,
  `docs/plan/05-database-schema-plan.md`,
  `docs/plan/07-manual-course-authoring.md`, and
  `docs/plan/11-api-and-event-contracts.md`
- ADRs: ADR-0001, ADR-0002, ADR-0004

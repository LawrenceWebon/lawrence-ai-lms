# Technical Decisions — F-002 Canonical Course Lifecycle

Status: **frozen for planning issue #27; pending independent review**

## Existing architecture to reuse

- F-001 verified identity and explicit tenant context.
- F-001 production-role PostgreSQL RLS helpers and fixed role/permission catalog.
- The modular-monolith service/adapter boundary in ADR-0001 and ADR-0002.
- Django-only migration authority and FastAPI-owned HTTP/OpenAPI boundary.
- RFC Problem Details, optimistic row versions, atomic audit/outbox facts, and
  deterministic synthetic UUID conventions already used by F-001.
- The canonical human-review/publication rules in CHG-023 and ADR-0004.

## Decisions

### F002-TD-001 — One canonical course aggregate and immutable published version

- Status: frozen.
- `Course` is the stable tenant-owned identity and holds the nullable current published
  version pointer.
- `CourseVersion` owns its section/lesson/block snapshot. Publication never copies into
  a separate manual or AI table.
- Only `draft` and `changes_requested` content may mutate. Published, submitted,
  approved, withdrawn, and archived snapshots are not edited in place.
- A material change after approval creates a new draft version or returns the existing
  mutable successor; it never clears an immutable historical approval.

### F002-TD-002 — Q-P04 closes with a provider-neutral rich-text document tree

- Status: owner-approved by the instruction to implement the recommended next task.
- One `rich_text` block contains a structured JSON document, not HTML.
- Allowed block nodes are `paragraph`, `heading` levels 2–4, `bullet_list`,
  `ordered_list`, and `list_item`; inline text may use unique `strong`, `emphasis`, or
  `code` marks.
- Empty text, unknown nodes/marks/attributes, URLs, raw HTML, embeds, assets, and scripts
  are rejected. Rendering still escapes text and uses an allowlisted renderer.
- This is the smallest readable course shape usable by F-005 and F-007 fixtures.

### F002-TD-003 — Canonical content hash binds review and publication

- Status: frozen.
- The hash input contains version-owned product content only: primary locale, title,
  description, ordered sections, ordered lessons, ordered blocks, required flags, and
  rich-text trees. It excludes UUIDs, timestamps, actors, row versions, state, review
  records, and publication pointers.
- Serialize the hash input as RFC 8785 JSON Canonicalization Scheme UTF-8 bytes and
  store `sha256:<lowercase-hex>`.
- Submit recomputes and stores `submitted_hash`; approve requires the same current hash
  and stores `approved_hash`; publish requires current, submitted, and approved hashes
  to match. A caller-supplied hash is only an expected value, never authority.

### F002-TD-004 — State transition and mutation contract

- Status: frozen.

| Source | Command | Target | Actor and guard |
|---|---|---|---|
| none | create course | `draft` | `courses.drafts.write`; creates course + v1 atomically |
| `draft`/`changes_requested` | update/reorder | same | author permission + expected row versions |
| `draft`/`changes_requested` | submit review | `under_review` | author permission + complete validation + expected hash/version |
| `under_review` | request changes | `changes_requested` | qualified human reviewer + exact submitted hash |
| `under_review` | approve | `approved` | qualified human + reviewer policy + exact submitted hash |
| `approved` | publish now | `published` | human publisher + exact approved hash + pointer CAS |
| `published` | withdraw | `withdrawn` | human publisher + reason code + pointer CAS |
| `withdrawn` | archive | `archived` | records-authorized human; retention/hold check remains a later production gate |

`scheduled` is a reserved canonical state. No F-002 route or worker enters it. Enabling
scheduled execution requires a focused decision defining who performs the publication
act without weakening ADR-0004.

### F002-TD-005 — Human and reviewer policy

- Status: frozen.
- `principal_type=user` is mandatory for request-changes, approve, publish, withdraw,
  and archive. AI, worker, provider, and generic service identities receive
  `HUMAN_ACTION_REQUIRED` even if a payload names an initiating user.
- Default first-pilot policy is `self_review_allowed` under P-010. A self-review writes
  an explicit audit attribute.
- `separate_reviewer_required` rejects the submitting actor as reviewer. F-002 does not
  silently choose high-risk rights policy; F-006 may require the stricter setting.
- The service derives reviewer policy from current server-owned tenant/course policy.
  A create/update payload cannot select or weaken it. The separate-reviewer fixture is
  injected through the trusted policy port, not a browser field.

### F002-TD-006 — Optimistic concurrency and idempotency

- Status: frozen.
- Every mutable aggregate/child has `row_version >= 1`. Commands compare caller
  expectations and increment affected versions exactly once.
- Reorder accepts the complete ordered child-ID list and expected parent/child versions;
  it validates set equality and renumbers atomically.
- Create, submit, approve, publish, withdraw, and archive require `Idempotency-Key`.
  Same key/request returns the stored result; changed request returns
  `IDEMPOTENCY_CONFLICT`.
- Simultaneous publish locks/compares the course pointer and version. At most one
  version becomes the current published version.

### F002-TD-007 — Tenant-safe persistence and no alternate adapters

- Status: frozen.
- Minimum tables are `courses`, `course_versions`, `course_instructors`,
  `curriculum_sections`, `lessons`, `lesson_content_blocks`, and
  `course_publication_reviews`.
- Every tenant-owned edge repeats `tenant_id` and uses a composite FK; every table has
  forced RLS and non-owner runtime grants. Published immutability is independently
  enforced by database trigger/constraint logic owned by Django migrations.
- FastAPI and Admin call the same public application service. The browser uses only the
  generated client after the integration issue regenerates OpenAPI.

## Frozen DTO contract

The executable source is
`contracts/f002/canonical-course.v1.schema.json`; the example in the same directory is
the shared fixture for all lanes. The versioned response names are:

| DTO | Required content |
|---|---|
| `CourseSnapshotV1` | stable course, one version, ordered curriculum, latest review, reviewer policy |
| `CourseSummaryV1` | course/version IDs, slug, title, state, row versions, published pointer |
| `MutationResultV1` | snapshot, changed row versions, content hash, idempotent replay flag |
| `ValidationReportV1` | `valid`, bounded stable errors `{code,path,message}` |
| `ReviewDecisionV1` | review ID, decision, reviewed hash, human actor ID, timestamp |

Input DTOs reject unknown fields and include the explicit tenant selector in the
header, never as authorization authority:

- `CreateCourseV1`: slug, primary locale, title, and description. Reviewer policy is
  returned but never caller-selected.
- `UpdateCourseVersionV1`: expected version row version plus changed scalar fields.
- `ReplaceCurriculumV1`: complete ordered section/lesson/block tree plus expected
  version row version; this coarse endpoint is the frozen first-slice edit boundary.
- `TransitionCourseVersionV1`: expected row version, expected content hash, optional
  stable reason code, and idempotency key where required.

## Frozen HTTP contract

The adapter lane owns schemas/routers but not application composition or generated
artifacts. All paths are under `/api/v1/tenants/{tenant_id}` and require
`Authorization` plus matching `X-Tenant-ID`.

| Method/path | Operation ID | Success |
|---|---|---|
| `POST /courses` | `createCourse` | `201 CourseSnapshotV1` |
| `GET /courses/{course_id}` | `getCourse` | `200 CourseSnapshotV1` |
| `PATCH /courses/{course_id}/versions/{version_id}` | `updateCourseVersion` | `200 CourseSnapshotV1` |
| `PUT /courses/{course_id}/versions/{version_id}/curriculum` | `replaceCourseCurriculum` | `200 CourseSnapshotV1` |
| `POST /courses/{course_id}/versions/{version_id}/submit-review` | `submitCourseReview` | `200 CourseSnapshotV1` |
| `POST /courses/{course_id}/versions/{version_id}/request-changes` | `requestCourseChanges` | `200 CourseSnapshotV1` |
| `POST /courses/{course_id}/versions/{version_id}/approve` | `approveCourseVersion` | `200 CourseSnapshotV1` |
| `POST /courses/{course_id}/versions/{version_id}/publish` | `publishCourseVersion` | `200 CourseSnapshotV1` |
| `POST /courses/{course_id}/versions/{version_id}/withdraw` | `withdrawCourseVersion` | `200 CourseSnapshotV1` |
| `POST /courses/{course_id}/versions/{version_id}/archive` | `archiveCourseVersion` | `200 CourseSnapshotV1` |

There is no list/search/catalog endpoint in F-002. F-007 owns learner-visible reads.

## Stable problem codes

`AUTHENTICATION_REQUIRED`, `TENANT_CONTEXT_REQUIRED`, `RESOURCE_NOT_FOUND`,
`TENANT_ACCESS_INACTIVE`, `COURSE_PERMISSION_DENIED`, `COURSE_VALIDATION_FAILED`,
`VERSION_CONFLICT`, `CONTENT_HASH_MISMATCH`, `COURSE_VERSION_IMMUTABLE`,
`REVIEWER_SEPARATION_REQUIRED`, `HUMAN_ACTION_REQUIRED`, `IDEMPOTENCY_CONFLICT`, and
`SERVICE_CONTRACT_ERROR`.

Denied tenant/resource selectors use neutral titles/details and never enumerate course
existence. Validation errors are bounded to 100 safe entries and never echo full lesson
content.

## Frozen event facts

The existing v1 event envelope applies. Events contain identifiers, hashes, versions,
reason codes, and policy flags only—never title, description, lesson text, review notes,
tokens, or unrestricted actor data.

| Event type | Minimum payload |
|---|---|
| `course.version.submitted.v1` | `course_id`, `course_version_id`, `content_hash`, `aggregate_version` |
| `course.version.changes_requested.v1` | same + `review_id`, `reason_codes` |
| `course.version.approved.v1` | same + `review_id`, `self_review` |
| `course.version.published.v1` | same + nullable `previous_published_version_id` |
| `course.version.withdrawn.v1` | same + `reason_code` |
| `course.version.archived.v1` | same |

## Shared hotspots and owner

The F-002 integration issue is the only owner of common settings/composition,
OpenAPI/client regeneration, root contracts/events beyond `contracts/f002`, shared CI,
and `manifest.json` after planning. The persistence issue solely owns the F-002 Django
migration graph, permission seed changes, RLS/grants, and data dictionary. Other lanes
must not edit those files.

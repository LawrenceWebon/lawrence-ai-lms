# Manual Course Authoring Plan

Status: **initial-MVP capability; implementation evidence pending**  
Change ID: CHG-023

## Goal

Build the canonical authoring system first. AI-generated course drafts must use this same model and workflow.

## Course lifecycle

The canonical state names are:

```text
draft -> under_review -> changes_requested -> under_review
      -> approved -> scheduled -> published -> withdrawn -> archived
```

An approved version may publish immediately without entering `scheduled`. `withdrawn` is the sole unpublished terminal transition before archive; aliases such as `unpublished` or compound statuses such as `scheduled_or_published` are not persisted states.

## Course builder steps

1. Basic information
2. Media
3. Curriculum
4. Outcomes, requirements, audience, and FAQ
5. Assessments
6. Certificate and completion rules
7. Availability; pricing appears only after paid commerce is separately enabled
8. Preview and validation
9. Review submission
10. Publication

## Curriculum model

```text
Course
└── Course Version
    ├── Module / Section
    │   ├── Lesson
    │   │   ├── Content Block
    │   │   ├── Resource
    │   │   ├── Quiz
    │   │   └── Assignment
    │   └── Section completion rule
    └── Course completion rule
```

## Supported lesson types

| Lesson/content type | Initial disposition |
|---|---|
| Rich text, downloadable resource, approved PDF, external link | initial MVP |
| Basic quiz | deferred assessment increment |
| Managed video/embed and audio with captions/transcripts | post-launch after provider/accessibility/privacy/cost approval; bytes do not traverse the web/API stack |
| Presentation and generic embedded content | post-launch after sandbox/CSP/accessibility review |
| Assignment and survey | post-launch learning increment |
| Live session | manual audited link may be post-launch; provider integration remains deferred |

## Authoring requirements

- Autosave drafts with optimistic concurrency.
- Explicit version history.
- Drag-and-drop ordering using stable position values.
- Preview as student.
- Duplicate module, lesson, quiz, or course.
- Validate required content before review.
- Provide accessibility fields for images, video captions, and transcripts.
- Never modify a published version in place.
- Create a new draft version for changes.
- Preserve the version assigned to existing enrollments.

### Prerequisite and ordering integrity

- Every prerequisite edge carries `tenant_id` and exact immutable `course_version_id`; both endpoints use composite same-tenant/version foreign keys.
- Self-edges, duplicate edges and references to a draft/published item in another version are rejected.
- The publication service locks or version-checks the graph, runs a complete acyclic-graph validation, and rejects cycles with a stable path/error code. A browser ordering check is never sufficient.
- Required lessons/sections have unique stable position values within their parent. Concurrent reorder uses expected `row_version` and one atomic renumber/rebalance operation.
- A new course version may change prerequisites; an enrolled learner remains pinned to the prior graph unless an explicit audited migration policy moves the enrollment.

## Publication validation

A course cannot be published unless:

- Title and description exist in the primary locale.
- At least one required lesson exists.
- Each lesson has valid content.
- Required assets completed processing.
- If and only if paid commerce is enabled, price/product/entitlement configuration is valid under the finance gate.
- Completion rules are achievable.
- Assessment references are valid.
- Instructor assignment exists.
- Course reviewer approval exists when required.

## Shared manual and AI rules

- `origin_type` records how an item was created.
- Manual editing is always allowed on AI drafts.
- Approved manual edits are never overwritten by regeneration.
- Regeneration creates a new artifact revision.
- AI suggestions appear as changes to review, not silent updates.

Pricing fields in the builder remain hidden and inert in the initial MVP; they appear only after paid commerce is separately enabled.

## Canonical publication state machine (CHG-023)

Manual, imported and future AI-assisted paths call one course-version canonicalizer and the same transition service:

```text
draft -> under_review -> changes_requested -> under_review
      -> approved -> scheduled -> published -> withdrawn -> archived
```

| Transition | Allowed actor | Required evidence/invariants |
|---|---|---|
| create/update draft | Authorized author/editor | Active tenant/membership, optimistic `row_version`, mutable draft only |
| submit review | Author/editor | Complete validation report and immutable submitted content hash |
| request changes/reject | Qualified reviewer | Rubric/version, findings and actor; high-risk separation rule |
| approve | Qualified human reviewer only | Reviewed hash, rubric/evidence, reviewer qualification; AI/service actor denied |
| schedule/publish | Authorized publisher | Same approved hash; valid schedule when used; active rights for every source; prerequisite DAG, assessment and accessibility integrity; compare-and-swap publication pointer |
| withdraw | Authorized publisher/compliance operator | Reason, impact, notification and audit |
| archive | Records-authorized actor | Not currently published; retention/legal-hold checks |

Published course versions and referenced curriculum/assessment content are immutable. Any material edit, source/rights change, regenerated artifact, prompt/model change affecting content, or failed evaluation creates a new draft/revision and invalidates prior approval for that new hash. One transaction atomically validates the approved immutable version, updates the course publication pointer, records audit/outbox events and rejects stale concurrent publication. Existing enrollments remain pinned according to explicit version-migration policy.

Required tests cover every allowed/forbidden transition and actor, same-person override audit, stale optimistic lock, edit-after-approval, simultaneous publish, schedule timing, self/duplicate/cyclic/cross-version prerequisites, concurrent reorder, rights expiry, validation failure, API/Admin/worker parity and direct model/service attempts to approve.

# AI LMS Feature Inventory

Status: **approved MVP sequence; F-001 ready for lane issue creation**

Derived from: `docs/product/spec.md`

## Delivery order

| ID | Feature | Outcome | Depends on | Initial disposition |
|---|---|---|---|---|
| F-000 | Repository and Codex setup | Agents share product, workflow, skill, issue, and PR conventions | none | current setup |
| F-001 | Minimal identity and tenant context | Instructor, reviewer, learner, and admin actions have a verified tenant context | F-000 | MVP foundation |
| F-002 | Canonical course lifecycle | Draft, review, publication, versioning, and course structure exist independently of AI | F-001 | MVP foundation |
| F-003 | PDF upload and source admission | Authorized instructor safely uploads a private PDF and sees its lifecycle | F-001, frozen source contract | MVP core |
| F-004 | PDF extraction and normalization | Worker converts a PDF into a versioned normalized book structure | F-003, frozen ingestion-job and normalized-source contracts | MVP core |
| F-005 | Structured course generation | System creates a schema-valid grounded course draft with provenance | F-002, F-004, frozen normalized-source and course-draft contracts | MVP core |
| F-006 | Instructor review and publication | Authorized human edits, approves, and publishes a canonical course version | F-002, F-005 or its frozen course-draft fixture | MVP core |
| F-007 | Learner course playback and progress | Enrolled learner consumes the published course and resumes progress | F-001, F-002 | MVP core |
| F-008 | End-to-end PDF-to-course integration | The complete defining journey works across the independently built slices | F-003–F-007 | MVP integration |
| F-009 | MVP hardening | Failure recovery, accessibility, observability, security, and release evidence meet the focused MVP gate | F-008 | MVP release |

## Feature contracts

### F-000 — Repository and Codex setup

- **Why:** gives every later task one product authority, workflow, skill set, and
  reviewable handoff format.
- **User flow/UI:** no product UI; maintainers navigate the documentation and use the
  issue/PR templates.
- **Constraints:** documentation only, no application scaffold or provider selection.

### F-001 — Minimal identity and tenant context

- **Why:** every source, course, job, review, publication, enrollment, and progress
  action requires an authoritative actor and tenant boundary.
- **User flow:** invited member signs in, receives an active membership context, and
  enters only tenants and actions allowed by their role.
- **UI overview:** sign-in, invitation acceptance when needed, active-tenant selector,
  access-denied and inactive-membership states, and minimal member administration.
- **Constraints:** private/manual onboarding, no public signup; tenant IDs from the
  browser or JWT are selectors rather than authorization authority.

### F-002 — Canonical course lifecycle

- **Why:** AI output needs a stable, human-controlled destination that also supports
  manual correction and immutable publication.
- **User flow:** authorized author creates or edits a draft, submits/reviews the exact
  version, and an authorized human publishes it.
- **UI overview:** minimal course structure editor, draft/review status, validation
  errors, version history, and publish action.
- **Constraints:** one canonical course model; published versions are immutable; the
  first content-block set is resolved by Q-P04; no broad standalone authoring suite.

### F-003 — PDF upload and source admission

- **Why:** the defining journey needs a private, rights-aware, safe source entry point.
- **User flow:** instructor confirms an approved rights basis, selects a PDF, uploads
  it, and sees admission, rejection, cancellation, or processing state.
- **UI overview:** upload form, rights confirmation, progress/status, stable rejection
  reason, retry/cancel controls, and source detail.
- **Constraints:** PDF only; private quarantine; byte-derived validation; limits are
  approved under Q-P03; declaration alone cannot bypass operation authorization.

### F-004 — PDF extraction and normalization

- **Why:** generation must consume a stable source structure rather than raw PDF bytes.
- **User flow:** instructor monitors extraction, sees affected pages and quality state,
  retries a safe stage, or replaces an unusable source.
- **UI overview:** stage timeline, page/quality summary, actionable failure, and retry.
- **Constraints:** deterministic versioned normalized-source contract; text PDF plus
  scanned-PDF OCR fallback; no vector dependency by default; leases, checkpoints,
  idempotency, and rights revocation apply.

### F-005 — Structured course generation

- **Why:** converts the normalized book into the editable course draft that defines the
  product value.
- **User flow:** instructor supplies the minimum generation intent, starts a run,
  monitors it, and receives a grounded draft or a clear blocked/failed result.
- **UI overview:** generation request, status, source/quality gaps, course outline and
  lesson draft with provenance, and regenerate/reject actions.
- **Constraints:** autonomy is Draft; structured output and immutable run/source
  provenance are mandatory; provider and numeric quality gates remain Q-P01/Q-P07;
  no assessments or automatic publication.

### F-006 — Instructor review and publication

- **Why:** generated material becomes learner-visible only through accountable human
  review and the canonical course lifecycle.
- **User flow:** authorized instructor or reviewer edits/reorders/rejects the draft,
  reviews source references, approves the exact revision, and explicitly publishes.
- **UI overview:** editable hierarchy and lesson view, provenance panel, diff/version
  state, review decision, validation summary, and publish confirmation.
- **Constraints:** P-010 reviewer policy; edits/regeneration invalidate stale approval;
  no worker/model/service identity can approve or publish.

### F-007 — Learner course playback and progress

- **Why:** validates that the generated and approved structure works as an LMS course.
- **User flow:** enrolled learner opens a published version, moves through supported
  lesson content, records progress, leaves, and resumes.
- **UI overview:** course overview, lesson player, navigation, progress, empty/no-access
  states, and resume action.
- **Constraints:** enrollment and progress are tenant/version scoped; learners cannot
  view source PDFs, generation artifacts, or unpublished versions by default.

### F-008 — End-to-end PDF-to-course integration

- **Why:** independently testable slices must prove the single defining journey works
  together without hidden branch or contract coupling.
- **User flow/UI:** exercises F-003 through F-007 as one critical browser journey.
- **Constraints:** one integration owner handles migration order, composition,
  OpenAPI/generated client, shared events, and full synthetic-fixture wiring.

### F-009 — MVP hardening

- **Why:** a successful happy path is not enough for a tenant-isolated, asynchronous,
  AI-assisted content workflow.
- **User flow/UI:** verifies recovery, accessibility, localization, denial, and operator
  support states across the defining journey.
- **Constraints:** applicable Definition of Done, security, ingestion, generation,
  removal, recovery, accessibility, privacy, and evidence gates must pass; production
  approval is separate from local MVP completion.

## Parallel implementation lanes

After F-001/F-002 and the shared contract-freeze issue establish stable fixtures,
F-003 through F-006 may be split across four agents:

| Lane | Feature ownership | Works against |
|---|---|---|
| A | F-003 PDF upload and ingestion lifecycle | upload/source DTO and synthetic storage fixture |
| B | F-004 extraction/OCR worker | ingestion job envelope and legal golden PDFs |
| C | F-005 structured course generation | normalized-source and course-draft fixtures |
| D | F-006 review/publication services | course-draft fixture and canonical course contract |

F-007 may replace a lane or begin after one lane completes. F-008 owns integration
wiring, generated artifacts, migration ordering, and the complete browser journey.

## Deferred features

- AI companion/RAG and conversational memory;
- payments, subscriptions, marketplace finance, and payouts;
- advanced assessments, assignments, gradebook, and certificates;
- custom domains, live classes, native mobile, SCORM/xAPI, and proctoring; and
- broad dashboards and product analytics.

Deferred items require a new product decision before feature planning begins.

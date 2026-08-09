# AI LMS Product Planning Audit

Status: **PASS for Plan Feature; NOT READY for implementation or production**

Audited: 2026-08-09

## Audit boundary

This audit applies the repository-specific Plan Product workflow to the focused
PDF-to-course MVP. It verifies product clarity and the handoff into Plan Feature; it
does not claim that code, providers, migrations, tests, privacy approvals, capacity,
recovery, or release evidence exist.

## Evidence and assumption map

| Area | Fact or approved decision | Assumption | Open question/gate |
|---|---|---|---|
| Product focus | P-001/P-009: authorized PDF to structured draft, human publication, learner consumption | One representative book is sufficient for the first vertical slice | None for F-001 planning |
| Target users | Private-tenant instructor/reviewer, learner, tenant admin, scoped operator | First implementation targets adults; minors remain excluded | Pilot tenant and representative evaluation cohort before release |
| Tenancy | P-003: private multi-tenant system with server-authoritative membership and isolation | Manual invitations/provisioning are adequate initially | Exact F-001 acceptance and admin flow during Plan Feature |
| Course lifecycle | One canonical draft/review/immutable-publication lifecycle supports manual edits and AI drafts | Minimal editor is enough; broad standalone authoring is unnecessary | Q-P04 content-block set before F-002/F-005 contract freeze |
| PDF admission | P-011: text and scanned PDF are the only required source formats | Synthetic/rights-cleared fixtures represent the initial risk set | Q-P03 limits; operation-rights and production legal gates |
| Extraction/OCR | Versioned normalized structure, quality gate, retryable async stages | Provider-neutral adapter and fixtures can precede provider selection | Q-P02 engine/thresholds and worker/runtime gate |
| Course generation | P-002: autonomy is Draft; structured, grounded, versioned, provenance-preserving output | Provider-neutral contracts/fakes can precede external generation | Q-P01 provider/model, Q-P04 content types, Q-P07 evaluation thresholds |
| Review/publication | P-010: authorized instructor may self-review in the pilot unless stricter tenant/high-risk policy applies | Instructor is qualified for ordinary pilot material | Separate-review configuration and high-risk override evidence before applicable release |
| Learner experience | Enrolled learner consumes a published version and resumes progress | Minimum readable lesson content is enough for the first journey | Q-P04 content types and locale/accessibility acceptance |
| Deferred scope | Commerce, RAG/chat, assessments, vector indexing by default, non-PDF imports, and broad LMS features are excluded | None | New product decision required before planning any deferred item |
| Production | P-005: synthetic/rights-cleared local data only | Local planning can proceed without production procurement | Privacy, retention, provider, region, worker, capacity, recovery, and release gates remain open |

## Final findings

### BLOCKER

None for entry into the Plan Feature workflow.

### IMPORTANT

1. The external 2026-08-02 audit/decision register still describes all AI ingestion
   and generation as post-MVP. P-009 and the synchronized current plan supersede only
   that disposition; all safety, provider, real-data, and production blockers from the
   older audit remain active.
2. Q-P04 must close before the canonical content-block and course-draft contracts are
   frozen. It does not block planning F-001.
3. Q-P02/Q-P03 must close before real extraction/OCR behavior and upload enforcement
   are accepted. Deterministic contracts and synthetic fixtures may be planned first.
4. Q-P01/Q-P07 and the rights/privacy/provider gates block provider-connected
   generation and release; they do not block provider-neutral contract planning.
5. The repository remains documentation-only. Product Planning PASS is not an
   implementation, staging, or production-readiness claim.
6. GitHub execution is not currently available: this checkout has no `origin`, and
   `gh auth status` reports an invalid token for the active account. Plan Feature may
   prepare the F-001 package and local issue body, but it cannot create the GitHub
   issue/branch/PR until repository linkage and authentication are restored.

### OPTIONAL

- Low-fidelity mockups were not required to resolve a blocking product ambiguity.
  Create them during F-003/F-005/F-006 feature planning only if the upload, status, or
  review interaction still forces a product decision.
- Numeric product success targets may be finalized with the rights-cleared evaluation
  cohort rather than invented during product planning.

### PASS

- The problem, focused outcome, users, roles, tenant model, goals, non-goals, and MVP
  boundary are explicit.
- The defining journey covers upload, extraction, generation, review, publication,
  learner playback, and progress with visible failure/recovery states.
- AI autonomy is Draft; source grounding, provenance, unsupported-content behavior,
  feedback, quality signals, and human-only publication are explicit.
- Source rights, revocation, tenant isolation, async retry/idempotency, and untrusted
  input/output boundaries are explicit.
- `features.md` is dependency ordered and every F-000–F-009 item maps to an approved
  spec requirement. No feature introduces commerce, RAG, assessments, non-PDF import,
  or another deferred capability.
- The affected scope/status sections in plan documents 00, 03–09, 11, 15, 16, 20, 24,
  and 26 are synchronized with P-009 without weakening production gates.
- No application implementation began during Plan Product.

## Two-way spec and feature coverage

| Specification outcome | Feature coverage |
|---|---|
| Codex/repository delivery setup | F-000 |
| Identity, tenant membership, roles and private access | F-001 |
| Canonical course draft/review/publication lifecycle | F-002, F-006 |
| Rights-aware private PDF admission | F-003 |
| Extraction/OCR, normalization, quality and recovery | F-004 |
| Grounded structured draft and provenance | F-005 |
| Human editing, approval and publication | F-006 |
| Learner playback and resumable progress | F-007 |
| Defining browser journey and shared integration | F-008 |
| Security, recovery, accessibility, privacy and release evidence | F-009 |

Coverage result: **complete with no unsupported feature scope**.

## Product Planning Gate

1. **PASS**
2. **Blocking items:** none for Plan Feature.
3. **Important non-blocking risks:** Q-P01–Q-P04, Q-P06–Q-P08 and the older audit's
   rights/privacy/provider/runtime/capacity/recovery gates must close at their named
   feature or environment boundary. GitHub issue/branch/PR operations also require a
   configured `origin` and renewed `gh` authentication.
4. **First recommended feature:** F-001 — Minimal identity and tenant context. It
   depends only on completed F-000, establishes the authority boundary required by
   every source/course/job operation, and does not require an AI/OCR/provider decision.

## Plan Feature handoff — F-001

- **Product source of truth:** `docs/product/spec.md`
- **Derived roadmap:** `docs/product/features.md`
- **Relevant decisions:** P-003, P-005, P-006, P-007, P-009
- **Goal supported:** ensure every later PDF/course operation has an authenticated,
  active, tenant-authorized actor.
- **Actors:** tenant administrator, instructor/reviewer, learner, platform operator.
- **Journey:** invite/provision member, sign in, resolve active tenant membership,
  permit an authorized action, and deny inactive/wrong-tenant access.
- **Product constraints:** private/manual onboarding; no public registration; browser
  and JWT tenant claims are selectors only; support access is scoped and audited;
  synthetic data only.
- **Dependencies:** F-000 complete; relevant identity/tenancy architecture and
  security contracts already documented.
- **Unresolved questions:** none that prevents F-001 planning. Production privacy,
  retention, capacity, and recovery inputs remain environment gates.
- **Explicit non-scope:** PDF upload, extraction, generation, course persistence,
  enrollment UI, provider selection, real data, deployment, and production enablement.
- **Next workflow output:** a bounded F-001 feature package and dependency graph, not
  application code.
- **GitHub handoff:** prepare locally until `origin` exists and `gh auth status` passes;
  do not invent a repository or bypass the authenticated issue workflow.

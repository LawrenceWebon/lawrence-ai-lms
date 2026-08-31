# Backend MVP Completion Execution Contract

Status: **READY FOR IMPLEMENTATION after the documentation gate below passes**

Owner instruction date: 2026-08-31

GitHub issue: [#63](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/63)

Delivery unit: one issue, one owner, one isolated worktree, one pull request

## Purpose and owner override

This document is the step-by-step implementation authority for the remaining local
backend work before the separate frontend theme-purchase task. The project owner
directed that the work be delivered in one pull request and that this Markdown
contract be written before application code changes.

That instruction narrowly overrides the normal per-feature issue/PR split in P-007
and `docs/workflows/README.md`. It does not waive:

- the protected `develop` base, isolated worktree, exact owned paths, or task-local
  resources;
- Django-only migrations, non-owner production roles, forced RLS, or server-derived
  tenant authority;
- operation-scoped source rights, immutable provenance, idempotency, leases,
  checkpoints, bounded retries, audit, or outbox facts;
- human-only review and publication, immutable published course versions, or learner
  version pins;
- independent exact-head review and all required checks; or
- the external-provider, real-data, privacy, retention, capacity, recovery, region,
  and production gates.

PR #59 remains a dependency. Issue #63 may be implemented and kept as a blocked draft,
but it must merge current `origin/develop` after #59 lands and rerun every applicable
gate before becoming ready for review.

## Product boundary

The enabled outcome is the local, rights-cleared backend path:

```text
admitted private PDF
  -> parser-backed extraction
  -> deterministic normalized source v1
  -> deterministic provider-neutral course draft v1
  -> authorized human canonicalization into an editable course draft
  -> existing human review, approval, and publication services
  -> existing enrolled learner playback and progress
```

This PR covers the implementation intent of issues #60 and #62, the planning and
implementation intent of #61, and backend work for F-004, F-005, F-006, F-008, and
the directly applicable F-009 gates.

It does not purchase, select, import, or style a frontend theme. It also excludes a
real OCR engine, external model, external storage, persistent worker provider, queue,
vector database, RAG/chat, assessments, commerce, notifications, real/private books,
deployment, and production activation.

## Actors, permissions, and tenant authority

| Actor | Allowed actions | Explicit denials |
|---|---|---|
| Tenant administrator | Review operation rights; start/read ingestion and generation; review/canonicalize drafts; use existing review/publish and enrollment services | Cannot bypass exact rights, source/run state, content hash, or immutable publication checks |
| Instructor | Upload admitted sources; start/read ingestion and generation; review own blueprint; canonicalize to an editable draft; use existing course lifecycle permissions | Cannot activate operation rights, act across tenants, or publish through a worker/model path |
| Reviewer | Read a permitted generation package and record a blueprint review when granted; use existing course review service | Cannot edit/canonicalize without `courses.drafts.write`; cannot publish without `courses.publish` |
| Learner | Existing published-version playback/progress only | Cannot read sources, normalized artifacts, generation runs, drafts, or mutate enrollment state directly |
| Worker service | Claim one durable job/run for one tenant and stage, persist normalized outputs, attempts, checkpoints, and facts | Initiating user is audit lineage only; no human approval, canonicalization, publication, broad tenant scan, or provider credentials |
| Platform operator | No standing content access | No direct tenant-content or source access in this local increment |

New permission keys are frozen as:

- `documents.ingestion.start` and `documents.ingestion.read` for tenant administrators
  and instructors;
- `course_generation.runs.create`, `course_generation.runs.read`,
  `course_generation.blueprints.review`, and
  `course_generation.drafts.canonicalize` for tenant administrators and instructors;
- generation read and blueprint review, but not canonicalization, for reviewers; and
- no new permission for learners.

Every API request treats the route/header tenant ID as a selector. The shared tenancy
service re-derives active tenant, entitlement, membership, permissions, and resource
ownership inside the transaction. Every worker transaction sets and re-verifies exact
job/run, tenant, service actor, and stage context.

## Frozen local dependency and parser boundary

Issue #61 is resolved locally with `pypdf==6.16.2` under its BSD-3-Clause license.
The release supports Python 3.14 and provides a pure-Python wheel. The implementation
uses `PdfReader` in strict mode, checks the root/pages/page boxes, rejects encrypted
input, and uses its text extraction API only after admission.

The parser runs in a child process with:

- a 30-second parent wall timeout and 15-second child CPU limit;
- a 192 MiB address-space ceiling plus the existing 64 MiB decoded-material gate;
- an empty credential environment and disabled socket construction;
- no filesystem path or tenant/provider credential, only the bounded input bytes;
- a maximum root-object recovery limit of 10,000; and
- a small JSON-safe observation returned to the parent.

`parser_accepted=true` is legal only after strict parser construction, root resolution,
page enumeration, and valid positive page boxes succeed. The existing marker, MIME,
polyglot, unsafe-action, byte, page, pixel, decoded-material, CPU, and wall checks stay
in place as independent defenses.

Frozen parser result mapping:

| Observation | Stable result |
|---|---|
| Missing PDF signature or MIME disagreement | `PDF_SIGNATURE_MISMATCH` / `PDF_MEDIA_TYPE_INVALID` |
| Encrypted reader | `PDF_ENCRYPTED` |
| Strict read/root/xref/page failure, including the reported 90-byte pseudo-PDF | `PDF_CORRUPT` |
| Bytes after terminal EOF or conflicting wrapper | `PDF_POLYGLOT_REJECTED` |
| Active content/embedded file/unsupported unsafe construct | `PDF_UNSAFE` |
| Resource envelope exceeded | Existing size/page/pixel/decoded reason; timeout or child failure is retryable validation unavailable |
| Fully parsed bounded document | `parser_accepted=true`; later extraction remains a separate stage |

Official implementation references, rechecked 2026-08-31:

- [pypdf package and Python classifiers](https://pypi.org/project/pypdf/)
- [PdfReader strict and recovery-limit contract](https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html)
- [pypdf text-extraction and OCR limitations](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)

## Operation-scoped source-rights contract

`SourceUseAuthorization.operation` is expanded from `store` to exactly:

```text
store | extract | ocr | generate
```

One authorization row exists per tenant/source version/operation. Admission creates
the `store` request. The first request for a later operation creates or returns its
idempotent `requested` authorization. A tenant administrator with
`documents.source_rights.review` must explicitly activate it. A store authorization
never implies extract, OCR, or generation authority.

At command time and again at worker execution time, authorization must be `active`,
inside `valid_from`/`valid_until`, attached to the exact tenant/source version, and
consistent with an admitted, unblocked source. Revocation, expiry, or dispute blocks
new work immediately. In-flight work checks the operation before every stage commit
and stops without marking output ready.

OCR authorization is required only if a page has no usable text layer. Because Q-P02
remains open, the local adapter then records `OCR_ADAPTER_UNAVAILABLE` as retryable and
does not manufacture text or mark the source generation-ready.

## F-004 extraction and normalized-source contract

### Durable states

An ingestion run uses:

```text
queued -> claimed -> extracting -> normalizing -> quality_check
       -> ready_for_generation
       -> retryable | failed | cancelled | rights_blocked
```

Allowed retries create a new attempt on the same run only while the retry budget is
available. Reprocessing after a completed/terminal run creates a new immutable run.
Only one non-terminal ingestion run exists per source version and parser/configuration
version. A claim has lease owner/expiry, heartbeat, checkpoint, attempt number, input
manifest hash, and output manifest hash.

### Normalized source v1

The authoritative normalized records are relational; JSON/Markdown artifacts are
immutable projections with checksums.

```json
{
  "schema_version": "normalized-source.v1",
  "source_version_id": "uuid",
  "content_sha256": "sha256:...",
  "locale": "en",
  "pages": [
    {
      "id": "uuid",
      "number": 1,
      "width_points": 612,
      "height_points": 792,
      "text_sha256": "sha256:...",
      "ocr_used": false,
      "elements": [
        {"id": "uuid", "position": 1, "type": "heading", "text": "..."},
        {"id": "uuid", "position": 2, "type": "paragraph", "text": "..."}
      ]
    }
  ],
  "sections": [
    {
      "id": "uuid",
      "position": 1,
      "title": "...",
      "start_page": 1,
      "end_page": 1,
      "element_ids": ["uuid"]
    }
  ]
}
```

Stable UUIDv5 identifiers derive from tenant, source version, parser/configuration
version, page number, element position/type/text hash, and section position. Repeating
the same input/configuration yields the same manifest and identifiers.

For this local vertical slice, pypdf extracts each page in layout mode without excess
vertical whitespace. Lines are normalized to Unicode NFC and LF endings. Blank runs
separate paragraphs. The first non-empty short line on a page is a heading candidate;
otherwise the section title is `Page N`. This heuristic is versioned and is never
represented as provider-quality evidence.

The local structural quality gate passes only when every page has bounded non-empty
text, every element belongs to the exact page/version/tenant, every section has a
valid page/element range, and both projections reproduce their stored hashes. Any
empty page requests OCR and remains retryable; a partial source cannot be marked ready.
Numeric real-data extraction quality thresholds remain blocked by Q-P02/Q-P07.

### F-004 persistence

The Documents domain owns:

- `document_ingestion_runs` and `document_ingestion_attempts`;
- `source_artifacts` for `canonical_json` and `normalized_markdown` projections;
- `document_pages`, `document_elements`, and `document_sections`;
- exact same-tenant composite foreign keys, named constraints/indexes, immutable-ready
  triggers, forced RLS, least grants, and worker job-scope policies; and
- `document.ingestion.requested.v1`, `document.ingestion.ready.v1`, and
  `document.ingestion.failed.v1` audit/outbox facts with identifiers and hashes only.

No vector/chunk table is added because F-005 does not require retrieval.

## F-005 structured-generation contract

### Provider-neutral boundary

No external AI provider or model is selected. The only enabled adapter is
`deterministic-source-course-v1`, which is test/local-only and makes no network calls.
Its immutable run snapshot records:

- adapter, code, `normalized-source.v1`, `course-blueprint.v1`, and
  `course-draft.v1` versions;
- source/version/ingestion IDs and ordered normalized section hashes;
- intent fields, locale `en`, input manifest hash, output hash, and policy version;
- `provider="local_deterministic"`, `model="none"`, prompt template checksum,
  token counts `0`, cost `0`, and no retained private prompt body; and
- complete normalized source, blueprint-item, generated-artifact, and canonicalization
  edges.

External-provider settings, credentials, routes, and fallback logic remain absent.

### Generation intent v1

Required request fields are:

```json
{
  "source_document_id": "uuid",
  "source_version_id": "uuid",
  "target_level": "beginner|intermediate|advanced",
  "target_duration_minutes": 1,
  "intended_audience": "1..300 characters",
  "teaching_style": "concise|guided|reference",
  "locale": "en",
  "supersedes_run_id": null
}
```

The server derives tenant, requester, normalized source, rights, adapter, schema, and
policy versions. The same idempotency key plus canonical request returns the same run;
the same key with different input fails with `IDEMPOTENCY_CONFLICT`.

### Run and review states

```text
queued -> planning -> blueprint_review
blueprint_review -> generation_queued       # exact-hash human approval
generation_queued -> generating -> review_ready
review_ready -> canonicalized | rejected
any worker stage -> retryable | failed | rights_blocked
```

Regeneration creates a new run with `supersedes_run_id`; it never updates or deletes a
reviewed/canonicalized run or overwrites canonical content.

### Blueprint and draft v1

The strict blueprint has title, description, audience, prerequisites, measurable
learning outcomes, and ordered modules. Each module and lesson has at least one
normalized source-section edge. The deterministic adapter creates one module and one
lesson per normalized section, bounded to 100 modules/lessons and the existing rich
text allowlist.

Each lesson artifact contains exactly one `rich_text` document using only paragraph,
heading, bullet-list, ordered-list, list-item, text, bold, italic, and code marks
already accepted by P-012/F-002. Raw HTML, links, embeds, media, provider payloads,
tool instructions, unknown nodes/marks, and assessment content are rejected.

Candidate source IDs in output are untrusted. Validation resolves every edge against
the exact current tenant/source/ingestion manifest. Missing, duplicate, cross-tenant,
cross-version, stale, or unsupported references fail the run; JSON IDs alone are never
lineage or authorization authority.

The Course Generation domain owns:

- generation runs, steps/attempts, immutable run snapshots, blueprints/items,
  generated lesson artifacts/revisions, source edges, blueprint decisions, and
  canonicalization records;
- same-tenant composite keys, immutable approved/review-ready records, forced RLS,
  API and exact-job worker policies; and
- `course_generation.requested.v1`, `course_generation.blueprint_ready.v1`,
  `course_generation.review_ready.v1`, `course_generation.rejected.v1`, and
  `course_generation.canonicalized.v1` facts with no source/lesson bodies.

## F-006 human canonicalization and publication contract

Blueprint approval requires a verified user principal, current generation-review
permission, expected run row version, exact blueprint revision, exact content hash,
and an idempotency key. A worker/service/model principal is denied even if it carries
an initiating user ID.

Canonicalization requires a verified user with both
`course_generation.drafts.canonicalize` and `courses.drafts.write`, expected run row
version, exact review-ready output hash, a unique requested course slug, and an
idempotency key. In one top-level transaction it:

1. locks and reauthorizes the generation run, source, `generate` right, and exact
   review-ready revision;
2. invokes the Courses domain public command boundary to create one unpublished
   `ai_generated` course/version and replace its curriculum;
3. records normalized artifact-to-course/version/section/lesson/block edges plus the
   canonicalization hash;
4. marks only that generation revision canonicalized; and
5. writes audit/outbox facts atomically.

The result is an ordinary mutable canonical draft. Instructors may edit it using the
existing optimistic course service. Any edit changes the canonical content hash and
invalidates stale review. Submission, approval, publication, withdrawal, successor
draft creation, immutable published versions, and learner pins continue exclusively
through the existing F-002/F-007 services.

Canonicalization is not approval or publication. No new publication endpoint, worker
shortcut, model actor, direct ORM adapter mutation, or automatic enrollment is added.

## Frozen HTTP contract

All routes are under `/api/v1/tenants/{tenant_id}` and use the existing verified actor,
`X-Tenant-ID`, request ID, RFC Problem Details, and `Idempotency-Key` conventions.

| Method and path | Outcome |
|---|---|
| `GET /source-documents/{document_id}/versions/{version_id}/authorizations` | List exact operation-right statuses visible to an authorized source reader |
| `POST /source-documents/{document_id}/versions/{version_id}/authorizations/{operation}` | Idempotently request `extract`, `ocr`, or `generate` authorization |
| `POST /source-documents/{document_id}/versions/{version_id}/authorizations/{operation}/review` | Tenant-admin activate/deny/revoke with expected row version |
| `POST /source-documents/{document_id}/versions/{version_id}/ingestion-runs` | Return `202` with queued run or replayed run |
| `GET /source-documents/{document_id}/versions/{version_id}/ingestion-runs/{run_id}` | Return state, safe progress, quality/error summary, and artifact hashes |
| `POST /course-generation-runs` | Return `202` with queued provider-neutral run |
| `GET /course-generation-runs/{run_id}` | Return state and a review package only to an authorized actor |
| `POST /course-generation-runs/{run_id}/approve-blueprint` | Record exact-hash human decision and queue lesson generation |
| `POST /course-generation-runs/{run_id}/reject` | Reject exact reviewable revision with stable reason codes |
| `POST /course-generation-runs/{run_id}/canonicalize` | Create one canonical editable draft and return its IDs/hashes |

The internal worker command boundary exposes `claim/run ingestion` and
`claim/plan/generate course` methods to the containerized worker process, not to the
browser/OpenAPI. The API never performs a provider call or treats in-process FastAPI
background tasks as durable execution.

## Stable error taxonomy

Existing F-001/F-002/F-003/F-007 codes remain compatible. New codes are:

```text
SOURCE_OPERATION_AUTHORIZATION_REQUIRED
SOURCE_OPERATION_AUTHORIZATION_INACTIVE
INGESTION_RESOURCE_NOT_FOUND
INGESTION_STATE_CONFLICT
INGESTION_LEASE_CONFLICT
INGESTION_RETRY_EXHAUSTED
EXTRACTION_PARSER_FAILED
OCR_REQUIRED
OCR_ADAPTER_UNAVAILABLE
DOCUMENT_QUALITY_INSUFFICIENT
GENERATION_RESOURCE_NOT_FOUND
GENERATION_PERMISSION_DENIED
GENERATION_SOURCE_NOT_READY
GENERATION_STATE_CONFLICT
GENERATION_LEASE_CONFLICT
GENERATION_RETRY_EXHAUSTED
GENERATION_SCHEMA_INVALID
GENERATION_PROVENANCE_INVALID
GENERATION_BLUEPRINT_HASH_MISMATCH
GENERATION_OUTPUT_HASH_MISMATCH
GENERATION_HUMAN_REQUIRED
GENERATION_SLUG_CONFLICT
```

Existence-sensitive authorization failures return the same neutral `404` form used by
the owning domain. Retryable worker failures never create a false ready/canonicalized
state. Validation errors expose safe field locations/codes, not source text or parser
internals.

## Schema, migration, and RLS order

The single integration owner owns the complete migration graph in this PR:

1. Learning forward migration and repository change for issue #60; no merged migration
   is rewritten.
2. Documents extraction schema/security migrations, operation-right expansion,
   permissions, named constraints/indexes, RLS/grants, and schema fingerprint.
3. New Course Generation app initial schema then security migration, permissions,
   same-tenant FKs, forced RLS, worker/API policies, triggers, and fingerprint.
4. Composition/settings registration only after migrations and domain tests pass.

Runtime roles remain non-owner and non-`BYPASSRLS`. Every tenant table has non-null
`tenant_id`, `UNIQUE (tenant_id,id)`, composite same-tenant relationships, tenant-first
indexes, default-deny grants, `ENABLE/FORCE ROW LEVEL SECURITY`, and absent-context/
wrong-tenant/tenant-change negative tests.

For issue #60, ordinary `lms_api_runtime` direct `UPDATE app.enrollments` is revoked.
Enrollment creation/revocation uses narrowly granted fixed-search-path database command
functions that re-check `learning.enrollments.manage`, expected row version, allowed
transition, and tenant context; the shared Learning service remains the sole public
application entrypoint. Learner playback/progress grants remain on their own tables.

## Test fixtures and required proofs

Only generated synthetic or explicitly rights-cleared fixtures are used. A committed
fixture generator records deterministic hashes for:

- parser-valid one-page and multi-page text PDFs;
- scanned/empty-page, encrypted, corrupt, truncated, polyglot, unsafe-action,
  page/pixel/decoded-limit, and the reported marker-only pseudo-PDF;
- normalized-source v1 and course-draft v1 golden JSON; and
- source prompt-injection text treated only as lesson/source data, never instructions.

Required focused proofs:

- issue #62 digest mutation differs for every original digest, including one beginning
  with `0`, and the wrong digest sees zero rows under the production role;
- issue #60 reproduces learner direct enrollment revocation RED and denies it GREEN,
  while tenant-admin service create/revoke, audit/outbox, idempotency, and playback/
  progress remain green;
- issue #61 rejects the 90-byte pseudo-PDF and preserves all valid admission/security
  cases;
- extraction idempotency, deterministic hashes/IDs, retries/leases/checkpoints,
  rights expiry/revocation, OCR-unavailable, partial failure, immutability, Admin/worker
  parity, API errors, and API/worker production-role RLS;
- generation strict schema, source-edge validity, prompt-injection inertness,
  wrong tenant/source/version denial, immutable revisions/snapshots, regenerate/no
  overwrite, exact-hash human review, service/model denial, idempotency/concurrency,
  canonicalization, and API/worker RLS;
- canonical draft edit -> submit -> approve -> publish through F-002, enrollment ->
  playback/progress through F-007, and no source/generation artifact exposure to the
  learner; and
- migration forward/reverse/forward, `makemigrations --check`, schema fingerprint/
  drift, OpenAPI/client, event schemas, architecture, Ruff/format, strict mypy, full
  non-RLS/RLS, existing E2E regressions, web build, docs/manifest, dependency/license,
  secret, and exact-diff checks.

Provider-backed OCR/generation quality, numeric real-data thresholds, production load,
recovery, accessibility for a future themed UI, and deployment remain explicitly
blocked—not falsely marked passed.

## Sequential implementation checkpoints

No later checkpoint starts until the current checkpoint's focused tests and diff pass.
All checkpoints remain commits on the one LMS-63 branch and PR.

| Checkpoint | Work | Exit evidence |
|---|---|---|
| 0 | Commit this contract, links, source entry, and manifest | Documentation checks pass; issue #63 says `READY FOR IMPLEMENTATION` |
| 1 | Add deterministic digest test helper and enrollment RLS remediation | Original regressions RED then GREEN; focused RLS/migration/service suites pass |
| 2 | Add pypdf dependency and parser-backed F-003 remediation | Pseudo-PDF RED then GREEN; complete F-003 parser/admission suites pass |
| 3 | Add F-004 domain, migration/RLS, adapter, worker commands, API/Admin, fixtures | Extraction unit/integration/production-role tests and schema gates pass |
| 4 | Add F-005 generation domain, migration/RLS, deterministic adapter, API/Admin, fixtures | Structured schema/provenance/human-review and generation RLS gates pass |
| 5 | Add F-006 canonicalization through Courses public services | Exact-hash canonicalization and existing publication bypass/concurrency suites pass |
| 6 | Add F-008 full backend journey and applicable F-009 hardening/evidence | PDF-to-published-to-playback backend journey plus full required suites pass |
| 7 | Merge latest approved `develop`, regenerate contracts/docs, final audit, push one PR | Draft PR is complete, dependency reconciled, checks green, handoff is `READY FOR CODE REVIEW` |

## Ownership, resources, and shared hotspots

- Issue: `#63`
- Branch: `feature/LMS-63-backend-mvp-completion`
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/backend-mvp-LMS-63`
- Host scratch: `/home/lawrence/Project Neo/tmp/LMS-63`
- Compose project: `ai-lms-lms-63`
- PostgreSQL port: `55263`
- Base/PR target: `develop`
- Merge dependency: PR #59 first; issue #63 before frontend theme work

Owned paths are the narrowly required files under:

```text
docs/features/
docs/evidence/
docs/product/
docs/plan/SOURCES.md
manifest.json
backend/pyproject.toml
backend/uv.lock
backend/src/lms/modules/documents/
backend/src/lms/modules/learning/
backend/src/lms/modules/courses/
backend/src/lms/modules/course_generation/
backend/src/lms/api/
backend/src/lms/adapters/admin/
backend/src/lms/config/settings/
backend/tests/
contracts/events/
contracts/openapi/
packages/api-client/
scripts/
```

Root lockfiles, CI, Compose, Docker inputs, frontend feature/UI/style files, and another
task's paths/resources are not owned unless an unavoidable generated-contract change is
first recorded in issue #63. The documentation manifest, Python lockfile, settings,
application composition, migration graph, OpenAPI, generated client, and event schemas
have this single integration owner for the life of the issue.

## Verification commands

The task starts and reuses its isolated services:

```bash
COMPOSE_PROJECT_NAME=ai-lms-lms-63 AI_LMS_POSTGRES_PORT=55263 \
AI_LMS_UID="$(id -u)" AI_LMS_GID="$(id -g)" docker compose up -d --build --wait
```

Focused commands are added with their checkpoint. Final required commands include:

```bash
make lint
make typecheck
make test
make test-rls
make openapi-check
make web-build
make e2e-f001
make e2e-f002
make e2e-f003
make e2e-f007
make docs-check
docker compose exec -T backend python backend/manage.py makemigrations --check --dry-run
docker compose exec -T backend python backend/manage.py check --deploy
git diff --check
git status --short --branch
```

The completion evidence records exact focused/full commands, results, migrations and
fingerprints, OpenAPI/event/client changes, production-role matrices, dependency and
license result, known blocked production gates, rollback, and whether remote actions
occurred.

## Rollback and stop conditions

Before merge, rollback is branch/PR abandonment; never rewrite merged migrations or
discard another worktree. After merge, code/config can disable the local ingestion and
generation composition while a reviewed forward migration preserves immutable audit,
rights, source, run, and canonicalization evidence. Published course versions and
enrollment pins are never deleted or rewritten as rollback.

Stop the affected checkpoint and correct the narrowest approved contract if:

- PR #59 changes a relevant dependency when it merges;
- a parser/OCR/model/provider decision would be invented rather than kept disabled;
- a migration cannot enforce same-tenant relationships or forced RLS under production
  roles;
- source rights, provenance, idempotency, or human-only publication would be weakened;
- application code needs an unowned active-worktree path; or
- a required test fails for a reason outside the checkpoint and cannot be isolated
  without expanding scope.

Passing this local contract does not claim production readiness. The next authorized
product task is the separate frontend theme-purchase/design step only after this PR is
independently reviewed, approved, and merged.

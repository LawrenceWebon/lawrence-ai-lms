# F-003 — PDF Source Admission

Status: **implementation merged; independent post-merge audit requires parser-backed remediation #61**

Feature ID: `F-003`
Planning issue: [#42](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/42)
Review-evidence correction:
[#51](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51)
Implementation: [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43)
and [local evidence](../../evidence/f003-source-admission-implementation.md)

## Outcome

An authorized instructor can declare the rights basis for one PDF, obtain a reviewed
`store` authorization, upload that PDF to a private local quarantine target, and see a
safe, tenant-scoped admission outcome. An admitted source is a versioned input to
F-004; it is not extracted, displayed, or generated from in this feature.

## Actors and authority

| Actor | Allowed in F-003 | Never implied |
|---|---|---|
| Instructor | Read own tenant's source-admission status; submit a declaration/admission request; use an active upload intent; cancel the request | Self-authorize source rights, choose a storage path, read another tenant's source, or start extraction |
| Source-rights reviewer | Review, activate, deny, revoke, or expire an operation-scoped `store` authorization | Access outside the active tenant, bypass a declaration, or authorize OCR/extraction/generation by implication |
| Tenant administrator | Holds the F-003 reviewer permissions in the first local fixture and can perform all listed human actions | Standing platform access or provider administration |
| Local validator/reconciler worker | Claims one durable job, re-derives tenant/stage scope, records byte-derived observation or removal result | Use an enqueue payload as authority, approve rights, or expose source content |
| Learner, AI, generic service, platform operator | No source-content access or admission action | Reading quarantined bytes, issuing rights authorization, or treating an ID/URL as authority |

The new fixed permissions are `documents.sources.read`, `documents.sources.admit`,
`documents.sources.cancel`, and `documents.source_rights.review`. The first local
matrix grants all four to `tenant_admin`, grants read/admit/cancel to `instructor`, and
grants none to `reviewer` or `learner`. A source-rights reviewer must be a different
active human actor from the declarant; a later policy change requires an explicit
product/legal decision.

Every command re-derives verified identity, active tenant membership, entitlement,
permission, source/version relationship, rights state, and operation scope in its
transaction. The route tenant, upload token, file name, MIME declaration, checksum, and
browser state are selectors or hints, never authorization authority.

## Local-only Q-P03 envelope

P-013 closes Q-P03 for this local implementation only. The validator derives each
value from bytes or trusted local inspection rather than trusting browser metadata.

| Limit | Local value |
|---|---:|
| Accepted media | `application/pdf` with recognized PDF signature and parser agreement |
| File bytes | 6 MiB (`6,291,456`) |
| Pages | 100 |
| Rendered pixels | 25,000,000/page; 250,000,000/source |
| Decoded parser material | 64 MiB |
| Validation budget | 15 CPU seconds; 30 wall seconds; no network |
| Upload intent lifetime | 15 minutes |
| Tenant rolling 24-hour admission attempts | 10; aggregate bytes 30 MiB |
| Tenant concurrent active upload intents | 2 |
| Tenant quarantine inventory | 20 objects; 60 MiB |

These limits are a local fixture safety envelope, not a capacity, legal, retention,
recovery, or production approval. Files above 6 MiB are rejected; no TUS or larger
upload class is enabled in F-003.

## User flow

1. An authenticated instructor selects an active tenant and enters a display name,
   declared PDF filename, rights basis, required attestation, and any bounded evidence
   reference.
2. The service creates a stable source document, immutable version 1, rights
   declaration, and a requested `store` authorization. No upload URL is issued yet.
3. A separate authorized source-rights reviewer activates or denies that exact `store`
   authorization. Activation issues an opaque, short-lived, tenant/purpose/version-bound
   upload intent; denial leaves the source non-uploadable with a stable safe code.
4. The instructor uploads bytes to the opaque local quarantine target. The target does
   not reveal a bucket, object key, or reusable tenant scope.
5. A local validator records server-derived size, signature/MIME, checksum, page/pixel
   observations, and bounded inspection result. It marks the version `admitted`,
   `rejected`, or retryable without silently advancing it.
6. The instructor sees an accessible status, safe rejection reason, expiry, or next
   allowed action. F-004 may consume only an `admitted` version after re-checking its
   own `extract` authorization.
7. Cancellation, authorization expiry, dispute, or revocation immediately blocks new
   upload/validation/extraction use. A durable removal job reconciles the quarantined
   object after commit; content is never treated as removed merely because a request was
   accepted.

## Requirements

- PDF is the only accepted source format. Extension, declared type, and client checksum
  are defense-in-depth hints; byte signature, parser result, size, page/pixel counts,
  checksum, and inventory state are authoritative.
- A declaration is evidence, not permission. Every store operation requires an active,
  separately reviewed `source_use_authorization` for the exact source version and
  `store` operation.
- Quarantine is private. Opaque targets expire, bind one source version and byte cap,
  cannot select a bucket/path/final destination, and return no tenant-source details on
  misuse.
- The local storage/inspection adapter is provider-neutral and fail-closed. It must not
  claim malware, OCR, or production-storage capability that is not present.
- The admission service writes state, idempotency, audit facts, and sanitized outbox
  facts transactionally. It never holds that transaction over storage or inspection.
- Each validation/removal attempt has durable job identity, lease, attempt, input/output
  manifest hash, retry class, stable terminal reason, and reconciliation evidence.
- Source bytes, object keys, rights evidence, full filenames, parsed content, bearer
  upload tokens, and unrestricted error text are excluded from events and general logs.

## Failure behavior

| Situation | Required result |
|---|---|
| Missing/stale tenant context, membership, entitlement, or permission | Fail closed; wrong source/version selectors receive neutral `404 RESOURCE_NOT_FOUND` |
| Declaration absent, denied, expired, disputed, or revoked | No upload target; stable rights-required/denied state without disclosing cross-tenant data |
| Same actor attempts rights review | `403 SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED`; no authorization changes |
| Quota, expired target, replayed target with different bytes, or stale row | Stable `429`, `410`, or `409` result; no duplicate admitted version/object inventory |
| MIME/signature mismatch, encrypted/corrupt PDF, page/pixel/decoded limit, or unsafe inspection result | `rejected` with a bounded stable reason; extraction is never enqueued |
| Validator/storage capability unavailable or observation is unknown | Fail closed as retryable; no `admitted` status |
| Cancel/revoke/expiry during upload or validation | Block work immediately; reconciling removal continues after commit and remains visible as pending/failed/completed |
| Object/DB mismatch or orphan | Reconciler records the mismatch and converges to a safe blocked/rejected/removal state; it never guesses success |

## Acceptance criteria

- Synthetic Alpha instructor can create a declaration but cannot upload until a separate
  Alpha rights reviewer activates `store`; Alpha gets an opaque time-limited target only
  after that review.
- The valid synthetic PDF is admitted only after server-derived observation fits every
  P-013 limit. Invalid signature, encrypted, corrupt, oversized, page/pixel-over-limit,
  expired, missing, and inspector-unavailable fixtures never become admitted.
- Beta, outsider, learner, inactive member, guessed source/version ID, modified upload
  token, and stale tenant selector reveal no Alpha source/object information.
- Repeated create/review/cancel/upload requests are idempotent for equivalent input and
  conflict for changed input; concurrent upload/revoke/cancel yields one safe terminal
  state and no duplicate durable job/object link.
- Cancellation and rights revocation immediately stop new use, create a sanitized audit
  and outbox fact, schedule removal after commit, and reconcile the object before
  reporting removal complete.
- FastAPI, Django Admin, local validator, and browser use the same application service
  boundary; OpenAPI/generated client, production-role RLS, accessibility, and existing
  F-001/F-002 regression evidence pass in the integration issue.

## Explicit non-goals

- OCR, text/layout extraction, normalization, segmentation, vector indexing, or course
  generation;
- external storage, scanner, OCR, queue, worker, region, or provider selection;
- real customer documents, non-local deployment, production retention/recovery, or
  provider transfer;
- public source URLs, learner source access, source download/preview, full rights
  evidence attachment management, bulk import, or standalone rights-management UI; and
- EPUB, DOCX, HTML, page-image input, assessments, analytics, notifications, commerce,
  or publication behavior.

## References

- Product: `docs/product/spec.md`
- Inventory: `docs/product/features.md`
- Decisions: P-001, P-003, P-005, P-009, P-011, P-013
- Plans: `docs/plan/04-domain-module-design.md`,
  `docs/plan/05-database-schema-plan.md`,
  `docs/plan/06-ai-schema-extension.md`, `docs/plan/08-book-ingestion-pipeline.md`,
  `docs/plan/11-api-and-event-contracts.md`, `docs/plan/12-security-and-multitenancy.md`,
  `docs/plan/15-testing-quality-gates.md`, and documents 23, 25–28
- ADRs: ADR-0001, ADR-0002, ADR-0005

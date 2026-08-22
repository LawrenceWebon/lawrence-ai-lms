# Technical Decisions — F-003 PDF Source Admission

Status: **frozen and implemented locally; independent review and protected checks pending**

## Planning review evidence correction

PR #44 merged the planning contract without the required independent pre-merge
approval record. The retrospective audit found three contradictions between its
executable schema and the decisions below. Correction
[#51](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51) fixes only those
contradictions and records the exact-head audit and controlled exception in the
[F-003 planning review correction evidence](../../evidence/f003-planning-review-correction.md).
PR #53 merged the correction, but its final merge head was not the independently
reviewed head and GitHub records no distinct approval. The project owner's
[#43 launch disposition](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43#issuecomment-5379136978)
closed only that already-merged governance hold without claiming retroactive approval.

## Existing architecture to reuse

- F-001 verified JWT identity, active tenant context, entitlement, fixed roles, and
  production-role RLS helpers.
- F-002 application-service, idempotency, optimistic-concurrency, audit/outbox,
  RFC Problem Details, OpenAPI/generated-client, Admin-adapter, and browser-boundary
  patterns.
- ADR-0001's modular-monolith transaction boundary, ADR-0002's Django/FastAPI
  authority split, and ADR-0005's durable-worker boundary without selecting a worker
  provider.
- The source-rights/document model direction in documents 05, 06, and 08. F-003 owns
  only the smallest executable admission subset; it must not pre-create F-004/F-005
  tables merely for future convenience.

## F003-TD-001 — Rights declaration and `store` authorization are separate

Status: **frozen**

`CreateSourceAdmissionV1` creates a source document/version and one immutable rights
declaration with a requested operation-scoped authorization. The declaration records a
bounded basis, attestation version, optional bounded reference, actor, and time; it is
not itself permission to store bytes.

Only a different active human actor with `documents.source_rights.review` may activate,
deny, revoke, expire, or dispute the exact `store` authorization. F-003 grants that
permission only to `tenant_admin` in the local fixture. A reviewer must re-derive the
tenant, source/version, declaration, operation, active membership, and entitlement in
the same transaction. The authorization has exactly one F-003 operation: `store`.
It does not imply `ocr`, `extract`, `embed`, `generate`, `display`, `retrieve`,
`chat`, `export`, or provider transfer.

This is a narrow safety default, not a broad rights-management product. Evidence
attachments, territory/audience UX, automated legal analysis, self-approval policy,
and every post-admission operation remain outside F-003.

## F003-TD-002 — P-013 is a local-only fail-closed envelope

Status: **frozen by the project-owner instruction to set Q-P03 before F-003 implementation**

| Key | Value |
|---|---:|
| `max_pdf_bytes` | `6,291,456` |
| `max_page_count` | `100` |
| `max_rendered_pixels_per_page` | `25,000,000` |
| `max_rendered_pixels_total` | `250,000,000` |
| `max_decoded_parser_bytes` | `67,108,864` |
| `validation_cpu_seconds` | `15` |
| `validation_wall_seconds` | `30` |
| `upload_intent_ttl_seconds` | `900` |
| `max_active_upload_intents_per_tenant` | `2` |
| `max_upload_intents_per_tenant_24h` | `10` |
| `max_upload_attempt_bytes_per_tenant_24h` | `31,457,280` |
| `max_quarantine_objects_per_tenant` | `20` |
| `max_quarantine_bytes_per_tenant` | `62,914,560` |

The accepted byte-derived media type is `application/pdf`, with a recognizable PDF
signature and parser agreement. The file extension is only a hint. The validator has
no network access and must reject an unknown, unavailable, encrypted, corrupt,
polyglot, or limit-exceeding observation rather than accept it optimistically.

The values support synthetic/right-cleared local fixtures only. They are not portable
to a real storage class, TUS implementation, OCR workload, capacity model, retention
schedule, object RPO, production worker, provider, region, or legal approval.

## F003-TD-003 — One immutable source version has admission and removal state

Status: **frozen**

`SourceDocument` is the tenant-owned stable source identity. F-003 creates immutable
version 1 and never overwrites its declared or byte-derived evidence. A retry after a
terminal rejection/cancellation/revocation creates a later source version or a new
admission only through a future explicit command; F-003 does not silently replace
bytes under an existing version.

The version admission state machine is:

```text
rights_pending
  --activate store authorization--> upload_pending
  --deny store authorization------> rejected

upload_pending
  --opaque target accepts bytes---> quarantined
  --cancel------------------------> cancelled

quarantined
  --validator claim---------------> validating
  --cancel/revoke/expiry----------> cancelled or blocked

validating
  --safe result-------------------> admitted
  --stable rejection--------------> rejected
  --retryable/unknown-------------> quarantined
  --cancel/revoke/expiry----------> cancelled or blocked

admitted --revoke/expiry/dispute--> blocked
```

`cancelled` and `blocked` immediately deny future upload, validation, extraction, and
read use. Removal is represented separately as `not_required`, `pending`, `completed`,
or `failed`, so a UI never confuses a request to remove an object with verified
absence. `rejected` contains only a stable safe code; it never stores or returns raw
parser/inspector output.

## F003-TD-004 — Quarantine is a provider-neutral port and opaque target

Status: **frozen**

The admission service creates a database-owned `UploadIntent` before any bytes move.
It binds tenant, source/version, purpose `source_quarantine`, maximum bytes, accepted
media, expiry, single-use/replay hash rule, and random opaque token digest. It never
stores or exposes a caller-selected storage bucket/key.

The local adapter returns an opaque target URL under the API for test use. It writes
bytes to private local quarantine outside the business transaction, derives an
observation, then calls the service to create/update the object inventory and enqueue a
durable validation job after commit. A failed DB observation leaves an orphan for
reconciliation; it is not considered admitted. A production direct signed-storage URL,
TUS, bucket policy, malware engine, or object provider is deliberately not selected by
this feature.

Equivalent target replay is permitted only when it observes the same completed object
checksum and byte count. A different body for the target conflicts and creates no new
source version. Expired, consumed, cancelled, revoked, and guessed targets are
neutral failures and expose no object/source detail.

## F003-TD-005 — Public DTO, HTTP, job, and event contract

Status: **frozen**

The executable Draft 2020-12 contract is
`contracts/f003/source-admission.v1.schema.json`; values and fixture manifest are
`contracts/f003/source-admission.v1.examples.json` and
`contracts/f003/fixtures/admission-fixtures.v1.json`.

| HTTP operation | Request/response | Guard |
|---|---|---|
| `POST /api/v1/tenants/{tenant_id}/source-documents/admissions` | `CreateSourceAdmissionV1` → `201 SourceAdmissionV1` | `documents.sources.admit`; `Idempotency-Key` |
| `POST /api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/rights-authorizations/{authorization_id}/decisions` | `ReviewSourceStoreAuthorizationV1` → `200 SourceAdmissionV1` | `documents.source_rights.review`; different human; `Idempotency-Key` |
| `POST /api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/upload-intents` | no body → `201 UploadIntentV1` | active `store`; `documents.sources.admit`; `Idempotency-Key` |
| `PUT /api/v1/source-upload-targets/{opaque_token}` | `application/pdf` bytes → `202 SourceAdmissionV1` | opaque target scope, expiry, byte/media limit; no tenant from caller |
| `GET /api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}` | none → `200 SourceAdmissionV1` | `documents.sources.read` |
| `POST /api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/cancel` | `CancelSourceAdmissionV1` → `200 SourceAdmissionV1` | declarant or `documents.sources.cancel`; `Idempotency-Key` |

The decision endpoint handles activation, denial, and revocation. Expiry/dispute may be
entered only through a trusted policy/reconciler command, never a browser value.

`AdmissionValidationJobV1` and `SourceRemovalJobV1` contain only IDs, declared stage,
lease/attempt/idempotency/correlation facts, policy version, object-inventory ID, and
manifest checksums. They carry no source body, object key, signed URL, rights evidence,
tenant authority, or raw provider payload. Workers re-read each named record under a
claimed job/stage scope.

Frozen event facts are `source.rights.declared.v1`,
`source.store_authorization.activated.v1`, `source.version.quarantined.v1`,
`source.admission.validation_requested.v1`, `source.version.admitted.v1`,
`source.version.rejected.v1`, `source.version.cancelled.v1`,
`source.rights.revoked.v1`, and `source.removal.completed.v1`. Their concrete event
schemas are generated/owned by #43 from the corrected repository envelope and
discriminated minimized payload shape; no event includes source content, object key,
target token, legal evidence, or full filename.

Stable problems are `SOURCE_RIGHTS_AUTHORIZATION_REQUIRED`,
`SOURCE_RIGHTS_AUTHORIZATION_DENIED`,
`SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED`, `SOURCE_ADMISSION_REJECTED`,
`SOURCE_ADMISSION_VALIDATION_UNAVAILABLE`, `UPLOAD_INTENT_EXPIRED`,
`UPLOAD_QUOTA_EXCEEDED`, `SOURCE_ADMISSION_STATE_CONFLICT`,
`SOURCE_ADMISSION_VERSION_CONFLICT`, `IDEMPOTENCY_CONFLICT`,
`TENANT_CONTEXT_REQUIRED`, and neutral `RESOURCE_NOT_FOUND`.

An `admitted` validation result and public snapshot require a non-null checksum,
bounded positive file/page/pixel observations, bounded decoded parser material,
recognized PDF media, confirmed PDF signature/parser acceptance, an accepted bounded
local inspection result, no rejection code, and an active `store` authorization.
Rejected results require a stable rejection code; retryable failures do not masquerade
as terminal rejection. Each rejected validation code is bound to its matching failed,
over-limit, missing-object, or checksum observation; a rejected result cannot report
an unavailable inspection. A retryable result requires an unavailable local inspection
and no terminal code, and every known observation is null or remains inside the
admission policy; known invalid or over-limit evidence is terminal, not retryable.
`PDF_MEDIA_TYPE_INVALID` requires an observed non-PDF media string rather than an
unknown/null observation. Every non-rejected public snapshot has a null rejection code.

`SourceAdmissionEventV1` uses the repository envelope: producer, tenant, aggregate
type/ID/version, occurred/recorded times, correlation/causation IDs, privacy class, and
payload. Each of the nine event types is discriminated against its compatible
admission state and reason/checksum shape. Rejection, cancellation, rights-revocation,
and removal-completion facts accept only their own frozen reason family; a
type/payload or type/reason mismatch is invalid.

## F003-TD-006 — Transaction, tenancy, retention, and removal boundary

Status: **frozen**

The Documents/Content Rights module owns the admission and removal sagas. Each local
command has one short PostgreSQL transaction:

```text
re-derive identity/tenant/membership/rights/resource
  -> reserve idempotency or compare row version
  -> write source/version/authorization or state change
  -> write audit + sanitized outbox / durable job intent
  -> commit
  -> invoke storage or inspector adapter / wake dispatcher
```

No database transaction spans a target upload, object delete, parser, scanner, or
validator call. Each external/local adapter observation is normalized in a separate
transaction and reconciled against the object inventory/checksum. All tenant-owned
tables use composite tenant FKs, `UNIQUE (tenant_id, id)`, forced RLS, default-deny
grants, and production-role tests. A browser tenant header, URL ID, or upload token
cannot bypass this enforcement.

Cancellation, expiry, revocation, and dispute atomically block new use and create a
durable removal/impact job. The reconciler verifies object absence and records proof
before `removal_status=completed`. Retention, legal hold, backup expiry, and actual
external deletion remain blocked by documents 25–28; F-003 uses only local synthetic
fixtures and cannot claim production deletion completeness.

## Shared hotspots and owner

Issue [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43) is the one
F-003 implementation and integration owner. It owns the Documents migration graph,
settings/composition, FastAPI/OpenAPI/generated client, Admin adapter, web/E2E, event
schemas, CI/Make targets, and documentation manifest. Its launch gate closed after PR
#55 merged, and the local candidate is recorded in the
[implementation evidence](../../evidence/f003-source-admission-implementation.md). No
parallel implementation issue may edit those hotspots.

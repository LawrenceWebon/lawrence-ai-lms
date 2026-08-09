# Book and Document Ingestion Pipeline

Status: **post-MVP, disabled pending rights/provider/retention/capacity gates**  
Change IDs: CHG-010, CHG-020

## Supported initial inputs

- Text PDF
- Scanned PDF
- EPUB
- DOCX
- Markdown
- Plain text
- HTML export
- Page images as an explicit scanned-document workflow

## Rights gate

Before upload, require the user to select and attest one basis:

- I own this content.
- My organization has a license to use it.
- I have written permission.
- It is public domain.
- Another documented legal basis applies.

The source remains blocked from generation until the declaration is recorded.

A declaration alone is not authorization. Before any store/OCR/extract/embed/generate/display/retrieve/provider-transfer operation, the service requires an active, reviewed `source_use_authorization` covering that exact operation, territory, audience and term. Missing, expired, disputed or revoked authorization fails closed.

## Upload flow

1. API validates tenant entitlement, role, declared expected type/size for admission, and rights declaration; declared metadata is never final byte evidence.
2. API creates `source_documents`, `source_document_versions`, and a tenant/purpose/path-bound upload intent with byte/page/pixel/archive quotas.
3. API returns a short-lived signed Supabase Storage upload URL.
4. Browser uploads directly to a private quarantine bucket.
5. A trusted worker derives final size, MIME/magic, checksum, page/pixel/archive characteristics from the bytes; client metadata is never authority.
6. Object inventory and DB record are reconciled, malware/parser sandbox checks pass, and only then is a durable ingestion job admitted.

Use TUS resumable upload for files over 6 MB or unreliable links. Uploads always land in a private quarantine bucket under a random, signed tenant/purpose key. Signed URLs are short-lived and cannot select a different tenant, bucket or final publication path.

## Pipeline states

```text
upload_pending
→ quarantined
→ validating
→ extracting
→ OCR if needed
→ normalizing
→ structure_detection
→ quality_check
→ chunking
→ indexing
→ ready
```

Failure states must be resumable from the last safe step.

## Processing stages

### 1. File validation

- Check extension, MIME type, and file signature.
- Enforce size and page limits by plan.
- Calculate SHA-256.
- Detect duplicate source versions.
- Reject encrypted or password-protected files unless a secure workflow exists.
- Run malware scanning before processing.
- Enforce extension/MIME/magic agreement, archive expansion/file-count/depth limits, page/pixel limits and parser CPU/memory/time/network limits.
- Run parsers in a sandbox with no ambient credentials and no unrestricted network access.
- Record immutable object key/version, server-derived SHA-256/size/MIME, scanner/parser versions and outcome.
- Reconcile orphan DB intents, missing objects, unreferenced objects and checksum mismatches on a schedule.

### 2. Layout-aware extraction

Use a layout-aware parser such as Docling for PDF and image-heavy documents. Extract:

- Reading order
- Headings
- Paragraphs
- Lists
- Tables
- Images and captions
- Page boundaries
- Bounding boxes
- Equations or code blocks where supported

### 3. OCR fallback

Run OCR only when:

- A page has no usable text layer.
- Extracted text density is below threshold.
- Character-quality heuristics fail.
- The user explicitly requests full OCR.

Store OCR confidence and quality flags per page.

### 4. Canonical normalization

Create:

- Canonical JSON document tree
- Normalized Markdown
- Per-page text
- Element-level records
- Hierarchical sections

Do not generate course content directly from raw PDF bytes.

### 5. Quality checks

Calculate:

- Extracted page coverage
- Character confidence
- Reading-order confidence
- Heading hierarchy validity
- Table extraction success
- Duplicate-page detection
- Language detection confidence
- Empty or corrupted page count

Block downstream embedding/generation when quality is below the approved versioned threshold. A reviewer may request reprocessing or mark pages for manual correction, but cannot improvise a threshold waiver. Any future exception policy requires named scope/reason/approver/expiry and cannot waive malware, rights, tenant-isolation or human-publication gates.

### 6. Structure-aware chunking

Primary chunking order:

1. Chapter and heading boundaries
2. Paragraph and list boundaries
3. Table boundaries
4. Token-size enforcement inside a section
5. Contextual prefix containing book title and hierarchy

Store small retrieval chunks and parent sections. Search small chunks but provide the larger parent context to the LLM when needed.

### 7. Pinecone indexing

- Use one tenant namespace.
- Upsert only rights-eligible chunks into a non-active generation using the complete metadata contract in documents 06/10.
- Record each pending/confirmed/failed operation and content checksum in PostgreSQL; a provider acknowledgement alone does not make the generation searchable.
- Reconcile expected IDs/count/hash with provider observations, then atomically activate the complete generation in PostgreSQL.
- Make reindexing safe and repeatable through deterministic IDs, generation cutover and read-time database reauthorization.
- Tombstone immediately and poll/reconcile provider deletion when a source version is revoked, archived or superseded.

## Job idempotency

Every step checks persisted state and output checksum before repeating. A retry must not create duplicate pages, chunks, vectors, or generation runs.

Each stage has a durable attempt row, lease owner/expiry, heartbeat, checkpoint, input manifest hash, output manifest hash, retry class and terminal reason. Tenant and provider concurrency caps are enforced from database-owned job state; an orchestration delivery is only a wake-up signal.

## Failure recovery

- Retain the original file only while its source-use authorization and document 25 retention/hold rule permit it.
- Store the failing step and stable error code.
- Allow retry from the step boundary.
- Allow parser configuration changes without creating a new source identity.
- Create a new ingestion run for each retry.
- Keep previous completed extraction versions available for audit.

## Rights invalidation and takedown (CHG-010)

On expiry, revocation, dispute, or scope reduction:

1. In the authorization transaction, set the source/version to blocked and make all new processing, retrieval, generation, publication and display checks fail immediately.
2. Insert a durable impact job and normalized items covering source → versions → objects/pages/elements/sections/chunks → vector generations → run context/output/artifacts → draft/published course versions → citations/cache/provider copies.
3. Apply the counsel-approved action per item: withdraw/unpublish, redact, detach, delete, tombstone, preserve under hold, notify, or require replacement source. Enrolled-learner treatment must be explicit.
4. Invalidate caches and active vector generation before asynchronous provider deletion; retrieval reauthorization prevents stale Pinecone results from being used.
5. Reconcile object keys/checksums, PostgreSQL edges, provider deletion observations, caches and published references until no unauthorized active edge remains.
6. Preserve only the minimum authorized declaration, decision, event and proof under document 25; never retain the content merely for convenience.
7. Escalate breaches of the removal SLO to the named legal/content/DPO owners. The numeric SLO is `TBD-BLOCKING` and prevents AI enablement.

Release evidence includes expiry/revocation tests against draft and published content, vector eventual-consistency polling, object/provider failure and retry, legal hold, cache invalidation, citation-open denial and a complete impact manifest.

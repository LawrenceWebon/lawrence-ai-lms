# AI, Document Ingestion, and RAG Schema Extension

These tables extend the base LMS schema for book ingestion, AI course generation, and the course companion.

Status: **PDF ingestion and structured generation planned for the focused MVP; RAG/vector companion scope deferred; executable schema and evidence pending**

Change IDs: CHG-003, CHG-009, CHG-015  
Scope override: product decisions P-001/P-009/P-011. Provider-connected or real-data
enablement gates remain Q-06, Q-07, Q-08, Q-09/Q-P07, documents 25–28, provider
approval, migrations, production-role RLS tests and end-to-end removal proof. Local
contract and fixture work does not authorize an external provider or production data.

Only the source-rights/document, ingestion, generation, review, provenance, model-run,
safety, usage, and generation-evaluation objects needed by an approved focused MVP
issue may enter the migration graph. AI companion tables and vector-specific objects
remain deferred unless a later product decision or F-005 quality evidence enables them.

Every tenant-owned table below has non-null `tenant_id`, `UNIQUE (tenant_id,id)`, and composite same-tenant foreign keys. A field list that omits those columns for readability does not waive the invariant. Arrays/JSON may preserve immutable provider payloads or display snapshots, but never act as the only relationship, authorization, rights, lineage, citation, evaluation, or deletion edge.

## Source-rights and document tables

### `app.source_rights_declarations`

Records the uploader's legal basis for processing a source.

Core fields:

```text
id, tenant_id, declared_by_user_id
rights_basis                    # owned, licensed, public_domain, permission, other
rights_holder_name
license_name
license_reference
declared_intended_uses          # uploader claim only; never an authorization edge
attestation_text
attested_at
expires_at
supporting_asset_id
status
```

The declaration is uploader evidence only and does not authorize processing. Add normalized `source_use_authorizations` with tenant, source/version, rights holder/basis/evidence asset, territory, audience, valid-from/until, status, reviewer/approver and one or more normalized permitted-operation rows for store, OCR, extract, embed, generate derivative, display excerpt, retrieve, learner chat, export and model-provider transfer. Authorization is denied unless an active record covers the exact operation, time, territory and audience.

Add `source_use_authorization_events` for approval, expiry, revocation, dispute, hold and resolution; and `source_impact_jobs`/`source_impact_items` to enumerate every downstream artifact/provider action and proof.

### `app.source_use_authorizations`

```text
id, tenant_id, source_document_id, source_version_id null
rights_holder_name, rights_basis, evidence_asset_id
territory_code, audience_scope, valid_from, valid_until
status, reviewed_by_id, approved_by_id, decision_at
policy_version, evidence_hash, denial_or_restriction_reason
```

### `app.source_use_authorization_operations`

One row per allowed operation; do not store the permission set only in JSON/arrays.

```text
id, tenant_id, source_use_authorization_id
operation                       # store, ocr, extract, embed, generate, display, retrieve, chat, export, provider_transfer
purpose, provider_scope null, content_scope null
allowed, condition_code, created_at
```

`source_use_authorization_events` is append-only and records actor, prior/new status, reason, effective time and evidence hash. Expiry/revocation/dispute commits the blocking event and durable impact job atomically.

### `app.source_documents`

Stable source identity.

```text
id, tenant_id, owner_user_id, rights_declaration_id
title, source_type, primary_locale_code
status                          # draft, uploaded, ingesting, ready, failed, archived, blocked
current_version_id
visibility                      # private, course_scoped, tenant_scoped
created_at, updated_at, archived_at
```

### `app.source_document_versions`

Immutable uploaded or normalized version.

```text
id, tenant_id, source_document_id, version_number
original_asset_id
normalized_markdown_asset_id
canonical_json_asset_id
content_sha256, mime_type, file_size_bytes
page_count, word_count, detected_locale_code
extraction_quality_score
status
created_by_id, created_at
```

### `app.source_artifacts`

Normalizes all stored source representations instead of adding one asset column per parser output:

```text
id, tenant_id, document_version_id, storage_object_id
artifact_role                   # original, normalized_markdown, canonical_json, page_image, thumbnail, parser_output
media_type, byte_size, content_sha256
producer_name, producer_version, status
created_at, trusted_at, superseded_at
```

The immutable original and every derived artifact have a checksum and object-inventory FK. Convenience asset fields on the version may be projections only and cannot be the sole lineage/recovery edge.

### `app.document_ingestion_runs`

```text
id, tenant_id, document_version_id, job_id
parser_name, parser_version, ocr_engine, configuration
status, current_step, progress_percent
started_at, completed_at, failed_at
error_code, error_message
quality_report_json
```

### `app.document_pages`

```text
id, tenant_id, document_version_id
page_number, label, width, height
text_content, markdown_content
image_asset_id, thumbnail_asset_id
ocr_used, ocr_confidence
```

### `app.document_elements`

Canonical layout elements.

```text
id, tenant_id, document_version_id, page_id, parent_element_id
position, element_type            # heading, paragraph, list, table, image, caption, code, equation
hierarchy_level
text_content, markdown_content, structured_json
bounding_box_json
source_start_offset, source_end_offset
quality_flags
```

### `app.document_sections`

Hierarchical detected structure.

```text
id, tenant_id, document_version_id, parent_section_id
section_key, position, level
title, summary
start_page, end_page
start_element_id, end_element_id
```

### `app.document_chunks`

Canonical retrieval chunks.

```text
id, tenant_id, document_version_id, section_id
parent_chunk_id, chunk_index, chunk_type
text_content, contextual_prefix
start_page, end_page
start_element_id, end_element_id
token_count, content_sha256
locale_code, status
```

### `app.vector_records`

Maps source-of-truth chunks to Pinecone.

```text
id, tenant_id, chunk_id
provider, index_name, namespace, vector_record_id
embedding_provider, embedding_model, embedding_dimension
metadata_snapshot, content_sha256
status, indexed_at, deleted_at
```

### `app.vector_sync_runs`

Tracks complete or incremental index synchronization.

Required fields include `tenant_id`, logical index purpose, embedding/schema version, `generation_id`, expected vector count/hash, observed count/hash, status, activation/supersession/tombstone timestamps, attempt/checkpoint and reconciliation evidence.

## Course-generation tables

### `app.course_generation_runs`

```text
id, tenant_id, source_document_id, document_version_id
requested_by_user_id, target_course_id
mode                             # new_course, update_course, regenerate_blueprint
status                           # queued, extracting, planning, generating, review_ready, approved, failed
requested_locale_code, target_level, target_duration
configuration_json
prompt_set_version
started_at, review_ready_at, completed_at, failed_at
```

### `app.course_generation_steps`

```text
id, tenant_id, generation_run_id, step_key, sequence_number
status, attempt_number
input_manifest_hash, output_manifest_hash
model_run_id
started_at, completed_at, failure_message
```

Inputs and outputs use normalized `job_artifacts`, `artifact_lineage_edges` and source/run link rows. The manifest hashes make the ordered set tamper-evident; arrays or JSON IDs are never the authoritative lineage.

Recommended step keys:

```text
source_quality_check
book_structure_analysis
course_blueprint_generation
learning_objective_generation
module_generation
lesson_generation
activity_generation
quiz_generation
assignment_generation
citation_validation
quality_evaluation
review_package_creation
```

### `app.generated_course_blueprints`

```text
id, tenant_id, generation_run_id, revision_number
proposed_title, proposed_description
level, estimated_duration_seconds
learning_outcomes_json
prerequisites_json
status
created_at, approved_at, approved_by_id
```

### `app.generated_blueprint_items`

Hierarchical modules, lessons, activities, and assessments.

```text
id, tenant_id, blueprint_id, parent_item_id
item_type, position, title, summary
learning_objectives_json
estimated_duration_seconds
status, reviewer_notes
```

### `app.generated_content_artifacts`

```text
id, tenant_id, generation_run_id, blueprint_item_id
artifact_type                    # lesson_body, summary, quiz, assignment, glossary, transcript
locale_code, revision_number
content_json, content_markdown
model_run_id
status                           # draft, needs_review, approved, rejected, superseded
approved_by_id, approved_at
```

### `app.content_review_tasks`

```text
id, tenant_id, generation_run_id, artifact_id
assigned_to_user_id, review_type, priority
status, due_at
review_notes, decision
completed_at
```

### Canonical course provenance fields

Add to `courses`, `course_versions`, sections, lessons, questions, and assignments:

```text
origin_type                      # manual, imported, ai_generated, ai_assisted
source_document_id null
source_generation_run_id null
source_artifact_id null
human_approved_at null
human_approved_by_id null
```

AI content must flow into the same canonical tables used by manually authored courses.

Normalized `artifact_source_edges` connect tenant, artifact/revision, source document/version, section/chunk/element/span, relationship type, citation/coverage purpose and authorization ID. `generated_blueprint_item_sources` and `generated_artifact_sources` replace source-ID arrays as authority.

## Prompt and model-run tables

### `app.ai_prompt_templates`

Stable prompt purpose and ownership.

### `app.ai_prompt_versions`

Immutable system prompt, schema, examples, safety rules, and checksum.

### `app.ai_model_runs`

```text
id, tenant_id, purpose, provider, model
prompt_version_id
input_hash, output_hash
input_tokens, output_tokens, cached_tokens
latency_ms, estimated_cost_minor, currency_code
status, error_code
request_metadata, response_metadata
started_at, completed_at
```

Each run references an immutable `ai_run_snapshots` record containing tenant, purpose, provider/model/version, prompt/version/checksum, ordered messages, normalized ordered context-item edges, tool/schema/policy/code/config versions, sampling parameters, safety settings, input/output hashes, usage/cost, region and provider request ID. Restricted provider request/response payloads may be retained only under document 25; general logs never contain source/chat bodies.

Normalized tables include `ai_run_context_items`, `ai_run_outputs`, `ai_run_source_edges`, `ai_run_evaluation_links` and `ai_run_tool_calls`. Each edge is tenant-safe and references an immutable source/artifact/version or a recorded external-input hash.

`ai_run_context_items` freezes each retrieved/input item in order with source/chunk/course version, eligibility/rights decision, retrieval/rerank score, citation anchor and content hash. `ai_run_outputs` records typed immutable artifacts and output hashes. An `ai_model_runs` row without its complete snapshot and normalized context/output/lineage edges cannot enter review.

Never store secret provider credentials or unrestricted full private content in general logs.

### `app.ai_usage_ledger`

Tracks tenant and feature consumption for quotas and billing.

### `app.ai_safety_events`

Records detected prompt injection, unsafe output, source-policy violation, PII leakage risk, or unsupported citation.

## AI companion tables — deferred

### `app.ai_assistant_configs`

```text
id, tenant_id, course_id
name, system_behavior
allowed_source_types
retrieval_top_k, rerank_top_n
minimum_relevance_score
answer_locale_mode
citations_required
knowledge_policy                 # course_sources_only for the approved behavior
status
```

`knowledge_policy` is constrained to `course_sources_only` for the approved first enablement. A broader mode requires a new product/privacy/evaluation decision; an instructor setting alone cannot enable it.

### `app.ai_conversations`

```text
id, tenant_id, assistant_config_id, user_id, enrollment_id
status, title
last_message_at
conversation_summary
summary_updated_at
```

### `app.ai_messages`

```text
id, tenant_id, conversation_id, role
content, content_redacted
status
model_run_id
created_at
```

### `app.ai_retrieval_runs`

```text
id, tenant_id, conversation_id, message_id
query_text_hash, rewritten_query
namespace, metadata_filter
retrieval_method
requested_top_k, result_count
latency_ms, status
```

### `app.ai_retrieval_results`

```text
id, tenant_id, retrieval_run_id, rank
chunk_id, vector_record_id
retrieval_score, rerank_score
selected_for_context
```

### `app.ai_message_citations`

```text
id, tenant_id, assistant_message_id, chunk_id
citation_order
quote_excerpt
source_document_id, document_version_id
page_start, page_end
course_id, lesson_id
```

### `app.ai_message_feedback`

```text
id, tenant_id, assistant_message_id, user_id
rating                           # helpful, not_helpful
reason_codes, comment
created_at
```

## Evaluation tables

- `ai_evaluation_datasets`
- `ai_evaluation_cases`
- `ai_evaluation_runs`
- `ai_evaluation_results`

All four carry tenant/scope classification and immutable dataset/version/case/run/result relationships. Dataset cases are rights-cleared and versioned; results store metric definition/version, numeric value, threshold version, pass/fail, evaluator identity/version, evidence hash and linked model/run/output. A JSON score blob is never the only release evidence.

Measure:

- Retrieval hit rate
- Citation validity
- Faithfulness
- Answer completeness
- Refusal correctness
- Cross-tenant leakage
- Prompt-injection resistance
- Course-generation structure quality
- Instructor acceptance and edit distance

## Pinecone data model — deferred unless F-005 proves vector retrieval necessary

Use one namespace per tenant. Example vector ID:

```text
chunk:{document_version_id}:{chunk_id}
```

Metadata:

```json
{
  "tenant_id": "...",
  "document_id": "...",
  "document_version_id": "...",
  "source_version_id": "...",
  "course_id": "...",
  "course_version_id": "...",
  "lesson_id": "...",
  "section_id": "...",
  "chunk_id": "...",
  "locale": "en-PH",
  "content_status": "approved",
  "visibility": "enrolled_students",
  "rights_status": "active",
  "embedding_version": "...",
  "index_generation": "...",
  "page_start": 10,
  "page_end": 11,
  "content_sha256": "..."
}
```

Authorization is resolved in PostgreSQL before search. Pinecone receives a trusted namespace and metadata filter; it never decides user permissions by itself.

Every upsert carries these fields. Every search uses the exact approved course/source version, active rights and active index generation alongside server-controlled tenant/course/visibility metadata; optional display fields never substitute for these filters.

## Vector consistency, activation, and deletion contract (CHG-015)

1. PostgreSQL creates a pending immutable vector generation and deterministic IDs scoped by tenant, source/course version, chunk and embedding version.
2. Workers upsert only into the pending generation and record each operation as pending/confirmed/failed without marking it searchable.
3. Reconciliation compares expected IDs/count/content hashes with provider observations. Only a complete reconciled generation can be atomically marked active in PostgreSQL.
4. Retrieval filters exact tenant namespace, active generation, approved course version, visibility and active rights. Returned chunk IDs are batch reauthorized against PostgreSQL after vector search and before context assembly.
5. Superseded/revoked generations are tombstoned immediately in PostgreSQL, excluded from retrieval, deleted from Pinecone, then polled/reconciled until absence is observed.
6. Repair and full rebuild start from PostgreSQL manifests. The run records counts, hashes, missing/extra IDs, retries, elapsed time and approval evidence.
7. The rights-removal SLO and escalation owner remain `TBD-BLOCKING` in document 25/Q-06; AI cannot be enabled until an end-to-end removal test passes.

## AI schema release gates

- Migrations prove every child has tenant ownership and composite tenant-safe FKs.
- Production-role RLS tests cover wrong tenant/course/version, stale membership, guessed IDs, citations, evaluation and deletion rows.
- Rights invalidation blocks new processing/retrieval/publication synchronously and completes the normalized impact job.
- A run can be reproduced from immutable snapshot/lineage without relying on mutable JSON identifiers.
- No service/model actor can approve or publish; document 09's state machine and database constraints pass.

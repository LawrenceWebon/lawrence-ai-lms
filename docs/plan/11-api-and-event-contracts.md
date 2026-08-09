# API and Event Contracts

Status: **approved contract direction; OpenAPI/event schemas and tests pending**  
Change IDs: CHG-019, CHG-044

## REST standards

- Base path: `/api/v1`
- Plural resources
- OpenAPI 3.1 contract
- Generated TypeScript client
- Cursor pagination for large lists
- UTC ISO 8601 timestamps
- Integer minor units for money
- Request and correlation IDs
- Idempotency keys for duplicate-sensitive commands
- RFC Problem Details error responses

### Executable contract and compatibility

Phase 0 generates and commits `contracts/openapi/openapi.json` from the FastAPI application, lints it, produces the TypeScript client and records both checksums in the phase evidence manifest. Handwritten examples in this document are explanatory and cannot replace the artifact.

- Every operation has a stable `operationId`, authentication/security scheme, request/response/error schemas, permission/capability classification and owner.
- Additive optional fields are normally compatible. Removing/renaming fields, narrowing accepted values, changing meaning/default/auth/status code, or making a field required is breaking and needs a new version/migration window.
- CI diffs OpenAPI against the approved baseline and runs generated-client compile plus consumer contract tests. A documented deprecation includes replacement, telemetry-safe usage evidence, deadline and owner.
- Deferred endpoint groups are absent from the production OpenAPI, not merely described as unavailable.

Versioned domain-event JSON Schemas live under `contracts/events/<event-type>/<version>.schema.json`. Sanitized provider request/event fixtures and exact signature/state mappings live under `contracts/providers/<provider>/<contract-version>/`; no secret or production payload is committed.

### Cursor pagination contract

List endpoints declare a deterministic unique ordering, normally `(created_at, id)` or a domain-specific immutable key. The opaque versioned cursor binds the last sort values, direction, normalized filter/sort hash and maximum age; it contains no secret or authorization grant and is integrity-protected when clients could alter it.

- Tenant and authorization scope are re-derived for every page; a cursor never expands access.
- A cursor used with different filters/sort/direction/endpoint is rejected with a stable 400 error.
- Forward/backward behavior, page-size maximum/default, empty/end response and invalid/expired cursor behavior are in OpenAPI.
- Inserts/deletes may affect later pages under documented keyset semantics; endpoints requiring a stable snapshot use an explicit snapshot/version boundary rather than pretending an offset is stable.
- Tests cover duplicate sort values, concurrent insert/delete, tenant change, tampering, expiry and no skipped/duplicated item within the declared semantics.

### Command idempotency contract

Duplicate-sensitive commands require `Idempotency-Key`. PostgreSQL reserves `(environment, tenant, actor-or-caller, method, normalized route/command, key)` with request hash, status, response reference/hash, timestamps and approved retention.

- Same key and same canonical request waits for, resumes or returns the recorded result.
- Same key with a different request hash returns an idempotency-conflict response and emits an integrity signal.
- Reservation and local business effect commit atomically. A crashed `in_progress` record is recovered through lease/expiry plus reconciliation; it is never blindly re-executed.
- Provider idempotency keys derive from the stable local command/step ID and remain distinct from provider-event inbox deduplication.
- Keys and stored responses follow privacy/retention rules and never contain bearer tokens or unrestricted sensitive bodies.

## Core API groups

The focused MVP contract includes identity/tenant, canonical course, enrollment,
progress, PDF document/ingestion, and structured course-generation groups. Each group
appears in OpenAPI only when its owning feature is implemented and its applicable
gate passes. Commerce, assessments, certificates, and AI chat/RAG groups remain absent
until separately enabled.

```text
/auth-context
/tenants
/memberships
/roles
/permissions
/courses
/course-versions
/curriculum-sections
/lessons
/enrollments
/progress
/documents
/document-ingestion-runs
/course-generation-runs
```

Deferred groups include question banks/quizzes/assignments/certificates, products/
carts/orders/payments/refunds/subscriptions, and AI conversations/messages. Their
presence in future design documents is not permission to expose them. Notifications
and support-ticket APIs also require a focused feature need rather than being scaffolded
by default.

## Important command endpoints

```text
POST /courses/{id}/submit-review
POST /courses/{id}/publish
POST /documents/uploads
POST /documents/{id}/ingestion-runs
POST /course-generation-runs
POST /course-generation-runs/{id}/approve-blueprint
POST /generated-artifacts/{id}/approve
```

AI conversation, commerce, payment, and other deferred command endpoints remain
outside the production OpenAPI until separately enabled.

## Error format

```json
{
  "type": "https://errors.example.com/document-quality-insufficient",
  "title": "Document quality is insufficient",
  "status": 409,
  "detail": "Twenty-three pages could not be extracted reliably.",
  "code": "DOCUMENT_QUALITY_INSUFFICIENT",
  "request_id": "req_...",
  "errors": []
}
```

## Event envelope

The envelope example below also requires `producer`, `aggregate_version`, `recorded_at` and `privacy_class`. Optional trace/schema IDs must be defined in the versioned contract rather than added ad hoc.

```json
{
  "event_id": "uuid",
  "event_type": "document.ingestion_completed",
  "event_version": 1,
  "tenant_id": "uuid",
  "aggregate_type": "source_document",
  "aggregate_id": "uuid",
  "occurred_at": "2026-08-01T00:00:00Z",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {}
}
```

## Event rules

- Events are immutable facts.
- Additive payload evolution is preferred.
- Breaking changes create a new event version.
- Consumers are idempotent.
- Outbox insertion happens in the source transaction.
- Analytics consumers may fail without blocking the business transaction.
- Payment and enrollment consumers require stronger monitoring and reconciliation.

### Delivery, ordering, and evolution contract (CHG-044)

- The source transaction writes the aggregate change, audit fact and outbox event atomically. Dispatch never occurs before commit.
- Schema registry/contract fixtures pin event type/version/producer, aggregate/version, tenant, correlation/causation, occurred/recorded times, required fields and privacy class. Breaking semantic or field changes create a new version and migration window.
- Consumers reserve an inbox key `(consumer, producer, event_id)` plus payload hash. Same ID/different hash is a security/integrity error; same hash returns/resumes the recorded result.
- Ordering is not assumed globally. Reducers that require order compare aggregate/provider version and occurred/recorded time, persist deferred gaps, and reconcile with authority.
- Retries have bounded backoff/jitter, lease/heartbeat, retryable/terminal classification and poison/DLQ evidence. Replay is audited and does not erase attempts.
- Events minimize content: no tokens/secrets, source/chat bodies, assignment text, grades, payment instrument data or unnecessary personal fields.
- Payment/email/job consumers use provider-neutral normalized events but always reconcile the provider/DB authority before irreversible effects.

## Webhook rules

- Verify signature before trusting payload.
- Persist provider event before processing.
- Unique provider event ID prevents duplicates.
- Return the provider-required success response quickly.
- Process business effects asynchronously.
- Keep a replay mechanism.
- Redact headers and payload fields before logs.
- Capture the raw body exactly once before parsing when the provider signature contract requires it; validate timestamp/replay tolerance and use constant-time comparison.
- Record environment/merchant/source, endpoint version, signature result, event ID, body hash and received time before reduction.
- A success redirect, callback ordering, or provider retry window is never the source of business truth.

## Provider adapter contract

Before enabling an external provider, its adapter records:

- exact product/API/version, account/merchant/environment, region and approved capability;
- normalized commands, observations and local/provider state mapping;
- authentication/signature/freshness/raw-body rules and credential owner;
- idempotency scope/window, timeout, retryable/terminal/unknown classification and circuit-breaker behavior;
- retrieval/reconciliation authority, pagination/order behavior and repair/compensation rules;
- rate/quota/cost limits, data classification/retention/deletion and prohibited payloads;
- sandbox fixtures for success, duplicate, hash conflict, invalid signature, out-of-order, timeout/unknown, rate limit and provider outage; and
- version/deprecation monitoring, kill switch, rollback/exit and accountable approver.

Domain services see typed normalized results. They do not switch between provider products at runtime, interpret raw SDK payloads, or use provider success as local authority without the documented reduction transaction.

## Authentication contract (CHG-019)

For every protected request:

1. Accept only the configured Supabase project HTTPS issuer and its project JWKS endpoint; never discover an issuer/JWKS URL from the token or request.
2. Allowlist asymmetric algorithms/appropriate key types and require a known, currently valid `kid`; reject `none`, symmetric confusion and unapproved algorithms.
3. Validate signature, issuer, subject, expiry, not-before/issued-at with a documented small clock skew, and the configured audience or Supabase role contract. Reject tokens from any other project/environment.
4. Cache keys only within official rotation/cache behavior; refresh once on unknown `kid`, fail closed when keys cannot be validated, and alert on sustained verification failure.
5. Treat JWT/user metadata as identity/session hints only. Re-read active user/profile, tenant, membership, entitlement, scope and resource ownership from PostgreSQL in the request transaction.
6. Next.js SSR uses a fresh request-scoped client and verified claims for route protection; `getSession()` alone is not authorization.

Tests cover missing/malformed/expired/not-yet-valid tokens, wrong issuer/project/audience/role/algorithm/key, revoked user/session, stale membership/role, key rotation/cache failure and valid token with wrong tenant/resource.

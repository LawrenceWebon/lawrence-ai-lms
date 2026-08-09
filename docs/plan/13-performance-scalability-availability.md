# Performance, Scalability, and Availability

Status: **provisional; workload, budget, object RPO and recovery evidence blocked**  
Change IDs: CHG-025, CHG-026, CHG-035, CHG-036

## Workload and budget authority (CHG-026)

[Document 27](27-capacity-workload-specification.md) is the required baseline/expected/3×/whale workload and budget model. [Document 28](28-storage-recovery-sizing-specification.md) owns storage, egress, backup and restore sizing. Until both are approved, pool sizes, queue/provider concurrency, storage tiers, scaling thresholds, cost claims and the objectives below are hypotheses—not production commitments.

## Initial service objectives

The approved provisional monthly objectives are 99.9% for core LMS journeys and 99.5% for authoring. Each row still needs an exact SLI formula, measurement source, eligibility/exclusions, window, error-budget owner and alert/runbook. Payment and AI objectives are inapplicable while those capabilities are disabled.

| Objective | Provisional target | Applicability |
|---|---:|---|
| Core LMS monthly availability | 99.9% | initial MVP |
| Authoring monthly availability | 99.5% | initial MVP |
| Critical API p95 | under 500 ms | initial MVP; exact route set/exclusions pending document 27 |
| Public page p75 LCP | under 2.5 seconds | initial MVP where a public page exists |
| Course-companion first token p95 | under 3 seconds | deferred; must be re-approved with AI workload/provider |
| Payment-event processing | under 2 minutes | deferred; must be re-approved with provider contract |
| Critical database RPO / RTO | 15 minutes / 60 minutes | provisional production recovery target |
| Accepted-object RPO / RTO | RPO `TBD-BLOCKING` / at most 4 hours | production blocker in document 28 |

## Horizontal scaling

Stateless components:

- Next.js
- FastAPI
- Django Admin
- Worker instances

Stateful managed components:

- Supabase PostgreSQL
- Supabase Storage
- Upstash Redis
- Pinecone

## Database performance

- Tenant-first composite indexes.
- Cursor pagination.
- Deliberate `select_related` and `prefetch_related`.
- Query budgets for dashboard endpoints.
- Database statement timeouts.
- Connection pooling.
- Avoid long transactions around external API calls.
- Materialized aggregates for analytics.
- Read replicas only for eventually consistent reads.

### Primary-only and replica-safe paths (CHG-035)

The primary is mandatory for authentication/authorization/membership/entitlement decisions, privileged grants, money/ledger/fulfillment, grade/progress read-after-write, course review/publication pointers, job/lease claims, idempotency/inbox/outbox reducers and any command validation that depends on current state. An immediately following read in the same journey stays on primary.

Only explicitly cataloged stale-tolerant public catalog, reporting or analytics queries may use a replica. Each records maximum acceptable lag, fallback, user disclosure where needed and measured lag/error behavior. Replica data never authorizes a resource or triggers an irreversible effect.

## Cache policy

If measured need and the D-025 allowlist justify Redis, use it only for:

- Tenant settings
- Translation catalogs
- Public course summaries
- Permission lookup summaries
- Rate-limit counters
- Distributed locks
- Short-lived AI conversation and stream coordination

Never cache authoritative payment or grade state without revalidation.

Authorization, membership/entitlement truth, privileged grants, grades/progress correctness, finance, job leases/idempotency, rights, evaluation/publication state and deletion tombstones are never authoritative in Redis/CDN and must be re-read from PostgreSQL.

Cache keys must include environment and tenant:

```text
prod:tenant:{tenant_id}:course:{course_id}:summary:v3
```

### Cache matrix (CHG-036)

Every cache entry has an approved row with key `(environment, tenant, resource, resource_version, locale, visibility)`, owner, source query, classification, TTL, maximum staleness, size, outbox invalidation event, cold-miss behavior and Redis/CDN outage behavior. No cache key may omit tenant for tenant data or rely on a mutable slug without version/tenant resolution. Tests cover wrong-tenant key construction, stale version, event loss/reconcile, eviction, cold start and Redis outage.

## Job scaling

Separate queues or flow-control keys:

```text
transactional-email
maintenance
future-critical-payments
document-validation
document-ocr
embedding
course-generation
reports
```

Only `transactional-email` and `maintenance` are initial candidates. Payment and AI/document queues are created only with their feature gates. Use tenant-level concurrency limits so one large customer cannot consume all workers.

## AI and ingestion performance

- Server-authorized direct private upload to Storage; use TUS over 6 MB or unreliable links.
- Stream download inside workers.
- Page-batch extraction.
- Incremental chunk persistence.
- Batch embedding requests.
- Skip unchanged chunks using content checksum.
- Generate lessons in parallel within controlled limits.
- Use only the approved pinned model/configuration for each task; no unreviewed smaller-model substitution or silent fallback.
- Reuse deterministic prompt/embedding outputs only with tenant/source/version/rights keys, approved retention and run-snapshot evidence.

## Availability controls

- At least two web and API instances where applicable.
- Worker retries with exponential backoff and jitter.
- Dead-letter or failed-job review flow.
- Outbox event relay.
- Idempotent consumers.
- Health endpoints.
- External uptime monitoring.
- Graceful degradation when PostHog, Sentry, or Pinecone is unavailable.

## Degraded modes

Rows for deferred services are conditional design requirements, not evidence that those integrations are enabled.

| Failure | Expected behavior |
|---|---|
| Pinecone unavailable | Course learning works; AI companion shows temporary unavailability |
| PostHog unavailable | Product works without analytics |
| Sentry unavailable | Local structured logs continue |
| Resend unavailable | Notification remains queued and retries |
| PayMongo webhook delayed | Order remains pending and reconciliation checks status |
| Worker unavailable | For an enabled worker flow, the PostgreSQL job remains queued/leased for recovery; no accepted input is silently lost |
| Upstash Redis unavailable | Fail closed for sensitive rate limits; bypass noncritical caches |

## Backup and recovery

- Supabase automated backups and PITR on production-capable plan.
- Regular logical exports of critical metadata.
- Storage inventory and restore process.
- Pinecone can be rebuilt from PostgreSQL chunks.
- Quarterly restore drill.
- Documented runbooks for database, storage, payments, and credentials.

### Independent object recovery contract (CHG-025)

- Supabase database backups/PITR do not include Storage object bytes and do not preserve custom-role passwords. Treat database, objects and configuration/secrets as separate recovery streams.
- Protect required private uploads/published assets with an independent versioned object copy/export in an approved region/account.
- Maintain a DB↔object manifest with tenant, bucket/key/version, DB reference, checksum, bytes, protection class, tombstone and last backup/restore verification.
- Restore in an isolated environment: DB/Auth/config and roles first, protected objects and checksum reconciliation second, deletion/tombstone replay third, derived assets/Pinecone rebuild fourth, authorization/integrity smoke tests before traffic.
- Pinecone is rebuilt from the PostgreSQL active-generation manifest; vector backup never becomes authority.
- Run a quarterly isolated drill, record achieved RPO/RTO, missing/corrupt counts, throughput, manual steps, full-volume projection and owner-approved corrective actions.

Critical DB RPO 15 minutes/RTO 60 minutes and object RTO ≤4 hours are provisional. The accepted-upload object RPO and funded proof remain `TBD-BLOCKING` in document 28.

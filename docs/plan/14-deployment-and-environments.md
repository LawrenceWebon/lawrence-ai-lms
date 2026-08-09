# Deployment and Environment Plan

Status: **approved topology direction; worker/provider tiers and recovery evidence pending**  
Change IDs: CHG-012, CHG-016, CHG-021, CHG-029, CHG-041

## Environments

```text
local
development
staging
production
```

Each non-local environment has separate:

- Supabase project
- Auth users and signing keys
- Storage buckets
- PayMongo credentials/webhooks only in separately enabled commerce environments
- Resend API key and domain configuration
- Upstash Redis database; QStash credentials only after D-024 approval
- Pinecone index/namespace only after AI enablement
- PostHog project/key only after analytics approval
- Sentry project/environment
- Cloudflare records

Provider credentials for deferred capabilities are absent rather than populated with inactive values. Preview/development cannot receive production secrets, callbacks, datasets or personal data.

### Environment isolation matrix

| Concern | Local | Preview/PR | Staging | Production | Recovery exercise |
|---|---|---|---|---|---|
| Data | Synthetic seed | Synthetic seed; destroyed at close | Synthetic or separately approved masked fixtures | Real data only after documents 25/26 | Encrypted restored copy under incident controls |
| Supabase | Local stack/dedicated dev | Isolated branch/project after ready | Separate project | Separate approved-region project | Replacement/restore project |
| Web/API/worker | Local containers | Isolated preview/bounded services | Production-equivalent topology/config | Approved `sin1` + selected Singapore runtime | Reproducible recovery capacity/config |
| Providers | Fakes/sandbox | Fakes/sandbox and generated callback endpoints | Sandbox/test accounts and canaries | Separate production accounts for enabled capabilities only | Read-only/reconciliation paths where supported |
| Storage | Local/dev private | Isolated private buckets | Isolated quarantine/trusted buckets | Approved private protection classes | Independent object restore target |
| Secrets/access | Approved local store/developer | Ephemeral PR scope/team | Staging vault/release roles | Component vault/least privilege/JIT support | Recovery vault/incident roles/dual control |
| DNS/email | Local/test host and mail sink | Generated host/no real mail | Staging domain plus sink/allowlist | Platform domain and approved transactional mail; custom domains post-launch | Platform fallback/status channel |
| Retention | Short local cleanup | Destroy at PR close | Bounded test policy | Document 25 | Exercise artifacts expire under approved policy |

Infrastructure/configuration is reviewed and versioned. Manual production console changes are incident-only, immediately recorded, imported/reconciled into the declared configuration and checked for drift. Provider project/account IDs, plan/tier, region and enabled capability appear in the deployment evidence; a default setting is not accepted silently.

## Deployment topology

### Vercel

Deploy:

- Next.js web, configured in `sin1` near the Singapore data plane
- Bounded lightweight FastAPI/BFF adapters only when their duration, bundle and transaction-pool behavior fit the recorded Vercel contract

Use preview deployments for pull requests. Preview must connect only to preview or development data, never production.

Django Admin defaults to the same Singapore-capable persistent backend runtime as the API/domain service. Vercel is prohibited for Admin until a recorded compatibility/load proof covers bundle/native dependencies, request duration, sessions, direct upload behavior, connection pooling, privileged operational access, logs and rollback (CHG-041).

### Dedicated worker runtime

The exact provider remains **open/blocked** under D-023/D-024. Do not deploy production workers or QStash data flows until an ADR records a Singapore-capable benchmark, plan/tier, DPA/transfer approval, cost/capacity envelope and recovery result.

Deploy versioned least-capability images. The core notification/maintenance worker does not include deferred OCR/model/vector SDKs. Future feature-gated image profiles may contain:

- Python application code
- Django ORM
- Docling and OCR dependencies
- Embedding and LLM adapters
- File-validation tools

Use the D-024-approved authenticated internal endpoint or durable-queue polling contract. If QStash is selected, validate current/next signatures and freshness; its presence is not assumed here.

PostgreSQL is the durable job authority. Jobs/attempts/checkpoints store tenant, stage, input/output manifest hashes, idempotency key, priority, lease owner/expiry, heartbeat, attempt, retry class, provider quota, status and error evidence. QStash/another transport may only deliver a signed at-least-once wake-up containing opaque job/correlation identifiers.

Required runtime behavior: separate process/resource classes for validation, OCR, embedding, generation, exports and maintenance; global/per-tenant/per-provider concurrency; fair backpressure; poison/DLQ and audited replay; lease recovery; graceful deploy drain; version-compatible resume; canary; hard cost/capacity stops; and region/provider outage recovery. Documents 27/28 and a production-shaped benchmark set the values.

### Supabase

- PostgreSQL
- Auth
- Storage
- RLS
- Backups and PITR

Use separate local/development/staging/production projects. Production target is Singapore (`ap-southeast-1`) subject to exact plan approval. Core application schemas are not exposed through the Data API; disable it where practical or expose only a dedicated minimal schema with explicit grants/RLS.

### Database connection contract

| Process | Connection | Required behavior |
|---|---|---|
| One-off migrator | Direct database endpoint | Migrator role only; TLS verification; lock/statement timeouts; no application traffic |
| Persistent API/Admin | Session pool unless a measured direct-connection exception is approved | Component role, bounded pool, prepared statements only when the selected pool mode supports them |
| Persistent worker/reconciler | Session pool | Separate component roles/pools; short job-stage transactions; never hold a connection during provider/CPU work |
| Vercel/burst FastAPI adapter | Transaction pool | API role, prepared statements disabled, per-request transaction, small bounded client pool and no session-scoped context |
| CI/test | Isolated project/branch endpoints | Never production; production-equivalent roles/policies and explicit teardown |

All connections require provider-supported TLS verification and environment/project identity checks. Startup validates declared connection mode against the endpoint and prepared-statement setting. Document 27 owns the total connection budget across instances, pool sizes, maintenance/migrator headroom and saturation thresholds. Pool tests prove transaction-local context reset and fail deployment on the wrong project/role/mode.

### Cloudflare DNS

Recommended hostnames:

```text
example.com                 # marketing/web
app.example.com             # application
api.example.com             # API when separated
admin.example.com           # internal admin
*.example.com               # tenant subdomains when supported
assets.example.com          # optional public media domain
```

Use DNSSEC. Configure Resend SPF, DKIM, and DMARC records through Cloudflare.

Cloudflare for SaaS is the approved single custom-hostname/certificate authority. Routing requires the normalized globally unique hostname, ownership verified, certificate active, tenant/entitlement active and provider record current. Removal/churn deletes the provider hostname and routing cache; the platform domain remains fallback. See document 05's lifecycle (CHG-021).

The verified normalized hostname and environment form the routing/cache key. Private/authenticated responses use `Cache-Control: private, no-store` and are never shared at the CDN. Public branded responses vary only on an explicit canonical host/tenant/locale/version key; tests cover forged `Host`/forwarded-host values, cache poisoning, cross-tenant cache reuse, stale domain removal and platform-domain fallback.

## Regional processing and transfer map (CHG-029)

| Component | Approved target | Data allowed | Blocking condition |
|---|---|---|---|
| Vercel web/bounded API | `sin1` | Request/session metadata and API payload necessary for core LMS | Exact plan/config and transfer inventory in document 26 |
| Supabase PostgreSQL/Auth/Storage | Singapore | Core authoritative data/private objects | Plan/tier, documents 25/26/28 and restore proof |
| Persistent API/Admin/worker | Singapore-capable provider `TBD-BLOCKING` | Only enabled-domain data | D-023 benchmark/ADR, DPA and capacity/recovery proof |
| Pinecone | Singapore, Standard/Enterprise if AI later enabled | Approved embeddings + minimal metadata only | AI disabled; Q-06/Q-07/Q-09 and provider/tier approval |
| QStash/Workflow | US/EU candidate only | Opaque job/correlation IDs; no learner/source/chat/grade/payment/secret payload | D-024 plus DPO/customer transfer approval or choose regional alternative |
| Resend/Sentry/PostHog | Exact region/project `TBD-BLOCKING` | Versioned minimum allowlists | Document 26 transfer/DPA and document 25 retention |
| Backup/DR | Region/provider `TBD-BLOCKING` | Approved encrypted protection classes | Documents 25/26/28 and customer approval |

No provider default region is accepted silently. The implemented diagram records storage, processing and transit per field/payload plus outage/failover behavior.

## CI/CD sequence

1. Install locked dependencies.
2. Lint and type-check.
3. Run backend unit and integration tests.
4. Run RLS and permission matrix tests.
5. Generate OpenAPI schema.
6. Detect breaking API changes.
7. Build Next.js production bundle.
8. Build and scan worker image.
9. Apply migrations to staging.
10. Deploy staging.
11. Run Playwright smoke tests.
12. Run ingestion golden-file tests only for an enabled ingestion deployment.
13. Run locked AI/RAG evaluation smoke sets only for an enabled AI deployment.
14. Require production approval.
15. Apply backward-compatible production migrations.
16. Deploy application and workers.
17. Run production smoke tests.
18. Monitor core error/latency/pool/outbox/recovery signals plus queue/payment/AI signals only when those capabilities are enabled.

## Database migration deployment

Use a one-off migration job with a migration-specific database role. Web instances must never run migrations automatically on startup.

### Sole Django migration authority (CHG-016)

Django migrations and reviewed `RunSQL`/`RunPython` own all application DDL, RLS, grants, helpers, triggers, extensions and bucket metadata. Supabase CLI migrations must not create a second application history; the CLI is limited to local/platform/branch configuration and tests.

Preview sequence: create/wait for the isolated Supabase branch/project → obtain branch-specific direct migrator credentials → run Django migrations once → seed approved synthetic data → record migration graph and schema fingerprint → run drift/RLS tests → deploy preview. Production uses a one-off direct migrator with lock/statement timeouts, backup/readiness check, expand/backfill/contract evidence and roll-forward/rollback plan. Runtime instances never migrate at startup.

## Release strategy

- Server-side feature-flag abstraction for user-facing changes; PostHog only after its privacy/configuration gate.
- Database expand-and-contract changes.
- Canary rollout for risky AI pipeline changes.
- Pin prompt versions per generation run.
- Roll back application without rolling back irreversible data migrations.

PostHog is used for flags only after its privacy/configuration gate; a local server-side flag adapter must be able to default safely without the provider. A flag cannot expose a deferred route/job/schema/credential or grant authorization.

Each release class has an explicit recovery path:

| Change | Recovery rule |
|---|---|
| Web/API/Admin | Re-deploy the last compatible immutable artifact; keep schema compatibility through expand/contract |
| Worker | Stop new claims, drain/checkpoint compatible attempts, canary the prior/next version and resume only version-compatible jobs |
| Database | Prefer roll-forward; rollback only when proven safe. Destructive contract occurs after old code is gone, backup/readiness checks pass and retention/hold rules permit it |
| Configuration/secret | Validate staged current/next value, rotate/revoke, drain old connections and alert on old-credential use |
| External provider | Kill new admission, preserve/reconcile durable local state, switch only to an already approved adapter/config; no silent fallback |
| AI prompt/model/index | Deferred until enabled; pin run/generation version, canary locked evaluation and keep prior active generation until reconciled cutover |

Promotion records source/image/config/schema fingerprints, applicable provider contract versions, exact tests, approvers, deploy/migration IDs and smoke/monitoring result. A failed non-waivable gate stops promotion and leaves the capability disabled.

## Local development

Use Docker Compose for:

- Web
- API
- Django Admin
- Worker
- Local Redis where useful

Use the Supabase CLI for local Auth, PostgreSQL, and Storage development when practical. External services use sandbox or test credentials.

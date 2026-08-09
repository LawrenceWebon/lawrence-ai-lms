# Capacity and Workload Specification

Status: **BLOCKED_INPUT**  
Decision authority: D-041; Q-14/Q-15 approved direction  
Change IDs: CHG-012, CHG-026, CHG-029, CHG-035, CHG-036, CHG-045, CHG-046

The baseline, expected, three-times-stress, and whale-tenant methodology is approved. Numeric launch and 12-month demand, provider tiers, and monetary budgets were not supplied and are not guessed here. Production procurement, pool sizing, load acceptance, and SLO claims remain blocked until every mandatory value has an owner and evidence.

## Approval and evidence record

| Item | Accountable owner | Evidence | Current state |
|---|---|---|---|
| Product demand forecast | `TBD-BLOCKING` | Dated launch and 12-month forecast | missing |
| Finance budget | `TBD-BLOCKING` | Base, growth, hard-stop and restore/security budgets | missing |
| SRE capacity model | `TBD-BLOCKING` | Versioned calculation and provider-tier mapping | missing |
| Largest-tenant profile | `TBD-BLOCKING` | Signed sales/customer assumption | missing |
| Load-test acceptance | `TBD-BLOCKING` | Production-shaped report with commit/config IDs | missing |
| Final capacity approver | `TBD-BLOCKING` | Dated approval | missing |

## Workload profiles

Enter values for launch baseline, expected 12-month peak, 3× stress, and a single whale tenant. `3×` multiplies the expected peak mix unless a dimension-specific rationale is recorded.

| Dimension | Launch baseline | 12-month expected peak | 3× stress | Whale tenant | Source/owner | Status |
|---|---:|---:|---:|---:|---|---|
| Contracted tenants / active tenants | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Registered users / MAU / DAU | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Peak concurrent learners / instructors / admins | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| API requests/s by route class and read/write ratio | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Auth operations/minute and invitation bursts | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Enrollment/progress/quiz/grade writes/s | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Course reads, dashboard queries, exports/day | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Email intents/hour and burst | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Uploads, pages, objects and bytes/day | Linked to document 28 | Linked to document 28 | derived | Linked to document 28 | `TBD-BLOCKING` | blocked |
| Worker jobs/hour by stage and duration distribution | `TBD-BLOCKING` | `TBD-BLOCKING` | derived | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Vector upserts/deletes/queries/s | AI disabled; `TBD before enablement` | `TBD` | derived | `TBD` | AI owner | deferred |
| AI/OCR tokens/pages/provider calls/minute | AI disabled; `TBD before enablement` | `TBD` | derived | `TBD` | AI owner | deferred |
| Video concurrency/bitrate | Hosted video deferred | Hosted video deferred | not applicable | not applicable | Product | deferred |

## Request and tenant-skew mix

The load fixture must state, rather than infer:

- route-level request percentages, response sizes, write amplification, think time and session duration;
- tenant distribution (median, p95 and whale), course size, enrollment size, class/cohort bursts and timezone concentration;
- background overlap with interactive traffic, including emails, exports, backups, scans and maintenance;
- cold-cache, warm-cache, provider-degraded, worker-drain and database-failover cases;
- data volume and index cardinality matching document 28.

## Derived service envelopes

| Component | Required calculation | Warning trigger | Critical/hard-stop trigger | Evidence |
|---|---|---|---|---|
| PostgreSQL compute/IO/storage | Query plans + writes + maintenance + restore window | `TBD-BLOCKING` | `TBD-BLOCKING` | production-shaped EXPLAIN/load report |
| API session pool | Concurrent transactions × measured hold time + headroom; stay below database/provider limits | `TBD-BLOCKING` | `TBD-BLOCKING` | pool saturation and reset tests |
| Vercel transaction pool | Burst concurrency without prepared statements; API role only | `TBD-BLOCKING` | `TBD-BLOCKING` | burst/load proof in `sin1` |
| Persistent worker/session pool | Stage concurrency × DB transaction behavior | `TBD-BLOCKING` | `TBD-BLOCKING` | worker benchmark |
| Redis | Approved TTL caches/rate counters only | `TBD-BLOCKING` | fail closed for sensitive limits | outage test |
| Job system | Arrival rate, service rate, retries and tenant/provider caps | `TBD-BLOCKING queue age` | `TBD-BLOCKING queue age` | soak/fault test |
| Storage/backup/egress | Document 28 projections and restore throughput | document 28 | document 28 | storage model/drill |
| Telemetry/email/provider quotas | Enabled allowlist × sampling/retry behavior | `TBD-BLOCKING` | `TBD-BLOCKING` | sandbox/contract tests |
| Optional AI/vector services | Disabled until provider/model and corpus approval | not applicable | kill switch | gated evaluation evidence |

Pool sizes are configuration, not constants in this plan. The migrator uses a direct migration connection; persistent API/admin/worker use only an approved session/direct mode; temporary/serverless clients use transaction pooling without prepared statements. Each configuration must prove that `SET LOCAL` context cannot leak between requests.

## SLO and load acceptance

- Provisional monthly objectives are 99.9% for core LMS journeys and 99.5% for authoring. Exact SLIs, exclusions, measurement source, error-budget owner and alert windows remain required.
- A profile passes only when critical journey correctness is zero-error, tenant negative tests remain zero-leak, p95/p99 targets pass, pool/CPU/IO/queue/storage headroom meets the approved margin, and cost remains within the approved budget.
- Stress tests must identify the first controlled limit, demonstrate fair tenant throttling, preserve idempotency, and recover without manual data repair.
- Results record environment/provider tiers, data-set checksum, commit/migration/config IDs, run time, tooling, dashboards, anomalies, owner and approval.

## Budget envelope

| Budget | Launch amount | 12-month amount | Hard stop | Owner | Status |
|---|---:|---:|---:|---|---|
| Core data plane and web/API | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Security, monitoring and incident operations | `TBD-BLOCKING` | `TBD-BLOCKING` | non-waivable minimum `TBD` | `TBD-BLOCKING` | blocked |
| Database/object backup and quarterly restore | `TBD-BLOCKING` | `TBD-BLOCKING` | non-waivable minimum `TBD` | `TBD-BLOCKING` | blocked |
| Worker capacity | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | blocked |
| Optional commerce | deferred | deferred | disabled | Finance | deferred |
| Optional AI/OCR/vector | deferred | deferred | disabled | AI/Finance | deferred |

## Approval gate

This specification becomes `approved` only when no core row contains `TBD-BLOCKING`, document 28 is approved, provider tiers and regions are recorded, production-shaped baseline/peak/3×/whale tests pass, and the product, SRE and finance owners sign the evidence record.


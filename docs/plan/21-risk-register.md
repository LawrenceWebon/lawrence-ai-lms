# Risk Register

Status: **active; named accountable owners and due dates remain blocking**  
Change ID: CHG-034

## Historical risk inventory (non-authoritative)

The original three-column inventory below is retained as historical input only. It is not sufficient for risk acceptance or release. The authoritative register follows it.

| Risk | Impact | Mitigation |
|---|---|---|
| Cross-tenant data leakage | Critical | Tenant-first schema, policies, RLS, matrix tests, namespace isolation |
| User uploads copyrighted content without rights | High | Reviewed operation-scoped source-use authorization, normalized lineage, immediate block and reconciled takedown |
| OCR or parser produces incorrect structure | High | Quality scores, golden files, manual review, parser versioning |
| AI hallucinates course content | High | Source citations, structured generation, validation, human approval |
| Prompt injection inside a book | High | Treat retrieval as data, injection detection, no arbitrary tools, adversarial tests |
| AI companion answers from wrong course | Critical | Server-built filters, enrollment checks, citation validation |
| Vercel function timeout for ingestion | High | Dedicated worker runtime and durable orchestration |
| Duplicate PayMongo webhook | High | Provider event uniqueness and idempotent transaction |
| Payment redirect falsely grants access | Critical | Server webhook/API verification only |
| Pinecone becomes inconsistent | Medium | PostgreSQL source of truth, checksum sync, rebuild process |
| Redis outage | Medium | Degraded cache behavior and safe rate-limit policy |
| Email outage | Medium | Persisted notification delivery and retry |
| Provider SDK breaking change | Medium | Adapter layer, version pinning, contract tests |
| AI cost overrun | High | Tenant quotas/budgets, one approved pinned model per task, safe scoped reuse, usage ledger and kill switch |
| Sensitive data captured by analytics | High | Event allowlist, masking, redaction, privacy review |
| Published course changes break enrollments | High | Immutable versions and enrollment version pinning |
| Schema migration locks production | High | Expand-contract, online indexes, staged backfills |
| Worker job retries duplicate output | High | Step state, checksums, unique constraints, idempotency keys |
| Poor answer quality hurts trust | Medium | Evaluation sets, feedback, low-score review queue, clear refusal |
| Vendor lock-in | Medium | Provider adapters, canonical PostgreSQL data, export capability |
| Custom tenant domain takeover | High | DNS ownership verification, lifecycle checks, automated cleanup |

## Authoritative governed register (CHG-034)

Likelihood/exposure is `TBD-BLOCKING` until an accountable owner reviews evidence. P0 launch gates cannot be waived.

| ID/category | Scenario | Impact | Likelihood/exposure | Accountable owner | Trigger/indicator | Controls | Required evidence | Due/review trigger | Residual/status |
|---|---|---|---|---|---|---|---|---|---|
| R-001 tenancy/P0 | Cross-tenant relationship or runtime RLS bypass | Critical confidentiality/integrity breach | `TBD-BLOCKING` | Data + Security `TBD-BLOCKING` | Wrong-tenant FK/query/pool context succeeds | Composite tenant FKs, non-owner roles, transaction-local context, RLS/JIT | Migrations + production-role negative matrix | Before any real tenant data | open/non-waivable |
| R-002 privacy/P0 | Processing without named controller/DPO/basis/retention/transfer approval | Critical regulatory/customer harm | `TBD-BLOCKING` | DPO/Legal `TBD-BLOCKING` | Any real personal data before docs 25/26 approval | Data gate, DPIA, inventory, DSAR/breach/hold tests | Signed documents 25/26 + exercises | Before non-local real data | open/non-waivable |
| R-003 operations/P0 | Worker duplicates/loses long jobs or transfers data to unapproved region | High/Critical | `TBD-BLOCKING` | Platform `TBD-BLOCKING` | D-023/D-024 unresolved or lease/reconcile failure | DB job authority, leases/checkpoints, signed minimal wake-up, region review | ADR/benchmark/fault/soak evidence | Before worker-enabled feature | open/non-waivable |
| R-004 recovery/P0 | Restored DB references missing objects/roles/config | Critical availability/integrity harm | `TBD-BLOCKING` | SRE `TBD-BLOCKING` | Object RPO/provider tier/drill absent | Independent object backup, manifest, isolated restore | Approved doc 28 + quarterly drill | Before production | open/non-waivable |
| R-005 finance/P0 | Duplicate/misordered provider events corrupt ledger/entitlement | Critical financial/access harm | Deferred capability | Finance/Data/Legal `TBD` | Any commerce enablement | Inbox, state reducer, balanced ledger, atomic entitlement, reconcile | Contract/property/concurrency/sandbox proof | Before commerce | deferred/non-waivable |
| R-006 AI rights/P0 | Unauthorized source operation persists after expiry/revocation | Critical rights/privacy harm | Deferred capability | Legal/Content/DPO `TBD` | Any ingestion/AI enablement | Operation-scoped authorization, normalized lineage, takedown/reconcile | End-to-end removal evidence + SLO | Before ingestion/AI | deferred/non-waivable |
| R-007 AI provenance/P0 | Output cannot be reproduced/evaluated or self-publishes | Critical trust/content harm | Deferred capability | AI/Product/QA `TBD` | Any AI enablement | Immutable run snapshot, locked thresholds, human-only hash approval | Corpus/results/transition tests | Before AI | deferred/non-waivable |
| R-008 capacity/P1 | Unknown workload exhausts DB/pool/queue/budget | High outage/cost harm | `TBD-BLOCKING` | Product/SRE/Finance `TBD-BLOCKING` | Doc 27 inputs/load proof absent | Baseline/peak/3×/whale model, headroom and hard stops | Approved doc 27 + load report | Before procurement/production | open |
| R-009 telemetry/P1 | Logs/analytics capture linkable content or personal data | High privacy harm | `TBD-BLOCKING` | DPO/Security/SRE `TBD-BLOCKING` | Event allowlist/retention/canary absent | Default off, allowlist/denylist, redaction canaries, access/retention | CI/staging capture tests | Before telemetry enablement | open |
| R-010 domain/P1 | Stale/custom hostname routes to wrong tenant | High security/availability harm | `TBD-BLOCKING` | Platform/Security `TBD-BLOCKING` | Ownership/cert/churn/cache mismatch | Global normalization/uniqueness, lifecycle/revalidation/removal | Provider sandbox + routing tests | Before custom domains | open |

## Risk lifecycle

Each change records probability/likelihood rationale, impact, exposure, control/evidence links, owner, action due date, review trigger, residual rating and status (`open`, `mitigating`, `accepted`, `closed`, `deferred`). Acceptance names the residual-risk approver and expiry. Review the register at least quarterly, at every phase/release boundary and on incident/provider/legal/architecture change. A deferred capability remains disabled. Closing a risk requires evidence, not a policy sentence.

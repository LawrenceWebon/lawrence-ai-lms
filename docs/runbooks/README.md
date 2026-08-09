# Operational Runbook Catalog

Status: **pre-implementation specification; no production runbook is executable or verified yet**

This catalog defines the runbooks that must exist before production or a conditional capability is enabled. Exact provider project IDs, roles, dashboards, commands, expected outputs, communication contacts and rollback/recovery proof cannot be supplied until the runtime, infrastructure and accountable owners exist. A checklist here is not incident readiness.

## Required runbooks

| Runbook | Scope | Gate/status | Primary plan authority |
|---|---|---|---|
| Database and object restore | PITR/logical restore, roles/config, independent object copy, tombstone replay, vector/derived rebuild and validation | Core production blocker; D-040/documents 25/28 | [Performance/recovery](../plan/13-performance-scalability-availability.md), [deployment](../plan/14-deployment-and-environments.md) |
| Cross-tenant access incident | Containment, role/key isolation, evidence, affected-tenant analysis, notification decision and safe re-enable | Core non-waivable | [Security](../plan/12-security-and-multitenancy.md), [privacy/DPIA](../plan/26-privacy-accountability-dpia-specification.md) |
| Authentication/JWKS/key incident | Wrong project/key, rotation/cache failure, credential exposure, session revocation and recovery | Core non-waivable | [API/auth contract](../plan/11-api-and-event-contracts.md), [secret ownership](../plan/22-environment-variables.md) |
| Migration/schema/RLS failure | Stop rollout, lock/traffic safety, roll-forward/rollback, fingerprint drift and production-role verification | Core non-waivable | [Schema plan](../plan/05-database-schema-plan.md), [deployment](../plan/14-deployment-and-environments.md) |
| Outbox/email/provider delivery | Queue age, duplicate/hash conflict, suppression, provider outage, replay and reconciliation | Required before transactional email | [Domain/outbox](../plan/04-domain-module-design.md), [integrations](../plan/17-payments-emails-integrations.md) |
| Custom-domain/certificate incident | Misrouting, stale host cache, certificate failure, takeover containment, provider removal and platform fallback | Post-launch capability | [Deployment/domain](../plan/14-deployment-and-environments.md) |
| Payment reconciliation/ledger incident | Event quarantine, fulfillment freeze, ledger/entitlement comparison, compensating entry and customer/finance escalation | Deferred; mandatory before commerce | [Finance contract](../plan/17-payments-emails-integrations.md) |
| Rights invalidation/takedown | Synchronous block, lineage impact, unpublish/redact/delete, provider/object/vector reconcile and evidence | Deferred; mandatory before ingestion/AI | [Ingestion/takedown](../plan/08-book-ingestion-pipeline.md) |
| Worker/queue recovery | Pause admission, lease/checkpoint inspection, poison isolation, version-compatible resume, drain/canary and backlog recovery | Blocked on D-023/D-024; mandatory before worker flows | [Deployment/worker](../plan/14-deployment-and-environments.md) |
| Vector/index recovery | Tombstone, active-generation rollback/cutover, reconcile, rebuild and authorization validation | Deferred; mandatory before RAG | [AI schema/vector contract](../plan/06-ai-schema-extension.md), [ADR 0003](../adr/0003-pinecone-source-of-truth.md) |

Individual executable runbook files are created with the implementation that supplies their exact commands and environment evidence. Conditional runbooks remain absent/non-applicable while their capabilities are hard-disabled.

## Required runbook structure

Every executable runbook contains:

1. **Identity and ownership** — stable runbook ID/version, service/capability, primary/backup owner, approver, last review/drill and expiry.
2. **Trigger and severity** — exact alert/query/threshold, user/security/privacy/finance impact and incident classification.
3. **Prerequisites and authority** — environment, minimum role/JIT approval, required dashboards/evidence stores and decisions that permit action.
4. **Safety and stop conditions** — data-loss, cross-tenant, financial, legal-hold, rights, migration-lock and credential risks; actions requiring dual approval.
5. **Diagnosis** — read-only commands/queries first, expected output, correlation/timeline collection and how to distinguish failure modes.
6. **Containment** — feature/admission freeze, credential/role isolation, queue/provider controls and preservation of immutable evidence.
7. **Recovery** — ordered commands with explicit targets, idempotency/retry behavior, expected result and rollback/roll-forward path.
8. **Verification** — tenant/security/financial/object/checksum/application smoke checks and criteria for traffic re-enable.
9. **Communication/escalation** — internal owners, DPO/Legal/Finance/provider/customer decision points and approved templates/clock start.
10. **Evidence and follow-up** — artifact hashes/links, achieved SLI/RPO/RTO, remaining discrepancy, post-incident review, risk/doc/test update and re-drill date.

## Safety rules

- Resolve the exact environment, tenant/resource/object/job and current authority with read-only checks before mutation.
- Never use a broad owner/migrator/provider credential for convenience. Privileged tenant access follows the AAL2 JIT/break-glass contract and records every action.
- Destructive actions require explicit target lists, legal-hold/retention/rights checks, recoverability assessment and the runbook's approval level.
- Do not “repair” immutable audit, ledger, grade, provider-event or published-version facts in place; use approved compensating/reduction workflows.
- Do not replay a job/event until its idempotency, current authority, prior attempt/result and downstream provider state are reconciled.
- Preserve raw security/provider evidence under its access/retention policy; do not copy secrets or sensitive bodies into tickets/chat/docs.
- A failed or ambiguous verification keeps traffic/capability disabled and escalates. Time pressure does not waive tenant, privacy, finance, rights or recovery gates.

## Drill and acceptance

A core runbook is accepted only after an isolated production-shaped exercise records exact versioned commands, participants, timestamps, expected/actual results, safety checks, achieved objectives and corrective actions in the [evidence index](../evidence/README.md). Tabletop-only review may validate escalation/communication but cannot prove database/object restore, RLS recovery, provider reconciliation or worker resume behavior.

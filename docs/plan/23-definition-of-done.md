# Definition of Done

Status: **authoritative risk-based gate; implementation evidence pending**  
Change IDs: CHG-034, CHG-047

## Feature definition of done

A feature is complete only when:

- Acceptance criteria pass.
- Tenant and authorization behavior is documented.
- Database migration is reviewed.
- API contract is updated.
- Backend tests pass.
- Playwright coverage exists for a critical journey when applicable.
- Required privacy-minimized logs/metrics and approved Sentry context exist, or telemetry remains locally contained while the provider gate is blocked.
- PostHog event/flag is absent by default; if separately approved, its versioned allowlist, purpose/basis, retention/region/deletion and tests are updated.
- Localization keys exist.
- Accessibility checks pass.
- Error and empty states exist.
- Security impact is reviewed.
- Operational and rollback notes exist.

## AI feature definition of done

Additionally:

- Prompt version is immutable.
- Structured output schema exists.
- Complete immutable run snapshot and normalized source/artifact/context/output provenance are stored.
- Operation-scoped source rights and provider/model approval are current.
- Citation behavior is validated.
- Rights-cleared locked evaluation dataset and numeric threshold version are approved and pass.
- Prompt-injection cases pass.
- Cost and token usage are measured.
- Human review gate cannot be bypassed.
- Tenant and source filters are server-controlled.
- Rights expiry/removal and vector/provider reconciliation pass end to end.

## Payment feature definition of done

Additionally:

- Exact provider product/account/state/signature contract is approved.
- Local/provider idempotency and duplicate/hash-conflict/out-of-order webhook tests pass.
- Amount and currency mismatch test passes.
- Reconciliation test passes.
- Append-only ledger balances per currency under concurrency/property tests.
- No raw card data is stored.
- Local entitlement effect occurs exactly once; any enrollment projection follows the approved product policy.
- Refund/dispute/access and tax/accounting policy are approved and tested.

## Release definition of done

- Staging migration succeeded.
- Production backup or recovery readiness confirmed.
- Critical Playwright smoke passed.
- Ingestion smoke passed when relevant.
- RAG evaluation smoke passed when relevant.
- No critical security scan findings.
- Applicable dashboards, owned alerts and executable runbooks are active and linked.
- Rollback or mitigation plan is documented.
- Release owner is identified.

## Authoritative risk-based Definition of Done (CHG-047)

The earlier checklists are minimum reminders. This section is authoritative. Every applicable row records evidence path, accountable owner, independent approver, result and date; `not_applicable` requires proof that the capability is absent and disabled.

| Gate | Required evidence | Owner/approver | Waiver policy |
|---|---|---|---|
| Scope and acceptance | User outcome, acceptance criteria, non-goals, capability/phase/decision IDs and no hidden blocker | Product / release approver | Normal exception process only |
| Schema and migration | Executable dictionary, tenant-safe FKs, constraints/indexes/RLS/grants, migration/drift/rollback evidence | Data / Security | Tenant P0 non-waivable |
| Authorization | JWT contract, service policy and real PostgreSQL production-role negative matrix including pool/JIT behavior | Security / independent security approver | Non-waivable |
| API/event/concurrency | OpenAPI/event compatibility, idempotency, outbox/inbox, ordering/replay, stale/concurrent/property tests | Domain owner / Architecture | P0 effects non-waivable |
| Privacy/data rights | Documents 25/26 mapping, minimization, retention/hold/DSAR/deletion/transfer and breach evidence | DPO/Legal | Non-waivable for real data |
| Finance | Provider contract, tax/capability approval, balanced ledger, atomic entitlement, refund/reconcile/concurrency evidence | Finance/Data/Legal | Non-waivable before commerce |
| AI/content rights | Operation authorization, immutable provenance/evaluation, human-only publication, removal/reconcile proof | Legal/Content/AI/QA | Non-waivable before AI |
| Security/supply chain | Threat/ASVS mapping, secrets/dependencies/licenses/SAST/container/SBOM/provenance and no unresolved critical finding | Security / independent approver | Critical non-waivable |
| Accessibility/localization | WCAG 2.2 AA automated + manual evidence, locale/timezone/RTL tests and approved exceptions | Product/QA / Accessibility owner | A/AA failure needs formal release block/approved remediation; P0 journeys non-waivable |
| Performance/recovery | Approved docs 27/28, load/fault/restore results, SLO/headroom/cost, dashboards/alerts/runbooks | SRE/Product/Finance | Recovery/core capacity non-waivable |
| Operations/release | Deploy/rollback-or-roll-forward, smoke, monitoring, incident/on-call, feature kill/disable and evidence manifest | SRE / Release approver | Normal exception process only |
| Traceability/docs | Code/migration/API/test/dashboard/runbook/source/ADR/CHG links updated and implementation re-audited | Documentation owner / Architecture | Cannot declare plan finalized without it |

## Controlled exceptions

An exception records gate, scope, reason, evidence, compensating control, residual risk, accountable owner, independent approver, issue link, start/expiry and automatic disable/review trigger. It cannot silently become permanent. P0 cross-tenant isolation, payment integrity, AI provenance/rights/human publication, required recovery, active blocking questions and critical security findings cannot be waived for launch.

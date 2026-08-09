# LMS Documentation Guide

Status: **approved documentation baseline; not production-ready and not a finalized implementation plan**

Last documentation decision update: 2026-08-02
Last consistency reconciliation: 2026-08-03

This directory is the current LMS planning baseline. It describes approved direction, gated future designs, and the evidence required before implementation or production. It does not prove that code, migrations, infrastructure, provider contracts, tests, capacity, privacy approvals, or recovery exercises exist.

## Authority and conflict rules

Use the following order when interpreting the documents:

1. [Product capability boundary](plan/00-product-vision.md) decides what may be built or enabled for the initial MVP.
2. The external [decision register](../../docs/final-review/16-DECISION-REGISTER.md) and [readiness checklist](../../docs/final-review/17-FINAL-READINESS-CHECKLIST.md) record confirmed, deferred, rejected and open decisions. An open or blocked gate is never silently resolved.
3. [Accepted ADRs](adr/README.md) govern architectural choices within the approved capability boundary.
4. Architecture, domain, schema, security, privacy and operational plans define implementation constraints.
5. Feature documents define behavior only for an enabled capability; a detailed deferred design is not authorization to scaffold, expose or configure it.
6. The [source register](plan/SOURCES.md) supports dated external claims. The separate Supabase production guide is advisory and must be adapted through the LMS API-first and Django-migration boundaries.

If documents conflict, apply the most restrictive active safety, privacy, tenant-isolation, financial, rights, recovery or capability gate and record the conflict. Do not choose a convenient interpretation.

## Current scope

The approved initial product is a private-institution LMS with manually administered contracts and entitlements:

- authentication, tenant membership, roles and audit;
- manual immutable course authoring, human review and publication;
- enrollment, course delivery, progress and basic quizzes; and
- the minimum operational, security, accessibility and recovery foundation required for those flows.

The concise implementation-facing product contract is now
[`docs/product/spec.md`](product/spec.md), with the dependency-ordered feature inventory
in [`docs/product/features.md`](product/features.md). The project-owner priority makes
PDF upload-to-course generation the focused MVP journey; detailed plan sections remain
the safety and architecture authority for that enabled journey.

Paid commerce, recurring billing, marketplace payouts, and RAG/chat remain disabled.
Source-document processing and structured course generation are enabled only for the
focused PDF-to-course MVP described above. They must still satisfy the applicable
rights, privacy, provider, security, recovery, and human-publication gates before real
data or production activation.

## Blocking state

The following decisions remain open because the repository cannot invent owners, measurements, provider selections or evidence:

| Decision | Missing input/evidence | Effect |
|---|---|---|
| D-023 | Singapore-capable persistent worker benchmark/provider | Worker-dependent capabilities stay disabled. |
| D-024 | Approved orchestration/wake-up transport and regional transfer | QStash or an alternative cannot be deployed for protected payloads. |
| D-040 | Accepted-upload object RPO and funded restore proof | Production recovery is not approved. |
| D-041 | Numeric workload, capacity, storage and budget envelope | Procurement/load acceptance is blocked. |
| D-042 | Named privacy/legal owners, exact retention matrix, data-flow/DPIA and transfer approval | Real personal data is prohibited; synthetic/local data only. |
| D-050 | Executable P0 closure and implementation evidence | Overall state remains `not_ready`. |

The owner-input specifications are [retention/legal hold](plan/25-data-retention-legal-hold-specification.md), [privacy/DPIA](plan/26-privacy-accountability-dpia-specification.md), [capacity/workload](plan/27-capacity-workload-specification.md), and [storage/recovery sizing](plan/28-storage-recovery-sizing-specification.md).

## Documentation map

### Product contract and delivery setup

| Document | Purpose |
|---|---|
| [Product specification](product/spec.md) | Concise PDF-to-course MVP outcome, scope, users, journey, and non-goals |
| [Feature inventory](product/features.md) | Dependency order and four parallel implementation lanes |
| [Product decisions](product/decisions.md) | Current owner-approved scope and workflow decisions |
| [Open product questions](product/open-questions.md) | Questions that gate later feature or production steps |
| [Feature workspace](features/README.md) | Optional durable feature-package template |
| [Delivery workflows](workflows/README.md) | Four-agent worktree and GitHub CLI lifecycle |

### Product, architecture, and engineering boundaries

| Document | Purpose |
|---|---|
| [00 — Product vision and capability matrix](plan/00-product-vision.md) | Initial MVP, deferred capabilities, personas and product/legal baseline |
| [01 — Architecture overview](plan/01-architecture-overview.md) | Components, trust boundaries, authority and request/async flows |
| [02 — Technology stack](plan/02-tech-stack.md) | Technology ownership, provider admission and dependency policy |
| [03 — Repository layout](plan/03-monorepo-folder-structure.md) | Proposed scaffold, artifact ownership and folder acceptance |
| [04 — Domain and transaction design](plan/04-domain-module-design.md) | Module dependencies, execution context, unit of work, outbox and sagas |
| [19 — Coding standards](plan/19-coding-standards.md) | Language, SQL, dependency and review rules |

### Data, identity, security, and contracts

| Document | Purpose |
|---|---|
| [05 — Database schema plan](plan/05-database-schema-plan.md) | Scope catalog and mandatory executable dictionary/invariants |
| [11 — API and event contracts](plan/11-api-and-event-contracts.md) | HTTP/JWT/event/webhook/idempotency contract |
| [12 — Security and multitenancy](plan/12-security-and-multitenancy.md) | Threat controls, roles, RLS, privileged access and negative tests |
| [22 — Environment variables](plan/22-environment-variables.md) | Public configuration, component secrets and rotation ownership |
| [25 — Retention and legal hold](plan/25-data-retention-legal-hold-specification.md) | Blocking system/field retention and deletion matrix |
| [26 — Privacy and DPIA](plan/26-privacy-accountability-dpia-specification.md) | Blocking accountability, processing, transfer and incident artifacts |

### Product workflows and integrations

| Document | Purpose |
|---|---|
| [07 — Manual course authoring](plan/07-manual-course-authoring.md) | Canonical immutable review/publication workflow |
| [08 — Document ingestion](plan/08-book-ingestion-pipeline.md) | Deferred rights-gated upload, quarantine, extraction and takedown |
| [09 — AI course generation](plan/09-ai-course-generation.md) | Deferred run/evaluation/human-canonicalization workflow |
| [10 — AI companion and RAG](plan/10-ai-chat-companion-rag.md) | Deferred authorized retrieval, course-only answers and citations |
| [17 — Payments, email and integrations](plan/17-payments-emails-integrations.md) | Active email direction and deferred finance/provider contracts |
| [18 — Localization and accessibility](plan/18-localization-accessibility.md) | Locale, RTL, time-zone and WCAG 2.2 AA requirements |

### Delivery, operations, and evidence gates

| Document | Purpose |
|---|---|
| [13 — Performance and availability](plan/13-performance-scalability-availability.md) | SLO direction, cache/replica rules and recovery boundaries |
| [14 — Deployment and environments](plan/14-deployment-and-environments.md) | Environment isolation, regions, workers, domains and migrations |
| [15 — Testing and quality](plan/15-testing-quality-gates.md) | Required suites and non-waivable release evidence |
| [16 — Observability and analytics](plan/16-observability-analytics.md) | Privacy-minimized telemetry, SLIs, alerts and analytics gate |
| [20 — Implementation roadmap](plan/20-implementation-roadmap.md) | Gated phases and capability/evidence traceability |
| [21 — Risk register](plan/21-risk-register.md) | Managed risks, owners, triggers and acceptance state |
| [23 — Definition of done](plan/23-definition-of-done.md) | Risk-based feature/release completion rules |
| [24 — Agent execution guide](plan/24-agent-execution-guide.md) | Mandatory context, stop conditions and completion report |
| [27 — Capacity and workload](plan/27-capacity-workload-specification.md) | Blocking numeric workload, service-envelope and budget inputs |
| [28 — Storage and recovery sizing](plan/28-storage-recovery-sizing-specification.md) | Blocking storage, egress, backup and restore inputs |
| [Official source register](plan/SOURCES.md) | Dated claim, limitation, recheck and owner register |
| [Runbook catalog](runbooks/README.md) | Required incident/recovery procedures, format and safety rules |
| [Evidence index](evidence/README.md) | Evidence schema, artifact rules and explicit pre-implementation state |
| [Delivery workflows](workflows/README.md) | Repository-specific four-agent, worktree, GitHub issue/PR, review and merge workflow |

AI relational entities are detailed in [06 — AI schema extension](plan/06-ai-schema-extension.md). All architecture decisions and their lifecycle are indexed in the [ADR guide](adr/README.md).

## Reading order

For implementation work:

1. this guide and the product capability boundary;
2. decision register/readiness state and relevant ADRs;
3. architecture plus domain/transaction design;
4. complete relevant data dictionary, constraints, roles/RLS and retention/privacy inputs;
5. the feature workflow and API/event contract;
6. security/threat requirements;
7. deployment, observability, testing, risk and definition-of-done evidence; and
8. repository/coding standards and current official-source claims.

AI agents additionally follow [the execution guide](plan/24-agent-execution-guide.md) and must state applicable decision, invariant/test, capability and evidence IDs before editing implementation.

## Status vocabulary

| Status | Meaning |
|---|---|
| `accepted` / `confirmed` | Direction is approved; implementation and evidence may still be absent. |
| `planned` | Intended work with no proof of implementation. |
| `open` / `blocked` | Required fact, owner, selection or evidence is missing; dependent work stops. |
| `deferred` | Outside current scope and disabled until a future gate closes. |
| `rejected` | Must not be implemented unless a superseding decision is approved. |
| `implemented` | Reserved for a linked code/migration/configuration artifact; prose alone cannot claim it. |
| `verified` | Reserved for a linked immutable test/deploy/provider/recovery result. |

## Ownership and maintenance

| Area | Accountable role | Review trigger/cadence |
|---|---|---|
| Product scope and roadmap | Product | Every phase/scope change |
| Architecture/domain/API | Architecture + domain owners | Every boundary/authority/contract change |
| Schema, roles, migrations and RLS | Data + Security | Every migration and production-role change |
| Privacy, retention, rights and transfers | DPO/Legal/Content Rights | Before real data/provider enablement and on legal/vendor change |
| Capacity, SLO, deployment and recovery | SRE/Platform/Finance | Before tier procurement/release and after measured threshold/drill |
| AI evaluation/provider behavior | Product/Content/AI/QA/DPO | Before AI enablement and every model/prompt/policy change |
| Commerce/tax/ledger | Finance/Legal/Data/Security | Before any paid capability and every provider/tax change |
| Accessibility | Product/QA/Accessibility owner | Every major UI flow and release |
| Source register | Documentation + named domain owner | Monthly for capability-sensitive claims and before affected implementation/release |

Named individuals, approval dates and immutable evidence links remain mandatory where documents 21 and 25–28 require them. A role label in this guide is not that approval.

## Historical and external material

- [`docs/final-review`](../../docs/final-review/00-REVIEW-INDEX.md) is the audit and decision evidence that produced this correction pass. Most review findings describe the pre-correction source and remain historical unless the readiness checklist says otherwise.
- [`setup-guide-docs/supabase-prod-guide`](../../setup-guide-docs/supabase-prod-guide/docs/supabase-production-guide/README.md) remains a separate reference. Adopt its security/testing principles, but the LMS uses API-first core access and Django-only application migrations.
- Do not rename/merge this current set into the proposed finalized outline while D-050 is open. When finalization is authorized, preserve history, update every link/manifest entry atomically, and archive superseded drafts rather than deleting them.

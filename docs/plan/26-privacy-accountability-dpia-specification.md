# Privacy Accountability and DPIA Specification

Status: **BLOCKED_INPUT**  
Decision authority: D-042; Q-13 approved direction  
Change IDs: CHG-027, CHG-028, CHG-029, CHG-045

The initial MVP excludes minors and uses a private-institution model. The controller/processor allocation, named privacy/legal owners, lawful bases, DPIA, breach decision path, and provider-transfer approvals remain organization-specific blockers. No real personal data may enter a non-local environment until the mandatory fields and approvals below are complete.

## Named accountability

| Role | Required named person/entity | Responsibility | Current state |
|---|---|---|---|
| Product entity / contracting party | `TBD-BLOCKING` | Identifies the service provider and contracting entity | missing |
| Personal information controller(s) | `TBD-BLOCKING per launch customer model` | Determines purposes/means and DSAR decisions | missing |
| Personal information processor(s) | `TBD-BLOCKING` | Operates only under documented instructions | missing |
| Data protection officer/privacy lead | `TBD-BLOCKING: name, title, contact` | DPIA, DSAR, transfer and breach governance | missing |
| Legal/counsel owner | `TBD-BLOCKING: name and contact` | Lawful basis, contracts, retention and notification advice | missing |
| Incident decision-maker | `TBD-BLOCKING: primary and alternate` | Classifies incidents and authorizes notices | missing |
| Security owner | `TBD-BLOCKING` | Technical safeguards and evidence | missing |
| Records/retention owner | `TBD-BLOCKING` | Owns document 25 | missing |
| Accessibility owner | `TBD-BLOCKING` | WCAG 2.2 AA evidence and exceptions | missing |

## Approved scope constraints

- Users known or reasonably believed to be minors are not supported in the initial MVP.
- Registration and tenant contracts must state the age/eligibility boundary; enforcement and exception handling require tests.
- Public marketplace, paid commerce, instructor payouts, external AI/OCR processing,
  general-purpose chat, session replay, and analytics autocapture are disabled. Local
  focused-MVP contract work may use synthetic or explicitly rights-cleared fixtures;
  this is not approval for provider transfer or real customer content.
- The initial data plane target is Singapore. A region choice does not itself approve any transfer or subprocessor.
- Support has no standing tenant-data access; document 12's AAL2 JIT grant is mandatory.

## Controller/processor and lawful-basis inventory

Complete one row for every enabled purpose before processing begins.

| Processing purpose | Data subjects and fields | Controller | Processor/subprocessor | Lawful basis/instruction | Necessity/proportionality | Subject notice/choice | Retention link | Status |
|---|---|---|---|---|---|---|---|---|
| Identity, invitations, authentication | `TBD-BLOCKING` | `TBD-BLOCKING` | Supabase + `TBD` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | blocked |
| Tenant membership and authorization | `TBD-BLOCKING` | `TBD-BLOCKING` | LMS/Supabase | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | blocked |
| Course delivery and progress | `TBD-BLOCKING` | `TBD-BLOCKING` | LMS providers | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | blocked |
| Support and security operations | `TBD-BLOCKING` | `TBD-BLOCKING` | Sentry/email + `TBD` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | blocked |
| Minimal product analytics | `TBD-BLOCKING event allowlist` | `TBD-BLOCKING` | PostHog only if approved | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | blocked |
| Paid commerce | Deferred | `TBD before enablement` | PayMongo | `TBD` | `TBD` | `TBD` | Document 25 | deferred |
| PDF source ingestion and structured course generation | `TBD-BLOCKING before real data` | `TBD-BLOCKING` | Storage/OCR/model providers unselected | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | blocked for real data/provider use; local fixtures only |
| AI companion/RAG/vector retrieval | Deferred | `TBD before enablement` | Provider not selected | `TBD` | `TBD` | `TBD` | Document 25 | deferred |

## Data-flow and transfer register

| Flow | Data classes | Origin → processing/storage region | Provider and subprocessors | Contract/DPA/transfer mechanism | Training/secondary use | Deletion/return | Approval | Status |
|---|---|---|---|---|---|---|---|---|
| Browser/Next.js → API/PostgreSQL/Auth/Storage | `TBD-BLOCKING` | User location → Singapore target | Vercel/Supabase exact plans `TBD` | `TBD-BLOCKING` | prohibited | Document 25 | DPO/customer `TBD` | blocked |
| API/worker → telemetry | Metadata allowlist only | Singapore → provider region `TBD` | Sentry/PostHog exact projects `TBD` | `TBD-BLOCKING` | prohibited | Document 25 | DPO `TBD` | blocked |
| API/worker → email | Minimum recipient/template facts | Singapore → Resend region `TBD` | Resend + subprocessors `TBD` | `TBD-BLOCKING` | prohibited | Document 25 | DPO `TBD` | blocked |
| QStash control-plane wake-up | No source, learner, chat, grade, payment, or secret payload | Singapore → US/EU if selected | Upstash `TBD` | `TBD-BLOCKING` | prohibited | short control retention `TBD` | DPO/customer `TBD` | blocked |
| AI/OCR processing for focused PDF-to-course | Disabled for external/real-data transfer | No transfer | Provider/model unselected | Required before enablement | provider training prohibited | Required | DPO/legal/customer | blocked; local fixtures only |
| Vector/RAG processing | Disabled | No transfer | Provider/model unselected | Required before enablement | provider training prohibited | Required | DPO/legal/customer | deferred |
| Backup/DR | `TBD-BLOCKING` | Singapore → approved DR region `TBD` | Backup provider `TBD` | `TBD-BLOCKING` | prohibited | Document 25 | DPO/customer `TBD` | blocked |

## DPIA work product

The signed DPIA must include:

1. processing description, data-flow diagram, purposes, lawful bases and contractual roles;
2. necessity and proportionality for each field, event, log, provider call and retention period;
3. threats to confidentiality, integrity, availability, tenant isolation, learner rights, licensed content, automated decisions and vulnerable users;
4. likelihood/impact scoring before and after controls, with accountable control owners and evidence;
5. DSAR, correction, deletion, objection, portability where applicable, legal hold, breach and complaint workflows;
6. transfer/subprocessor analysis for each exact provider, plan, region and disaster-recovery path;
7. a conclusion of approved, approved with dated actions, or rejected, signed by the DPO/privacy owner and accountable executive.

## Breach decision and notification procedure

- Security triage creates a timestamped incident record, affected systems/tenants/subjects, data classes, evidence-preservation scope, containment owner and decision deadline.
- The named DPO and legal owner determine whether notification duties apply. The system must support the applicable 72-hour decision/notification window without treating this document as legal advice.
- Customer, regulator, and affected-person notices require approved content, delivery evidence, and an immutable decision log.
- Every exercise records detection-to-decision time, missing contacts/evidence, corrective actions, owners and due dates.

## Approval gate

This document becomes `approved` only after every `TBD-BLOCKING` is completed, the data-flow diagram and signed DPIA are linked, exact provider transfers are approved, document 25 is approved, and a DSAR plus breach-tabletop exercise supplies evidence. Until then, only synthetic/local data may be used.

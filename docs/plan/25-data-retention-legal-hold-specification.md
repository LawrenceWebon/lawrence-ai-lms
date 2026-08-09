# Data Retention, Deletion, and Legal-Hold Specification

Status: **BLOCKED_INPUT**  
Decision authority: D-042; Q-12 approved direction  
Change IDs: CHG-010, CHG-025, CHG-027, CHG-043, CHG-045

This document is the required system-and-field retention matrix for the LMS. The minimization, deletion-propagation, legal-hold, and backup-expiry direction is approved. Exact periods are intentionally not invented. Production personal data must not be admitted until every `TBD-BLOCKING` value has a named accountable owner, legal basis, approval date, and evidence link.

## Accountable approvals

| Approval | Accountable person | Required evidence | Current state |
|---|---|---|---|
| Data-protection owner | `TBD-BLOCKING: Lawrence` | Written appointment and contact route | missing |
| Legal/counsel owner | `TBD-BLOCKING: Lawrence` | Approved retention/legal-hold opinion | missing |
| Records owner | `TBD-BLOCKING: Lawrence` | Signed field/system matrix | missing |
| Security-log owner | `TBD-BLOCKING: Lawrence` | Approved security-event retention | missing |
| Finance/tax owner | Not applicable to initial MVP | Required before paid commerce | deferred |
| Final approver | `TBD-BLOCKING: Lawrence` | Dated approval record | missing |

## Mandatory retention matrix

Every row must be completed at field or immutable-record-family level. A service default, vendor maximum, or engineering preference is not legal approval.

| Data family | Authoritative system | Purpose and lawful basis | Active-use retention | Post-closure retention | Deletion/anonymization action | Legal-hold behavior | Backup expiry | Downstream deletion targets | Owner | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| Identity and authentication linkage | Supabase Auth + PostgreSQL | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Disable identity; delete or retain minimum linkage as approved | Suspend deletion while scoped hold is active | `TBD-BLOCKING` | Auth replicas, logs, support systems | `TBD-BLOCKING` | blocked |
| Tenant membership, roles, invitations, JIT grants | PostgreSQL | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Revoke immediately; delete/anonymize approved history | Preserve only held records and access evidence | `TBD-BLOCKING` | Cache, audit export | `TBD-BLOCKING` | blocked |
| Enrollment, progress, attempts, assignments | PostgreSQL + Storage | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Delete/anonymize learner content while preserving approved aggregate facts | Hold by tenant, subject, course, and matter ID | `TBD-BLOCKING` | Objects, search, analytics, exports | `TBD-BLOCKING` | blocked |
| Grades, certificates, credential evidence | PostgreSQL + Storage | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Preserve only mandated credential facts; separate optional content | Immutable hold marker and access audit | `TBD-BLOCKING` | Certificate files, exports | `TBD-BLOCKING` | blocked |
| Course content and licensed assets | PostgreSQL + Storage | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Withdraw, delete, or retain according to rights and enrollment policy | Rights hold is distinct from litigation hold | `TBD-BLOCKING` | CDN/cache, object backup | `TBD-BLOCKING` | blocked |
| Source documents, OCR, chunks, vectors, citations | PostgreSQL + Storage + Pinecone | AI disabled in initial MVP; Q-06 approval required before use | `TBD-BLOCKING` | `TBD-BLOCKING` | Block synchronously; traverse lineage; delete/rebuild/reconcile | Preserve only counsel-authorized evidence | `TBD-BLOCKING` | Pinecone, caches, provider copies | `TBD-BLOCKING` | conditional blocker |
| AI prompts, run snapshots, outputs, chat | PostgreSQL + approved providers | AI disabled in initial MVP | `TBD-BLOCKING` | `TBD-BLOCKING` | Delete content and provider copies; preserve minimal approved audit facts | Matter-scoped hold with access restriction | `TBD-BLOCKING` | Model/OCR providers, telemetry | `TBD-BLOCKING` | conditional blocker |
| Support tickets and attachments | PostgreSQL + Storage | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Delete/redact content; retain minimum service evidence | Hold attachments independently | `TBD-BLOCKING` | Email, Sentry, exports | `TBD-BLOCKING` | blocked |
| Security and privileged-access events | Audit schema + security telemetry | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Immutable for approved period; restrict rather than silently mutate | Preserve integrity hash and hold scope | `TBD-BLOCKING` | Sentry/log archive | `TBD-BLOCKING` | blocked |
| Product analytics | Approved server-side allowlist only | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Delete pseudonymous subject/tenant mapping and provider profile | No replay/content capture by default | `TBD-BLOCKING` | PostHog | `TBD-BLOCKING` | blocked |
| Payment, invoice, tax, ledger | Not used in initial MVP | Required before paid commerce | `TBD-BLOCKING` | `TBD-BLOCKING` | Preserve statutory facts; delete optional metadata | Finance/legal hold | `TBD-BLOCKING` | PayMongo, email, exports | `TBD-BLOCKING` | deferred |
| Database and object backups | Independent backup stores | Recovery | Rolling windows derived from approved RPO/RTO | `TBD-BLOCKING` | Cryptographic expiry or scheduled deletion; restored data immediately re-enters deletion queue | Hold copies must be segregated and access-controlled | `TBD-BLOCKING` | DR copies | `TBD-BLOCKING` | blocked |

## Deletion and anonymization contract

1. A deletion request creates an immutable request, scope, legal-basis decision, owner, deadline, and correlation ID.
2. The coordinator enumerates PostgreSQL rows, Auth identity, Storage objects, cached values, analytics profiles/events, vector generations, provider copies, exports, and backup-expiry obligations.
3. Each target records `pending`, `blocked_by_hold`, `deleted`, `anonymized`, `not_found`, `provider_pending`, or `failed` with attempt evidence.
4. Restores replay the deletion/tombstone journal before the environment can serve traffic.
5. Completion requires reconciliation by stable identifiers and counts; a successful API response alone is insufficient.
6. Aggregate analytics may survive only when the approved owner demonstrates that re-identification is not reasonably possible.

## Legal-hold contract

- A hold has `hold_id`, matter/reference, authority, scope, custodian/data subjects, systems, start, review date, approver, and release approval.
- A hold prevents only covered destructive actions; it does not grant broader access or silently extend unrelated data.
- Conflicting deletion requests remain visible with reason and next review date.
- Hold access is least-privilege, audited, and separate from normal support access.
- Releasing a hold resumes the ordinary deletion clock and queued deletion work.

## Release evidence

This specification moves to `approved` only when the matrix has no `TBD-BLOCKING`, the owners above sign it, DSAR/deletion and legal-hold tests pass across every enabled provider, backup expiry is demonstrated, and links to the test run and approval record are added here.


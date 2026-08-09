# Security, Privacy, and Multi-Tenancy

Status: **approved control design; migrations, role grants, tests and owner evidence pending**  
Change IDs: CHG-004, CHG-006, CHG-027

## Security baseline

Use OWASP ASVS 5.0.0 as the verification baseline and maintain a versioned abuse-case/threat model. Phase 0 maps applicable ASVS requirement IDs and every threat/control below to an owning implementation and test; a generic checklist is not verification evidence.

## Threat model and trust inventory

| Actor/event | Protected objective | Representative abuse | Primary controls/evidence |
|---|---|---|---|
| Unauthenticated attacker | Accounts, uploads, API availability | Credential stuffing, reset enumeration, malicious upload, denial of wallet | Neutral auth responses, MFA for privileged actors, rate/bot controls, signed upload admission, budgets and alerts |
| Malicious learner | Other tenants/courses, assessments, grades/certificates | IDOR, forged tenant selector, answer scraping, progress/grade tampering | Complete mediation, composite tenant FKs, production-role RLS, immutable attempts, server scoring and relationship tests |
| Malicious tenant instructor/admin | Other tenants or unauthorized learner/finance data | Role confusion, cross-tenant edges, self-approval, unsafe export | Scoped RBAC/ABAC, reviewer separation, JIT export, same-tenant constraints and audit |
| Compromised support/platform operator | Broad tenant data | Standing superuser, hidden impersonation or export | AAL2 JIT grants, scope/approval/expiry, dual control, break-glass review and immutable events |
| Compromised API/worker credential | Database/provider authority | Owner/bypass use, lateral movement, cross-tenant batch | Per-component roles/secrets, no owner/`BYPASSRLS`, transaction context, least grants, rotation and anomaly alerts |
| Malicious source/object | Worker/model/data plane | Malware, polyglot/archive bomb, parser exploit, prompt injection | Private quarantine, byte-derived validation, scan/sandbox/budgets, untrusted-data separation and adversarial tests |
| Forged/replayed provider event | Entitlements, money, messages or jobs | Signature bypass, duplicate/reordered event | Exact raw-body verification, freshness, unique inbox/body hash, state reducer and reconciliation |
| Poisoned AI corpus/question | Rights, tenant data, model behavior/cost | Indirect injection, retrieval poisoning, exfiltration, denial of wallet | Operation rights, tenant/version filters, DB reauthorization, no tools, output/citation validation and budgets |
| Supply-chain/build compromise | Code, artifacts, secrets, migrations | Dependency/action/image tampering or malicious migration | Lockfiles, pinned actions, SBOM/provenance, scans, review and least-privilege CI/migrator |
| Operator/vendor failure | Availability and integrity | Bad migration, region/object loss, stale vector, missed webhook | Expand/contract, independent backup/restore, manifests, reconciliation, kill switches and exercises |

Required trust/data-flow boundaries are maintained in documents 01, 14 and 26. A new route, runtime role, provider, object class, cross-region transfer, browser data path, privileged action or model tool updates this table and the corresponding negative tests before enablement.

## Tenant isolation

Every tenant-owned record contains `tenant_id`. Every request validates:

1. Authenticated user
2. Active tenant
3. Active membership
4. Role and permission
5. Scope
6. Resource tenant ownership

Use both application policies and PostgreSQL RLS.

## Authentication

- Supabase Auth with email verification.
- MFA required for platform administrators and tenant owners.
- Shorter privileged-session lifetime.
- Session revocation and sign-out-all-devices.
- Rate-limit login, reset, invitation, and OTP endpoints.
- Never use user-editable metadata as authoritative permissions.

## Database roles

Separate:

- Migration role
- Runtime API role
- Worker role
- Read-only analytics role
- Emergency administrative role

Normal runtime roles must not own tables or bypass RLS.

### Role and connection matrix (CHG-004)

| Role | Connection mode | Permitted capability | Prohibited capability | RLS posture |
|---|---|---|---|---|
| Object owner (no login) | none at runtime | Own schemas/tables/functions | Application traffic or staff login | Owner; use a separate non-login identity |
| Migrator | direct one-off job | Django migration DDL/RLS/grants/helpers under deployment approval | Web/API/worker traffic | Elevated only for migration window |
| API | approved persistent session pool or transaction pool for temporary/serverless clients | Explicit CRUD/execute grants needed by core services | Ownership, DDL, `BYPASSRLS`, arbitrary schemas | Non-owner; RLS enforced and forced on tenant-owned tables |
| Worker | approved persistent connection mode | Explicit job/domain grants scoped to enabled stages | Standing cross-tenant scans, owner credentials | Non-owner; same tenant context/RLS contract |
| Reconciler | persistent scheduled process | Narrow inbox/outbox/object/vector reconciliation selectors/commands | General support or product queries | Non-owner; explicit service scope and audited batches |
| Analytics reader | read-only connection | Approved views/aggregates only | Raw content, grades, chat, finance, cross-tenant identifiers | RLS/security-invoker views + scoped grants |
| JIT support | API-mediated only | Time/resource/action grant described below | Direct DB role, shared impersonation, standing tenant access | RLS + grant ID context |
| Break-glass | isolated emergency path | Incident-scoped action after approved activation | Routine operations | Time-bound credential, dual approval and review |

All grants are allowlisted and default privileges revoked. Runtime roles cannot `SET ROLE` to owner/migrator, create extensions, alter policies, change context helpers, or call unrestricted security-definer functions.

Tenant-owned application tables use `ENABLE ROW LEVEL SECURITY` plus `FORCE ROW LEVEL SECURITY`. Global reference tables are explicitly inventoried and least-granted. An exception requires a P0 security record, compensating isolation, negative tests and expiry; table ownership or `BYPASSRLS` is never granted to make a runtime flow work.

### Transaction-local authorization context

- Validate actor, tenant, request and optional grant IDs as UUIDs before setting them.
- Begin one transaction on one connection, use `set_config(..., true)`/`SET LOCAL`, re-read active membership/entitlement/resource ownership, then execute domain/audit/outbox work on that same connection.
- Missing actor/tenant context returns no tenant rows and rejects tenant writes. An invalid/mismatched context is an authorization failure, not a fallback to platform scope.
- Pool checkout/return tests prove transaction rollback/reset removes context; session-level tenant settings are forbidden.
- Workers set context per claimed job transaction and re-read job tenant/scope; a payload tenant ID alone is never authority.
- Policy helpers use fixed safe `search_path`, reviewed owner, explicit arguments where practical, and no public execution.

### Privileged tenant access (CHG-006)

There is no standing support/platform access to tenant data and no shared impersonation token.

1. Operator authenticates at AAL2 with a short privileged session.
2. A request names tenant, resource set, read/write/export/finance action scope, ticket, reason, duration and expected customer/legal notice.
3. An authorized approver issues a short-lived, revocable grant; export, financial action and other high-risk scopes require dual approval.
4. API and RLS require the active grant ID and enforce actor/tenant/resource/action/expiry on every request.
5. Start, each access/change/export, denial, extension, revocation and expiry produce immutable security events with request/correlation IDs.
6. The UI shows privileged mode and prevents silent background reuse. Grant expiry terminates access even if a browser session remains.
7. Break-glass activation is incident-only, separately credentialed, immediately alerted, and reviewed after use with customer/legal notice according to document 26.

Required tables include `privileged_access_requests`, `privileged_access_approvals`, `privileged_access_grants`, `privileged_access_events` and immutable export manifests, all tenant-safe where applicable.

## Storage security

Buckets:

```text
quarantine-private
source-documents-private
course-assets-private
public-course-media
assignment-submissions-private
certificates-private
exports-private
```

- Use signed URLs.
- Generate opaque tenant/purpose/object keys server-side and authorize them through the PostgreSQL object inventory; do not trust a caller prefix.
- Derive checksum, byte length and MIME/magic type from quarantined bytes and reconcile object↔database state.
- Scan and sandbox-parse untrusted files under decompression/page/pixel/CPU/memory/network limits before marking them trusted.
- Never expose owner, legacy service-role or per-component secret credentials.

## Edge and API protection

- Cloudflare DNSSEC.
- Cloudflare WAF and edge rate limits where plan and topology permit.
- Upstash tenant and user rate limits for authenticated operations.
- Strict CORS allowlist.
- Content Security Policy.
- Secure, HttpOnly, SameSite cookies.
- CSRF protection for cookie-authenticated mutations.
- Request size and upload limits.
- SSRF protection on external URLs.

## Payment security

- Never store raw card numbers or CVV.
- Use PayMongo-hosted or tokenized workflows.
- Verify webhook signatures.
- Verify amount, currency, order, and merchant context.
- Payment success redirects do not activate enrollment.
- All financial state changes are auditable and idempotent.

## AI-specific security

- Treat source documents as untrusted.
- Detect prompt injection in retrieved content.
- No arbitrary shell, network, database, or code tools for the companion.
- Tenant and course scope is resolved outside the model.
- Model output cannot change permissions or status directly.
- Structured output validation is required.
- AI drafts cannot publish themselves.
- Limit context and output sizes.
- Redact PII before provider calls when possible.
- Maintain provider data-retention configuration and agreements.

## Analytics and monitoring privacy

Do not send to PostHog or Sentry:

- Passwords or tokens
- Raw payment data
- Full books or lesson bodies
- Student assignment content
- Private chat content
- Sensitive profile data

Use approved provider-specific keyed pseudonyms only when correlation is necessary; internal opaque UUIDs remain linkable personal/tenant data. PostHog session replay is disabled, not merely masked, until a separate approval exists.

Opaque IDs remain personal data when linkable. PostHog autocapture and session replay are disabled initially; Sentry and any enabled analytics use a versioned field/event allowlist, pseudonymous correlation, explicit retention/deletion, role review and redaction canaries. Documents 25 and 26 are blocking authorities.

## Data governance (CHG-027)

- [Document 25](25-data-retention-legal-hold-specification.md) owns field/system retention, legal hold, deletion propagation and backup expiry.
- [Document 26](26-privacy-accountability-dpia-specification.md) owns named controller/processor/DPO/legal roles, lawful-basis inventory, DPIA, minors exclusion, breach decisions and transfer approvals.
- Only synthetic/local data is permitted until both documents are approved.
- Every schema field, event, log, object, provider payload and backup class maps to a purpose/basis, classification, access owner, region/subprocessor, retention and DSAR/deletion action.
- A feature is blocked if that mapping or accountable owner is missing.

## Audit events

Record events only for enabled domains; deferred event types become active with their feature gate and retention/privacy mapping.

Record:

- Role and permission changes
- Tenant suspension
- Course publication
- AI source upload and rights declaration
- AI artifact approval or rejection
- Grade changes
- Certificate issue and revoke
- Refund and payout approval
- Administrator impersonation
- API-key creation and revocation
- Security configuration changes

## Required security tests

- Cross-tenant API matrix
- RLS policy tests
- Storage path traversal tests
- IDOR tests
- Privilege escalation tests
- Webhook replay tests
- Upload polyglot and MIME mismatch tests
- Prompt-injection and citation-forgery tests
- Secret scanning
- Dependency and container scanning
- Production-role matrix across API, worker, reconciler, analytics and JIT support; owner/migrator connections are forbidden in these tests
- Missing/malformed/stale transaction context and connection-pool reset/leakage tests
- Composite same-tenant FK tests for insert/update/delete and guessed cross-tenant IDs
- JIT request/approval/scope/expiry/revocation, dual-approval, break-glass and immutable event tests
- Wrong-project JWT, disallowed algorithm/key, stale membership and revoked-session tests
- Data API disabled/minimal-schema grants and security-invoker view tests
- DSAR, deletion, legal-hold, restored-tombstone replay and breach-tabletop evidence from documents 25/26
- ASVS requirement-to-control/test traceability and abuse cases for every actor/boundary above

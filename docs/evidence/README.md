# Implementation and Release Evidence Index

Status: **local implementation evidence exists; no production or release evidence exists**

Documentation states intended controls. Evidence demonstrates that a specific code, migration, configuration, provider contract, environment and test run implemented those controls. No document may label a capability `implemented`, `verified`, production-ready or finalized solely because a plan section exists.

## Evidence record

Phase 0 creates a machine-readable evidence manifest. Each entry contains:

| Field | Requirement |
|---|---|
| Evidence ID/type | Stable ID and class: build, migration, contract, test, security, privacy, capacity, deploy, recovery, incident or approval |
| Scope | Capability/domain, decision/risk/CHG/invariant/test IDs and affected environment |
| Source identity | Repository revision, dirty-state policy, build/image/migration/config/provider fixture versions |
| Reproduction | Exact command/workflow, inputs/profile/seed and expected pass criteria |
| Result | Passed/failed/blocked/not-applicable with timestamps, measured values and discrepancies |
| Artifact | Immutable CI/artifact-store URL plus SHA-256/attestation; repository path only for small non-sensitive records |
| Producer | Automation or accountable operator identity and execution environment |
| Owner/approver | Accountable owner and independent approver where the gate requires it |
| Freshness | Created, valid-through/review trigger and superseding evidence ID |
| Classification | Public/internal/confidential/restricted, retention and deletion/legal-hold mapping |

`not_applicable` requires evidence that the capability, route, job, schema, credential, provider callback and UI are absent or hard-disabled. `blocked` is not converted to `passed` by an exception when the gate is non-waivable.

## Required evidence classes

| Class | Minimum artifacts |
|---|---|
| Build/supply chain | Reproducible locked install, lint/type/build, SBOM, provenance, dependency/license/secret/SAST/container scans |
| Schema/security | Django migration graph, generated dictionary/ERD/fingerprint, roles/grants/RLS source, drift result and production-role tenant/JIT/pool matrix |
| API/events/providers | OpenAPI/event schema diff, generated-client checksum, idempotency/concurrency results and sanitized live-sandbox contract fixtures |
| Product flows | Unit/integration/Playwright/accessibility evidence tied to acceptance criteria and exact enabled capability |
| Privacy/retention | Signed documents 25/26, processing/transfer inventory, DSAR/deletion/hold and breach-tabletop results |
| Performance/capacity | Approved documents 27/28, baseline/expected/3×/whale load results, correctness/headroom/cost and limit configuration |
| Deployment/operations | Environment/region/tier inventory, deploy/migration/smoke IDs, dashboards/alerts/on-call and feature-disable/rollback proof |
| Recovery/incidents | Independent DB/object restore, tombstone/reconcile/rebuild, achieved RPO/RTO and runbook exercise/post-incident records |
| Conditional finance/AI | Balanced-ledger/property/reconciliation evidence or rights/provenance/evaluation/human-publication/removal evidence before enablement |

## Storage and security rules

- Do not commit secrets, tokens, production personal data, raw provider payloads, books, chats, submissions, payment data or unrestricted logs as evidence.
- Store large/restricted artifacts in the approved immutable artifact system; commit only metadata, checksum, classification and access-controlled link.
- CI identities write automated records. Humans cannot hand-edit a failed result into a pass; supersede it with a new run.
- Artifact retention follows documents 25/26 and legal holds. Expiry/deletion must preserve required minimal audit linkage without retaining prohibited content.
- Every release manifest pins evidence to one source/deployment revision. Evidence from another environment/version is informative, not proof for the release.

## Current state

The repository contains the local synthetic backend path from F-001 through F-008.
The historical [F-003](f003-source-admission-implementation.md) and
[F-007](f007-learner-playback-implementation.md) records preserve the findings from
their original merged heads. PR #64 subsequently implemented issues #60–#62 together
with extraction, deterministic generation, human canonicalization, and backend
integration. It merged as `bebcc22d5ec475a52a124872838468d5cb897158` from exact head
`136326cd39f730b3d77feec866c142a432e15f29`; an independent post-merge audit found no
Critical, Error, or Warning findings. Issues #60–#62 are closed as absorbed.

The [backend MVP completion record](backend-mvp-completion.md) holds the exact local
verification and audit evidence. This is not release or production evidence:
deployment, external OCR/model/storage/queue providers, real/private data,
retention/recovery/privacy/capacity approval, provider-backed quality thresholds, and
production activation remain pending or blocked. Frontend theme purchase/design
planning is the next product task.

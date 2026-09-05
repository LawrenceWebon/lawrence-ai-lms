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

The repository now contains local F-001/F-002 code plus F-003 and F-007 implementation
candidates. The [F-003 local implementation record](f003-source-admission-implementation.md)
and [F-007 local implementation record](f007-learner-playback-implementation.md) pin
their application commits, synthetic inputs, migration/RLS results, API/client/build
checks, and browser regressions. They are local candidate evidence only: protected PR
checks, independent review, release, deployment, retention/recovery, provider, and
production gates remain pending or blocked. The
[F-003 planning review correction](f003-planning-review-correction.md) remains a
governance record rather than implementation or release evidence.

The [backend MVP completion record](backend-mvp-completion.md) tracks PR #64's
local extraction, generation, human canonicalization, and backend integration
candidate, including its outstanding PR #59 dependency and verification status.

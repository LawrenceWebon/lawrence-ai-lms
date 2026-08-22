# Readiness Audit — F-003 PDF Source Admission

Status: **READY FOR IMPLEMENTATION AFTER #51 REVIEW AND MERGE**

- [x] F-003 remains inside the focused PDF-to-course MVP and has no expanded source
  format, OCR, provider, or production scope.
- [x] Product outcome, actors, non-goals, authorization, tenant isolation, failure,
  cancellation, revocation, and privacy boundaries match the product specification.
- [x] P-013 closes Q-P03 for local-only F-003 with explicit bytes/pages/pixels/time/
  TTL/tenant quotas; the plan states it is not production capacity evidence.
- [x] Source declaration, reviewed operation-scoped `store` authorization, opaque
  quarantine intent, admission/removal states, DTOs, job envelopes, events, and
  deterministic synthetic fixtures are frozen.
- [x] The Documents module is the authority; Django owns migrations/RLS, FastAPI owns
  HTTP/OpenAPI, and adapters/workers call the shared service boundary.
- [x] No transaction spans storage, validation, removal, or other I/O; durable job,
  lease, checkpoint, idempotency, outbox, audit, and reconciliation behavior is explicit.
- [x] Contract, software, upload-security, RLS, removal, API/Admin, browser,
  accessibility, logging, and regression tests are planned with exact evidence gates.
- [x] One issue #43 has exclusive ownership of migrations, composition, OpenAPI/client,
  CI, web/E2E, event schemas, and manifest; no concurrent F-003 hotspot exists.
- [x] Production/real-data/provider/retention/recovery/privacy gates remain visible and
  are not marked passed.
- [x] Planning issue #42 merged in PR #44 at exact planning head
  `62a7c5af0a9f209da70d724ae506336d35c3ff86` and merge commit
  `83a0c487ff782192d4c18e08cfebd86eb4cf626f`.
- [x] PR #44's missing pre-merge review record is treated as a temporal governance
  defect, not as evidence that the required approval occurred.
- [x] An independent post-merge audit of the exact PR #44 head is linked from the
  controlled-exception record and truthfully reports three blocking contract defects.
- [x] Correction #51 makes admitted snapshots/results fail closed, restores the
  repository event envelope, binds rejected/retryable evidence and event reason
  families, and labels the fixture manifest as scenario metadata while requiring #43
  artifact provenance evidence.
- [x] The one-time exception records scope, reason, compensating controls, residual
  risk, accountable owner, approver gate, expiry, and change trigger without weakening
  future review requirements.
- [ ] Correction #51 has an independent exact-SHA review, a distinct authorized
  GitHub approval, protected checks, and a verified merge into `develop`.

## Verdict

The audit performed the missing review and rejected ratification of #44's contradictory
contract. Correction #51 addresses every blocking finding against the already-approved
fail-closed, P-013, and event-envelope behavior and records the historical ordering as
a one-time exception. Issue #43 remains blocked until the unchecked correction gate
above closes and #51 merges into `develop`. Once that happens, #43 can be independently
tested against the corrected F-003 schema, scenario manifest, and P-013 envelope
without importing an unmerged sibling branch.

## Known limitations and blocked gates

- The storage, scanner, parser, OCR, queue, worker runtime, region, provider, and
  production bucket are intentionally unselected. F-003 uses a local provider-neutral
  adapter and synthetic/right-cleared fixtures only.
- Documents 25–28 still block real-data retention, legal hold, provider transfer,
  object backup/RPO, production capacity, recovery, and release claims.
- F-004 owns extraction/OCR, normalized source structure, and its quality thresholds;
  F-005 owns generation/provider/evaluation; F-006 owns generated-draft review;
  F-007 owns learner access.
- The exception applies only to PR #44's historical ordering defect. Any F-003
  contract change or correction-PR head change requires a new exact-SHA review; no
  future approval is waived.
- #40/#41 record F-002's separate missing pre-merge review evidence. That issue remains
  independent and is not presented as solved here.

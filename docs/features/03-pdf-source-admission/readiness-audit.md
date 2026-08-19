# Readiness Audit — F-003 PDF Source Admission

Status: **READY FOR INDEPENDENT PLANNING REVIEW**

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

## Verdict

Issue #43 is ready to be provisioned only after this planning change receives an
independent exact-SHA review, a distinct authorized GitHub approval, and merges into
`develop`. Until then it remains blocked and no implementation branch/worktree may be
created. Once merged, #43 can be independently tested against the frozen F-003 schema,
fixture manifest, and P-013 envelope without importing an unmerged sibling branch.

## Known limitations and blocked gates

- The storage, scanner, parser, OCR, queue, worker runtime, region, provider, and
  production bucket are intentionally unselected. F-003 uses a local provider-neutral
  adapter and synthetic/right-cleared fixtures only.
- Documents 25–28 still block real-data retention, legal hold, provider transfer,
  object backup/RPO, production capacity, recovery, and release claims.
- F-004 owns extraction/OCR, normalized source structure, and its quality thresholds;
  F-005 owns generation/provider/evaluation; F-006 owns generated-draft review;
  F-007 owns learner access.
- #40/#41 record F-002's separate missing pre-merge review evidence. That issue must be
  resolved independently and is not presented as solved here.

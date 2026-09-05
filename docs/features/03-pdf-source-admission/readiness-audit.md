# Readiness Audit — F-003 PDF Source Admission

Status: **IMPLEMENTATION MERGED — POST-MERGE AUDIT CHANGES REQUIRED; #61 BLOCKS F-004**

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
- [x] Correction #51 merged through PR #53 as
  `5b89c6a8e62140f8032492b5454a12b2ef063bce`; the merged tree matches PR head
  `57bb2692eebfc81c6198589bfdd4fb7afeb17286`, protected checks passed, and its clean
  worktree/task-local resources were removed.
- [x] The project owner's explicit
  [#43 launch disposition](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43#issuecomment-5379136978)
  closes only the already-merged PR #53 governance hold without claiming retroactive
  review or approval.
- [x] #43 started from exact `origin/develop`
  `b733f94718826d7c7f98e08e44285639ece07813` in its declared worktree, Compose project,
  database port, and `/home/lawrence/Project Neo/tmp/LMS-43` host scratch child.
- [x] Application commit `f4b3af0b7d4595617f4effcba1b263a02f04e540`
  passed the focused, full non-RLS, production-role RLS, migration, OpenAPI/client,
  build, F-001/F-002/F-003 browser, architecture, lint, and type gates recorded in the
  [implementation evidence](../../evidence/f003-source-admission-implementation.md).
- [x] PR #56 merged exact head
  `ecbac896157fe157973f5116da91366cdacb8304` as
  `ed4670e6fa765d3edfb84610a450bef371a653ca`; its configured protected checks passed,
  but GitHub records no submitted review or distinct pre-merge approval.
- [x] An independent post-merge audit reproduced a marker-shaped 90-byte pseudo-PDF
  being admitted with `parser_accepted=True` without a real PDF parser and returned
  `CHANGES REQUIRED` on the exact merged head.
- [ ] #61 freezes the parser-backed boundary and its follow-up implementation
  remediation is independently reviewed and merged.

## Verdict

PR #56 is merged and its configured checks passed, but merge did not predetermine the
independent audit result. The post-merge audit found that marker/regex inspection can
report parser acceptance for structurally invalid pseudo-PDF bytes. F-003 therefore
remains implemented but not a clean dependency for F-004. Issue #61 must freeze and
launch a parser-backed fail-closed correction with RED-to-GREEN evidence.

## Known limitations and blocked gates

- The storage, scanner, parser, OCR, queue, worker runtime, region, provider, and
  production bucket are intentionally unselected. F-003 uses a local provider-neutral
  adapter and synthetic/right-cleared fixtures only.
- Documents 25–28 still block real-data retention, legal hold, provider transfer,
  object backup/RPO, production capacity, recovery, and release claims.
- F-004 owns extraction/OCR, normalized source structure, and its quality thresholds;
  F-005 owns generation/provider/evaluation; F-006 owns generated-draft review;
  F-007 owns learner access.
- F-004 planning may continue only as non-implementing contract work; F-004
  implementation cannot start until #61 and its follow-up remediation merge cleanly.
- The exception applies only to PR #44's historical ordering defect. PR #53's head
  changed after its `851d8fbb...` review and merged at `57bb2692...`; the owner
  disposition closes only #43's launch hold and waives no future approval.
- #40/#41 record F-002's separate missing pre-merge review evidence. That issue remains
  independent and is not presented as solved here.

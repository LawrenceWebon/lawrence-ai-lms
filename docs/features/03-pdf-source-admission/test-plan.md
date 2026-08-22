# Test Plan — F-003 PDF Source Admission

Status: **frozen verification plan; implementation blocked on governance disposition**

## Contract and fixture correctness

- Validate the F-003 Draft 2020-12 schema, every named DTO/example, event payload
  shape, job envelope, and fixture manifest.
- Assert P-013's exact byte/page/pixel/decoded/time/TTL/tenant quota values and reject
  altered values or a larger implicit upload class.
- Reject unknown properties, raw source bytes/text, storage object keys, signed target
  tokens, unbounded rights evidence, browser actor/tenant authority, and an operation
  other than `store`.
- Assert all source/version/rights/intent/job tenant and parent edges agree, IDs are
  UUIDs, checksums are canonical SHA-256 strings, and events/jobs minimize content.
- Reject admitted results with missing/failed evidence, rejected results whose frozen
  code contradicts their observation, retryable results without an unavailable
  inspection or with known terminal evidence, non-rejected snapshots with terminal
  codes, and event reasons from a different or unfrozen reason family.

## Domain, policy, and transaction correctness

- Instructor creates a declaration/request but cannot activate it; a distinct active
  tenant-admin reviewer can activate, deny, and revoke only the exact source/version.
- Verify fixed permission matrix, permission removal, inactive membership/tenant/
  entitlement denial, reviewer separation, rights expiry/dispute, and no inferred
  extract/OCR/generation/provider authority.
- Cover every admission and removal-state transition, including invalid/immutable
  transitions and safe retry from an unknown validator observation.
- Same idempotency key/same canonical request replays exactly one response/effect;
  changed request conflicts. Stale row/version and concurrent review/upload/cancel/
  revoke commands produce one safe outcome without partial facts.
- Inject failure at every local transactional boundary to prove source/version state,
  idempotency, audit, outbox, and durable job intent all roll back together.
- Prove storage/inspection/removal port calls occur after commit and no DB transaction
  spans those calls.

## Uploaded-document security and admission

- Valid small synthetic PDF: byte-derived signature/MIME, checksum, pages/pixels, and
  object inventory pass P-013 then enter `admitted` only after validation job success.
- Invalid fixtures: non-PDF MIME/signature mismatch, PDF polyglot, encrypted/password
  PDF, corrupt/truncated PDF, byte cap, page cap, per-page pixel cap, total pixel cap,
  decoded-material cap, parser timeout, unsafe inspection marker, missing object,
  checksum mismatch, and unavailable inspector.
- Target tests: no active rights authorization, expired/consumed/cancelled/revoked
  target, token mutation/guess, body over cap, content-type mismatch, same-target
  same-body replay, same-target different-body conflict, tenant quota/concurrency/24h
  limit, and no caller-supplied bucket/path/final location.
- Upload scanner/parser tests run with no ambient network or credentials. A missing
  safe local inspection capability is retryable/blocked; it is never treated as clean.

## Persistence, RLS, and reconciliation

- Django-only migration graph, generated data dictionary, named checks/indexes, forward
  migration, rollback/roll-forward evidence, and no undeclared source tables.
- Every tenant-owned source/right/authorization/intent/inventory/job/attempt/audit edge
  has `UNIQUE (tenant_id,id)`, composite FK, RLS, grants, and insert/update/delete
  negatives under production API and worker roles.
- Missing/wrong/stale transaction context, stale membership/entitlement, guessed source
  or version, Alpha/Beta leakage, target path traversal, worker job from another tenant,
  and connection-pool reset fail closed.
- Orphan DB intent, orphan object, missing object, duplicate observation, checksum
  mismatch, expired lease, worker crash, retry, failed deletion, and reconciler replay
  converge without duplicate object/source links or false removal completion.
- Cancellation/revocation/expiry blocks immediately, while removal completion requires
  observed object absence and an auditable reconciled result.

## API, Admin, and browser journey

- Strict request schemas, IDs, headers, operation IDs, body media type, statuses,
  Problem Details, neutral wrong-tenant/not-found behavior, and generated-client
  compatibility match the frozen contract.
- FastAPI, Admin, opaque target route, validator, and reconciler invoke one public
  service boundary; direct model writes and generic Admin edits cannot bypass policy.
- Playwright uses the generated client for core source data and proves instructor
  declaration, pending review, reviewer approval, valid synthetic upload, validation,
  admitted/rejected/cancelled/blocked states, expiration, and no direct storage client.
- Keyboard navigation, labels, validation summary, live status/error announcement,
  focus restoration, contrast/reflow at 200%, and no browser-persisted tenant/
  authorization state meet the existing baseline.

## Privacy and operational boundaries

- Events, audit, logs, errors, generated OpenAPI examples, test artifacts, browser
  source, and screenshot evidence contain no PDF bytes/text, signed URL/token, object
  key, unbounded file name, rights evidence, private prompt, or real data.
- The planning fixture manifest is deterministic scenario metadata only and contains no
  PDF artifact. Issue #43 must create only synthetic/right-cleared PDF artifacts and a
  separate executable manifest containing each artifact's origin, license, path, and
  SHA-256 before claiming upload-security or implementation evidence.
- Retention/legal-hold, provider deletion, object backup/RPO, external transfer, and
  production recovery remain explicit `not_applicable` only to this local slice; they
  are not marked passed or silently waived.

## Commands and pass criteria

The #43 worktree runs its dedicated Compose services once and reuses them. Its PR must
record exact commands/results for:

```text
docker compose up -d --build --wait
pytest backend/tests/contracts/test_f003_contracts.py backend/tests/documents \
  backend/tests/api/test_source_admission.py backend/tests/adapters/test_documents_admin.py \
  backend/tests/integration/test_f003_source_admission.py
pytest backend/tests -m rls
make lint
make typecheck
make test
make test-rls
make openapi-check
make web-build
make e2e-f001
make e2e-f002
make e2e-f003
make docs-check
git diff --check
```

All applicable commands must pass with no lint/type warnings. The implementation must
add an explicit `e2e-f003` target before claiming the browser gate passed. The
repository's protected checks remain required on the exact review SHA.

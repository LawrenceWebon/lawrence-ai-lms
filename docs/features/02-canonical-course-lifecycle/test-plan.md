# Test Plan — F-002 Canonical Course Lifecycle

## Software correctness

### Contract

- Validate the Draft 2020-12 schema and shared example.
- Reject unknown properties, HTML/URLs/embeds, unknown tree nodes or marks, invalid
  headings, duplicate marks, empty text, duplicate/zero positions, mismatched tenant
  IDs, noncanonical hashes, and unsupported states.
- Prove all three parallel lanes consume the same fixture checksum.

### Unit and policy

- Every allowed and forbidden transition/state pair.
- Default role/permission matrix and explicit permission removal.
- Self-review allowed versus separate-reviewer denial.
- AI/worker/service approval and publication denial.
- Canonical hash stability under key order/insignificant serialization differences and
  change sensitivity for every product-content field.
- Validation errors, immutable states, stale versions, reorder set mismatch, and
  idempotency hash conflicts.

### Database and migration

- Forward migration, clean rollback/roll-forward strategy, graph order, schema
  fingerprint, named constraints/indexes, and `makemigrations --check`.
- Composite same-tenant FK negatives for every edge on insert/update/delete.
- Forced RLS as API runtime role: missing/wrong/stale context, guessed ID, cross-tenant
  CRUD, tenant-ID mutation, inactive membership/entitlement, view/helper access, and
  pool reset.
- Positive/negative state checks, unique positions, unique version numbers/slugs,
  one current publication pointer, immutable published rows/children, and direct ORM/SQL
  mutation attempts.

### Service and transaction

- Create course + v1 atomically; optimistic update and full curriculum replacement.
- Submit/approve/publish recompute rather than trust the supplied hash.
- Request changes permits later mutation but preserves append-only review evidence.
- Publish pointer, version state, audit, idempotency, and outbox commit together; injected
  failure rolls all facts back.
- Same-key replay returns one effect; changed payload conflicts.
- Simultaneous update/reorder/approve/publish produces one winner without partial state.
- New draft version leaves the published snapshot byte-for-byte unchanged.

### API and Admin

- Exact methods, operation IDs, strict schemas, headers, success statuses, Problem
  Details media type/codes, response validation, and OpenAPI compatibility fixture.
- Authentication/tenant/permission/IDOR matrix for every operation.
- Admin uses the same service; critical lifecycle fields are read-only and generic model
  save/action paths cannot transition state.
- No course body or tenant name appears in neutral denied responses or logs.

### Integration and browser

- Alpha instructor creates a course, replaces its structured text curriculum, submits,
  approves under self-review policy, and publishes the exact hash.
- Version history shows immutable published v1 and a separate mutable v2 draft.
- Beta/outsider guessed selectors reveal nothing; revoked membership immediately loses
  access.
- Keyboard order, focus/error announcements, 200% zoom/reflow, labels, validation
  summary, and publish confirmation meet the existing accessibility baseline.
- Browser source contains no direct core-table client or persisted authorization state.

## Security and privacy

- Structured document rendering escapes text and has no raw HTML/URL/embed execution.
- Secret scan and a log-capture assertion prove no tokens or full lesson bodies enter
  general logs/events.
- Production-role tests, architecture imports, direct adapter writes, and service-bypass
  attempts fail.
- Synthetic `.invalid` identities and invented lesson text only; no private books,
  prompts, provider payloads, or real data.

## Not applicable

- Uploaded-document, OCR, AI/provider quality, provenance, prompt injection, enrollment,
  progress, commerce, notification, and production recovery suites are absent because
  F-002 enables none of those capabilities. Human-only publication and tenant isolation
  remain applicable and non-waivable.

## Commands and pass criteria

Each implementation worktree starts its dedicated Compose stack and reuses it:

```text
docker compose up -d --build --wait
make lint
make typecheck
make test
make test-rls
make openapi-check
make docs-check
```

Lane-focused commands are declared in `implementation-plan.md`. The integration issue
also runs `make web-build`, `make e2e-f001`, the F-002 focused Playwright spec, migration
authority/schema drift, architecture boundaries, secret scan, and `git diff --check`.
All applicable tests must pass with zero lint/type warnings. Existing F-001 regression
and protected GitHub checks must remain green.

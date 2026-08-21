# Readiness Audit — F-002 Canonical Course Lifecycle

Status: **POST-MERGE AUDIT REQUIRED — implementation checks passed before merge**

- [x] Outcome and non-goals match `docs/product/spec.md` and F-002 inventory.
- [x] P-012 closes Q-P04 with the smallest readable structured-text contract.
- [x] Snapshot/history, successor, request/response DTO, lifecycle, hash, event-fact,
  permission, and fixture contracts are executable.
- [x] Authorization, tenant, human-review, immutability, privacy, and publication rules are explicit.
- [x] Failure, idempotency, concurrency, rollback, and recovery behavior are explicit.
- [x] Test plan covers contract, unit, database, RLS, API/Admin, browser, accessibility, and security behavior.
- [x] Three initial issues have disjoint paths and consume the same committed fixture.
- [x] Persistence and integration shared hotspots each have one named owner.
- [x] Every issue declares focused commands, non-goals, resources, dependencies, and merge order.
- [x] No provider, real-data, AI, PDF, learner, commerce, or production gate is silently enabled.

## Readiness verdict

Corrective issue #33 and implementation issues #28–#30 merged into `develop` in the
declared order. Integration issue #31 composed the real service and PostgreSQL adapter,
published the frozen OpenAPI and event artifacts, generated the TypeScript client, and
provided the minimal authoring browser journey. Its PR #39 merged at
`99bd51beae9cad4774986dd797b245fd19da60a3` after the documented check suites passed.

GitHub now reports `REVIEW_REQUIRED` for PR #39 and contains no submitted independent
review or distinct approval. The pre-merge review gate was therefore not recorded. An
independent post-merge audit and explicit project-owner disposition are required before
F-002 can be declared delivery-complete; this audit does not retrospectively replace a
required GitHub approval.

## Known limitations

- F-002 uses synthetic text and local infrastructure only.
- `scheduled` remains a reserved canonical state without route/worker behavior.
- Retention/legal-hold and production recovery approvals remain launch gates, not local
  implementation blockers.
- F-007 owns learner reads, enrollment pinning, playback, and progress evidence.
- F-005/F-006 own AI provenance, source rights, and generated-draft integration.

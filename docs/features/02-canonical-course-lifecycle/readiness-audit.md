# Readiness Audit — F-002 Canonical Course Lifecycle

Status: **NOT READY — corrective issue #33 requires review and merge**

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

The corrective contracts are internally parallel-ready, but the existing implementation
branches still point at the pre-correction base. Issues #28–#30 remain blocked until
issue #33's corrective PR receives a fresh independent exact-SHA review, a distinct
authorized GitHub approval, and merges into `develop`. The coordinator may then update
the three issue markers, merge that exact base into each published branch without
rebasing, rerun the shared contract test, and start Agents A–C simultaneously.

## Known limitations

- F-002 uses synthetic text and local infrastructure only.
- `scheduled` remains a reserved canonical state without route/worker behavior.
- Retention/legal-hold and production recovery approvals remain launch gates, not local
  implementation blockers.
- F-007 owns learner reads, enrollment pinning, playback, and progress evidence.
- F-005/F-006 own AI provenance, source rights, and generated-draft integration.

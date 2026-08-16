# Readiness Audit — F-002 Canonical Course Lifecycle

Status: **READY AFTER PLANNING PR MERGE**

- [x] Outcome and non-goals match `docs/product/spec.md` and F-002 inventory.
- [x] P-012 closes Q-P04 with the smallest readable structured-text contract.
- [x] API, DTO, lifecycle, hash, event-fact, permission, and fixture contracts are frozen.
- [x] Authorization, tenant, human-review, immutability, privacy, and publication rules are explicit.
- [x] Failure, idempotency, concurrency, rollback, and recovery behavior are explicit.
- [x] Test plan covers contract, unit, database, RLS, API/Admin, browser, accessibility, and security behavior.
- [x] Three initial issues have disjoint paths and consume the same committed fixture.
- [x] Persistence and integration shared hotspots each have one named owner.
- [x] Every issue declares focused commands, non-goals, resources, dependencies, and merge order.
- [x] No provider, real-data, AI, PDF, learner, commerce, or production gate is silently enabled.

## Readiness verdict

The contracts are internally parallel-ready, but implementation branches must not be
created from a base that lacks them. The external gate is therefore the independent
approval and merge of planning issue #27's PR. After that merge, the coordinator may
replace the implementation issues' `BLOCKED ON #27` marker with
`READY FOR IMPLEMENTATION`, create their linked branches from the exact merge SHA, and
start Agents A–C simultaneously.

## Known limitations

- F-002 uses synthetic text and local infrastructure only.
- `scheduled` remains a reserved canonical state without route/worker behavior.
- Retention/legal-hold and production recovery approvals remain launch gates, not local
  implementation blockers.
- F-007 owns learner reads, enrollment pinning, playback, and progress evidence.
- F-005/F-006 own AI provenance, source rights, and generated-draft integration.

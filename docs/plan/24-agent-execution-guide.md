# Implementation Agent Execution Guide

Status: **authoritative execution policy**  
Change IDs: CHG-033, CHG-048

## Agent mission

Implement the LMS incrementally according to this documentation set without weakening tenant isolation, schema ownership, payment correctness, or AI review controls.

## Mandatory reading order

1. `../README.md` and `../../README.md` for status, authority and navigation.
2. `00-product-vision.md` for the approved launch/deferred capability boundary.
3. `../../../docs/final-review/16-DECISION-REGISTER.md` and `../../../docs/final-review/17-FINAL-READINESS-CHECKLIST.md`; stop when the requested capability depends on an open/deferred/rejected decision or blocked gate.
4. Relevant ADRs, especially migration ownership, PostgreSQL/Pinecone authority, human publication and worker runtime.
5. `01-architecture-overview.md` and `04-domain-module-design.md` for trust, execution-context and transaction rules.
6. `03-monorepo-folder-structure.md`, `05-database-schema-plan.md` and the complete relevant schema/security contract; never infer a field or relationship from a table name.
7. The feature-specific workflow plus `11-api-and-event-contracts.md`.
8. `12-security-and-multitenancy.md` and documents 25/26 for affected data, roles, threats, retention and privacy.
9. `15-testing-quality-gates.md`, `20-implementation-roadmap.md`, `21-risk-register.md` and `23-definition-of-done.md` for evidence and release gates.
10. `19-coding-standards.md`, relevant runbooks/evidence, and current entries in `SOURCES.md`.
11. Relevant chapters under `../../../setup-guide-docs/supabase-prod-guide/docs/supabase-production-guide/`, applying LMS-specific overrides rather than copying generic browser-CRUD or CLI-migration choices.

## Before changing code

- Identify the owning domain.
- State the applicable decision IDs, invariant/test IDs, capability disposition and exact files before editing.
- Search for existing models, services, policies, tests, and ADRs.
- Confirm whether a migration is required.
- List security and tenant-isolation impacts.
- List events and external integrations affected.
- Do not introduce another ORM or migration owner.
- Resolve applicable D/Q/CHG/risk IDs and read their current status/evidence. Do not implement an `open`, `blocked`, `deferred` or rejected capability as though it were approved.
- Verify relevant official-source entries in `SOURCES.md` are within their recheck date and re-verify capability/limits before provider-sensitive work.
- Identify exact migration, OpenAPI/event, test, dashboard/runbook, privacy/retention and rollout evidence paths that the change must produce.
- Refuse any shortcut that uses owner/`BYPASSRLS`, a browser core Data API path, session-level tenant context, unbalanced/mutable finance, incomplete AI lineage, AI/service approval, or unapproved provider/region transfer.

## Implementation sequence

1. Add or update domain model and migration.
2. Add constraints and indexes.
3. Add policy.
4. Add service transaction.
5. Add selector.
6. Add audit and outbox event.
7. Add FastAPI schemas and route.
8. Regenerate OpenAPI client.
9. Add frontend workflow.
10. Add unit, integration, permission, and Playwright tests.
11. Update documentation and ADR when necessary.

## Rules for AI features

- Store source provenance.
- Use structured output validation.
- Never auto-publish.
- Never overwrite approved manual content.
- Never trust a tenant or namespace supplied by the model or browser.
- Add evaluation cases before changing production prompts.
- Keep model-provider code behind adapters.
- Use idempotent generation steps.

## Rules for financial features

- Use transactions and row locks.
- Use minor currency units.
- Verify external state server-side.
- Write ledger entries.
- Preserve immutable history.
- Add duplicate and replay tests.

## Completion report format

```text
Feature:
Domain:
Files changed:
Migration:
API changes:
Security impact:
Tenant isolation:
Tests added:
Observability:
Known limitations:
Rollback:
Decision/risk/CHG IDs:
Official sources and recheck dates:
Exact commands and results:
Migration/schema fingerprint:
Production-role RLS/authorization evidence:
Privacy/retention/finance/AI applicability and evidence:
Deployment/dashboard/runbook evidence:
Traceability and documentation updates:
```

A completion report links evidence; it never substitutes “implemented”, “tested” or “ready” for a path and result. Update the roadmap phase manifest and capability traceability row. If a required decision/input remains open, leave the feature disabled and report the blocker instead of choosing a provider, legal period, budget, workload or threshold.

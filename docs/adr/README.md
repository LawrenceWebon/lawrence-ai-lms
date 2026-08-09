# Architecture Decision Records

Status: **current decision index; implementation evidence remains separate**

ADRs preserve why a durable architecture choice was made, its consequences, rejected alternatives, ownership and the evidence that should trigger review. An accepted ADR approves direction; it does not prove the described migration, runtime, provider, policy or test exists.

## Current decisions

| ADR | Status | Decision | Important gate |
|---|---|---|---|
| [0001 — Modular monolith](0001-modular-monolith.md) | Accepted | One transactional Django domain system with independently deployable process types | Split only on measured scale/reliability/data/team evidence |
| [0002 — Django/FastAPI boundary](0002-django-fastapi-boundary.md) | Accepted | Django owns models/services/migrations; FastAPI owns HTTP/OpenAPI | No second app-DDL history or router-owned business logic |
| [0003 — PostgreSQL/Pinecone authority](0003-pinecone-source-of-truth.md) | Accepted; AI deferred | PostgreSQL is canonical; Pinecone is a rebuildable authorized projection | AI/right/provider/reconciliation gates remain closed |
| [0004 — Human AI review](0004-ai-human-review.md) | Accepted; AI deferred | Only qualified humans approve immutable AI-assisted content for publication | AI/service actors cannot approve or publish |
| [0005 — Hybrid worker boundary](0005-hybrid-serverless-workers.md) | Boundary accepted; provider open | Long work uses a persistent container worker, not normal web requests | D-023/D-024 provider/orchestration benchmark and approval |

The in-repository [product decisions](../product/decisions.md) are the current status
authority for decisions that do not yet have their own ADR. The
[product audit](../product/product-audit.md) and feature readiness audits govern
whether accepted direction has sufficient implementation evidence. The older external
workspace audit remains historical context and is not shipped in this public repository.

## Required ADR structure

Every new or amended ADR contains:

1. stable ID and title;
2. status using the vocabulary below;
3. decision date, accountable owners and approver;
4. supersedes/superseded-by links;
5. related decision/change/risk IDs;
6. context and forces;
7. decision, including exact authority and trust boundary;
8. consequences and operational/test obligations;
9. alternatives considered and why rejected; and
10. measurable review triggers.

Recommended status vocabulary:

- `Proposed` — under review and not implementable as approved direction.
- `Accepted` — direction approved; implementation proof is tracked elsewhere.
- `Deferred` — intentionally outside current scope.
- `Rejected` — evaluated and not allowed.
- `Superseded by ADR-NNNN` — historical; successor governs new work.

Do not rewrite an ADR to hide a changed decision. Add a successor, mark the prior record superseded and preserve its context. Minor clarity/evidence-link updates may amend an accepted ADR without changing its decision.

## Template

```markdown
# ADR NNNN: Title

| Field | Value |
|---|---|
| ID | ADR-NNNN |
| Status | Proposed |
| Decision date | YYYY-MM-DD or pending |
| Owners | accountable roles |
| Approver | pending |
| Supersedes / superseded by | None / none |
| Related IDs | D-..., CHG-..., R-... |

## Context

Problem, constraints, evidence and affected authority/trust boundaries.

## Decision

The selected behavior and what is explicitly not selected.

## Consequences

Implementation, migration, security, privacy, operations and test obligations.

## Alternatives considered

Options and rejection reasons.

## Review trigger

Measurable conditions and responsible owner.
```

## Review rules

- A provider/runtime ADR records exact product, plan/tier, region, capacity, data flow, DPA/subprocessors, cost, failure/recovery and benchmark evidence.
- A data-authority ADR identifies the sole source of truth, projections, consistency/reconciliation and deletion/rebuild behavior.
- A boundary ADR names allowed dependency directions, credential/role ownership and tests that prevent bypass.
- An ADR cannot waive a non-waivable P0, tenant-isolation, privacy, finance, rights, human-publication or recovery gate.
- Update this index, links, source claims and generated document manifest in the same change as an ADR addition or status change.

# ADR 0004: AI Content Requires Human Approval

| Field | Value |
|---|---|
| ID | ADR-0004 |
| Status | Accepted; AI capability deferred |
| Decision date | 2026-08-02 |
| Owners | Product, Content, AI, Legal |
| Approver | Project owner |
| Supersedes / superseded by | None / none |
| Change ID | CHG-050 |

## Status
Accepted

## Context

Generated educational content can contain unsupported claims, unsafe assessment material, rights violations or stale source interpretations. Model output and automated evaluation cannot assume the legal/content accountability of a qualified reviewer, and a separate AI publication path would bypass canonical course invariants.

## Decision
All AI-generated blueprints, lessons, questions, assignments, and translations are drafts. A qualified human must approve them before publication.

## Consequences

- Publication workflow and provenance are mandatory.
- Generation must support artifact-level review and regeneration.
- Fully autonomous publishing is out of scope.

## Approval consequence

Only a qualified human can approve the immutable reviewed hash. High-risk/regulated content and rights exceptions require a second person unless a separately approved audited override exists. AI/provider/service actors are denied approval/publication; material change invalidates approval. Manual and AI paths use the same canonical transition and publication service.

## Alternatives considered

- Autonomous publication and self-evaluation as approval were rejected.
- Separate AI publication tables/path were rejected because they could bypass canonical course invariants.

## Review trigger

Review only if product/legal risk classification changes and an independent evaluation plus control design demonstrates an equal-or-stronger human-accountability outcome. Fully autonomous publication remains rejected unless this ADR is explicitly superseded.

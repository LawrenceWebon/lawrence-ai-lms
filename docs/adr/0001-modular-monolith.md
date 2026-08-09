# ADR 0001: Use a Modular Monolith

| Field | Value |
|---|---|
| ID | ADR-0001 |
| Status | Accepted |
| Decision date | 2026-08-02 |
| Owners | Architecture |
| Approver | Project owner |
| Supersedes / superseded by | None / none |
| Change IDs | CHG-050, CHG-052 |

## Status
Accepted

## Context

The LMS needs shared transactions across tenancy, course publication, learning and future gated finance/AI domains, while no implementation or production measurement shows a need for distributed data authority. Web, API, Admin and worker processes still need independent deployment and scaling without turning each process into a separate domain system.

## Decision
Use one PostgreSQL transactional system divided into clear Django domain modules. Deploy web, API, admin, and workers independently.

## Consequences

- Strong transactions are preserved.
- Operational complexity remains manageable.
- Module boundaries must be enforced by code review.
- High-load domains can be extracted later through outbox events.

## Alternatives considered

- Premature microservices were rejected because no measured independent scale/reliability/team boundary justifies distributed transactions and operations.
- An unstructured monolith was rejected because domain ownership, dependency and transaction boundaries remain mandatory.

## Review trigger (CHG-052)

Reconsider only when production evidence shows a domain needs materially independent scaling, reliability/failure isolation, data-authority/compliance boundary or stable autonomous team ownership. A replacement ADR must quantify current bottleneck/SLO/cost/team evidence, extraction/data migration and dual-run cost, transaction/event consistency, rollback and operational ownership. Traffic growth alone is not a split decision.

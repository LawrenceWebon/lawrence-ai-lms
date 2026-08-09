# ADR 0005: Hybrid Vercel and Dedicated Worker Deployment

| Field | Value |
|---|---|
| ID | ADR-0005 |
| Status | Accepted boundary; exact worker/orchestrator provider open |
| Decision date | 2026-08-02 |
| Owners | Platform, SRE, Security, DPO, Finance |
| Approver | Project owner for boundary; provider approval pending |
| Supersedes / superseded by | None / none |
| Change IDs | CHG-012, CHG-050 |

## Status
Accepted

## Context

Document parsing, malware scanning, OCR, embedding, generation and large exports can exceed web/serverless duration, memory, dependency and retry constraints. The architecture needs a persistent worker boundary, while exact provider, region and orchestration choices remain unproven and cannot be invented from a product name.

## Decision
Deploy Next.js and lightweight FastAPI workloads on Vercel. Run OCR, document parsing, embeddings, course generation, and large exports on containerized Python workers orchestrated through durable messages.

## Consequences

- The requested Vercel deployment remains central.
- An additional worker runtime is required.
- Job endpoints must authenticate orchestration messages and be idempotent.

## Provider-selection gate

Do not treat this ADR as selecting a provider. D-023/D-024 remain open. Benchmark Singapore-capable persistent runtimes and any regional queue/wake-up alternative using documents 27/28. Record plan/tier, CPU/memory/disk/duration/concurrency, deployment/drain, network/egress, session pooling, DPA/region/subprocessors, recovery, cost and support. QStash US/EU may carry only opaque wake-up identifiers after transfer approval; PostgreSQL remains durable job authority with leases/checkpoints/idempotency/reconciliation.

## Alternatives considered

- Long OCR/AI work in normal Vercel/API requests was rejected.
- In-process FastAPI background tasks as durable job authority were rejected.
- QStash/Workflow as domain/job truth was rejected; it is at most a delivery transport.

## Review trigger

Review after the Phase 0 benchmark, provider regional/capability change, measured worker SLO/cost failure, or an approved decision to remove all worker-dependent capabilities.

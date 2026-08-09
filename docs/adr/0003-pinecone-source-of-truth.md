# ADR 0003: PostgreSQL Is Authoritative; Pinecone Is Rebuildable

| Field | Value |
|---|---|
| ID | ADR-0003 |
| Status | Accepted; AI capability deferred |
| Decision date | 2026-08-02 |
| Owners | Data, AI, Security |
| Approver | Project owner |
| Supersedes / superseded by | None / none |
| Change IDs | CHG-015, CHG-050, CHG-051 |

## Status
Accepted

## Context

Future RAG needs vector retrieval, but permissions, rights, immutable source/course versions, citations and deletion obligations are relational business facts. Pinecone propagation is eventually consistent and cannot enforce current membership or serve as the only evidence for takedown.

## Decision
Store source documents, chunks, permissions, and citations in PostgreSQL. Store vector representations in Pinecone with IDs that map back to PostgreSQL.

## Consequences

- Pinecone loss does not lose business data.
- Reindexing and consistency jobs are required.
- Authorization remains outside Pinecone.

## Operational consistency contract (CHG-051)

PostgreSQL owns an immutable generation manifest with deterministic vector IDs, expected IDs/count/hash and pending/active/superseded/tombstoned status. Workers populate a non-active generation, reconcile provider observations, then atomically activate it in PostgreSQL. Queries filter exact tenant/course/version/rights/generation and reauthorize returned chunk IDs in PostgreSQL before context/citation use. Revocation tombstones immediately, excludes results, deletes/polls provider state to observed absence and escalates against the approved removal SLO. Full rebuild proof records counts/hashes/missing/extra IDs and authorization tests.

## Alternatives considered

- Pinecone as content/authorization authority was rejected.
- In-place unversioned vector replacement was rejected because eventual consistency can mix stale and new content.

## Review trigger

Review on vector provider/index-schema change, consistency model change, measured rebuild/RTO failure, tenant scale limit or approved replacement retrieval architecture.

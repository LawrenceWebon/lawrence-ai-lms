# ADR 0002: Django Owns Models; FastAPI Owns HTTP APIs

| Field | Value |
|---|---|
| ID | ADR-0002 |
| Status | Accepted |
| Decision date | 2026-08-02 |
| Owners | Architecture, Data, API |
| Approver | Project owner |
| Supersedes / superseded by | None / none |
| Change IDs | CHG-016, CHG-050 |

## Status
Accepted

## Context

The chosen Python stack combines Django's ORM, migration graph and Admin with FastAPI's HTTP/OpenAPI boundary. Without one explicit owner, duplicate models or Supabase CLI SQL histories could diverge, and routers/workers could bypass the shared tenant transaction and domain invariants.

## Decision
Django owns ORM models, migrations, services, policies, selectors, and admin. FastAPI owns HTTP request and response handling and OpenAPI.

## Consequences

- No duplicate models or migrations.
- FastAPI routers remain thin.
- Workers and admin reuse the same services.

## Migration authority consequence (CHG-016)

Django migrations and reviewed `RunSQL`/`RunPython` are the sole authority for application DDL, RLS, grants, helpers, triggers, extensions and bucket metadata. Supabase CLI may provision/test local, platform and branch configuration but must not create a parallel app migration history. Preview/production wait for the target project, run one direct-role Django migration job, record migration graph/schema fingerprint/drift and then deploy runtime services. Web/API/worker startup never migrates.

## Alternatives considered

- Supabase CLI application migrations were rejected for this LMS because dual authority would diverge from Django models/history.
- FastAPI-owned duplicate ORM/models were rejected because they split invariants and transactions.

## Review trigger

Review if Django ceases to own the domain model, a separately authoritative service is approved, or the Supabase branching/migration contract materially changes. Any change requires one migration authority, drift strategy and rollback proof.

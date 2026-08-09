# Coding Standards

Status: **approved engineering policy; lockfiles/tooling evidence begins in Phase 0**  
Change ID: CHG-040

## Python

Tooling:

- Ruff linting and formatting
- mypy strict mode
- pytest
- pre-commit
- Central `pyproject.toml`

Rules:

- Type every public function.
- Use keyword-only service parameters.
- Avoid `Any` outside adapter boundaries.
- Use timezone-aware datetimes.
- Use integer minor units for money.
- External calls require timeout and bounded retry.
- No broad exception suppression.
- No business logic in FastAPI routers.
- No provider calls in Django models.
- No provider/network call while a business database transaction is open; use the durable intent/saga contract.
- No environment lookups scattered through domain code.
- Domain exceptions map to HTTP errors in one place.
- Background jobs use durable claims, leases/checkpoints, idempotency, bounded retry classification and reconciliation.
- Use structured Pydantic schemas for AI output.

## TypeScript and Next.js

- TypeScript strict mode.
- ESLint flat configuration.
- Server Components by default.
- Small Client Component boundaries.
- Generated OpenAPI types.
- Use `unknown` for untrusted input.
- Runtime validation at browser and external boundaries.
- No direct core-table mutations from UI.
- No authorization based on hidden controls.
- No secret environment variables exposed to the client.

## SQL and migrations

- Django migrations are the only schema owner.
- Name constraints and indexes explicitly.
- Index foreign keys used in joins.
- Tenant-first indexes for tenant queries.
- No mutable published versions.
- No irreversible migration without rollback and backup plan.
- Use expand-and-contract changes.

## AI code

- Prompts are versioned and reviewed.
- Structured generation uses strict schemas.
- Store complete immutable run snapshots and normalized provenance/source/context/output edges; arrays/JSON IDs are not relationship authority.
- Never concatenate untrusted source into system instructions.
- No hidden automatic publishing.
- Add evaluation cases for each prompt change.
- Log metadata, not private prompt bodies.

## Git

Branch names:

```text
feature/LMS-123-manual-course-review
fix/LMS-456-tenant-context-reset
chore/LMS-789-upgrade-sdk
```

Pull requests include:

- Problem
- Design
- Security impact
- Tenant-isolation impact
- Database migration
- API change
- Tests
- Screenshots
- Rollback plan
- Capability/decision/risk/CHG IDs and evidence paths

## Documentation

- Architecture decisions go into ADRs.
- Public APIs remain in OpenAPI.
- Operational procedures go into runbooks.
- Every domain has a short README describing ownership and invariants.

## Runtime, dependency, and upgrade policy (CHG-040)

- Declare supported runtime/framework/database versions centrally and commit exact Python/Node/package/image lockfiles plus toolchain files.
- CI performs reproducible clean installs and vulnerability, license, secret, SAST, dependency and container/SBOM/provenance checks.
- Review end-of-support and security advisories continuously; recheck auth/key, database/pooling, deployment limits, queue, payment, email, AI/vector and privacy-sensitive official docs monthly and before production release.
- Renovation/upgrades include changelog/source review, generated API/event/schema compatibility, migration/rollback plan and focused contract/regression tests.
- Breaking or capability-sensitive changes require an ADR/decision record and accountable approval. Preview/beta dependencies require explicit risk acceptance and fallback.
- Do not copy version pins from the historical Supabase guide; select supported versions at scaffold time and record evidence in Phase 0.

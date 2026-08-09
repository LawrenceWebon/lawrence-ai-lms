# Lane B Prompt — Tenancy, Membership, Entitlement, and RLS

## Tests first

Add only domain-policy, migration/constraint, production-role RLS, cross-tenant,
concurrency, audit/outbox, and rollback tests listed in `test-plan.md`.

## Implementation

After test review, implement only Lane B using Django-owned models/migrations and
public services/selectors/policies. Complete the executable dictionary first. Do not
add routers/UI, custom roles, owner/`BYPASSRLS` shortcuts, or edit shared artifacts.

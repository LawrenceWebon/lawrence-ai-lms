# Lane C Prompt — Membership API and Admin Adapters

## Tests first

Add only frozen-contract API/Admin tests for permissions, IDOR, invitation replay and
expiry, idempotency/version conflict, neutral errors, and service-call parity.

## Implementation

After test review, implement thin FastAPI schemas/routers and adapter-only Admin
actions against the frozen tenancy service fake/contract. Do not write ORM state
directly, create migrations, send real email, or edit OpenAPI/generated artifacts.

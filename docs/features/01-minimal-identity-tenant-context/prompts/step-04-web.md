# Lane D Prompt — Web Authentication and Tenant Context

## Tests first

Add only component and mock-transport Playwright tests for sign-in, invitation,
explicit tenant selection, loading/empty/error/denial, session expiry, and accessibility.

## Implementation

After test review, implement only the owned web feature paths against the frozen
TypeScript fixture. Do not query core tables from Supabase, edit the generated client,
add course dashboards/analytics, or treat hidden controls as authorization.

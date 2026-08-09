# Lane A Prompt — JWT Identity and Execution Context

## Tests first

Add only the token/JWKS/revocation/identity-candidate and transaction-context reset
tests listed in `test-plan.md`, using the frozen tenant-authorizer fake.

## Implementation

After test review, implement only Lane A in its owned identity/auth-dependency paths.
Do not add tenancy mutations or migrations, trust JWT permissions, edit shared files,
or weaken failure assertions. Run `make lint`, `make typecheck`, and the focused tests.

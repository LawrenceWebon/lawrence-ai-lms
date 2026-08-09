# F-001 Step Prompts

These prompts are planning artifacts. Do not run an implementation prompt until the
readiness audit passes and the corresponding GitHub issue owns an isolated worktree.

Every prompt must first read `AGENTS.md`, the product files, all five files in this
feature package, the approved issue, and the current repository implementation. Tests
are written or confirmed before production code. Stop on any material mismatch.

| Prompt | Scope |
|---|---|
| `step-00-foundation.md` | scaffold and frozen contracts |
| `step-01-identity.md` | Lane A JWT/execution context |
| `step-02-tenancy.md` | Lane B tenancy/RLS |
| `step-03-adapters.md` | Lane C API/Admin adapters |
| `step-04-web.md` | Lane D web/E2E fixtures |
| `step-05-integration.md` | ordered integration/regeneration |

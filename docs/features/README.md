# Feature Planning Workspace

Create a durable feature folder only when a GitHub issue needs more detail than fits
comfortably in the issue and PR. Copy `docs/features/_template` to:

```text
docs/features/[NN]-[feature-slug]/
```

The GitHub issue remains the execution assignment. The feature folder records stable
product/technical contracts and test plans; it must not become a second product spec.

For parallel work, every implementation-plan item declares its issue, agent, branch,
worktree, owned paths, frozen contracts, dependencies, shared integration owner, test
commands, and merge order.

## Active feature packages

- [F-001 — Minimal identity and tenant context](01-minimal-identity-tenant-context/feature.md)
- [F-002 — Canonical course lifecycle](02-canonical-course-lifecycle/feature.md)
- [F-003 — PDF source admission](03-pdf-source-admission/feature.md)

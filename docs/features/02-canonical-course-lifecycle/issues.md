# GitHub Issues — F-002 Canonical Course Lifecycle

Planning issue [#27](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/27)
provisioned the graph. Corrective issue
[#33](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/33) froze the executable
contracts, and implementation lanes A–C merged in dependency order. Integration issue
#31 merged through [PR #39](https://github.com/LawrenceWebon/lawrence-ai-lms/pull/39),
but GitHub records no independent review or distinct approval for that PR. The required
review evidence is therefore unrecorded and F-002 is not closed as a delivery gate.

| Lane | Issue | Current state |
|---|---|---|
| A | [#28](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/28) — persistence, permissions, migrations, and RLS | `MERGED` |
| B | [#29](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/29) — lifecycle policies and services | `MERGED` |
| C | [#30](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/30) — FastAPI and Admin adapters | `MERGED` |
| I | [#31](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/31) — integration, generated client, web, and E2E | `MERGED; REVIEW/APPROVAL EVIDENCE UNRECORDED` |

Exact branches, worktrees, Compose resources, owned paths, tests, and merge order are
authoritative in `implementation-plan.md` and copied into each GitHub issue. No agent
may infer wider ownership from this summary.

# GitHub Issues — F-002 Canonical Course Lifecycle

Planning issue [#27](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/27)
provisioned the graph. Independent review found incomplete executable contracts, so
corrective issue [#33](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/33)
now owns the freeze. Implementation issues remain blocked until its PR receives a
fresh exact-SHA review, distinct authorized GitHub approval, and merge into `develop`.

| Lane | Issue | Current state |
|---|---|---|
| A | [#28](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/28) — persistence, permissions, migrations, and RLS | `BLOCKED ON #33` |
| B | [#29](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/29) — lifecycle policies and services | `BLOCKED ON #33` |
| C | [#30](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/30) — FastAPI and Admin adapters | `BLOCKED ON #33` |
| I | [#31](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/31) — integration, generated client, web, and E2E | depends on A–C merges |

Exact branches, worktrees, Compose resources, owned paths, tests, and merge order are
authoritative in `implementation-plan.md` and copied into each GitHub issue. No agent
may infer wider ownership from this summary.

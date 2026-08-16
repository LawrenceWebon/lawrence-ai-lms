# GitHub Issues — F-002 Canonical Course Lifecycle

Planning issue [#27](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/27)
freezes the product/technical contracts and provisions the issue graph. Implementation
issues remain blocked until the planning PR is independently approved and merged.

| Lane | Issue | State before planning merge |
|---|---|---|
| A | [#28](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/28) — persistence, permissions, migrations, and RLS | `BLOCKED ON #27` |
| B | [#29](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/29) — lifecycle policies and services | `BLOCKED ON #27` |
| C | [#30](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/30) — FastAPI and Admin adapters | `BLOCKED ON #27` |
| I | [#31](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/31) — integration, generated client, web, and E2E | depends on A–C merges |

Exact branches, worktrees, Compose resources, owned paths, tests, and merge order are
authoritative in `implementation-plan.md` and copied into each GitHub issue. No agent
may infer wider ownership from this summary.

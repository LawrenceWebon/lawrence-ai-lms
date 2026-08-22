# GitHub Issues — F-003 PDF Source Admission

Planning issue [#42](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/42)
established the frozen F-003 contract in merged PR #44. Correction issue
[#51](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51) records the exact
post-merge audit, corrects its three blocking contract findings, and documents the
one-time exception for #44's missing pre-merge approval evidence.
Implementation issue [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43)
deliberately owns one complete vertical slice rather than splitting shared Documents
migrations, admission state, OpenAPI/client, local storage adapter, and browser wiring
across branches.

| Issue | Scope | State | Dependency |
|---|---|---|---|
| [#42](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/42) | Feature package, frozen DTO/job/event/fixture contract, P-013, test plan, ownership | merged in PR #44 | none |
| [#51](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51) | Exact-head audit, fail-closed/event/fixture-boundary corrections, controlled exception, readiness, serialized manifest | independent exact-SHA review, distinct approval, checks, and merge required | PR #44 merged |
| [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43) | Private local PDF source admission, migration/RLS, API/Admin, local adapter/worker, OpenAPI/client, web/E2E, evidence | `BLOCKED` | #51 independently approved and merged |

After #51 merges and cleans up, #43 branches from the resulting latest `develop` as
`feature/LMS-43-f003-source-admission` and uses only
`/home/lawrence/Project Neo/worktrees/ai-lms/source-admission-LMS-43` with Compose
project `ai-lms-lms-43` and PostgreSQL port `55243`. #43 must not start before then.

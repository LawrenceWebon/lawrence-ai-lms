# GitHub Issues — F-007 Learner Course Playback and Progress

Planning issue [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45)
established the proposed F-007 boundary and executable contracts. Planning correction
[#50](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/50) records the project
owner's F007-Q01–Q04 decisions and freezes the resulting contract before implementation
issue [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) may start.

| Lane | Issue | Current gate |
|---|---|---|
| Initial planning | [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45) — private enrollment, version-pinned playback, and explicit progress | merged in PR #47 |
| Decision correction | [#50](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/50) — freeze P-014 and F007-Q01–Q04 | independent exact-SHA review, distinct approval, checks, and merge required |
| Implementation | [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) — one vertical learner playback/progress slice | `BLOCKED` until the #50 correction PR merges |

The contract contains no remaining product decision hidden behind implementation.
After #50's pull request is independently approved and merged, #46 may be updated to
`READY FOR IMPLEMENTATION`, link the exact merge SHA, and provision only its declared
branch, worktree, Compose project, and PostgreSQL port from the resulting latest
`origin/develop`.

The authoritative owned paths, tests, dependencies, non-goals, shared-hotspot owner,
and merge order are in `implementation-plan.md`. No application branch or worktree may
be provisioned before the #50 correction merge gate closes.

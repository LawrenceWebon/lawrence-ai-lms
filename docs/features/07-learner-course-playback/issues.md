# GitHub Issues — F-007 Learner Course Playback and Progress

Planning issue [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45)
established the proposed F-007 boundary and executable contracts. Planning correction
[#50](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/50) records the project
owner's F007-Q01–Q04 decisions and freezes the resulting contract before implementation
issue [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) may start.

| Lane | Issue | Current gate |
|---|---|---|
| Initial planning | [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45) — private enrollment, version-pinned playback, and explicit progress | merged in PR #47 |
| Decision correction | [#50](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/50) — freeze P-014 and F007-Q01–Q04 | merged in PR #52; distinct approval was not recorded |
| Implementation | [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) — one vertical learner playback/progress slice | `BLOCKED` pending an owner-approved disposition for PR #52's approval defect |

The contract contains no remaining product decision hidden behind implementation.
PR #52 merged as `eb0fb3e808c37073e99625609c1338ce4b1ce51e`; its reviewed head
has the same tree and protected checks passed, but GitHub records no distinct submitted
approval. The clean #50 worktree and task-local Compose resources were removed. After
that remaining gate receives an explicit valid disposition, #46 may be updated to
`READY FOR IMPLEMENTATION` and provision only its declared branch, worktree, Compose
project, PostgreSQL port, and host scratch child
`/home/lawrence/Project Neo/tmp/LMS-46` from the then-latest `origin/develop`.

The authoritative owned paths, tests, dependencies, non-goals, shared-hotspot owner,
and merge order are in `implementation-plan.md`. No application branch, worktree,
scratch child, or Compose project may be provisioned before the remaining approval gate
closes.

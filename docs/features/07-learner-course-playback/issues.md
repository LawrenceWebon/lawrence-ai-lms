# GitHub Issues — F-007 Learner Course Playback and Progress

Planning issue [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45)
established the proposed F-007 boundary and executable contracts. Planning correction
[#50](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/50) records the project
owner's F007-Q01–Q04 decisions and freezes the resulting contract before implementation
issue [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46). The owner later
recorded the narrow launch disposition required for #46 to start.

| Lane | Issue | Current gate |
|---|---|---|
| Initial planning | [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45) — private enrollment, version-pinned playback, and explicit progress | merged in PR #47 |
| Decision correction | [#50](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/50) — freeze P-014 and F007-Q01–Q04 | merged in PR #52; distinct approval was not recorded |
| Implementation | [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) — one vertical learner playback/progress slice | local candidate at `dd758909e3060032ecbe28f8175d3849a4c26208`; draft PR, protected checks, and independent review pending |

The contract contains no remaining product decision hidden behind implementation.
PR #52 merged as `eb0fb3e808c37073e99625609c1338ce4b1ce51e`; its reviewed head has
the same tree and protected checks passed, but GitHub records no distinct submitted
approval. The
[project-owner disposition](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46#issuecomment-5380754610)
accepted that residual governance risk only to authorize #46 and did not claim
retroactive approval.

#46 was provisioned from exact base
`ed4670e6fa765d3edfb84610a450bef371a653ca` on its declared branch, worktree, Compose
project, PostgreSQL port, and host scratch child. Its application candidate is
`dd758909e3060032ecbe28f8175d3849a4c26208`, with results in the
[local implementation evidence](../../evidence/f007-learner-playback-implementation.md).
Protected checks, independent exact-head review, distinct authorized approval, and
merge remain pending.

The authoritative owned paths, tests, dependencies, non-goals, shared-hotspot owner,
and merge order are in `implementation-plan.md`. The active task resources must be
preserved until GitHub reports the implementation PR merged or the project owner
explicitly abandons it.

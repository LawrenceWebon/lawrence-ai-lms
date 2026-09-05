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
| Implementation | [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) — one vertical learner playback/progress slice | merged in PR #57; post-merge audit returned `CHANGES REQUIRED` |
| Remediation | [#60](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/60) — deny learner enrollment revocation through RLS | ready after workflow reconciliation #59; required before F-008 |

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
PR #57 later merged at exact head `843d34b168f7cb0b140f7663e775585c80b35cfd` as
`7c891c30d5281ed40eab592aa2ab4d14c0c83a33`; configured checks passed. The independent
[post-merge audit](https://github.com/LawrenceWebon/lawrence-ai-lms/pull/57#issuecomment-5384244065)
returned `CHANGES REQUIRED` after proving learner-runtime self-revocation. #60 owns the
narrow forward RLS correction.

The authoritative owned paths, tests, dependencies, non-goals, shared-hotspot owner,
and merge order are in `implementation-plan.md`. The merged #46 author resources were
cleaned and verified absent; review-only resources are removed after durable audit
evidence is recorded.

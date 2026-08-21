# GitHub Issues — F-007 Learner Course Playback and Progress

Planning issue [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45) owns
the product/technical boundary, executable DTO/event contracts, synthetic fixtures,
tests, and readiness decision. Implementation issue
[#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) exists but is
explicitly blocked.

| Lane | Issue | Current state |
|---|---|---|
| Planning | [#45](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/45) — freeze private enrollment, version-pinned playback, and explicit progress | `PLANNING REVIEW REQUIRED` |
| Implementation | [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46) — one vertical learner playback/progress slice | `BLOCKED` |

Issue #46 may become `READY FOR IMPLEMENTATION` only after the project owner resolves
F007-Q01, F007-Q02, F007-Q03, and Q-P08/F007-Q04, those decisions are reflected in the
exact executable contracts, and #45 receives independent exact-SHA approval and merges
to `develop` with protected checks green.

The authoritative branch, worktree, Compose resources, owned paths, tests,
dependencies, non-goals, shared-hotspot owner, and merge order are in
`implementation-plan.md` and copied into issue #46. No agent may infer wider ownership
from this summary, and no branch/worktree is provisioned while the issue is blocked.

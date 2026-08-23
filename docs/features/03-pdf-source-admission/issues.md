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
| [#51](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51) | Exact-head audit, fail-closed/event/fixture-boundary corrections, controlled exception, readiness, serialized manifest | merged in PR #53; merge-head review and distinct approval were not recorded | PR #44 merged |
| [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43) | Private local PDF source admission, migration/RLS, API/Admin, local adapter/worker, OpenAPI/client, web/E2E, evidence | merged in PR #56; post-merge audit returned `CHANGES REQUIRED` | owner launch disposition recorded |
| [#61](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/61) | Freeze the parser-backed fail-closed admission remediation contract and implementation issue | planning required; blocks F-004 implementation | PR #56 post-merge audit |

PR #53 merged as `5b89c6a8e62140f8032492b5454a12b2ef063bce`; the clean #51
worktree and task-local Compose resources were removed. Its merge head
`57bb2692eebfc81c6198589bfdd4fb7afeb17286` was not the independently reviewed
`851d8fbbac83087e1b00ea36581fd2450aa174ee` head, and GitHub records no distinct
approval. The project owner's
[launch disposition](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43#issuecomment-5379136978)
closed only that historical hold after PR #55 merged at
`b733f94718826d7c7f98e08e44285639ece07813`; it does not claim retroactive approval.
#43 branched from that exact `develop` commit as
`feature/LMS-43-f003-source-admission` and uses only
`/home/lawrence/Project Neo/worktrees/ai-lms/source-admission-LMS-43` with Compose
project `ai-lms-lms-43`, PostgreSQL port `55243`, and host scratch child
`/home/lawrence/Project Neo/tmp/LMS-43`. Local implementation evidence is recorded in
[the F-003 evidence record](../../evidence/f003-source-admission-implementation.md).
PR #56 later merged at exact head `ecbac896157fe157973f5116da91366cdacb8304` as
`ed4670e6fa765d3edfb84610a450bef371a653ca`; configured checks passed. The independent
[post-merge audit](https://github.com/LawrenceWebon/lawrence-ai-lms/pull/56#issuecomment-5384251039)
returned `CHANGES REQUIRED` after admitting a structurally invalid pseudo-PDF. #61 is
the next F-003 task and blocks F-004 implementation.

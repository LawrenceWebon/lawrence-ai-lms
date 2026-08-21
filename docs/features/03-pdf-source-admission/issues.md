# GitHub Issues — F-003 PDF Source Admission

Planning issue [#42](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/42) freezes
the F-003 contract. Implementation issue
[#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43) deliberately owns one
complete vertical slice rather than splitting shared Documents migrations, admission
state, OpenAPI/client, local storage adapter, and browser wiring across branches.

| Issue | Scope | State | Dependency |
|---|---|---|---|
| [#42](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/42) | Feature package, frozen DTO/job/event/fixture contract, P-013, test plan, ownership | `READY FOR INDEPENDENT PLANNING REVIEW` | none |
| [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43) | Private local PDF source admission, migration/RLS, API/Admin, local adapter/worker, OpenAPI/client, web/E2E, evidence | `BLOCKED` | #42 independently reviewed, approved, and merged |

After #42 merges, #43 branches from that exact `develop` head as
`feature/LMS-43-f003-source-admission` and uses only
`/home/lawrence/Project Neo/worktrees/ai-lms/source-admission-LMS-43` with Compose
project `ai-lms-lms-43` and PostgreSQL port `55243`. #43 must not start before then.

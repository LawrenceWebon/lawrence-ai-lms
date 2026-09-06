# F-007 Local Learner-Playback Implementation Evidence

Status: **implementation merged; independent post-merge audit returned CHANGES REQUIRED; #60 pending**

- Evidence ID: `F007-LOCAL-IMPLEMENTATION-2026-08-22`
- Classification: internal, synthetic/local-only implementation evidence
- Issue: [#46](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46)
- Base: `ed4670e6fa765d3edfb84610a450bef371a653ca`
- Implementation commit: `dd758909e3060032ecbe28f8175d3849a4c26208`
- Branch: `feature/LMS-46-f007-learner-playback`
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/learner-playback-LMS-46`
- Compose project/database port: `ai-lms-lms-46` / `55246`
- Host scratch: `/home/lawrence/Project Neo/tmp/LMS-46`
- Producer: #46 implementation context; not an independent reviewer or approver

The project-owner launch disposition is recorded in the
[#46 issue comment](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46#issuecomment-5380754610).
It closes only the historical PR #52 launch hold and does not claim retroactive review
or approval. The implementation commit above is the immutable application-code input
to this evidence; the later documentation commit and exact draft-PR head must still be
recorded in the #46 handoff.

## Implemented boundary

The candidate adds the local Learning domain, Django-owned schema and forced RLS,
tenant-safe FastAPI/Admin composition, manual tenant-admin assignment and terminal
revocation, immutable published-version pins, private learner dashboard/playback,
explicit optimistic and idempotent progress commands, five minimized event contracts,
generated OpenAPI/client types, and a minimal learner web journey. It preserves the
frozen F-007 limits and adds no self-enrollment, public catalog, source/PDF access, AI,
provider, queue, commerce, assessment, analytics, or production enablement.

Current tenant, entitlement, membership, permission, enrollment ownership, pinned
version availability, and lesson membership are re-derived server-side. Tenant-owned
learning edges use composite constraints and forced RLS. The learner role receives
only `learning.playback.read`; the tenant-admin role receives only
`learning.enrollments.manage`; instructor and reviewer roles receive neither. Playback
GETs do not mutate state. Progress, idempotency, audit, and outbox facts commit together,
and stale commands fail without overwriting the winning state.

The player uses the generated client, renders only the F-002 allowlisted rich-text tree,
escapes untrusted text, stores no browser authorization state, and clears rendered
content after access loss. Existing enrollments remain pinned when the publication
pointer advances; re-enrollment creates a new record pinned to the then-current version
and copies no historical progress.

## Local verification

All project commands ran in the task's pinned Compose services. Host `make` and
PowerShell were unavailable, so each Make target's underlying command was executed
directly in the same Compose services; the Python documentation checker provided the
repository's equivalent local manifest/link validation.

| Gate | Exact command/result |
|---|---|
| Focused F-007 | `pytest backend/tests/contracts/test_f007_contracts.py backend/tests/contracts/test_f007_event_registry.py backend/tests/learning backend/tests/api/test_learning.py backend/tests/adapters/test_learning_admin.py backend/tests/integration/test_f007_learning_composition.py -q` — 64 passed |
| Full non-RLS regression | `pytest backend/tests tests -m 'not rls' -q` — 615 passed, 30 deselected |
| Production-role RLS | `pytest backend/tests -m rls -q` — 30 passed, 602 deselected |
| Learning migration round trip | `python backend/manage.py migrate learning zero --noinput`; `python backend/manage.py migrate learning --noinput` — both learning migrations reversed and reapplied successfully |
| Migration drift | `python backend/manage.py makemigrations --check --dry-run` — no changes detected |
| Python lint/format | `ruff check backend scripts tests`; `ruff format --check backend scripts tests` — passed; 177 files formatted |
| Python types | `mypy --config-file backend/pyproject.toml backend/src scripts` — passed for 78 source files |
| Architecture/migration authority | `python scripts/check_architecture.py`; `python scripts/check_migration_authority.py` — passed; 18 Django migration files |
| OpenAPI/client drift | `python scripts/generate_openapi.py --check`; `./scripts/check_openapi_client.sh` — current |
| JavaScript/TypeScript | `npm run lint`; `npm run typecheck` — all workspaces passed |
| Production web build | `npm run build --workspace @ai-lms/web` — passed; `/learner-courses` and `/learner-courses/[enrollmentId]` emitted |
| F-001 browser regression | Playwright F-001 foundation/integration/lane-D specs — 12 passed |
| F-002 browser regression | Playwright `f002-course-editor.spec.ts` — 2 passed |
| F-003 browser regression | Playwright `f003-source-admission.spec.ts` — 5 passed |
| F-007 browser journey | Playwright `f007-learner-playback.spec.ts` — 3 passed |
| Diff and credential probes | `git diff --cached --check` and staged high-risk credential-pattern scan — passed with no match |
| Documentation | `python scripts/docs_check.py --write-manifest`; `python scripts/docs_check.py`; `git diff --check` — manifest and equivalent local link checks passed; exact PowerShell execution remains for CI |

The F-007 browser cases prove the safe empty dashboard; real Admin API assignment;
escaped rich text; read-only GET behavior; explicit resume, complete, and reopen;
reload/sign-in resume; stale second-session conflict and recovery; v2 pointer advance
with the v1 pin preserved; revocation and withdrawal content clearing; wrong-tenant and
IDOR denial; absence of browser storage; keyboard focus and semantic navigation; exact
`en` metadata; RTL-ready interaction; forced-color and reduced-motion emulation; and
400% reflow.

The browser environment was Playwright 1.62.1 with Google Chrome for Testing
151.0.7922.34 in Ubuntu 24.04.4 LTS. These are automated Chromium results produced by
the #46 implementation context. No manual screen-reader or other assistive-technology
session was performed, so this record makes no manual AT interoperability claim.

During verification, the initial F-007 browser selector also matched Next.js's own live
announcer and was narrowed to the product alert. The same run exposed genuine
two-column overflow at 400% zoom; the player breakpoint was corrected and the final
browser suite passed. The architecture gate then identified direct ORM persistence in
API composition; persistence moved behind the Learning and Courses module boundaries,
and the final architecture and regression suites passed. Finally, additive F-007 RLS
policies changed the expected F-002 course database-catalog fingerprint; the expected
identity was regenerated and the clean full suite passed. The first draft-PR quality
run then caught that the evidence/status edit had removed historical readiness phrases
asserted by the frozen F-007 contract test. Those phrases were restored as explicit
launch-history statements without changing application code; the exact failing test
and a clean 615-test non-RLS rerun passed. No initial failure is presented as passing
evidence.

## Deterministic generated identities

| Artifact | Identity |
|---|---|
| Learning schema fingerprint | `sha256:80310048160ddcc04222c1491c281c5e693f133dfee040a2f8c4bd6990495925` |
| Learning migrated database-catalog fingerprint | `sha256:4c8519719e05db95f2438a1085d835598ffd5c6b992af484cac7250ea6361657` |
| Course migrated database-catalog fingerprint after additive F-007 policies | `sha256:645b6eff7edeefce656456767e80b97cdd29835a8be99a98090fa5117101553f` |
| Generated OpenAPI file | `354dd253cac49c7851ebe7569ddbe2c54119117c7f6db8c88f472cef37ee4e54` |
| Generated TypeScript schema file | `aa1fcd9a5dd7e026ff1b8b835660eb9f91f3028dc8c3c4978dd9a8069634aa1e` |

## Security, privacy, and operational limits

- Tests use deterministic synthetic tenant, learner, course, and rich-text data only.
  No private PDF, production identity, provider payload, prompt, chat, or credential was
  introduced.
- The implementation Compose stack, worktree, and exact host scratch child were
  removed after GitHub reported PR #57 merged. Independent review used separate
  disposable resources.
- Retention/legal hold, production capacity, recovery, deployment, real-data, broader
  locale, and manual assistive-technology acceptance remain pending or out of scope.
  They are not marked passed.
- No external provider, production data, deployment, release, or production mutation
  was used.
- PR #57 merged with configured checks green. Its independent post-merge audit proved
  that an enrolled learner using the production runtime can directly revoke its own
  enrollment and bypass service idempotency/audit/outbox facts. Remediation #60 is
  required before F-008 integration.

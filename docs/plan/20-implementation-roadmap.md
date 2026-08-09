# Implementation Roadmap

Status: **planned only; no code, migrations, policies, infrastructure or test evidence exists**  
Change IDs: CHG-022, CHG-030, CHG-031

## Approved phase disposition

| Phase | Disposition | Rule |
|---|---|---|
| 0–1 | Core foundation | May begin only with synthetic/local data until documents 25–28 and P0 schema/RLS gates close |
| 2–3 | Focused LMS foundation | Minimal canonical authoring/review/publication, learning and progress; evidence-based exits required |
| 4 | Deferred assessment increment | Quizzes, assignments, grading and certificates are not required for the focused MVP |
| 5 | Deferred paid commerce | Disabled until Q-05/C-04, provider capability/tax contract and finance integrity suites close |
| 6 | Split | Manual tenant contracts/local entitlements move into Phase 1; recurring/usage billing remains deferred |
| 7–9 | Focused PDF-to-course MVP | Local contract/fixture work may proceed in dependency order; provider, real-data and production activation remain gated |
| 10 | Deferred AI companion/RAG | Disabled until separately approved and its rights/retrieval/evaluation gates close |
| 11 | Continuous hardening | Core recovery/security/capacity work begins in Phase 0; it is not postponed until after features |

No table/API/provider credential/job/route/UI for a deferred capability is considered
part of the MVP. Focused ingestion/generation phases may add only issue-owned artifacts
after contracts freeze; their inclusion does not approve an external provider, real
data, or production release.

## Phase evidence manifest (CHG-030)

Phase 0 creates a versioned manifest with these required link types:

| Evidence class | Required artifact |
|---|---|
| Build/source | Repository path, commit, exact lockfiles, generated manifest/checksum, SBOM/provenance |
| Schema | Django migration graph, executable dictionary/ERD, schema fingerprint/drift report, roles/grants/RLS/policy source |
| Contracts | OpenAPI/event/schema diff and generated client version |
| Verification | Exact commands/results for unit/integration/RLS/security/Playwright/accessibility/load/fault/restore and conditional finance/AI suites |
| Delivery | CI run, image/deploy ID, environment/provider tiers/regions, migration execution and smoke result |
| Operations | Dashboards, alert rules/owners, runbooks, backup/restore and incident evidence |
| Governance | ADR/decision/risk/DoD/CHG/source freshness, privacy/retention/capacity/recovery approvals |

Every phase exit links its manifest entries and is independently approved. A sentence such as “tests pass” or “deployed” without immutable evidence is not an exit. After each phase, re-audit documentation against implementation and leave later behavior labeled planned.

## Phase 0 — Repository and engineering foundation

Deliver:

- Monorepo
- Next.js, FastAPI, Django, worker skeleton
- Local Supabase setup
- Ruff, mypy, ESLint, pytest, Playwright
- CI pipeline
- OpenAPI generation
- Privacy-gated telemetry adapter/redaction tests; no PostHog key/event and no non-local Sentry export before documents 25/26 provider approval
- Initial core threat model, runbook catalog and evidence index

Exit criteria:

- One authenticated health flow works end to end.
- CI blocks lint, type, migration, and test failures.
- Evidence manifest exists and records all Phase 0 paths/commands/results.
- Core auth/JWKS/key, migration/RLS failure, cross-tenant incident and database/object restore runbooks have owners and versioned drill plans; production still waits for successful applicable exercises.
- No real personal data or deferred capability credential is present.
- P0 schema/RLS/JIT designs have executable tests ready before Phase 1 data.

## Phase 1 — Identity, tenancy, and authorization

Deliver:

- Supabase Auth
- Profiles
- Tenants and domains
- Memberships
- Roles, permissions, and scopes
- RLS helpers and policies
- Tenant onboarding
- Audit logs

Exit criteria:

- Full cross-tenant permission matrix passes.
- Manual contract/local entitlement and onboarding step state are authoritative; no access before entitlement/readiness.
- Production-role RLS, composite same-tenant FK, pool reset and JIT privileged-access negative tests pass.
- Documents 25–28 have no core `TBD-BLOCKING` before production/real data.

## Phase 2 — Organization and manual course foundation

Deliver:

- Branches, departments, programs, groups
- Categories
- Course and course version
- Sections, lessons, content blocks, assets
- Manual course builder
- Review and publication

Exit criteria:

- Instructor can publish a manual course through the approved workflow.
- Production-role/API/Admin tests prove the exact immutable version/hash, reviewer/publisher permissions, prerequisite DAG, concurrent transition handling, publication pointer and enrollment-version behavior.

## Phase 3 — Learning experience

Deliver:

- Course catalog
- Enrollment
- Course player
- Progress
- Minimum student/instructor views required for the approved journey
- Notes, bookmarks and broad dashboards only as separately accepted post-launch increments

Exit criteria:

- Student can enroll, resume, and complete a course.
- Cross-tenant, version-pinning, concurrent/idempotent progress and primary read-after-write tests link to the phase evidence manifest.

## Phase 4 — Assessments, grading, and certificates — deferred increment

**Outside the focused MVP.** This phase requires a separate product decision.

Deliver:

- Question bank
- Quizzes and attempts
- Server-side scoring and immutable attempt snapshots
- Assignments, gradebook and certificates only as separately accepted post-launch increments

Exit criteria:

- Learner completes the approved basic quiz journey with a server-verifiable immutable result.
- Attempt snapshots/scoring and any later enabled certificate rule pass constraint, authorization, concurrency and Playwright evidence; deferred assignment/advanced-grade/certificate behavior is not claimed.

## Phase 5 — Commerce and payments

**Deferred and disabled.** This phase cannot start merely because Phase 4 exits.

Deliver:

- Product and price
- Cart and checkout
- PayMongo integration
- Orders, payments, refunds
- Balanced ledger and local entitlement; instructor earnings/payouts remain outside this phase
- Resend receipts
- Reconciliation

Exit criteria:

- Verified sandbox payment creates exactly one enrollment and balanced ledger entries.

## Phase 6 — SaaS billing and platform administration

Manual contract/local entitlement administration belongs to Phase 1. Recurring subscription, usage billing and finance-dependent suspension/dunning remain deferred.

Deliver:

- Plans, features, usage
- Tenant subscriptions and invoices
- Tenant suspension and grace periods
- Platform dashboards
- Support tickets

Exit criteria:

- Tenant plan limits are enforced server-side.

## Phase 7 — Focused PDF upload and ingestion

**Focused MVP planned.** Product/contract planning and local implementation with
synthetic or rights-cleared PDFs may proceed after F-001 and the source contracts
freeze. Real documents, external OCR, staging/production storage, and production worker
activation wait for the applicable rights, provider, retention, workload/storage,
privacy, and runtime gates.

Deliver:

- Rights declaration
- Private signed uploads
- Quarantine and validation
- Provider-neutral extraction adapter
- OCR fallback
- Canonical JSON and Markdown
- Pages, elements, sections, chunks
- Ingestion review UI

Pinecone/vector indexing is excluded unless F-005 quality planning proves it necessary
and a separate gate enables it.

Exit criteria:

- Golden files meet extraction and citation thresholds.

## Phase 8 — AI course blueprint

**Focused MVP planned.** Provider-neutral contracts, deterministic fakes, run
provenance, and rights-cleared evaluation fixtures may proceed after the normalized
source and course-draft contracts freeze. Provider-connected generation waits for the
approved provider/model and locked numeric evaluation gates.

Deliver:

- Prompt registry
- Model adapter
- Generation runs and steps
- Source analysis
- Blueprint generation
- Instructor blueprint editor and approval
- Cost and usage tracking

Exit criteria:

- Approved blueprint maps every item to source sections.

## Phase 9 — Structured lesson generation and canonical draft review

**Focused MVP planned.** It depends on the minimal canonical course lifecycle and the
approved blueprint/draft contracts. Provider-backed integration or release requires
immutable provenance, human-only publication, evaluation, and rights-removal proof.

Deliver:

- Lesson artifacts
- Citation validation
- Artifact review and diff
- Canonicalization into course draft version

Quiz, assignment, and assessment generation remain outside the focused MVP.

Exit criteria:

- No AI content can publish without recorded human approval.

## Phase 10 — AI course companion

**Deferred and disabled.** Course-version isolation, retrieval reauthorization and locked evaluation thresholds are prerequisites.

Deliver:

- Assistant configuration
- Authorized retrieval
- Pinecone search and reranking
- Streaming answers
- Citations
- Feedback
- Evaluation dashboard
- Prompt-injection defenses

Exit criteria:

- RAG evaluation passes faithfulness, citation, refusal, and isolation thresholds.

## Phase 11 — Scale and hardening

Deliver:

- Performance tuning
- Read models and caching
- Queue flow control
- Disaster recovery drill
- Penetration test
- Accessibility audit
- Cost monitoring
- Complete and exercise scale/provider/conditional-capability runbooks; core runbook work began in Phase 0

Exit criteria:

- Production readiness review is approved.

## Capability traceability (CHG-031)

| Capability | Domain/authority | Schema/API | Required proof | Phase/disposition |
|---|---|---|---|---|
| Auth/tenant/membership/roles | Identity/tenancy; PostgreSQL + Supabase Auth identity | Core tenancy dictionary; `/auth-context`, tenants/memberships | JWT + production-role RLS/composite-FK/JIT matrix | 0–1 core |
| Manual contract/entitlement/onboarding | Tenancy/entitlement | tenant lifecycle/step/entitlement tables and commands | Retry/compensation/reconcile + access-before-entitlement denial | 1 core |
| Manual course/review/publication | Course/curriculum | immutable course version + transition commands | Actor/state/hash/concurrency/rights/assessment tests | 2 MVP |
| Enrollment/player/progress | Learning | enrollment pinned to version + progress commands | Cross-tenant/read-after-write/idempotency journeys | 3 MVP |
| Quizzes/assessments | Assessment | future versioned question/attempt contracts | Separate product decision plus constraint/scoring/concurrency/Playwright evidence | 4 deferred increment |
| Certificates/advanced grading/live links/custom domains | Learning/tenancy | feature-specific dictionary/API | Phase-specific authorization/accessibility/domain proof | post-launch increment |
| Paid commerce/tenant recurring billing | Finance/entitlement | future inbox/state/ledger/refund/subscription APIs | Q-05 + provider sandbox + property/concurrency/reconcile | 5–6 deferred |
| Instructor marketplace/payouts | Marketplace finance | no MVP schema/API | Linked accounts/legal/tax/settlement proof | outside initial roadmap |
| PDF source admission/ingestion/OCR | Content intelligence | documents 06/08 source schema/API/jobs | P-009/P-011 + upload/rights/removal/worker evidence; external/production gates remain | 7 focused MVP |
| Structured course generation/review | Content intelligence/course | run/lineage/evaluation/artifact and canonical-draft APIs | P-002/P-009 + Q-P01/Q-P04/Q-P07 + immutable provenance + human-only publication | 8–9 focused MVP; provider/release gated |
| Vector indexing for generation | Content intelligence | vector manifest/reconcile contract only if enabled | F-005 necessity evidence plus rights/removal/provider/evaluation proof | deferred unless proven necessary |
| AI companion/RAG | Learning intelligence | future conversation/retrieval/citation APIs | Course-version zero-leak, DB reauth, deletion and locked eval | 10 deferred |

Each implemented row must expand to exact model/migration, endpoint/event, test, dashboard/runbook and evidence paths in the Phase manifest. Unmapped tables/routes are rejected or explicitly deferred.

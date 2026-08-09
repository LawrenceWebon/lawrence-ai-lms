# Monorepo and Folder Architecture

Status: **approved target layout; Phase 0 scaffold and CI evidence do not yet exist**  
Related findings and decisions: H-03, H-21, D-003, D-009, CHG-016, CHG-030, CHG-040

The tree in this document is a target, not a claim about the current documentation-only repository. Phase 0 creates it incrementally. Initial scaffolding contains only the private-LMS domains approved in document 00; commerce, source ingestion, AI generation, RAG, payouts, Realtime, and other deferred capabilities must not gain deployable routes, jobs, credentials, or provider configuration until their gates close.

## Target repository tree

```text
lms-saas/
├── apps/
│   ├── web/                              # Next.js App Router
│   ├── api/                              # FastAPI composition/HTTP entrypoint
│   ├── admin/                            # Django Admin entrypoint
│   ├── worker/                           # approved background process entrypoints
│   └── e2e/                              # Playwright projects and fixtures
├── packages/
│   ├── api-client/                       # generated from committed OpenAPI
│   ├── ui/                               # shared application UI
│   ├── config-eslint/
│   ├── config-typescript/
│   └── test-data/                        # synthetic builders; no production exports
├── backend/
│   ├── pyproject.toml
│   ├── manage.py
│   ├── src/lms/
│   │   ├── config/
│   │   ├── api/
│   │   ├── application/                  # execution context, unit of work, command bus
│   │   ├── common/                       # stable primitives with multiple consumers
│   │   ├── modules/                      # bounded domain modules
│   │   ├── platform_database/            # shared DB objects through Django migrations
│   │   ├── integrations/                 # provider adapters implementing domain ports
│   │   ├── workers/                      # task adapters; no independent business rules
│   │   └── observability/
│   └── tests/
├── contracts/
│   ├── openapi/                          # generated OpenAPI, baseline, compatibility report
│   ├── events/                           # versioned JSON Schemas and examples
│   └── providers/                        # sanitized signed-request/response fixtures
├── database/
│   ├── README.md                         # ownership and generation rules
│   ├── generated/                        # ERD, dictionary, schema snapshot, fingerprint
│   ├── security/                         # object-to-migration/grant/RLS/helper catalog
│   ├── seeds/                            # deterministic non-production seeds
│   └── fixtures/                         # synthetic database test fixtures
├── evals/
│   ├── ingestion/                        # deferred golden files and expected structure
│   ├── retrieval/                        # deferred rights-cleared RAG cases
│   ├── generation/                       # deferred locked generation cases
│   └── adversarial/                      # authorization/upload/prompt abuse cases
├── infra/
│   ├── docker/
│   ├── terraform/
│   ├── cloudflare/
│   ├── vercel/
│   ├── supabase/                         # platform/local config, never app-DDL history
│   └── monitoring/
├── docs/
│   ├── README.md
│   ├── plan/
│   ├── adr/
│   ├── api/
│   ├── threat-models/
│   ├── runbooks/
│   └── evidence/
├── scripts/
├── .github/workflows/
├── compose.yaml
├── Makefile
├── README.md
└── .env.example                       # names/examples only; never real secrets
```

## Database artifact ownership

There is one application migration authority: Django. The repository layout must not create an executable `database/migrations`, `supabase/migrations`, ad hoc SQL-deploy, or startup-migration path.

| Artifact | Canonical location | Rule |
|---|---|---|
| Domain tables, constraints and indexes | Owning module's `migrations/` | Django migration graph is executable authority. |
| Shared schemas, roles, grants, RLS, helpers, triggers, extensions and bucket metadata | `backend/src/lms/platform_database/migrations/` | Use reviewed `RunSQL`/`RunPython`; order dependencies explicitly. |
| Security object inventory | `database/security/` | Review catalog maps every object to its Django migration, owner, grants, policy and tests; it is not independently deployed. |
| Data dictionary, ERD and schema fingerprint | `database/generated/` | Generated from the migrated database; CI fails on unexplained drift. |
| Supabase project/local configuration | `infra/supabase/` | Supabase CLI may provision/test platform configuration but never owns application DDL. |
| Test data | `database/seeds/`, `database/fixtures/`, `packages/test-data/` | Synthetic and deterministic; production data is prohibited. |

Every SQL object has exactly one owning Django migration and one owning module. Generated snapshots carry a generated-file header and are never edited manually.

## Backend structure

```text
backend/src/lms/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── test.py
│   │   └── production.py
│   ├── logging.py
│   ├── urls.py
│   └── asgi.py
├── api/
│   ├── dependencies/                    # JWT identity, trusted host/route selector
│   ├── middleware/                      # request/correlation IDs; no tenant authority
│   ├── errors/
│   ├── routers/v1/
│   └── openapi.py
├── application/
│   ├── context.py                       # verified identity -> authorized DB context
│   ├── unit_of_work.py                  # transaction + SET LOCAL + membership reread
│   ├── commands.py
│   └── outbox.py                        # durable dispatch signal/poller
├── common/
│   ├── database/
│   ├── exceptions/
│   ├── idempotency/
│   ├── money/
│   ├── pagination/
│   ├── security/
│   ├── storage/
│   └── types/
├── modules/
│   ├── identity/
│   ├── tenancy/
│   ├── organizations/
│   ├── assets/
│   ├── catalog/
│   ├── courses/
│   ├── curriculum/
│   ├── enrollments/
│   ├── learning/
│   ├── assessments/
│   ├── auditing/
│   └── notifications/
├── platform_database/
│   ├── migrations/
│   └── tests/
├── integrations/
│   ├── supabase/
│   ├── resend/
│   ├── upstash/
│   ├── sentry/
│   └── posthog/
├── workers/
│   ├── dispatch/
│   ├── notifications/
│   └── maintenance/
└── observability/
```

Modules for assignments, gradebook, certificates, commerce, payments, subscriptions, ledger, payouts, documents, course generation, AI companion, live-provider integrations, or other post-MVP scope are added only in the phase that owns them and only after the corresponding decision and release gates close. A future module is documented in the scope catalog; it is not pre-scaffolded as an accidentally enabled feature.

## Domain module structure

```text
modules/courses/
├── apps.py
├── models/
├── migrations/
├── services/                            # public commands and transaction coordinators
├── selectors/                           # optimized, side-effect-free reads
├── policies/                            # reusable authorization decisions
├── ports/                               # interfaces needed from other domains/providers
├── events/
├── admin/
└── tests/
    ├── unit/
    ├── integration/
    ├── api/
    ├── permissions/
    └── concurrency/
```

HTTP routers and worker task adapters live outside the module or in an explicitly adapter-only package. They may parse/validate transport input and call a public service; they may not write ORM models directly.

## Next.js structure

```text
apps/web/src/
├── app/[locale]/
│   ├── (marketing)/
│   ├── (auth)/
│   ├── (student)/dashboard/
│   ├── (instructor)/instructor/
│   ├── (tenant-admin)/organization/
│   └── (platform-admin)/platform/
├── features/
│   ├── auth/
│   ├── courses/
│   ├── learning/
│   └── assessments/
├── components/
├── lib/
│   ├── api/generated/                   # generated; never manually edited
│   ├── supabase/                        # Auth/session and signed Storage only
│   ├── auth/
│   ├── tenant/
│   └── observability/
├── messages/
└── types/
```

Deferred UI feature folders such as `checkout`, `documents`, `course-generation`, and `ai-companion` are created only when their capability is enabled. Browser code never imports a database client for core-table reads or writes.

## Contract, test, and evidence locations

| Concern | Required location/evidence |
|---|---|
| HTTP contract | `contracts/openapi/` source snapshot, lint result, compatibility baseline and generated-client checksum |
| Domain events | `contracts/events/<event>/<version>.schema.json` plus producer/consumer fixtures |
| Provider events | Sanitized raw-body/header/signature fixtures under `contracts/providers/`; secrets are never committed |
| RLS/tenant safety | Production-role matrix tests in the owning backend module plus the `database/security/` catalog |
| Threat models | `docs/threat-models/` with assets, actors, trust boundaries, abuse cases and control/test IDs |
| Operations | `docs/runbooks/` with detection, safe actions, escalation, recovery and evidence capture |
| Release proof | `docs/evidence/` indexes immutable CI/deploy artifacts; large or sensitive reports remain in the approved artifact store |
| AI quality | `evals/` contains only rights-cleared, versioned fixtures after AI gates close |

## Dependency and folder rules

- Allowed direction is entrypoint/adapter → application service → domain policy/model → common primitive. Provider adapters implement domain ports; domain code does not import provider SDKs.
- A domain may use another domain only through its documented public service, selector, port, or event contract. Direct cross-domain model mutation and circular imports are prohibited.
- No generic `utils.py` dumping ground. Shared primitives need at least two real consumers and a named owner.
- Generated OpenAPI clients, schema snapshots, manifests and ERDs are never manually edited.
- Environment-specific values come from validated settings; provider secrets do not appear in source, fixtures, docs, build logs or frontend bundles.
- DreamsLMS vendor assets stay isolated under `vendor-theme/` until converted into reviewed application components; vendor code never becomes an authorization or domain layer.
- Operational procedures belong in runbooks, architectural choices in ADRs, contracts in `contracts/`, and generated proof in the evidence index. Do not duplicate the same authority in feature READMEs.

## Phase 0 scaffold acceptance

The proposed layout becomes implemented only when:

1. every committed path has an owner and current launch/deferred classification;
2. import-boundary checks reject forbidden domain/provider dependencies;
3. Django migration checks prove there is no second application-DDL history;
4. OpenAPI/event generation and compatibility checks run in CI;
5. schema/security catalogs and the document manifest reproduce without drift;
6. synthetic unit, integration, production-role RLS, concurrency and Playwright test locations execute in CI;
7. deferred feature routes/jobs/configuration are absent or hard-disabled; and
8. the Phase 0 evidence manifest links exact commands, artifacts and results.

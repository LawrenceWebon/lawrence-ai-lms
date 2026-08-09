# Domain Module and Transaction Design

Status: **approved domain and transaction contract; implementation/tests pending**  
Related findings and decisions: C-02, C-04, G-003, G-004, D-001–D-004, D-006, CHG-005, CHG-016, CHG-019, CHG-044

Use lightweight command/query separation inside the modular monolith. There is no framework-specific command bus requirement, but every entrypoint uses the same authenticated execution-context and unit-of-work contract. HTTP routers, Django Admin actions, management commands, scheduled jobs, and worker handlers cannot create alternate authorization or transaction paths.

## Dependency direction

```text
FastAPI / Django Admin / worker task / management command
                         |
                         v
               application command service
                         |
             +-----------+-----------+
             v                       v
       domain policy/model      domain public port
             |                       ^
             v                       |
       common primitives       provider adapter
```

- Entrypoints parse transport input, authenticate the caller/message, and call one public application service.
- Application services coordinate authorization, transactions, idempotency, locks, domain mutations, audit and outbox records.
- Domain models and policies own invariants and cannot import FastAPI, provider SDKs, task runners, or presentation schemas.
- Integrations implement domain ports and return normalized typed results. Raw SDK objects do not cross into domain code.
- A module may not mutate another module's models directly. Cross-module writes use an explicit coordinator and the owning module's public command API inside the same unit of work.
- Import/lint rules and architecture tests reject cycles and forbidden adapter-to-model shortcuts.

## Execution context

The browser, JWT custom claims, host header, route parameter, job payload, and provider payload are untrusted selectors—not tenant authority. Every entrypoint produces an identity candidate and passes it to the shared unit-of-work wrapper.

An authorized context contains, at minimum:

```text
principal_type                  # user, service, privileged_operator
principal_id
initiating_user_id null         # audit lineage only; never service authorization
tenant_id
membership_id null              # mandatory for user principals
request_or_job_id
correlation_id
authentication_time / assurance_level
granted scopes
optional JIT privileged_access_grant_id
```

For an interactive request, `principal_id` is the verified Supabase subject and the membership is mandatory. For a worker, it is a registered service identity constrained by component role, claimed job, tenant and stage; the user who initiated a job is audit lineage, not current worker authority. The wrapper constructs context only after it:

1. verifies the pinned JWT or signed internal/provider message contract;
2. resolves the normalized host/route to a candidate tenant server-side;
3. acquires one connection as the approved non-owner/non-`BYPASSRLS` runtime role and begins a transaction;
4. validates and sets actor, tenant, request/job and optional JIT IDs with transaction-local settings;
5. re-reads active user, membership, entitlement, resource ownership, assurance and JIT grant from PostgreSQL in that transaction; and
6. fails closed for missing, stale, mismatched, expired, revoked, or pool-contaminated context.

Workers repeat authorization at execution time. An enqueue-time decision, cached membership, namespace, tenant ID in a payload, or privileged dispatcher credential never carries authorization forward.

The identity bootstrap has one narrow exception before a tenant is selected: an
authenticated actor may list only their own minimal membership candidates or accept a
presented invitation. These operations set actor/request context, use dedicated
least-granted services or fixed-search-path helpers, return no tenant content, and
derive/re-verify the tenant before any tenant-owned mutation. They do not create a
general actor-only query path or an authorized tenant context.

## Commands and services

Services change state. A top-level command service owns one unit of work; nested domain operations join it and may neither commit nor open an independent correctness transaction.

```python
def publish_course(
    *,
    context: AuthorizedContext,
    course_id: UUID,
    expected_row_version: int,
    idempotency_key: str,
) -> PublishedCourse:
    ...
```

A command service must:

1. state its owning domain and transaction owner;
2. re-check policy and resource relationship using current database state;
3. reserve/verify an idempotency record when replay could duplicate an effect;
4. validate business invariants and enabled-capability gates;
5. lock rows or use an expected version when concurrent modification is possible;
6. call only approved module interfaces;
7. write domain records, immutable audit facts and durable outbox events atomically; and
8. return a domain result without performing a provider call while the transaction is open.

Validation in a router, UI, serializer, model callback, or task wrapper is additional defense; it never replaces service and database enforcement.

## Selectors

Selectors return optimized read models and have no business-state side effects.

```python
def get_student_course_dashboard(
    *, context: AuthorizedContext, student_id: UUID
) -> StudentCourseDashboard:
    ...
```

Selectors:

- accept the authorized context rather than a caller-trusted tenant ID;
- retain RLS and relationship authorization;
- declare query shape, index and maximum result/cursor behavior;
- may use caches only under document 13's allowlist; and
- may use replicas only for explicitly approved stale-tolerant catalog/analytics paths.

Authorization/membership, entitlement/money, grade/progress read-after-write, course publication, job claims, privileged access and other correctness reads stay on the primary.

## Policies

Policies answer reusable authorization and lifecycle questions for services, Admin, workers, and tests.

```python
def can_publish_course(
    *, context: AuthorizedContext, course: Course, version: CourseVersion
) -> PolicyDecision:
    ...
```

A policy returns an allow/deny decision plus stable reason code and relevant rule/version. It is deny-by-default, checks tenant/resource relationship and current state, and does not perform a mutation or call a provider. Database constraints and RLS still enforce their independent boundaries.

## Transaction patterns

### Local atomic command

Use one short PostgreSQL transaction when every correctness fact is local:

```text
authorize/current-state read
  -> reserve idempotency
  -> lock or compare version
  -> mutate owning-domain facts
  -> write audit + outbox
  -> commit
  -> signal dispatcher after commit
```

Examples include quiz submission/scoring, assignment grade plus history, course-version approval/publication pointer, and enrollment progress updates. A failure rolls back all local facts.

### External-provider saga

Never keep a database transaction open across HTTP, email, object, queue, payment, AI, OCR, or vector-provider calls.

```text
transaction A: validate + create durable intent/outbox -> commit
external step: adapter call with stable idempotency key
transaction B: record normalized observation/result -> commit
provider event/reconciliation: converge authority and schedule next step
```

The owning saga records step, attempt, input/output hashes, idempotency key, lease/checkpoint, retry class, compensation, reconciliation and terminal evidence. A timeout means “unknown” until retrieval/reconciliation proves the provider state; it is not treated as failure or success by guesswork.

### Provider-event reduction

Webhook admission verifies the exact raw-body signature/freshness contract, reserves a unique provider/environment event ID plus body hash, persists the observation, and acknowledges according to the provider contract. A separate idempotent reducer locks the inbox item and applies normalized state transitions in one transaction. Duplicate same-ID/same-hash delivery returns the stored result; same ID/different hash is an integrity incident. Out-of-order gaps remain pending and reconcile against the provider or local authority.

## Outbox and after-commit semantics

- The domain change, audit fact and outbox row are inserted in the same transaction.
- Django `transaction.on_commit` may wake a dispatcher only after a successful commit. It is an optimization, not durable delivery; a database poller recovers a failed or lost wake-up.
- A rollback creates no externally visible event. Consumers never observe an uncommitted domain fact.
- Dispatch uses leases, bounded retries/backoff, attempt history, payload hash and destination-specific idempotency.
- Consumers reserve their inbox before effects and record completion atomically with local changes.
- Events are completed facts in the versioned envelope defined by document 11; commands such as “send email” are explicit outbox intents rather than misleading facts.
- Payloads contain the minimum identifiers/classification needed by the consumer, never secrets or unrestricted source, chat, assessment, grade, or payment data.

## Saga ownership

| Workflow | Owning coordinator | Local authority | External effect | Current disposition |
|---|---|---|---|---|
| Tenant onboarding/suspension/closure | Tenancy | Tenant, entitlement, domain and step records | Auth/domain/email provisioning | Initial MVP; provider steps require approved configuration |
| Transactional email | Notifications | Outbox, preferences, delivery observations | Resend send/retrieve | Initial MVP after privacy/domain/retention gates |
| Custom-domain activation/removal | Tenancy | Domain claim/lifecycle events | Cloudflare hostname/certificate | Post-launch |
| Payment/refund/entitlement | Commerce/Finance | Order, event inbox, ledger and entitlement | PayMongo | Deferred and disabled |
| PDF source ingestion/OCR | Documents | Job and source/artifact manifests | Storage/OCR adapter | Focused MVP; external provider/real-data/production gated |
| Vector indexing | Documents | Vector generation/reconcile manifests | Pinecone | Deferred unless F-005 proves necessary |
| Rights invalidation/takedown | Content Rights | Authorization, impact graph/items and audit | Object/vector/provider removal | Focused MVP safety requirement; production evidence pending |
| Structured course generation/review | Course Generation | Run snapshot, lineage, artifacts and approval | Model provider adapter | Focused MVP; provider-backed integration/release gated |

No workflow uses Redis, QStash, email, analytics, a provider redirect, or Pinecone as its saga state or business authority.

## Bounded contexts

| Context | Owns | Initial disposition |
|---|---|---|
| Identity | User profile, preferences and consent links; Supabase Auth owns credentials/session identity | launch |
| Tenancy | Tenant, domain, membership, role, permission, scope, local entitlement, privileged grants | launch |
| Organizations | Branch, department, program, period and group | launch as required by approved MVP slice |
| Assets | Object inventory, purpose, ownership, access grants and trusted/quarantine state | launch minimum |
| Courses | Stable course identity, immutable versions, instructors, review and publication pointer | launch |
| Curriculum | Sections, lessons, content blocks and resources | launch |
| Learning | Enrollment, version pin, progress, paths, notes and sessions | launch minimum |
| Assessments | Question versions, quizzes, attempts, answers and server-side scoring | deferred focused-product increment |
| Assignments/Gradebook/Certificates | Submissions, rubric/grade history and credentials | post-launch increment |
| Communication/Notifications | Announcements, message intent, preferences and delivery observations | launch minimum email; broader features later |
| Commerce/Finance | Product/order, payment facts, ledger, refund, settlement and entitlement projection | deferred and disabled |
| Documents/Content Rights | Source authorization, immutable PDF versions, extraction, optional segments and takedown | focused MVP; provider/production gated |
| Course Generation | AI run, blueprint/artifact lineage, evaluation and review workflow | focused MVP; provider-backed integration/release gated |
| AI Companion | Configuration, conversation, retrieval, citation and feedback | deferred and disabled |
| Operations | Provider inbox/outbox, job execution, audit and operational evidence | launch minimum; feature-specific parts gated |

## Cross-domain transaction ownership

| Invariant | Transaction owner | Required atomic facts |
|---|---|---|
| Course publication | Courses | approved immutable hash/version, publication pointer, audit and outbox |
| Quiz submission | Assessments | attempt snapshot, answers, score/result, grade/progress effect when applicable, audit/outbox |
| Assignment grading | Assignments/Gradebook | grade decision, immutable history, aggregate projection and audit/outbox |
| Tenant activation | Tenancy | active local entitlement + readiness state; provider provisioning remains saga steps |
| Future payment fulfillment | Commerce/Finance | accepted normalized event, balanced ledger, order/payment reduction, entitlement period and outbox |
| Future AI canonicalization | Courses coordinated with Course Generation | approved artifact/version/hash, normalized lineage, canonical draft/version and audit/outbox |

“Where possible” is not a transaction rule. If required local facts share PostgreSQL, they commit together under the named owner. External effects are saga steps after commit. If a future service split makes that impossible, a superseding ADR must specify consistency, compensation and failure ownership.

## Django, FastAPI, Admin, and worker boundary

- Django owns models, migrations, domain/application services, selectors, policies and Admin registration.
- FastAPI owns request parsing, authentication dependencies, response schemas, OpenAPI and HTTP behavior; routers call the shared unit-of-work/command boundary.
- Django Admin actions invoke the same services and require explicit current actor/tenant/JIT context for sensitive operations. Critical status fields are not editable through generic model forms.
- Workers validate signed delivery, claim the durable PostgreSQL job, reconstruct current authorization/context and call the same services. Task code cannot write models or call providers outside the owning saga adapter.
- Pydantic/event/provider schemas are transport contracts, not duplicate ORM/domain models.
- Django model signals are not used to hide cross-domain workflows or provider effects. Explicit services and outbox records make ordering and evidence visible.

## Required architecture tests and evidence

Before Phase 1 exit, provide:

1. API, Admin and worker tests proving the same command cannot bypass policy/service boundaries;
2. missing/wrong/stale tenant, membership, entitlement, resource and JIT-context negative tests under production roles;
3. session/transaction pool reuse tests proving context cannot bleed between requests;
4. duplicate/idempotency and concurrent-version/row-lock tests for each critical command;
5. commit/rollback tests proving outbox atomicity and a failed `on_commit` wake-up is recovered by polling;
6. fault tests proving no provider call occurs before commit or while a business transaction is held;
7. webhook duplicate, hash-conflict, out-of-order, poison and reconciliation tests for each enabled provider;
8. import-boundary tests rejecting router/task/Admin direct writes and domain-to-provider imports; and
9. traceability from command/service to invariant, migration, RLS policy, contract, test, alert/runbook and immutable CI result.

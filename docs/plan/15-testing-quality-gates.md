# Testing and Quality Gates

Status: **approved verification design; no implementation evidence exists**  
Change IDs: CHG-038, CHG-046

## Test pyramid

### Python unit tests

- Domain services
- Policies
- Value objects
- Chunking logic
- Prompt-output validation
- Payment calculations
- Completion rules

### Database integration tests

- Django models and constraints
- Transactions and row locks
- RLS policies
- Migrations
- Outbox behavior
- Payment idempotency
- Course-version immutability

### FastAPI tests

- Authentication dependencies
- Tenant resolution
- Error format
- OpenAPI contract
- Permission matrix
- Upload and webhook validation

### Playwright tests

Critical journeys:

Only journeys 1–5 (adapted to private/manual onboarding) are core-MVP candidates. Payment, ingestion, generation and RAG journeys are non-applicable until their feature gates close; they must not be treated as launch evidence merely because they appear in this future test catalog.

1. Tenant registration and owner login
2. Invite instructor and student
3. Create and publish a manual course
4. Enroll and complete a lesson
5. Complete a quiz
6. Purchase a course through sandbox checkout
7. Upload a book
8. Review ingestion result
9. Approve generated blueprint
10. Review and publish generated lesson
11. Ask the course companion and open citations
12. Change locale and verify RTL

## Ingestion golden files

Maintain legal test documents representing:

- Text PDF
- Scanned PDF
- Multi-column PDF
- Table-heavy PDF
- EPUB
- DOCX
- Corrupted document
- Password-protected document
- Mixed language

Assert:

- Page count
- Heading hierarchy
- Text coverage
- Table structure
- Stable chunk IDs or checksums
- Page citations
- No duplicate elements

## RAG evaluation

Test cases include:

- Answer directly present in one chunk
- Answer spread across several sections
- Unsupported question
- Ambiguous question
- Prompt injection embedded in source
- Attempt to access another course
- Attempt to access another tenant
- Citation mismatch
- Question in another locale
- Graded-assessment answer request

## Generated-course evaluation

Score:

- Blueprint coherence
- Objective coverage
- Lesson-source alignment
- Duplicate content
- Citation validity
- Question correctness
- Difficulty alignment
- Instructor edit distance

## Performance tests

Add load tests for:

- Course catalog
- Course player progress updates
- Chat streaming
- Payment webhooks
- Bulk enrollment
- Book upload initiation

Load acceptance uses document 27's baseline, expected, 3× and whale profiles plus document 28's production-shaped data/restore sizes. A synthetic request count without the approved mix, tenant skew, provider tiers, commit/config IDs and correctness assertions is not capacity evidence.

## Mandatory security and integrity suites (CHG-046)

| Suite | Minimum proof | Release effect |
|---|---|---|
| JWT/Auth | Wrong issuer/project/audience/algorithm/key/time, rotation failure, revoked user/session, stale membership | Non-waivable core gate |
| PostgreSQL tenant/RLS | Real PostgreSQL; API/worker/reconciler/analytics/JIT roles; missing context; cross-tenant CRUD/FKs/views/helpers; pool reuse/reset | Non-waivable core gate |
| Privileged access | AAL2 request/approval/scope/expiry/revoke/dual approval/break-glass and immutable events | Non-waivable core gate |
| Schema/migration | Named constraints/indexes, same-tenant FKs, state invariants, forward/rollback/roll-forward, lock budget and drift fingerprint | Non-waivable affected gate |
| Publication | Manual/AI path parity, actor separation, immutable hash, stale/concurrent transitions, rights/evaluation invalidation | Non-waivable before publish |
| Payments | State-model contract, raw signature/replay, duplicate/out-of-order events, property/concurrency tests, balanced ledger, exactly-once entitlement, refund/reconcile | Required only before commerce; cannot be waived |
| Upload/ingestion | MIME/magic/polyglot/archive/page/pixel/malware/sandbox limits, orphan reconcile, stage retry/lease/checkpoint | Required only before ingestion; cannot be waived |
| AI/RAG | Rights operations, immutable run lineage, locked numeric evaluations, cross-tenant/course/version zero-leak, prompt injection, citation-open auth, human-only publish | Required only before AI; cannot be waived |
| Removal/deletion | Rights expiry/revoke through objects/vectors/published citations; DSAR/legal hold/backups/restored tombstones/provider reconcile | Non-waivable for enabled data classes |
| Resilience/recovery | Provider timeouts/retries/circuit breakers, queue poison/replay, worker drain, DB/object isolated restore and achieved RPO/RTO | Non-waivable production gate |
| Accessibility | Automated axe plus manual keyboard/focus/screen-reader/zoom/reflow/captions and representative-user evidence | Non-waivable WCAG gate |

Tests record code/migration/config/provider fixture versions and run as production-equivalent roles. Mocks supplement but do not replace real PostgreSQL policies/constraints, live sandbox signature contracts or isolated restore drills.

## CI quality gates

Backend:

```text
ruff check
ruff format --check
mypy --strict
pytest
python manage.py makemigrations --check
python manage.py check --deploy
```

Frontend:

```text
eslint
tsc --noEmit
unit tests
next build
playwright smoke
```

Security:

```text
secret scan
dependency scan
container scan
SAST
RLS matrix
```

Critical tenancy and enabled enrollment/publication tests must pass before merge. Payment, certificate, ingestion and AI suites are `not_applicable` only while those capabilities are absent and hard-disabled; each becomes mandatory before its first implementation can merge or deploy.

### Non-waivable release evidence

CI/release artifacts link exact commands/results for lint/type/unit/integration, schema drift and migrations, OpenAPI/event compatibility, production-role RLS matrix, security/dependency/license/container scans, applicable property/concurrency/evaluation/load/accessibility/recovery suites, build/image/SBOM/provenance, deployment smoke, dashboards/runbooks and rollback/roll-forward proof. A gate may be `not_applicable` only when its capability is absent and disabled; it cannot be marked passed without evidence. P0 tenant, payment, AI-provenance/human-publication and recovery gates cannot be waived.

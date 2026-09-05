# Local Backend MVP Completion Evidence

Status: **local implementation and verification complete; PR #59 dependency open**

Date: 2026-09-05

Issue: [#63](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/63)

PR: [#64](https://github.com/LawrenceWebon/lawrence-ai-lms/pull/64)

Contract: [backend execution contract](../features/backend-mvp-completion-execution.md)

## Scope and revisions

The branch delivers the local synthetic PDF admission, extraction, deterministic
generation, human canonicalization, course publication, and learner backend path.
The parser is `pypdf==6.16.2`; the generation adapter is
`deterministic-source-course-v1`, with no external model or OCR provider.

| Checkpoint | Commit | Result |
|---|---|---|
| Contract freeze | `479440c` | Owner-authorized scope and resource contract |
| Enrollment/digest remediation | `9d5861b` | Implements the #60/#62 remediation scope |
| Strict parser admission | `c4dec9a` | Implements the parser selection/remediation scope of #61 |
| Extraction/normalization | `95ca9d4` | Durable local ingestion and normalized source records |
| Structured generation | `5c839e4` | Source-grounded deterministic drafts and human blueprint review |
| Human canonicalization | `4d3bbb5` | Editable canonical drafts, immutable origin evidence, publication rights guards |
| Backend integration proof | This evidence revision | Full PDF-to-learner HTTP journey, migration restoration, and regression verification |

The first five commits predate this resumed verification session. Their original
RED runs are not reconstructed or claimed as newly observed. The current full checks
verify the resulting implementation; the newly observed reproductions are below.

## Reproductions and fixes

- Removing generated curriculum failed with Django `RestrictedError` on the origin
  edge's content-block FK. The edge now stores immutable historical target IDs, with
  a database insert trigger locking and validating the exact tenant, version,
  section/lesson/block hierarchy, and artifact document. Durable source, artifact,
  run, course, and version edges retain composite same-tenant foreign keys.
- Revoking `generate` authorization after human approval still allowed publication.
  The existing Courses command now locks and rechecks source rights for approval and
  publication. A database trigger applies the same rule to direct writes and follows
  the predecessor chain for successor drafts. No new publication route exists.
- Production-role course approval failed because submitter lookup read the general
  audit table. `courses.0004_submission_actor_lookup` exposes only the submitting
  actor for the authorized tenant/version. General audit reads remain unavailable.
- The F-003 browser positive fixture was a marker-only PDF without a valid xref. The
  strict parser correctly rejected it. The browser now uses the committed synthetic
  parser-valid PDF: 1,073 bytes, SHA-256
  `3be1c6ba99cbc5f4ccf3d75257baaefd8bab593082b2f2a1aea662a13c1cf115`.
- The document rollback test must restore the complete migration graph now that
  generation depends on documents. Its finalizer restores all recorded leaf targets.
- Permission/capability assertions and schema fingerprints were aligned with the
  enabled F-004/F-005 implementation. Other deferred capabilities remain prohibited.

The curriculum-removal and revoked-rights tests first produced **2 failed, 1 passed**,
then **3 passed** after the fixes. The subsequent canonicalization/course/schema and
production-role gate produced **168 passed**. This includes atomic rollback after a
synthetic fact failure, stale revision/hash rejection, immutable provenance, forged
target denial, and successor/direct-publication denial.

## Reproduction environment and commands

All project commands run in the existing task Compose services at
`/home/lawrence/Project Neo/worktrees/ai-lms/backend-mvp-LMS-63`, with
`COMPOSE_PROJECT_NAME=ai-lms-lms-63` and PostgreSQL port `55263`.
Host scratch is `/home/lawrence/Project Neo/tmp/LMS-63`.

The host has neither `make` nor `pwsh`. The equivalent commands from each Make target
were executed through Compose. Documentation uses the repository's equivalent Python
checker; CI remains responsible for the exact PowerShell checks.

```bash
docker compose exec -T backend ruff check backend scripts tests
docker compose exec -T backend ruff format --check backend scripts tests
docker compose exec -T backend mypy --config-file backend/pyproject.toml backend/src scripts
docker compose exec -T backend python scripts/check_architecture.py
docker compose exec -T backend python scripts/check_migration_authority.py
docker compose exec -T backend pytest backend/tests tests -m 'not rls' --tb=short -q --reuse-db
docker compose exec -T backend python backend/manage.py migrate --noinput
docker compose exec -T backend pytest backend/tests -m rls --tb=short -q
docker compose exec -T backend python backend/manage.py makemigrations --check --dry-run
docker compose exec -T backend python scripts/generate_openapi.py --check
docker compose exec -T web ./scripts/check_openapi_client.sh
docker compose exec -T web npm run lint
docker compose exec -T web npm run typecheck
docker compose exec -T web npm run build --workspace @ai-lms/web
docker compose exec -T web npm run test:e2e --workspace @ai-lms/e2e -- \
  f001-foundation.spec.ts f001-integration.spec.ts f001-lane-d.spec.ts \
  f002-course-editor.spec.ts f003-source-admission.spec.ts \
  f007-learner-playback.spec.ts --workers=1
docker compose exec -T backend python scripts/docs_check.py --write-manifest
docker compose exec -T backend python scripts/docs_check.py
docker compose exec -T backend uv pip check
docker compose exec -T web npm audit --omit=dev --audit-level=high
docker compose exec -T backend python backend/manage.py check --deploy
git diff --check
git status --short --branch
```

The browser command passed **22 tests**. An initial combined run with six workers
caused the suites' shared resettable fixture to collide; the single-worker run
preserves the isolation normally supplied by the separate Make targets/CI jobs.

For concurrent RLS verification, the same task's disposable test database name is
explicitly set to `test_lms63_rls` before invoking pytest, so it cannot overlap the
non-RLS suite's `test_postgres`. Both use the recorded task Compose project. RLS
verification removed its temporary database on completion; the final non-RLS rerun
reuses `test_postgres` within this still-active task's disposable Compose database.
One earlier failed HTTP test had a transient teardown connection warning; a readback
after process exit confirmed no test-database connections remained.

The exact isolated RLS invocation was:

```bash
docker compose exec -T backend python -c 'from django.conf import settings; settings.DATABASES["default"]["TEST"] = {"NAME": "test_lms63_rls"}; import pytest; raise SystemExit(pytest.main(["backend/tests", "-m", "rls", "-q", "--tb=short"]))'
```

## Verification results

| Gate | Result |
|---|---|
| Canonicalization/course/schema/production-role focused suite | 168 passed |
| Full non-RLS suite | 650 passed, 38 deselected in 316.00 seconds |
| Full RLS suite | 38 passed in the isolated task test database |
| Complete backend PDF-to-learner HTTP journey | Passed, including persisted progress and private-resource denials |
| Generation and document migration reverse/forward | Passed, including complete-graph restoration in the full suite |
| Migration drift | No changes detected |
| Architecture and migration authority | Passed; 30 Django migration files |
| Backend Ruff/format and strict mypy | Passed; 96 source files typechecked |
| Web lint/typecheck/build | Passed |
| OpenAPI and generated TypeScript drift | Passed |
| F-001/F-002/F-003/F-007 browser regressions | 22 passed |
| Python installed dependency consistency | 53 packages compatible |
| pypdf license and OSV version query | BSD-3-Clause; no advisories returned for 6.16.2 |
| npm production dependency audit | Zero reported vulnerabilities |
| Added-line credential/private-key pattern inspection | No matches |
| Changed skills | None; skill validation not applicable |
| Final Markdown/manifest and exact diff | Passed; 95 versioned Markdown files; clean whitespace check |

The preceding full non-RLS run had 649 passes and one failure because the document
migration test restored only its own app, leaving dependent generation tables absent.
After correcting complete-graph restoration, the final equivalent full suite passed
all 650 tests. No production behavior was changed for this test-isolation correction.

The deployment check completed with seven warnings under local **test** settings:
W002, W004, W008, W009, W012, W016, and W020. This is not a passing production
configuration or launch approval. Advisory lookup results are time-specific and do
not substitute for a production supply-chain/security review.

## Limits, rollback, and remote actions

External OCR/model/storage/queue providers, real/private books, production activation,
provider-backed quality, numeric real-data evaluations, capacity/recovery/retention,
and the themed frontend remain outside this local delivery. The new full journey is
a backend HTTP/worker integration proof; the existing browser regressions do not claim
a newly implemented complete PDF-generation frontend.

Issues #60–#62 remain open and are linked as scope absorbed by PR #64; no completed
merge or independent approval is implied. PR #59 is still open. The execution contract
requires #59 to merge, then the latest `develop` to be integrated and all applicable
gates rerun before PR #64 becomes ready for review. This author does not approve or
merge either PR.

Rollback before merge is owner-directed branch/PR abandonment. After merge, use a
reviewed forward change to disable the local ingestion/generation composition while
preserving source rights, audit, provenance, published versions, and enrollment pins.
The task database's empty canonicalization migrations were reversed and reapplied to
refresh the local schema; both generation and canonicalization row counts were zero.
No application data was removed, and no other task resources were touched.

Remote actions before this evidence commit: GitHub reads and one progress/scope comment
on issue #63. Branch push, draft PR update, exact head SHA, and hosted CI outcomes are
recorded in the subsequent PR handoff. No approval, merge, or deployment is authorized
or claimed by this record.

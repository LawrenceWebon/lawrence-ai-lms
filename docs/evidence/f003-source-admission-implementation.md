# F-003 Local Source-Admission Implementation Evidence

Status: **local implementation candidate verified; protected PR checks and independent review pending**

- Evidence ID: `F003-LOCAL-IMPLEMENTATION-2026-08-22`
- Classification: internal, synthetic/local-only implementation evidence
- Issue: [#43](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43)
- Base: `b733f94718826d7c7f98e08e44285639ece07813`
- Implementation commit: `f4b3af0b7d4595617f4effcba1b263a02f04e540`
- Branch: `feature/LMS-43-f003-source-admission`
- Worktree: `/home/lawrence/Project Neo/worktrees/ai-lms/source-admission-LMS-43`
- Compose project/database port: `ai-lms-lms-43` / `55243`
- Host scratch: `/home/lawrence/Project Neo/tmp/LMS-43`
- Producer: #43 implementation context; not an independent reviewer or approver

The project-owner launch disposition is recorded in the
[#43 issue comment](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/43#issuecomment-5379136978).
It closes only the historical PR #53 launch hold and does not claim retroactive review
or approval. The implementation commit above is the immutable application-code input
to this evidence; the later documentation commit and exact draft-PR head must still be
recorded in the #43 handoff.

## Implemented boundary

The candidate adds the local Documents domain, Django-owned schema and forced RLS,
tenant-safe FastAPI/Admin composition, opaque upload targets, private local quarantine,
bounded byte-derived PDF inspection, durable validation/removal jobs, nine concrete
event contracts, generated OpenAPI/client types, and the minimal instructor/reviewer
browser journey. It preserves the frozen F-003 limits and does not add OCR, extraction,
generation, an external provider, or production enablement.

Storage, inspection, and removal I/O occur outside business transactions. Source,
version, declaration, authorization, upload-intent, storage-object, job, and attempt
edges use tenant-composite constraints. Runtime API and worker roles are non-owner;
forced RLS re-derives tenant, actor, token, job, and stage scope. Events and general
audit facts omit PDF content, full file names, rights evidence, bearer upload tokens,
and private object locators.

## Local verification

All project commands ran in the task's pinned Compose services. The task database was
rolled back through `documents zero` and forward through
`documents.0002_document_security` before the browser matrix so the live adapter used
the final migration SQL.

| Gate | Exact command/result |
|---|---|
| Focused F-003 | `pytest backend/tests/contracts/test_f003_contracts.py backend/tests/contracts/test_f003_event_contracts.py backend/tests/documents backend/tests/api/test_source_admission.py backend/tests/adapters/test_documents_admin.py backend/tests/integration/test_f003_source_admission.py -q` — 158 passed |
| Full non-RLS regression | `pytest backend/tests tests -m 'not rls' -q` — 568 passed, 26 deselected |
| Production-role RLS | `pytest backend/tests -m rls -q` — 26 passed, 555 deselected |
| Migration round trip | `python backend/manage.py migrate documents zero --noinput`; `python backend/manage.py migrate documents --noinput` — reverse and forward migrations passed |
| Migration drift | `python backend/manage.py makemigrations --check --dry-run` — no changes detected |
| Python lint/format | `ruff check backend scripts tests`; `ruff format --check backend scripts tests` — passed; 147 files formatted |
| Python types | `mypy --config-file backend/pyproject.toml backend/src scripts` — passed for 65 source files |
| Architecture/migration authority | `python scripts/check_architecture.py`; `python scripts/check_migration_authority.py` — passed; 15 Django migration files |
| OpenAPI/client drift | `python scripts/generate_openapi.py --check`; `./scripts/check_openapi_client.sh` — current |
| JavaScript/TypeScript | `npm run lint`; `npm run typecheck` — all workspaces passed |
| Production web build | `npm run build --workspace @ai-lms/web` — passed; `/source-documents` emitted as a dynamic route |
| F-001 browser regression | Playwright F-001 foundation/integration/lane-D specs — 12 passed |
| F-002 browser regression | Playwright `f002-course-editor.spec.ts` — 2 passed |
| F-003 browser journey | Playwright `f003-source-admission.spec.ts` — 5 passed |
| Diff and credential probes | `git diff --cached --check` and staged high-risk credential-pattern scan — passed with no match |
| Documentation | `python scripts/docs_check.py --write-manifest`; `python scripts/docs_check.py`; `git diff --check` — manifest generated and equivalent local link/manifest check passed for 92 files; PowerShell unavailable locally, so the exact PowerShell run remains for CI |

The F-003 browser cases prove separate reviewer activation, valid byte admission,
neutral cross-tenant denial, revocation/removal, rejection, cancellation, switched-user
reauthorization before restoring metadata, validation focus, 200% reflow, generated
client use, and absence of browser-persisted authorization/source state.

During verification, one abandoned command session overlapped the first focused test
database and produced a single transient state-boundary failure. The isolated case and
a clean 158-test rerun passed without a production change. The first full regression
also exposed a genuinely stale Step-0 guard that still prohibited the now-approved
Documents module; the guard was corrected. Its other isolated quota failure passed
alone, as a full file, after the migration sequence, and in the clean 568-test rerun.
No failing result is presented as passing evidence.

## Deterministic artifacts and generated identities

Every PDF is repository-authored ASCII test data under CC0-1.0. The executable
artifact manifest validates each path, origin, license, and digest.

| Artifact | SHA-256 |
|---|---|
| `synthetic-valid-one-page.pdf` | `6350af32579ffbd7b251a6244bf9bd036d303cbc7404ae06d5e02f1b8f5b994f` |
| `synthetic-signature-mismatch.pdf` | `6632b76d4ea7b4846b85664c1b81c935ac1f1c3639c50e955e8b1d92f0b46954` |
| `synthetic-encrypted.pdf` | `89ce04d4c34af288bd0a6a4c70316d3a1a4d26d6b9e39e415c760f86c2455343` |
| `synthetic-corrupt.pdf` | `59a535d21a08e07d540167522eee5d1115dcbcb2d5f49eb2858b0a2ae36d184f` |
| `synthetic-pixel-cap.pdf` | `8575591cc3b09bc1d85f529407d010c0b05baa398d659aa16f6d51d9d67e477e` |
| `synthetic-unsafe.pdf` | `3b7d99cd1156a763a1f67a84436e19a7f2cc99d7748ef65aa15a76ec315e3b3b` |
| `synthetic-polyglot.pdf` | `e9edde2810555ea39f8649b4f6822fc0ee4f1c991d50152f64a2872d9fe9a423` |

Additional reproducibility identities:

| Artifact | Identity |
|---|---|
| Document schema fingerprint | `sha256:09cb1ccd00cc4cbe88fc9c353bfc775f1b1f981656588b7e7d46239f6cd2003b` |
| Migrated database-catalog fingerprint | `sha256:2d49eb3fd95cb658299f49162200ed679fc859b4eab76046c0fbb3a9be2126cd` |
| Generated OpenAPI file | `942e44ebf77e17e835615c2775d0816be53fda26a7dd32d76a9ac930c2372c7f` |
| Generated TypeScript schema file | `f45d899c5227fb9717a07ce00c44c455872ae313fb869648cf7bc81b7d6106db` |

## Security, privacy, and operational limits

- The local inspector enforces the frozen PDF signature, EOF/polyglot, encryption,
  structural page/media-box, byte/page/pixel, decoded-stream, CPU, and wall limits. It
  is not a full production PDF parser or antivirus product and makes no such claim.
- The default `/tmp/ai-lms-f003-quarantine` path is inside the isolated Compose
  container only. Host task scratch is the required
  `/home/lawrence/Project Neo/tmp/LMS-43`, which remained empty; no repository worktree
  or host task resource was placed under `/tmp`.
- Retention/legal hold, provider deletion, object backup/RPO, external transfer,
  production capacity, and recovery remain blocked or not applicable to this local
  synthetic slice. They are not marked passed.
- No external provider, network document service, real document, production data,
  credential, deployment, release, or production mutation was used.
- Protected GitHub checks, an independent exact-head review, a distinct authorized
  approval, and merge are pending. The implementation producer must not approve or
  merge its own PR.

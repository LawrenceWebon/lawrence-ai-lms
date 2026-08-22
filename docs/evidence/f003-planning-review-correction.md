# F-003 Planning Review Correction Evidence

Status: **audit findings corrected; independent correction review and merge pending**

- Evidence ID: `F003-PLANNING-REVIEW-CORRECTION-2026-08-21`
- Classification: internal planning-governance evidence; synthetic/local scope only
- Accountable owner: project owner
- Correction issue: [#51](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51)

## Immutable source identity

| Item | Evidence |
|---|---|
| Original planning issue | [#42](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/42) |
| Original planning PR | [#44](https://github.com/LawrenceWebon/lawrence-ai-lms/pull/44) |
| Exact planning head | `62a7c5af0a9f209da70d724ae506336d35c3ff86` |
| Merge commit | `83a0c487ff782192d4c18e08cfebd86eb4cf626f` |
| Merged at | `2026-08-21T09:30:42Z` |
| Correction base | `origin/develop` at `9fd3f31be42718009af775ca501c17e919e39755` |
| GitHub review record | zero submitted reviews; `REVIEW_REQUIRED` after merge |

The PR #44 head contains four commits and fourteen changed paths, all inside the
declared F-003 planning ownership. Git history and path-restricted diffs confirm that
the merge commit and later correction base contain the same F-003 schemas, examples,
fixture, contract test, and feature package as the exact planning head.

The original audited file checksums are:

| Path | SHA-256 |
|---|---|
| `contracts/f003/source-admission.v1.schema.json` | `a7ff16b19595ba2dd4988975fbdd1c93cb7d2a054d1b3bb660635188c294eacb` |
| `contracts/f003/source-admission.v1.examples.json` | `a484f904ca83bcc88b3a4d07b097bea1fee413ee0f94b2d025e70c7782f37ab2` |
| `contracts/f003/fixtures/admission-fixtures.v1.json` | `1d7560d23731cb59a15946d58187d6aa4de3d9f41bec260406f4104a97d39d96` |
| `backend/tests/contracts/test_f003_contracts.py` | `095050ae9e38dd0aea56eece3fcfd95e8ce3da18368d8da138dc5c117abffe18` |

## Historical gate defect

The repository workflow required an independent exact-SHA review and a distinct
authorized GitHub approval before PR #44 merged. PR #44 merged without either review
record. Passing checks and the author handoff comment do not satisfy that human review
gate, and this correction does not claim otherwise. The missing temporal ordering
cannot be recreated retroactively.

The exact PR head did pass the protected checks that existed at merge time:

- [documentation](https://github.com/LawrenceWebon/lawrence-ai-lms/actions/runs/32467802055/job/96728037507)
- [quality](https://github.com/LawrenceWebon/lawrence-ai-lms/actions/runs/32467802076/job/96728037860)
- [RLS](https://github.com/LawrenceWebon/lawrence-ai-lms/actions/runs/32467802076/job/96728037827)
- [F-001 end to end](https://github.com/LawrenceWebon/lawrence-ai-lms/actions/runs/32467802076/job/96728037538)
- [F-002 end to end](https://github.com/LawrenceWebon/lawrence-ai-lms/actions/runs/32467802076/job/96728037797)

## Independent post-merge audit

- Review date: `2026-08-21`
- Review producer: independent Codex review context, separate from correction author
- Exact reviewed SHA: `62a7c5af0a9f209da70d724ae506336d35c3ff86`
- Audit evidence comment:
  [issue #51 audit](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/51#issuecomment-5371324839)
- Verdict: **CHANGES REQUIRED**

The audit traced issue #42, the product contract, P-013, ADR-0001, ADR-0002, ADR-0005,
relevant plan sections, every F-003 schema/example/fixture, and the focused contract
tests. It confirmed no later F-003 semantic drift but reproduced three blockers:

1. admitted snapshots/results accepted missing or failed byte-derived evidence,
   rejection codes, and inactive rights;
2. the event shape rejected required repository-envelope fields and accepted an
   event-type/payload mismatch; and
3. the test plan claimed PDF artifact origin/checksum evidence that the scenario-only
   fixture JSON did not contain.

A same-identity comment is review evidence only; it is not the distinct GitHub
approval required for the correction PR.

## Correction response

Issue #51 corrects the findings without changing the approved product envelope:

- admitted results/snapshots now require bounded size, page, per-page/total pixel, and
  decoded-material observations; checksum, PDF MIME/signature/parser agreement, local
  inspection acceptance, active `store` rights, and no rejection reason;
- rejected and retryable result/reason combinations are explicit;
- `SourceAdmissionEventV1` now carries the repository producer/aggregate/recorded/
  causation/privacy envelope and discriminates all nine event facts; and
- the fixture contract declares itself scenario metadata only, while #43 must produce
  a separate executable actual-PDF origin/license/path/SHA-256 manifest before
  implementation evidence can pass.

Correction prepared: `2026-08-22`. Corrected contract candidate checksums are:

| Path | SHA-256 |
|---|---|
| `contracts/f003/source-admission.v1.schema.json` | `f36068b42fb083c438e9eb76ce9486372d3c131bd2ace6063be3c003b2b08d75` |
| `contracts/f003/source-admission.v1.examples.json` | `2dc829c68772ac891cd3dece560f9ec8af025404145cc05a344464bc7ac24b49` |
| `contracts/f003/fixtures/admission-fixtures.v1.json` | `f251416802e93226a4e58486a7533b249ca15442d848e94364e6a52756b86287` |
| `backend/tests/contracts/test_f003_contracts.py` | `488305f9ea4592530228485aa96a29c0b9261da03a697d3115636a7f27239ff9` |

## One-time controlled exception

| Field | Recorded decision |
|---|---|
| Gate | #43 launch condition requiring independent exact-SHA review and distinct approval before PR #44 merged |
| Scope | PR #44's historical review-order and evidence defect only |
| Reason | PR #44 merged before the required independent review record existed |
| Compensating controls | Independent exact-head audit; correction of every blocking finding; executable negative tests; current-base and protected CI; no #43 implementation; no provider or real data |
| Residual risk | A further planning defect may exist; any correction-review finding blocks readiness and must be fixed before #43 starts |
| Accountable owner | Project owner, by explicit instruction on `2026-08-22` |
| Independent approver | Required on correction #51's exact PR head; not yet satisfied |
| Expiry | One-time exception expires when correction #51 merges and #43 is updated; it grants no future bypass |
| Review trigger | Any change to an F-003 contract, fixture, test, limit, or correction head invalidates the applicable exact-SHA evidence and requires review again |

## Verification and limitations

On the correction base before status edits:

- `pytest backend/tests/contracts/test_f003_contracts.py -q`: 7 passed;
- `pytest backend/tests/contracts -q`: 48 passed;
- exact head-to-merge and merge-to-current path-restricted F-003 diffs: empty.

On the corrected candidate:

- `pytest backend/tests/contracts/test_f003_contracts.py -q`: 56 passed;
- `pytest backend/tests/contracts -q`: 97 passed;
- focused Ruff lint and format checks: passed;
- Draft 2020-12 schema and JSON syntax validation: passed.

This evidence ratifies planning content only. It does not prove application code,
migrations, RLS, upload security, storage, parser/scanner capability, retention,
recovery, capacity, provider behavior, real-data handling, production readiness, or
deployment. Those remain implementation or release gates.

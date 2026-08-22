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
- rejected results bind frozen terminal codes to their failed, over-limit,
  missing-object, or checksum observation; retryable results require an unavailable
  inspection and no terminal code; non-rejected snapshots cannot carry one;
- `SourceAdmissionEventV1` now carries the repository producer/aggregate/recorded/
  causation/privacy envelope, discriminates all nine event facts, and binds rejection,
  cancellation, revocation, and removal reason families; and
- the fixture contract declares itself scenario metadata only, while #43 must produce
  a separate executable actual-PDF origin/license/path/SHA-256 manifest before
  implementation evidence can pass.

## Correction review cycle

The first correction candidate was PR #53 at exact head
`24b07a76b05b5be6f379bc95ead770d5e66a39bd`. Its independent review returned
**CHANGES REQUIRED** in the
[exact-SHA review comment](https://github.com/LawrenceWebon/lawrence-ai-lms/pull/53#issuecomment-5377057852).
Although 56 focused and 97 total contract tests plus all protected checks passed, the
reviewer's negative probes proved that:

1. rejected, retryable, and quarantined states still accepted contradictory evidence
   or unfrozen/terminal reasons; and
2. rejected, cancelled, and removal-completed events accepted reasons from the wrong
   family or an arbitrary uppercase value.

The follow-up adds the missing negative cases and the explicit mappings summarized
above. The first verdict remains immutable review evidence; the follow-up head requires
a new independent exact-SHA review and distinct authorized approval.

Follow-up correction prepared: `2026-08-22`. Corrected contract candidate checksums
after the first review findings are:

| Path | SHA-256 |
|---|---|
| `contracts/f003/source-admission.v1.schema.json` | `5d55036341419678fa10fc6fdfdb1dbcbee9de86990756afc20604e5bbbe7c9a` |
| `contracts/f003/source-admission.v1.examples.json` | `2dc829c68772ac891cd3dece560f9ec8af025404145cc05a344464bc7ac24b49` |
| `contracts/f003/fixtures/admission-fixtures.v1.json` | `f251416802e93226a4e58486a7533b249ca15442d848e94364e6a52756b86287` |
| `backend/tests/contracts/test_f003_contracts.py` | `db067281d0551eaa6a3d87db288bce7d757cbf257bd0ca86925e8d7fe2efe3de` |

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

On the first corrected candidate reviewed at
`24b07a76b05b5be6f379bc95ead770d5e66a39bd`:

- `pytest backend/tests/contracts/test_f003_contracts.py -q`: 56 passed;
- `pytest backend/tests/contracts -q`: 97 passed;
- focused Ruff lint and format checks: passed;
- Draft 2020-12 schema and JSON syntax validation: passed.

The follow-up candidate adds 18 executable cases for the reviewer's contradictory
result/snapshot and event-reason probes. Local verification passes 74 focused and 115
total contract tests. Its exact committed SHA, protected checks, and independent
re-review verdict are recorded on PR #53; none is treated as approved before that
review.

This evidence ratifies planning content only. It does not prove application code,
migrations, RLS, upload security, storage, parser/scanner capability, retention,
recovery, capacity, provider behavior, real-data handling, production readiness, or
deployment. Those remain implementation or release gates.

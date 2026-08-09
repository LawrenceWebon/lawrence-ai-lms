# AI LMS Delivery Workflows

Status: **repository-specific workflow authority**

This file adapts the workflow guides in this directory to the actual repository and
the current product priority. It overrides generic example paths or serial-execution
advice in the longer guides when they conflict with this file.

## Current delivery focus

The primary product slice is:

```text
authorized PDF upload
  -> safe extraction/OCR when needed
  -> normalized book structure
  -> grounded structured course draft
  -> instructor review and editing
  -> human publication
  -> learner course experience
```

The implementation reuses the architecture and invariants already described in:

- [product scope](../plan/00-product-vision.md);
- [repository structure](../plan/03-monorepo-folder-structure.md);
- [domain and transaction design](../plan/04-domain-module-design.md);
- [database contract](../plan/05-database-schema-plan.md);
- [AI and ingestion schema](../plan/06-ai-schema-extension.md);
- [manual authoring](../plan/07-manual-course-authoring.md);
- [PDF ingestion](../plan/08-book-ingestion-pipeline.md);
- [course generation](../plan/09-ai-course-generation.md);
- [API and event contracts](../plan/11-api-and-event-contracts.md);
- [testing gates](../plan/15-testing-quality-gates.md); and
- [definition of done](../plan/23-definition-of-done.md).

The project-owner instruction promoting PDF-to-course into the core MVP supersedes
the older sequencing that deferred documents 06, 08, and 09. The Plan Product audit
on 2026-08-09 synchronized only affected status/scope sections in documents 00,
03–09, 11, 15, 16, 20, 24, and 26. It did not reopen unrelated architecture or
production-gate decisions.

Commerce, marketplace payouts, recurring billing, AI companion/RAG, public course
discovery, advanced grading, certificates, live classes, and broad analytics remain
outside this focused MVP unless separately approved. Vector retrieval is included
only if the approved generation design demonstrates that it is necessary.

Until the privacy, retention, capacity, and recovery inputs in documents 25-28 are
approved, agents use synthetic/local data and rights-cleared test PDFs only. Local
implementation is allowed; production enablement is not implied.

## Repository source of truth

Use this precedence:

1. the latest explicit project-owner instruction;
2. `docs/product/spec.md`;
3. approved entries in `docs/product/decisions.md` and the derived feature inventory;
4. `docs/README.md`, accepted ADRs, and relevant `docs/plan` contracts;
5. the approved GitHub issue and its linked decision/acceptance notes;
6. the pull request contract and implementation evidence;
7. existing code and tests;
8. agent inference.

Keep `docs/product` concise and product-facing. Detailed architecture, schema,
security, and operations remain in `docs/plan`. When an owner instruction changes an
older plan disposition, update the product files and affected plan sections together
before or alongside the first dependent implementation PR.

## Delivery flow

```text
select plan slice
  -> freeze shared contracts
  -> create dependency graph and GitHub issues
  -> provision up to four isolated worktrees
  -> implement and test independently
  -> open one pull request per issue
  -> cross-review exact pull-request SHA
  -> merge in declared integration order
  -> run integration, migration, E2E, and release gates
```

Planning is proportional to the change. Do not rerun the full product-planning
workflow for an already documented feature. Use it only for a real product-scope
decision. Normal delivery begins with a focused GitHub issue derived from the plan.

## Codex skill routing

Repository skills live in `.agents/skills`; `.codex/config.toml` is reserved for
project settings. Use the smallest skill matching the requested stage:

| Stage | Skill | Stops at |
|---|---|---|
| Feature planning | `$plan-ai-lms-feature` | `READY FOR IMPLEMENTATION` |
| Feature implementation | `$implement-ai-lms-feature` | `READY FOR CODE REVIEW` |
| Independent PR review | `$review-ai-lms-pr` | `APPROVED FOR MERGE`, `CHANGES REQUIRED`, or `BLOCKED` |
| Guarded merge | `$merge-ai-lms-pr` | verified merge record; deployment remains separate |

The packaging examples in the longer workflow guides are design references, not
additional skills that must be scaffolded. This table is the active repository set.

## Four-agent execution model

Up to four implementation agents may work concurrently. The unit of ownership is:

```text
one GitHub issue
  = one accountable agent
  = one branch
  = one worktree
  = one independently reviewable pull request
```

Each issue must declare:

- objective and acceptance criteria;
- owning domain and owned paths;
- base branch and branch name;
- input/output API, event, job, and fixture contracts;
- dependencies and merge order;
- shared files the agent must not edit;
- required test and evidence commands;
- explicit non-goals; and
- relevant plan, decision, risk, and change IDs.

### Independence rules

- Agents never share a worktree or branch.
- An agent stages only declared paths; do not use `git add .` or `git add -A`.
- Independent implementation PRs target the owner-approved integration branch,
  `develop`. Stacked PRs are exceptional
  and must declare `Depends-on: #<PR>` in the issue and PR.
- Cross-lane dependencies are versioned contracts and fixtures, not imports from an
  unmerged sibling branch.
- Each lane can run its focused tests using fakes or committed synthetic fixtures.
- Each lane uses unique local resources: Compose project name, ports, test database or
  schema, queue/bucket prefixes, and temporary directories. One agent must not stop,
  migrate, truncate, or reseed another agent's resources.
- No agent reviews or approves its own PR. A different agent/context reviews it.
- If all agents use one GitHub identity, an agent review is recorded as a PR comment;
  any required GitHub approval must come from a distinct authorized reviewer.
- Development may be parallel; shared integration and merges remain ordered.

### Shared hotspots

The issue graph names one integration owner for each shared hotspot:

- root dependency files and lockfiles;
- Django migration graph and shared/platform database objects;
- common settings and application composition;
- OpenAPI source, generated clients, and compatibility baselines;
- shared event schemas;
- CI configuration;
- documentation manifest; and
- cross-domain generated artifacts.

Other agents consume the frozen contract or fixture and do not concurrently edit the
hotspot. If a conflict touches another agent's owned path, stop and hand it to the
integration owner rather than guessing.

### Example four-agent split

After a short contract-freeze issue establishes shared DTOs, job envelopes, and the
canonical course-draft shape, four backend-capable agents can work independently:

| Agent | Independent slice | Primary ownership |
|---|---|---|
| A | PDF upload, storage admission, and ingestion lifecycle API | assets/documents application services and API |
| B | PDF extraction and optional OCR worker | parser adapter, stage runner, golden fixtures |
| C | normalized-book to structured-course generation | generation service, structured schemas, provenance/evals |
| D | canonical draft persistence, instructor review, and publication API | courses/curriculum services and review state |

The frontend review/player work may replace one lane or follow as a separate issue.
Agents B-D build against the frozen contracts and synthetic fixtures; they do not wait
for another agent's unmerged implementation. The integration owner performs final
wiring, migration ordering, OpenAPI/client regeneration, and full E2E verification in
a small integration PR when those changes cannot safely belong to one lane.

## GitHub CLI and Git worktree policy

The project authorizes agents to use `gh` for GitHub issues, linked branches, pushes,
draft pull requests, PR updates, checks, and reviews within an approved issue. Merge
and deployment still require the gates in the Merge/Deploy workflow. Never use
`--admin`, bypass required checks, force-push, or rewrite a published shared branch.

`gh` manages GitHub objects. `git` manages local commits, diffs, and worktrees.

### Project branch policy

- `develop` is the base for implementation issues and pull requests.
- `master`, `staging`, and `production` are release/environment branches and must be
  protected before they are used for merge or deployment.
- GitHub's repository default may remain `master`; default-branch metadata does not
  override the project owner's explicit `develop` base.
- On 2026-08-09 GitHub rejected both rulesets and classic branch protection for this
  private repository with HTTP 403 because the current account plan does not support
  that feature. Do not represent those branches as protected, change visibility, or
  bypass review gates. Enable the required protections after the repository gains a
  supporting GitHub plan or visibility decision.

### 1. Repository preflight

Verify both GitHub's default branch and the owner-approved integration branch:

```bash
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef
git remote get-url origin
git status --short --branch
git worktree list
```

Copy the verified values into explicit task variables:

```bash
REPO=OWNER/REPOSITORY
BASE=develop
AI_LMS_WT_ROOT=/absolute/path/to/ai-lms-worktrees
```

Stop if authentication, `origin`, `develop`, or canonical checkout state is unexpected.
Never discard existing changes. The current local repository must have a GitHub
`origin` before the remote steps below can run.

### 2. Create one issue and linked branch per task

Prepare an issue body file containing the required ownership and acceptance contract,
then run:

```bash
gh issue create --repo "$REPO" --title "[PDF ingestion] Short task" \
  --body-file ISSUE.md --assignee "@me"

ISSUE=123
BRANCH=feature/LMS-123-pdf-upload

gh issue develop "$ISSUE" --repo "$REPO" --name "$BRANCH" --base "$BASE"
gh issue develop --list "$ISSUE" --repo "$REPO"
```

The coordinator creates linked branches and provisions worktrees sequentially because
all worktrees share repository Git metadata:

```bash
git fetch --prune origin "$BASE"
git fetch origin "$BRANCH"

WORKTREE="$AI_LMS_WT_ROOT/agent-1-LMS-123"
test ! -e "$WORKTREE"
git worktree add --track -b "$BRANCH" "$WORKTREE" "origin/$BRANCH"
gh issue comment "$ISSUE" --repo "$REPO" \
  --body "Claimed by Agent A on $BRANCH; worktree isolated; owned paths recorded in the issue."
```

If the branch or path already exists, inspect and stop. Never reset or opportunistically
reuse it. If the execution environment already provides isolated repository clones,
use those instead of creating nested worktrees.

### 3. Implement and commit inside the assigned worktree

Before every commit:

```bash
git status --short --branch
git diff --check
git diff --name-only "origin/$BASE...HEAD"
git add -- path/owned-by-this-issue another/owned-path
git diff --cached --check
git commit -m "feat(ingestion): implement PDF upload lifecycle"
```

Use the branch forms from [coding standards](../plan/19-coding-standards.md):
`feature/LMS-<issue>-<slug>`, `fix/LMS-<issue>-<slug>`, or
`chore/LMS-<issue>-<slug>`.

Before the first push, merge the latest approved base branch without rewriting history
and rerun the task's verification commands:

```bash
git fetch origin "$BASE"
git merge --no-edit "origin/$BASE"
git push --set-upstream origin "$BRANCH"
```

Published branches are not rebased or force-pushed. Base conflicts in shared hotspots
go to the integration owner.

### 4. Open and maintain the pull request

The PR body follows [coding standards](../plan/19-coding-standards.md) and includes
`Closes #<issue>` plus problem, design, security, tenant isolation, migration, API,
tests, screenshots, rollback, and plan/evidence IDs.

```bash
gh pr create --repo "$REPO" --draft --base "$BASE" --head "$BRANCH" \
  --title "feat(ingestion): accept PDF uploads" --body-file PR_BODY.md

gh pr view "$BRANCH" --repo "$REPO" \
  --json number,url,baseRefName,headRefName,headRefOid,isDraft
gh pr checks "$BRANCH" --repo "$REPO"
```

When the implementation gate passes:

```bash
gh pr ready "$BRANCH" --repo "$REPO"
gh pr checks "$BRANCH" --repo "$REPO" --required --watch --fail-fast
```

### 5. Independent review

The reviewer reads GitHub evidence and records the exact `headRefOid`:

```bash
PR=456
gh pr view "$PR" --repo "$REPO" \
  --json baseRefName,headRefName,headRefOid,files,commits,reviews,statusCheckRollup
gh pr diff "$PR" --repo "$REPO"
gh pr checks "$PR" --repo "$REPO" --required
```

Post one evidence-based verdict:

```bash
gh pr review "$PR" --repo "$REPO" --request-changes --body-file REVIEW.md
# or, only after all blocking findings pass:
gh pr review "$PR" --repo "$REPO" --approve --body-file REVIEW.md
```

The author fixes findings in the implementation worktree. Every new push changes the
reviewed SHA and requires re-review.

### 6. SHA-locked merge

The integration/merge owner confirms the reviewed SHA, required checks, approval,
mergeability, and declared dependency order. Use the repository-approved merge method;
the default below is squash:

```bash
REVIEWED_SHA=$(gh pr view "$PR" --repo "$REPO" --json headRefOid --jq .headRefOid)
gh pr checks "$PR" --repo "$REPO" --required --watch --fail-fast
gh pr merge "$PR" --repo "$REPO" --squash --auto --delete-branch \
  --match-head-commit "$REVIEWED_SHA"
gh pr view "$PR" --repo "$REPO" --json state,mergedAt,mergeCommit
```

Never merge with `--admin`. Merge concurrent PRs one at a time. After each merge, the
remaining branch owners merge the latest base, rerun tests, push, and obtain review of
the new SHA. This serializes integration, not feature development.

### 7. Cleanup

Only the coordinator removes a task worktree, and only after GitHub reports the PR as
merged and the worktree is clean. Closed-but-unmerged work is preserved until an
explicit disposition.

```bash
gh pr view "$PR" --repo "$REPO" --json state
git -C "$WORKTREE" status --porcelain
git worktree remove "$WORKTREE"
git fetch --prune origin
git worktree prune
```

Do not delete a non-merged branch or a dirty worktree. Do not run bulk formatting,
branch cleanup, `git gc`, or `git worktree prune` while other agents are active.

## Workflow-stage responsibilities

| Stage | Main artifact | GitHub action | Exit |
|---|---|---|---|
| Plan Product | Narrow plan correction only when scope changes | planning issue/PR | scope synchronized |
| Plan Feature | Issue DAG, frozen contracts, acceptance/test plan | create four bounded issues | `READY FOR IMPLEMENTATION` |
| Implement | Code, tests, evidence, focused commits | push and open draft PR | `READY FOR CODE REVIEW` |
| Code Review | Exact-SHA findings and verdict | PR review/comment | `APPROVED FOR MERGE` or changes |
| Merge/Deploy | integration order, merge and release evidence | protected `gh pr merge` flow | verified merge/deploy state |

## Non-negotiable implementation boundaries

- Django migrations are the sole application schema authority.
- A top-level command owns one transaction; do not hold it across Storage, OCR, AI,
  vector, or other network calls.
- HTTP, Admin, and worker adapters call shared application services rather than
  mutating ORM models directly.
- Tenant and membership authority is re-derived server-side and enforced with
  production-role RLS; browser/model/job payload identifiers are never authority.
- Async stages are idempotent and use durable state, leases/checkpoints, bounded
  retries, reconciliation, and explicit unknown/failure states.
- AI produces structured drafts with immutable provenance. Only an authorized human
  can approve and publish a canonical course version.
- Upload and generation tests use synthetic or rights-cleared fixtures and include
  malicious-file, cross-tenant, retry, provenance, and publication-bypass cases.
- Generated files and shared contracts have one named owner and are never hand-edited
  by multiple agents.

The longer workflow documents provide stage-specific checklists and prompts. Apply
only the sections relevant to the selected issue; passing this workflow never requires
performing unrelated enterprise, commerce, RAG, or deployment work.

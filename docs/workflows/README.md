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

Defect investigation and performance work use the cross-cutting
[Debugging and Performance workflow](DEBUGGING_PERFORMANCE_AI_LMS_CODEX_WORKFLOW.md).
That workflow may be entered from implementation, review, CI, support, or operations;
once it produces a bounded fix, the normal issue/worktree/PR and independent-review
rules below still apply.

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

The debugging/performance guide is workflow authority, not an installed repository
skill. Use the existing implementation skill only after a defect has a valid
reproduction and proven root cause, or after a performance task has a reproducible
baseline and one measured bottleneck. Adding dedicated debugging/performance skills
requires its own approved repository change.

## Debugging and performance workflow

Use [the cross-cutting guide](DEBUGGING_PERFORMANCE_AI_LMS_CODEX_WORKFLOW.md) with these
repository-specific gates:

| Work type | Required evidence before implementation | Verified handoff |
|---|---|---|
| Reproducible defect | Exact symptom, valid failing behavioral test when feasible, execution trace, and cause-level explanation | Original RED test is GREEN; adjacent, tenant/security, and applicable AI checks pass |
| Intermittent defect | One hypothesis at a time, two or three privacy-safe observations, and a precise trigger flow | Confirmed hypothesis becomes a regression test; rejected diagnostics are removed |
| Performance audit | User-visible symptom, representative data/flow, metric and stable baseline | Ranked evidence report only; no production-code optimization |
| Performance fix | One measured bottleneck and a repeatable before scenario | Equivalent after measurement, material improvement, correctness evidence, and a stable guard where valuable |

The guide's commerce, payment, AI companion/RAG, vector, and provider examples apply
only when those capabilities are separately approved and enabled. They are not
permission to add routes, schema, dependencies, credentials, test data, or production
configuration. Never trade correctness, tenant isolation, source rights, privacy,
accessibility, or approved AI quality for a passing test or faster-looking result.

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
- Every task branch starts from the latest protected `develop` branch and its pull
  request targets `develop`. Stacked PRs are exceptional
  and must declare `Depends-on: #<PR>` in the issue and PR.
- Cross-lane dependencies are versioned contracts and fixtures, not imports from an
  unmerged sibling branch.
- Each lane can run its focused tests using fakes or committed synthetic fixtures.
- Each lane uses unique local resources: Compose project name, ports, test database or
  schema, queue/bucket prefixes, and temporary directories. One agent must not stop,
  migrate, truncate, or reseed another agent's resources.
- Repository worktrees live only under
  `/home/lawrence/Project Neo/worktrees/ai-lms/`. Project Python/Node dependencies
  execute only in the lane's reusable Docker Compose services; agents do not create a
  host `.venv`, install host `node_modules`, place worktrees inside the repository, or
  use `/tmp` for worktrees.
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

- `develop` is GitHub's default branch and the base/PR target for every task, including
  feature, fix, chore, documentation, and integration work.
- Before provisioning a task worktree, fetch `origin/develop` and create the issue-linked
  branch from that exact head. Do not branch new work from `master`, `staging`,
  `production`, or another task branch.
- The active repository ruleset `Protect long-lived branches` protects `develop`,
  `master`, `staging`, and `production`. For non-bypass actors it requires a pull
  request, one approval, dismissal of stale approvals, resolved conversations, squash
  merge, linear history, and the strict GitHub Actions checks `quality`, `rls`,
  `e2e-f001`, and `documentation`; force-pushes and deletion are disabled. Each check
  must pass on the latest base before merge.
- The repository-admin role remains the only bypass actor and its bypass mode is
  `pull_request`, so it cannot authorize a direct push. That technical capability is
  not workflow authorization: never use it to replace an independent exact-SHA review,
  the required distinct GitHub approval, or a required check. When an author cannot
  self-approve, the PR waits for a distinct authorized reviewer. A same-identity agent
  review comment is evidence, not the required GitHub approval.
- Classic branch protections are intentionally removed so this ruleset is the single
  branch-protection authority. Read back the effective rules after any settings change;
  workflow/config changes require their own issue, PR, independent review, and checks.
- `master`, `staging`, and `production` remain release/environment branches. Promotion
  between them follows the separately authorized merge/deploy workflow; task branches
  never target them directly.

### 1. Repository preflight

Verify that GitHub's default and owner-approved integration branch is `develop`:

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
AI_LMS_WT_ROOT="/home/lawrence/Project Neo/worktrees/ai-lms"
```

Stop if authentication, `origin`, GitHub's default `develop`, or canonical checkout
state is unexpected. Never discard existing changes. The current local repository must
have a GitHub `origin` before the remote steps below can run.

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
reuse it. An environment-provided isolated checkout must still use the exact
`/home/lawrence/Project Neo/worktrees/ai-lms/` root.

### 3. Implement and commit inside the assigned worktree

Assign a unique Compose project name and ports, then build/start the task services once:

```bash
COMPOSE_PROJECT_NAME=ai-lms-lms-123
AI_LMS_POSTGRES_PORT=55123
AI_LMS_UID="$(id -u)"
AI_LMS_GID="$(id -g)"
export COMPOSE_PROJECT_NAME AI_LMS_POSTGRES_PORT AI_LMS_UID AI_LMS_GID
docker compose up -d --build
docker compose ps
```

Reuse those running services for every project command. Stable Make targets delegate
to `docker compose exec -T`; do not run `uv sync`, create a worktree `.venv`, run
`npm ci` on the host, or stop another task's Compose project. Rebuild only when an
owned dependency manifest or Docker build input changes.

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

### 7. Mandatory post-merge cleanup

The coordinator performs cleanup after every task PR merges to `develop` and before
provisioning the next task. A local handoff such as `READY FOR CODE REVIEW` or
`APPROVED FOR MERGE` is not completion for cleanup purposes because review fixes may
still be required. A closed-but-unmerged task is preserved unless the project owner
explicitly records abandonment or another disposition.

Resolve exact values from the issue/worktree record; do not use globs or guessed
paths. Then:

```bash
gh pr view "$PR" --repo "$REPO" --json state,mergedAt,mergeCommit,headRefName
git -C "$WORKTREE" status --porcelain

COMPOSE_PROJECT_NAME="$TASK_COMPOSE_PROJECT" \
AI_LMS_POSTGRES_PORT="$TASK_POSTGRES_PORT" \
docker compose -f "$WORKTREE/compose.yaml" down --volumes --remove-orphans

git worktree remove "$WORKTREE"
test ! -e "$WORKTREE"
git worktree list --porcelain
docker compose ls -a
git fetch --prune origin
```

The required sequence is:

1. verify GitHub reports `MERGED`, or cite the explicit owner-approved abandonment;
2. verify the worktree has no tracked, staged, or untracked changes;
3. stop only the task's recorded Compose project and remove its disposable volumes;
4. remove the registered worktree with `git worktree remove`, which also removes its
   directory;
5. verify the directory, worktree registration, containers, networks, and disposable
   volumes are gone; and
6. record what was removed and whether any retained artifact remains recoverable.

Stop on a dirty tree, unresolved PR state, unexpected path, or resource-name mismatch.
Never use `rm -rf` as a substitute for `git worktree remove`; never remove an active,
reviewing, open, or closed-unmerged task; and never stop another task's Compose project.
Local branch deletion is a separate, explicit merged-branch action. Do not run bulk
branch cleanup, `git gc`, or global `git worktree prune` while other agents are active.

## Workflow-stage responsibilities

| Stage | Main artifact | GitHub action | Exit |
|---|---|---|---|
| Plan Product | Narrow plan correction only when scope changes | planning issue/PR | scope synchronized |
| Plan Feature | Issue DAG, frozen contracts, acceptance/test plan | create four bounded issues | `READY FOR IMPLEMENTATION` |
| Debug / Performance | Reproduction and root cause, or baseline and ranked bottleneck | focused issue/PR after evidence gate | `BUG FIX VERIFIED`, `PERFORMANCE FIX VERIFIED`, or evidence blocker |
| Implement | Code, tests, evidence, focused commits | push and open draft PR | `READY FOR CODE REVIEW` |
| Code Review | Exact-SHA findings and verdict | PR review/comment | `APPROVED FOR MERGE` or changes |
| Merge/Deploy | integration order, merge/release evidence, and task cleanup | protected `gh pr merge` flow | verified merge/deploy state and removed merged-task worktree |

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

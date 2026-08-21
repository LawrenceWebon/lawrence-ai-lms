# Implement — AI LMS / Codex Workflow

> **Purpose:** Safely execute one approved implementation step from the **Plan Feature** workflow using Codex, tests-first development, repository guardrails, narrow scope, deterministic verification, AI-specific evaluations where required, and a clean handoff to **Code Review**.
>
> **Workflow position:**  
> `Plan Product → Plan Feature → Implement → Code Review → Merge / Deploy`
>
> **Implementation boundary:** This workflow changes code. It does **not** silently redesign the product, rewrite the feature plan to justify implementation drift, merge to the protected branch, deploy to production, run destructive production migrations, or make unrelated refactors.
>
> **Terminal state:** `READY FOR CODE REVIEW`

---

## Repository-specific application

Follow [the repository workflow authority](README.md). Implementation may run across
four independent agents when each owns a separate GitHub issue, branch, worktree, path
set, contract, and PR. The serial wording in this guide applies within one issue; it
does not force unrelated issues to wait.

This repository authorizes `gh` operations for approved issues: linked branch creation,
push, draft PR creation/update, check inspection, and review handoff. It does not
authorize bypassing checks, force-pushing, self-merging, deployment, paid resources,
or production data changes. The exact commands and shared-hotspot rules are in
`README.md`.

Use the existing `docs/product` contract, relevant `docs/plan` files, and the approved
issue. Create a durable `docs/features` folder only when the issue needs it. Progress
belongs in issue/PR comments and evidence rather than a single shared status file that
all four agents edit.

When work begins from a defect, regression, intermittent failure, or performance
symptom, enter the
[Debugging and Performance workflow](DEBUGGING_PERFORMANCE_AI_LMS_CODEX_WORKFLOW.md)
before changing production code. A defect reaches this implementation workflow only
after valid reproduction and root-cause evidence; a performance change reaches it only
after a repeatable baseline identifies one measured bottleneck. The issue, isolated
worktree, owned-path, test, review, and merge rules remain unchanged.

---

# 1. What This Workflow Solves

AI coding agents are fast enough to make implementation mistakes faster than a human reviewer can notice them.

The implementation workflow therefore needs more than:

> "Here is the feature plan. Build it."

The agent must instead operate inside a controlled execution loop:

```text
Approved feature step
        │
        ▼
Implementation preflight
        │
        ▼
Create / verify focused branch
        │
        ▼
Load exact step + repository instructions
        │
        ▼
Verify baseline
        │
        ▼
Write / validate tests first
        │
        ▼
RED
        │
        ▼
Minimum implementation
        │
        ▼
GREEN
        │
        ▼
Refactor without scope expansion
        │
        ▼
Security / tenant / AI validation
        │
        ▼
Lint / typecheck / static analysis / tests
        │
        ▼
Diff + scope review
        │
        ▼
Local AI review
        │
        ▼
Fix blocking findings
        │
        ▼
Record progress
        │
        ▼
Implementation Gate
        │
        ▼
READY FOR CODE REVIEW
```

The core principle is:

> **Codex may decide implementation details inside the approved step. It may not decide new product scope, trust boundaries, major architecture, or production actions on its own.**

---

# 2. Required Inputs

The Implement workflow begins only after the selected feature passes the **Feature Planning Gate**.

Recommended inputs:

```text
AGENTS.md                                      # when present
docs/workflows/README.md
docs/README.md
docs/product/spec.md, features.md, and decisions.md
relevant docs/plan and ADR files
approved GitHub issue with ownership/contract/test fields
frozen API/event/job/fixture contracts
declared base branch, worktree, and owned paths
```

---

# 3. Outputs

For each implementation step, the workflow should produce:

1. production code for **only the approved step**;
2. tests required by that step;
3. passing applicable verification checks;
4. an inspectable diff;
5. a local implementation review;
6. an updated progress record;
7. a concise implementation summary;
8. a branch/commit that is ready for the Code Review workflow.

Durable progress is recorded in the GitHub issue and draft PR so four agents do not
contend on one shared status file. Repository evidence files are added only when the
plan's evidence contract requires them.

Optional local-only working files:

```text
.codex/work/[feature-slug]/
├── current-step.md
├── review-checklist.md
└── session-notes.md
```

Local working files should be ignored by Git unless the team deliberately wants them versioned.

---

# 4. Source-of-Truth Hierarchy During Implementation

Implementation must follow this precedence:

1. `AGENTS.md` and applicable nested agent instructions for repository operation
2. `docs/workflows/README.md` for repository execution policy
3. `docs/product/spec.md`
4. approved product decisions and derived features
5. relevant accepted ADRs and `docs/plan` contracts
6. approved GitHub issue, frozen contracts, and acceptance/test plan
7. existing production code as evidence of current implementation patterns
8. pull-request contract and generated step prompts
9. agent inference

Important:

- Existing code does not override an approved product requirement merely because it already exists.
- A generated implementation prompt does not override the feature plan.
- A passing test does not override the approved plan or issue when the test is wrong.
- Codex must not edit planning documents merely to make an implementation deviation appear approved.

If two high-priority sources conflict materially, stop the affected implementation work and report the conflict.

---

# 5. The Unit of Work: One Approved Implementation Step

The default unit of implementation is:

> **one implementation step from `implementation-plan.md`**

Not:

- the whole product;
- the whole feature;
- "all remaining TODOs";
- adjacent cleanup;
- unrelated tech debt.

Example:

```text
Feature:
Generate Course From Uploaded Book

Step 1:
Establish generation lifecycle, authorization boundary,
and persisted generation state.
```

The implementation agent should complete Step 1 and stop at the Implementation Gate.

Step 2 begins only after the workflow allows it.

---

# 6. Codex Autonomy and Approval Boundaries

Codex should be proactive **inside** an approved implementation step.

It should not repeatedly ask permission for safe, local, in-scope actions.

---

## 6.1 Allowed without additional approval

When required by the approved step, Codex may:

- read repository files;
- search code;
- inspect git history when useful;
- inspect local configuration examples;
- edit in-scope source code;
- edit in-scope tests;
- add files required by the approved architecture;
- run local non-destructive commands;
- run tests;
- run linting;
- run formatting;
- run type checking;
- run static analysis;
- run a local build;
- run local development migrations against a disposable/local database when the approved step requires it;
- inspect local diffs;
- make local commits if the repository workflow explicitly authorizes Codex to do so;
- update the implementation progress file;
- fix defects introduced by its own in-scope changes.

---

## 6.2 Requires explicit prior authorization or repository policy

Codex must not assume permission to:

- push to a remote;
- open or modify a remote PR;
- merge a PR;
- force-push;
- rewrite shared Git history;
- deploy;
- change cloud infrastructure;
- modify production data;
- run production migrations;
- rotate secrets;
- create paid resources;
- change billing configuration;
- disable security controls;
- broaden IAM/service permissions;
- publish packages;
- send real user emails/messages;
- invoke consequential external writes.

A repository may grant some of these through a documented workflow.

If so, follow that documented authorization.

---

## 6.3 Never do silently

Codex must not silently:

- expand feature scope;
- add an unrelated feature;
- change tenant boundaries;
- weaken RLS or authorization;
- make an AI action more autonomous;
- auto-publish AI-generated learning content when review was required;
- alter grading semantics;
- change data retention rules;
- introduce a new external provider;
- add a large framework;
- disable tests;
- delete failing tests;
- weaken assertions merely to get green;
- use `any`, suppressions, ignored errors, or similar escape hatches solely to bypass quality checks;
- expose secrets;
- copy production secrets into local files;
- bypass failing security checks.

---

# 7. Implementation Safety Principles

---

## 7.1 Read before editing

Before making a code change, Codex must inspect:

- root `AGENTS.md`;
- applicable nested `AGENTS.md`;
- the selected feature step;
- relevant technical decisions;
- required tests;
- repository code directly affected by the step;
- adjacent tests;
- current schema/migrations if data is affected;
- authorization/RLS patterns if protected resources are affected.

---

## 7.2 Minimum necessary change

Implement the smallest coherent change that satisfies:

- the selected step;
- its tests;
- its acceptance checks;
- its security constraints.

Passing tests is not permission to add extra abstractions.

---

## 7.3 Prefer existing architecture

Before creating a new:

- service;
- repository;
- helper;
- middleware;
- queue abstraction;
- model wrapper;
- authorization mechanism;
- validation library;
- UI pattern;

search for an existing project pattern.

Reuse it when appropriate.

---

## 7.4 No speculative generalization

Do not convert a single feature need into a generic platform unless the plan explicitly requires it.

Avoid:

```text
GenericWorkflowEngine
UniversalAIProviderFramework
DynamicPermissionDSL
AbstractEverythingRepository
```

when a simple feature-specific implementation satisfies the approved design.

---

## 7.5 Make invalid states difficult

Prefer implementation structures that enforce:

- valid lifecycle transitions;
- tenant ownership;
- authorization;
- structured AI output;
- bounded input;
- typed failure states;
- explicit nullability;
- validated external data.

---

## 7.6 Fail visibly

Do not swallow:

- exceptions;
- failed jobs;
- authorization failures;
- provider errors;
- invalid model output;
- malformed webhooks;
- missing source data.

Convert expected failures into the repository's approved error model.

Log only safe operational information.

---

# 8. Guardrails Before AI-Generated Code

The project should have deterministic quality guardrails before significant feature implementation.

At minimum, identify the repository's existing:

- testing framework;
- formatter;
- linter;
- type checker / static analyzer;
- build check;
- pre-commit hooks or equivalent;
- CI checks.

Examples by stack may include:

```text
TypeScript / JavaScript
- ESLint or repository equivalent
- Prettier or repository formatter
- TypeScript type checking

Python
- Ruff
- Mypy or repository type checker
- Pytest
- pre-commit
```

These are examples, not mandatory package choices.

Do not replace an existing toolchain merely because another tool is popular.

---

## 8.1 Guardrail bootstrap rule

If the repository has **no** baseline guardrails and Plan Product/Plan Feature explicitly approved adding them, create a separate foundation step before feature behavior.

Do not hide a major tooling migration inside a product feature diff.

---

## 8.2 Guardrails are evidence, not decoration

A guardrail only counts if:

1. the command exists;
2. the agent knows when to run it;
3. it runs successfully;
4. failures block completion appropriately.

A sentence in `AGENTS.md` saying "run tests" is not enough if nobody actually runs them.

---

# 9. AGENTS.md as Durable Repository Guidance

`AGENTS.md` should contain durable instructions that apply repeatedly.

Good candidates:

- project stack;
- architectural boundaries;
- naming conventions;
- standard test commands;
- lint/typecheck/build commands;
- required security rules;
- tenant-isolation rules;
- preferred existing abstractions;
- prohibited patterns;
- generated-file rules;
- migration rules;
- AI evaluation commands;
- scope rules.

---

## 9.1 Do not turn AGENTS.md into a dumping ground

Do not add a rule because of one accidental implementation detail.

A new rule should generally be:

- reusable;
- broadly applicable;
- likely to prevent repetition;
- short;
- objectively checkable where possible.

---

## 9.2 Guardrail improvement loop

When review repeatedly finds the same class of mistake:

```text
review finding
    ↓
fix current code
    ↓
identify durable principle
    ↓
update AGENTS.md / tooling / hook
    ↓
future agent gets stronger default
```

Examples:

```text
Repeated problem:
Agents bypass an existing framework action.

Durable rule:
"Before implementing custom mutation logic, search for an existing
framework/domain action and reuse it unless the feature plan says otherwise."
```

Do not encode one-off feature details as global policy.

---

# 10. Hooks and Automated Verification

Guardrails should run automatically where practical.

Useful layers:

```text
AGENTS.md
    ↓
developer / Codex commands
    ↓
pre-commit or local hooks
    ↓
CI
```

---

## 10.1 Hook safety

Hooks should not:

- modify broad unrelated files;
- run destructive commands;
- depend on production secrets;
- make network writes;
- silently skip failures;
- take so long that developers routinely bypass them.

---

## 10.2 Recommended hook split

Fast checks:

```text
pre-commit
- formatting
- lint on changed files
- lightweight type/static checks
- fast tests where practical
```

Full checks:

```text
pre-push or CI
- full typecheck
- full static analysis
- integration tests
- build
- migration verification
- AI eval smoke suite where appropriate
```

Exact commands must come from the repository.

---

# 11. Branch and PR Strategy

AI-generated changes are easier to review when the branch matches the implementation step.

---

## 11.1 Default branch scope

Use the repository convention from document 19:

```text
feature/LMS-[issue]-[short-name]
fix/LMS-[issue]-[short-name]
chore/LMS-[issue]-[short-name]
```

Examples:

```text
feature/LMS-123-pdf-upload
feature/LMS-124-pdf-extraction
```

---

## 11.2 Branch rule

One branch should have one clear purpose.

Avoid mixing:

- feature behavior;
- unrelated dependency upgrades;
- formatting of unrelated files;
- generic refactors;
- another feature.

---

## 11.3 Stacked branches

Independent issues and PRs targeting the owner-approved `develop` branch are
preferred. Agents use frozen contracts and fixtures so one unmerged implementation
does not block another.

Use stacked branches only for a genuine, declared dependency:

```text
develop
  └─ step-01
       └─ step-02
            └─ step-03
```

Record `Depends-on: #<PR>` in both issue and PR. Never hide the dependency or import
code from an unmerged sibling branch merely to make local tests pass.

---

## 11.4 External Git actions

For this repository, the project owner authorizes an implementation agent to create
the issue-linked branch, push its own focused commits, and open or update a draft PR
with `gh`, following [the shared GitHub CLI policy](README.md#github-cli-and-git-worktree-policy).

The Implement workflow never merges or deploys.

---

# 12. Durable Implementation Progress

Long-running feature work must be resumable without relying on chat memory.

For the four-agent workflow, the durable record is the assigned GitHub issue, draft
PR, commits, checks, and review comments. Update those records at meaningful gates.

The following file is optional only when one issue has exclusive ownership of it; do
not make all agents edit one shared feature status file:

```text
docs/features/[feature]/implementation-status.md
```

Template:

```markdown
# Implementation Status — [Feature]

## Current Status
IN PROGRESS

## Current Step
Step [N] — [Name]

## Branch
[branch name]

## Completed Steps
- [x] Step 1 — ...
- [ ] Step 2 — ...
- [ ] Step 3 — ...

## Current Step Checklist
- [x] Context loaded
- [x] Baseline verified
- [x] Tests added
- [x] RED confirmed
- [ ] Implementation complete
- [ ] GREEN confirmed
- [ ] Full verification complete
- [ ] Local review complete
- [ ] Ready for Code Review

## Verification Evidence
- Tests:
- Lint:
- Typecheck:
- Static analysis:
- Build:
- AI evals:

## Known Pre-existing Failures
- ...

## Deviations From Plan
- None

## Open Implementation Questions
- None

## Last Known Good Commit
[hash]

## Next Action
[precise next action]
```

If used, update the file after meaningful gates, not after every tiny edit.

---

# 13. Workflow Overview

```text
Phase 0   Implementation eligibility
Phase 1   Load instructions and selected step
Phase 2   Establish focused Git workspace
Phase 3   Verify clean baseline
Phase 4   Reconfirm step contract and stop conditions
Phase 5   Implement tests first
Phase 6   Confirm RED correctly
Phase 7   Implement minimum GREEN change
Phase 8   Confirm GREEN
Phase 9   Refactor safely
Phase 10  Validate data / migration behavior
Phase 11  Validate auth / tenant / security behavior
Phase 12  Validate AI-specific behavior and evals
Phase 13  Validate UI / user journey when applicable
Phase 14  Run complete automated guardrails
Phase 15  Inspect diff and scope
Phase 16  Local AI code review
Phase 17  Fix review findings using checklist
Phase 18  Update durable progress and documentation
Phase 19  Prepare implementation summary / PR material
Phase 20  Implementation Gate
```

---

# 14. Phase 0 — Implementation Eligibility

## Goal

Do not start coding an unapproved or under-planned step.

---

## Checks

Confirm:

- selected feature exists;
- Feature Planning Gate returned `READY FOR IMPLEMENTATION`;
- selected implementation step exists;
- previous required steps are complete;
- blocking feature questions are resolved;
- approved tests exist for the step;
- technical decisions required by the step exist;
- the step has explicit non-scope.

---

## Prompt

```text
We are beginning IMPLEMENT for:

Feature: [FEATURE]
Implementation Step: [STEP NUMBER / NAME]

Before editing code:

1. Read the feature planning artifacts.
2. Confirm the feature planning gate is READY FOR IMPLEMENTATION.
3. Confirm this exact step exists in implementation-plan.md.
4. Confirm its prerequisites are complete.
5. Identify its acceptance checks.
6. Identify its required tests.
7. Identify its explicit non-scope.
8. Identify any approved technical decisions that constrain it.

Do not edit production code yet.

Return:
- ELIGIBLE TO IMPLEMENT
or
- NOT ELIGIBLE

If not eligible, list only blockers.
```

---

# 15. Phase 1 — Load Repository Instructions and Context

## Goal

Give Codex the smallest complete context necessary to implement correctly.

---

## Read first

At minimum:

```text
AGENTS.md
nested AGENTS.md affecting target files
feature.md
technical-decisions.md
implementation-plan.md
test-plan.md
selected step prompt if present
```

Then inspect:

- code directly affected;
- adjacent tests;
- relevant schema;
- RLS/policies;
- related service/component patterns.

---

## Context rule

Do not load hundreds of unrelated files "just in case."

Search first.

Open the smallest relevant set.

---

## Prompt

```text
Load the implementation context for Step [N].

Read:
- repository AGENTS.md instructions;
- selected feature artifacts;
- approved tests;
- relevant nearby implementation;
- relevant nearby tests.

Then summarize privately for execution:

- behavior to add;
- behavior not to add;
- existing patterns to reuse;
- files/areas likely affected;
- tests that define success;
- security/tenant constraints;
- failure behavior.

Do not modify code until this context is established.
```

---

# 16. Phase 2 — Establish a Focused Git Workspace

## Goal

Make the change independently inspectable and reversible.

---

## Verify

```text
git status
current branch
upstream/base
uncommitted changes
```

---

## Dirty workspace rule

Never overwrite unrelated user changes.

If unrelated changes already exist:

- identify them;
- do not reset them;
- do not format them;
- do not stage them accidentally;
- use a separate worktree/branch when appropriate.

---

## Branch rule

Create or use the approved feature-step branch.

Do not work directly on a protected branch unless repository policy explicitly permits it.

---

## Suggested prompt

```text
Inspect Git state before implementation.

Confirm:
- current branch;
- working-tree status;
- whether unrelated changes exist;
- expected base branch;
- whether this step has its own branch/worktree.

Do not discard or overwrite existing work.

Use the repository's branch convention.
```

---

# 17. Phase 3 — Verify the Baseline

## Goal

Know the repository's state before attributing failures to the new change.

---

## Run the narrowest useful baseline

Examples:

- relevant existing tests;
- typecheck for affected package;
- relevant lint check;
- relevant build target.

For risky foundation changes, run the full expected baseline.

---

## Record pre-existing failures

If a check already fails before implementation:

```markdown
## Known Pre-existing Failures

- `command`
  - failure:
  - affected area:
  - unrelated to current step because:
```

Do not claim a clean implementation if required verification remains red, but distinguish introduced failures from existing failures.

---

## Baseline prompt

```text
Before changing code, establish a verification baseline for this step.

Run the narrowest existing checks that cover the affected area.

Record:
- commands;
- passing checks;
- pre-existing failures;
- environment limitations.

Do not fix unrelated baseline failures unless they block this approved step and
the fix is separately approved.
```

---

# 18. Phase 4 — Reconfirm the Step Contract

## Goal

Prevent scope drift once Codex sees the codebase.

---

## Create a short execution contract

```markdown
## Step Execution Contract

### Must implement
- ...

### Must preserve
- ...

### Must not implement
- ...

### Tests required
- ...

### Security boundaries
- ...

### Completion checks
- ...
```

This can live in the progress file or remain in the agent's working context.

---

## Stop conditions

Stop and report rather than improvise when:

- product spec conflicts with the implementation plan;
- required architecture does not exist and adding it materially changes scope;
- an unapproved new dependency becomes necessary;
- schema changes are materially larger than planned;
- an authorization requirement is unclear;
- a tenant boundary cannot be enforced as planned;
- a destructive data migration appears necessary;
- an AI action would become more autonomous than approved;
- the test plan cannot represent the intended behavior;
- implementing the step requires implementing a future step first;
- repository reality invalidates a major technical decision.

Minor implementation details do not require stopping.

---

# 19. Phase 5 — Implement Tests Before Production Code

## Goal

Create an independent executable target for the approved behavior.

---

## TDD loop

```text
Requirement
   ↓
Test
   ↓
RED for expected reason
   ↓
Implementation
   ↓
GREEN
   ↓
Refactor
```

---

## 19.1 Test sources

Tests must derive from:

1. feature acceptance criteria;
2. step behavior;
3. technical contracts;
4. authorization/tenant rules;
5. failure requirements;
6. regression expectations.

Not from whatever implementation Codex happens to write.

---

## 19.2 Do not over-test implementation details

Prefer:

```text
Instructor without permission receives authorization failure.
```

over:

```text
Private helper method is called exactly twice.
```

unless the internal behavior is itself part of a meaningful contract.

---

## 19.3 Reuse test conventions

Before adding tests, inspect:

- factories;
- fixtures;
- test helpers;
- auth setup;
- database reset strategy;
- network mocking;
- time mocking;
- job/queue test utilities;
- browser test patterns.

Do not create a parallel testing system.

---

## Test-first prompt

```text
Implement ONLY the approved tests for Step [N].

Requirements:

- derive them from the step contract and test plan;
- use existing project test conventions;
- reuse existing factories/fixtures/helpers;
- include authorization and tenant isolation where required;
- include important failure behavior;
- include idempotency/concurrency behavior when required;
- do not implement production feature behavior;
- do not weaken existing tests.

After adding tests, run the narrowest test command needed to demonstrate RED.

Report the exact reason each new failing test is expected to fail.
```

---

# 20. Phase 6 — Confirm RED Correctly

## Goal

A failing test is useful only if it fails because the required behavior is missing.

---

## Valid RED

Examples:

- expected endpoint/action does not exist;
- expected state transition is missing;
- authorization rule is not enforced;
- response/result lacks required behavior;
- missing persistence;
- missing job/event.

---

## Invalid RED

Examples:

- syntax error in the test;
- missing test fixture;
- wrong import path;
- broken environment;
- unrelated database failure;
- typo in assertion;
- incorrect assumption about existing behavior.

Fix invalid tests before implementation.

---

## RED gate

Do not start production implementation until:

- test code itself is valid;
- the test fails for the intended feature reason;
- existing relevant tests remain understood;
- new tests accurately represent the plan.

---

# 21. Phase 7 — Implement the Minimum GREEN Change

## Goal

Write the smallest coherent production change that makes the approved tests pass.

---

## Implementation loop

For each small coherent slice:

```text
inspect
  ↓
edit
  ↓
run narrow test
  ↓
fix
  ↓
repeat
```

---

## Rules

- stay inside selected step;
- reuse existing abstractions;
- preserve current conventions;
- use typed/validated boundaries;
- implement authorization at the trusted/server boundary;
- avoid frontend-only permission enforcement;
- avoid hidden fallback behavior;
- avoid broad refactors;
- avoid unrelated formatting;
- avoid dependency additions unless explicitly approved.

---

## Implementation prompt

```text
Implement only Step [N].

Use the approved feature documents and tests as the contract.

Rules:

- make the minimum coherent production change;
- reuse existing repository architecture;
- preserve current behavior outside this step;
- enforce authorization/tenant rules at trusted boundaries;
- do not implement later steps;
- do not add unapproved packages/services;
- do not weaken tests;
- do not rewrite the plan to justify deviations;
- do not perform remote/deployment actions.

Run the narrowest relevant tests after each coherent change.

If repository reality materially contradicts the plan, stop and report it.
```

---

# 22. Phase 8 — Confirm GREEN

## Goal

Prove the step's behavior works without regressing its immediate neighborhood.

---

## Run

1. new tests;
2. directly adjacent existing tests;
3. targeted integration tests;
4. targeted type/static checks if appropriate.

---

## GREEN means

- all approved step tests pass;
- existing targeted tests pass;
- no assertion was weakened;
- no test was skipped to get green;
- no failure was hidden with a broad exception.

---

## Anti-patterns

Do not:

```text
.skip
xfail
@ts-ignore
# type: ignore
catch(Exception) { return success; }
```

merely to make validation pass.

Such mechanisms may be legitimate only when independently justified by repository policy and the plan.

---

# 23. Phase 9 — Refactor Safely

## Goal

Improve clarity after correctness exists, without changing approved behavior.

---

## Refactor candidates

- duplicated new code;
- unclear names;
- oversized functions;
- violation of existing architecture;
- redundant validation;
- poor separation already addressed by repository patterns.

---

## Do not refactor

- unrelated legacy code;
- nearby modules "while here";
- broad architecture;
- another feature;
- package versions.

---

## Refactor loop

```text
GREEN
  ↓
small refactor
  ↓
same tests
  ↓
GREEN
```

If behavior changes, it is no longer a pure refactor.

---

# 24. Phase 10 — Data and Migration Validation

> Apply when the step changes persistent data.

## Goal

Ensure data changes are safe, tenant-aware, reversible where reasonable, and compatible with existing records.

---

## Check

- migration naming/order;
- forward migration;
- local rollback if project supports it;
- nullable/default behavior;
- existing-record compatibility;
- constraints;
- indexes;
- foreign keys;
- tenant ownership;
- RLS/policies;
- generated types;
- seed/fixture updates;
- migration runtime risk;
- destructive behavior.

---

## Migration rules

Do not:

- modify an already-applied shared migration unless project policy permits it;
- run a production migration from this workflow;
- delete columns/data as a convenience;
- disable RLS temporarily and forget to restore it;
- use service-role access as a shortcut around authorization.

---

## Supabase / multi-tenant LMS

For tenant-owned records, test at least:

```text
tenant A can access authorized tenant A record
tenant A cannot access tenant B record
unauthorized user cannot mutate record
service/background operation preserves tenant identity
```

Exact tests depend on the approved architecture.

---

# 25. Phase 11 — Authorization, Tenancy, Privacy, and Security Validation

## Goal

Verify security behavior as part of implementation, not as a later cleanup task.

---

## Authorization checklist

- [ ] authentication is enforced where required;
- [ ] role/permission is checked;
- [ ] resource ownership is checked where required;
- [ ] server-side enforcement exists;
- [ ] object IDs cannot bypass tenant boundaries;
- [ ] background jobs receive trusted tenant context;
- [ ] privileged service credentials do not become a general bypass.

---

## Input checklist

- [ ] strings bounded;
- [ ] identifiers validated;
- [ ] URLs validated where relevant;
- [ ] files validated;
- [ ] file sizes bounded;
- [ ] MIME/content mismatch considered;
- [ ] pagination bounded;
- [ ] AI prompts/context bounded.

---

## Privacy checklist

- [ ] sensitive fields are not logged;
- [ ] source documents are not exposed to unauthorized learners;
- [ ] learner records are tenant-scoped;
- [ ] external providers receive only required data;
- [ ] analytics avoid unnecessary sensitive content.

---

## Prompt

```text
Validate Step [N] against its security contract.

Inspect the actual diff and tests.

Verify:
- auth;
- authorization;
- tenant isolation;
- ownership;
- input validation;
- sensitive logging;
- external data exposure;
- state mutation safety.

Add or strengthen tests only when required by the approved feature behavior.

Do not broaden feature scope.
```

---

# 26. Phase 12 — AI-Specific Implementation and Evaluation

> Apply to LLM, RAG, embeddings, reranking, AI-generated course content, AI companions, AI grading/feedback, or other probabilistic behavior.

## Goal

Do not treat "the model returned something" as successful implementation.

---

# 26.1 Separate software correctness from AI quality

### Software correctness

Deterministic checks may validate:

- authorized caller;
- correct tenant/course context;
- request validation;
- correct retrieval filter;
- structured response parsing;
- persistence;
- lifecycle state;
- retries/timeouts;
- citation IDs exist;
- cost/usage captured;
- failure state shown.

### AI quality

Evaluations may validate:

- groundedness;
- correctness;
- citation correctness;
- relevance;
- educational usefulness;
- refusal when evidence is absent;
- no cross-course leakage;
- no cross-tenant leakage;
- prompt-injection resistance;
- course-structure completeness.

Both are required when the plan says both are required.

---

# 26.2 Do not hardcode around eval examples

The implementation must solve the behavior class.

Do not add brittle special cases that merely make the known eval dataset pass.

---

# 26.3 AI output validation

Machine-consumed AI output should be validated before persistence or action.

Examples:

```text
schema validation
allowed enum transitions
maximum generated item count
required source references
course/module/lesson hierarchy validity
```

Malformed output should enter an explicit failure/retry path.

---

# 26.4 Grounding boundary

For course-grounded AI:

- retrieval must remain inside authorized tenant/course sources;
- retrieved document text is data, not trusted system instruction;
- missing evidence should follow the approved fallback/refusal policy;
- citations should map to permitted source records;
- learner-visible citations must not expose forbidden source content.

---

# 26.5 AI provider failure

Test approved behavior for relevant:

- timeout;
- rate limit;
- malformed structured output;
- safety refusal;
- partial stream;
- retry exhaustion;
- provider outage.

---

# 26.6 AI eval gate

Run the approved eval suite for changes that materially affect:

- prompts;
- retrieval;
- chunking;
- reranking;
- context construction;
- model selection;
- structured output;
- AI post-processing.

Do not claim AI behavior is validated when only unit tests ran.

---

# 27. Phase 13 — UI and User-Journey Verification

> Apply when the step changes a user-facing flow.

## Goal

Validate the behavior on the surface a user actually uses.

---

## Check

- loading;
- empty;
- success;
- error;
- permission denied;
- retry;
- disabled state;
- async progress;
- mobile/responsive behavior if relevant;
- keyboard/accessibility basics;
- stale/duplicate submission;
- page refresh/re-entry when relevant.

---

## UI rule

A correct backend with a misleading UI is not a complete user-facing step.

Likewise, a UI hiding a button is not sufficient authorization.

---

## Manual / browser verification record

```markdown
### User Journey Verification

Scenario:
[scenario]

Result:
PASS / FAIL

Evidence:
[brief description / screenshot reference if workflow supports it]

Notes:
...
```

---

# 28. Phase 14 — Run Complete Automated Guardrails

## Goal

Move from narrow development checks to the repository's required step-completion checks.

---

## Typical order

Use the real project commands.

A common sequence:

```text
format/check formatting
lint
typecheck
static analysis
targeted tests
integration tests
full relevant test suite
build
AI eval smoke/full suite where required
```

---

## Do not invent command names

Read:

- `package.json`;
- `pyproject.toml`;
- `Makefile`;
- task runner config;
- CI workflow;
- `AGENTS.md`;
- repository docs.

Use the project's existing commands.

---

## Failure rule

If a required check fails because of the implementation:

fix it before completion.

If a required check is blocked by environment or a pre-existing issue:

record the exact limitation and do not falsely claim it passed.

---

# 29. Phase 15 — Diff and Scope Review

## Goal

Review what changed, not what Codex remembers changing.

---

## Inspect

```text
git status
git diff --stat
git diff
git diff --check
```

Use equivalent repository tooling if needed.

---

## Scope questions

For every changed file:

1. Why did this step need this file?
2. Is the change necessary?
3. Did formatting touch unrelated code?
4. Did a generated file update legitimately?
5. Did a dependency/lockfile change unexpectedly?
6. Did an API/schema surface expand?
7. Did authorization become weaker?
8. Did tests become weaker?
9. Did future-step code leak in?

---

## Diff budget

There is no universal maximum diff size.

However, when the diff is much larger than the planned step implied, treat that as a review signal.

Ask:

> Is the step too large, or did implementation drift?

Do not normalize a huge diff just because Codex produced it.

---

# 30. Phase 16 — Local AI Code Review

## Goal

Use a separate review pass before handing the work to the formal Code Review workflow.

The reviewer should inspect the **actual diff**.

---

## Prefer reviewer separation

When possible:

- implementation agent writes code;
- fresh Codex context or separate reviewing agent reviews it.

This reduces anchoring to the implementer's assumptions.

---

## Local review severity

Use:

### Critical
Security, data loss, cross-tenant exposure, privilege escalation, major integrity failure.

### Error
Incorrect behavior, broken requirement, likely runtime failure, missing required test.

### Warning
Maintainability, incomplete failure behavior, risky implementation, architectural drift.

### Suggestion
Useful improvement that is not required for correctness.

### Nitpick
Very minor style/readability item.

---

## Review prompt

```text
Review the current implementation diff for:

Feature: [FEATURE]
Step: [STEP]

Read:
- AGENTS.md
- spec.md
- feature.md
- technical-decisions.md
- implementation-plan.md
- test-plan.md

Then review the actual Git diff.

Evaluate:

1. correctness;
2. scope compliance;
3. acceptance criteria;
4. test quality;
5. authorization;
6. tenant isolation;
7. input boundaries;
8. data integrity;
9. error handling;
10. concurrency/idempotency where relevant;
11. repository architecture consistency;
12. unnecessary duplication;
13. unapproved dependencies;
14. AI grounding/evaluation behavior where relevant;
15. accidental future-step implementation.

Classify findings:
- Critical
- Error
- Warning
- Suggestion
- Nitpick

For each finding include:
- file;
- line/area;
- problem;
- why it matters;
- minimal fix.

End with:
- merge/code-review readiness assessment.

Do not modify code during this review pass.
```

---

# 31. Phase 17 — Turn Review Findings Into a Checklist

## Goal

Fix review findings systematically without losing track.

---

## Checklist format

```markdown
# Implementation Review Fixes — [Feature] Step [N]

## Critical
- [ ] ...

## Error
- [ ] ...

## Warning
- [ ] ...

## Suggestion
- [ ] ...

## Nitpick
- [ ] ...

## Verification
- [ ] targeted tests pass
- [ ] required full checks pass
- [ ] final diff inspected
```

---

## Fix order

Default:

```text
Critical
  ↓
Error
  ↓
Warning
  ↓
Suggestion if worthwhile/in-scope
  ↓
Nitpick if worthwhile/in-scope
```

Do not allow suggestions/nitpicks to create scope expansion.

---

## Verify each fix

After resolving an issue:

- rerun the relevant test/check;
- mark it complete only when verified;
- if one fix resolves multiple findings, verify each finding independently.

---

# 32. Phase 18 — Rapid Review and Guardrail Refinement

## Goal

Use implementation mistakes to improve the repository's future defaults.

---

## Ask after fixes

Did this review expose a repeatable problem such as:

- wrong framework abstraction;
- repeated duplicate validation;
- repeated RLS mistake;
- inconsistent route naming;
- overly broad mass assignment;
- unsafe logging;
- AI prompt data treated as trusted instruction;
- incorrect test command;
- repeated import pattern.

If yes, consider a durable guardrail.

---

## Where a guardrail belongs

### AGENTS.md

Use when it is a durable agent instruction.

### Linter/static analysis

Use when a machine can reliably detect the violation.

### Test helper/framework

Use when the correct pattern should be easier than the wrong pattern.

### Hook/CI

Use when the check must never be forgotten.

### Architecture/ADR

Use when it is a meaningful design decision.

---

## Do not add guardrails reflexively

One unusual bug does not require a global rule.

Prefer high-value, repeatable rules.

---

# 33. Phase 19 — Update Durable Progress

## Goal

Make the implementation resumable and auditable.

---

## Update `implementation-status.md`

Record:

- current step;
- completed checks;
- test results;
- known baseline failures;
- deviations;
- review findings status;
- branch;
- current/last-known-good commit;
- next action.

---

## Plan deviation record

If implementation needed a minor approved deviation:

```markdown
## Deviations From Plan

### DEV-001
**Original plan:** ...
**Observed repository reality:** ...
**Change:** ...
**Why behavior/scope is unchanged:** ...
**Approval/source:** ...
```

Material product/architecture deviations should go back to Plan Feature rather than being silently accepted here.

---

# 34. Phase 20 — Prepare the Code Review Handoff

## Goal

Give the next reviewer enough evidence to review without reconstructing the entire session.

---

## Implementation summary template

```markdown
# Implementation Summary

## Feature
[Feature]

## Step
[Step]

## What Changed
- ...

## Why
- ...

## Files / Areas Changed
- ...

## Tests Added / Updated
- ...

## Verification
- `command` — PASS
- `command` — PASS

## Debugging Evidence
- Not applicable / reproduction, root cause, and RED to GREEN proof

## Performance Evidence
- Not applicable / scenario, baseline, before/after, and regression guard

## Security / Tenant Verification
- ...

## AI Evaluation
- Not applicable / results

## User Journey Verification
- Not applicable / results

## Known Pre-existing Issues
- None / ...

## Deviations From Plan
- None / ...

## Explicitly Not Implemented
- ...

## Review Focus
- ...

## Status
READY FOR CODE REVIEW
```

---

# 35. Implementation Gate

The implementation step is complete only when this gate passes.

---

## 35.1 Eligibility

- [ ] Feature was approved.
- [ ] Feature Planning Gate passed.
- [ ] Exact implementation step was selected.
- [ ] Prerequisite steps are complete.
- [ ] A defect has valid reproduction and proven root cause where applicable.
- [ ] A performance change has a stable baseline and one measured bottleneck where applicable.

---

## 35.2 Scope

- [ ] Only the selected step was implemented.
- [ ] Explicit non-scope remains unimplemented.
- [ ] No unrelated refactor was introduced.
- [ ] No unapproved dependency/service was added.
- [ ] No future-step leakage exists.

---

## 35.3 Tests-first evidence

- [ ] Required tests were written/validated before production behavior.
- [ ] RED failed for the intended reason.
- [ ] GREEN passes.
- [ ] Tests were not weakened.
- [ ] Relevant regressions are covered.

---

## 35.4 Code quality

- [ ] Existing architecture is reused.
- [ ] Code follows AGENTS.md.
- [ ] Formatting passes.
- [ ] Lint passes.
- [ ] Typecheck/static analysis passes where required.
- [ ] Required build passes.
- [ ] No unexplained dead code/debug code remains.

---

## 35.5 Data safety

Where applicable:

- [ ] Migration behavior was tested locally.
- [ ] Existing records remain compatible.
- [ ] Constraints/indexes are appropriate.
- [ ] Tenant ownership is explicit.
- [ ] RLS/policies are tested.
- [ ] No production migration was executed.

---

## 35.6 Security

- [ ] Auth is enforced.
- [ ] Authorization is enforced.
- [ ] Tenant isolation is tested.
- [ ] Input boundaries are enforced.
- [ ] Sensitive data is not unnecessarily logged.
- [ ] External calls do not leak unauthorized data.
- [ ] Destructive actions are controlled.

---

## 35.7 AI-specific gate

Where applicable:

- [ ] AI input is bounded.
- [ ] Correct tenant/course context is used.
- [ ] Structured output is validated.
- [ ] Grounding behavior is implemented.
- [ ] Missing-evidence behavior is implemented.
- [ ] Prompt-injection boundary is preserved.
- [ ] AI provider failures are handled.
- [ ] AI evals required by the plan pass.
- [ ] Cost/usage observability required by the plan exists.
- [ ] Human review/autonomy level is unchanged from approved design.

---

## 35.8 Diff / review gate

- [ ] Full diff was inspected.
- [ ] Unexpected lockfile/generated changes are explained.
- [ ] Local AI review was completed.
- [ ] Critical findings = 0.
- [ ] Error findings = 0.
- [ ] Required Warning findings are resolved or explicitly accepted.
- [ ] Final checks were rerun after fixes.

---

## 35.9 Handoff

- [ ] Implementation status updated.
- [ ] Implementation summary prepared.
- [ ] Known limitations documented.
- [ ] Review focus documented.
- [ ] Task Compose identifiers and the post-merge cleanup owner are recorded.
- [ ] No merge/deploy action was performed.

---

## Gate output

Return exactly one:

```text
READY FOR CODE REVIEW
```

or

```text
NOT READY FOR CODE REVIEW
```

If not ready, list blocking failures.

---

# 36. Master Codex Prompt — Implement One Feature Step

Use this as the main implementation prompt after Plan Feature has passed.

```text
You are executing the IMPLEMENT workflow for an AI-enabled LMS.

Feature:
[FEATURE NAME]

Implementation Step:
[STEP NUMBER — STEP NAME]

Your terminal state is:

READY FOR CODE REVIEW

You are NOT responsible for merging or deploying.

==================================================
AUTHORITY
==================================================

You may perform safe, local, in-scope implementation actions:
- inspect files;
- edit required source/tests;
- run non-destructive local commands;
- run tests/lint/typecheck/static analysis/build;
- inspect diffs;
- update implementation progress.

Do not assume authority to:
- push;
- create/modify a remote PR;
- merge;
- deploy;
- modify production data;
- run production migrations;
- alter cloud infrastructure;
- create paid resources;
- change secrets;
- widen IAM permissions;
unless repository instructions explicitly authorize that action.

Never silently:
- expand product scope;
- weaken authorization/RLS;
- change AI autonomy;
- add unrelated features;
- disable tests;
- weaken assertions;
- add major unapproved dependencies;
- implement future steps.

==================================================
SOURCE OF TRUTH
==================================================

Read in this order:

1. AGENTS.md and applicable nested AGENTS.md
2. docs/product/spec.md
3. approved product decisions / ADRs
4. feature.md
5. technical-decisions.md
6. implementation-plan.md
7. test-plan.md
8. features.md
9. existing implementation evidence
10. step prompt

If a material conflict exists, stop the affected work and report it.

Do not edit planning docs merely to justify implementation drift.

==================================================
PHASE 0 — ELIGIBILITY
==================================================

Confirm:

- Feature Planning Gate is READY FOR IMPLEMENTATION.
- Selected step exists.
- Prerequisites are complete.
- Acceptance checks exist.
- Required tests exist.
- Explicit non-scope exists.

If not, return NOT ELIGIBLE and blockers.

==================================================
PHASE 1 — LOAD CONTEXT
==================================================

Read all applicable instructions and selected feature artifacts.

Inspect only relevant:
- implementation code;
- tests;
- schema/migrations;
- auth/RLS;
- adjacent architecture;
- external integration wrappers.

Identify:
- behavior to add;
- behavior to preserve;
- behavior not to add;
- patterns to reuse;
- tests;
- security/tenant rules;
- failures.

==================================================
PHASE 2 — GIT WORKSPACE
==================================================

Inspect:
- current branch;
- git status;
- unrelated local changes;
- expected base.

Never discard user changes.

Use a focused branch/worktree according to repository policy.

Do not work on a protected branch unless explicitly allowed.

==================================================
PHASE 3 — BASELINE
==================================================

Run the narrowest useful existing checks before implementation.

Record:
- passing baseline;
- pre-existing failures;
- environmental limitations.

Do not fix unrelated failures.

==================================================
PHASE 4 — STEP CONTRACT
==================================================

Reconfirm:

MUST IMPLEMENT
MUST PRESERVE
MUST NOT IMPLEMENT
TESTS REQUIRED
SECURITY/TENANT BOUNDARIES
COMPLETION CHECKS

Stop if repository reality materially invalidates the approved plan.

==================================================
PHASE 5 — TESTS FIRST
==================================================

Implement only the approved tests first.

Use current repository test patterns.

Tests must represent:
- acceptance behavior;
- auth/tenant rules;
- important failure behavior;
- idempotency/concurrency where applicable.

Do not implement production behavior yet.

Run the new tests.

==================================================
PHASE 6 — RED GATE
==================================================

Confirm each new test fails for the intended missing-feature reason.

Fix invalid test failures such as:
- bad fixture;
- wrong import;
- syntax error;
- environment error;
- incorrect assumption.

Do not begin production implementation until RED is meaningful.

==================================================
PHASE 7 — MINIMUM GREEN IMPLEMENTATION
==================================================

Implement the minimum coherent production change.

Rules:
- only this step;
- reuse existing architecture;
- no speculative abstractions;
- no unapproved dependencies;
- no future-step code;
- server-side/trusted authorization;
- validated inputs;
- explicit failures;
- tenant-safe behavior.

Run targeted tests frequently.

==================================================
PHASE 8 — GREEN GATE
==================================================

Run:
- new tests;
- adjacent tests;
- relevant integration checks.

All must pass unless a documented pre-existing failure applies.

Do not skip/weaken tests to get green.

==================================================
PHASE 9 — REFACTOR
==================================================

Refactor only implementation introduced by this step or directly required to
fit existing architecture.

After every refactor:
- rerun targeted tests;
- preserve behavior.

No unrelated cleanup.

==================================================
PHASE 10 — DATA
==================================================

If persistent data changed, verify:
- local migration;
- compatibility;
- constraints/indexes;
- tenant ownership;
- RLS/policy behavior;
- generated types/fixtures;
- rollback strategy where supported.

Never run production migrations.

==================================================
PHASE 11 — SECURITY
==================================================

Validate:
- auth;
- authorization;
- ownership;
- tenant isolation;
- IDOR resistance;
- input bounds;
- file validation;
- sensitive logs;
- external data disclosure;
- destructive mutations.

Add missing approved security tests.

==================================================
PHASE 12 — AI
==================================================

If AI behavior changed, separately validate:

SOFTWARE CORRECTNESS
- tenant/course context;
- retrieval filters;
- request/response validation;
- structured output;
- persistence;
- retries;
- citations;
- usage metadata.

AI QUALITY
- groundedness;
- correctness;
- citation quality;
- missing-evidence behavior;
- tenant/source isolation;
- prompt-injection resistance;
- educational usefulness where required.

Run the approved AI eval suite for relevant changes.

Do not hardcode implementation to known eval examples.

==================================================
PHASE 13 — UI
==================================================

If user-facing behavior changed, validate relevant:
- loading;
- empty;
- success;
- error;
- permission denied;
- retry;
- async progress;
- refresh/re-entry;
- duplicate submission;
- responsive/accessibility basics.

Record manual/browser verification if required.

==================================================
PHASE 14 — FULL GUARDRAILS
==================================================

Discover actual repository commands from:
- AGENTS.md;
- package manifests;
- pyproject;
- Makefile/task runner;
- CI.

Run applicable:
- formatter/check;
- lint;
- typecheck;
- static analysis;
- targeted tests;
- integration tests;
- relevant/full suite;
- build;
- AI evals.

Do not invent command names.

==================================================
PHASE 15 — DIFF REVIEW
==================================================

Inspect:
- git status;
- diff stat;
- full diff;
- whitespace/error check.

For every changed file ask:
- why did this step need this?
- is it necessary?
- did unrelated formatting occur?
- did a lockfile change?
- did scope expand?
- did auth weaken?
- did tests weaken?
- did future-step code leak in?

Remove accidental changes.

==================================================
PHASE 16 — LOCAL AI REVIEW
==================================================

Perform a fresh review of the actual diff.

Classify findings:
Critical
Error
Warning
Suggestion
Nitpick

Review:
- correctness;
- scope;
- tests;
- auth/tenancy;
- data integrity;
- failure handling;
- concurrency;
- existing architecture;
- unnecessary duplication;
- AI behavior.

Do not modify code during the review pass.

==================================================
PHASE 17 — REVIEW FIX CHECKLIST
==================================================

Turn actionable findings into a checklist.

Fix:
Critical → Error → required Warning

Suggestions/Nitpicks only if in-scope and worthwhile.

After fixes rerun affected tests/checks.

Do not mark a finding resolved without verification.

==================================================
PHASE 18 — GUARDRAIL LEARNING
==================================================

Determine whether a review finding represents a durable, repeated repository
rule.

If yes, update the appropriate approved location:
- AGENTS.md;
- linter/static check;
- test helper;
- hook/CI;
- ADR.

Do not add global rules for one-off feature details.

==================================================
PHASE 19 — PROGRESS
==================================================

Update implementation-status.md with:
- step status;
- branch;
- tests/checks;
- known pre-existing failures;
- deviations;
- review findings;
- next action;
- last known good commit if available.

Material plan deviations must return to Plan Feature.

==================================================
PHASE 20 — IMPLEMENTATION GATE
==================================================

Return READY FOR CODE REVIEW only when:

- selected step is complete;
- required tests are green;
- required guardrails pass;
- auth/tenant/security requirements pass;
- AI eval requirements pass when applicable;
- diff is scoped;
- Critical findings = 0;
- Error findings = 0;
- required Warning findings are resolved/accepted;
- progress is updated;
- implementation summary is ready;
- no merge/deploy action has been performed.

Otherwise return:

NOT READY FOR CODE REVIEW

and list blocking failures only.
```

---

# 37. Codex Prompt — Resume an Interrupted Implementation

Use this after a new Codex session or a long break.

```text
Resume implementation for:

Feature: [FEATURE]
Step: [STEP if known]

Do not rely on previous chat context.

Read:

1. AGENTS.md
2. product/feature planning artifacts
3. implementation-status.md
4. current Git status and branch
5. current diff
6. relevant tests

Reconstruct:

- current approved step;
- completed checklist items;
- last known passing checks;
- current uncommitted changes;
- known pre-existing failures;
- unresolved review findings;
- next action.

Verify the state instead of trusting the status file blindly.

Do not repeat completed work unless verification shows it is incomplete.

Continue only the current approved implementation step.

Do not merge or deploy.
```

---

# 38. Codex Prompt — Fix a Failed Guardrail

```text
A required implementation guardrail failed:

Command:
[COMMAND]

Failure:
[OUTPUT]

Feature:
[FEATURE]

Step:
[STEP]

Diagnose the failure using repository evidence.

Classify the cause:

1. introduced by current implementation;
2. pre-existing repository failure;
3. incorrect/new test;
4. environment/tooling issue;
5. approved plan/repository contradiction.

If introduced by current implementation, fix it with the smallest in-scope
change and rerun the relevant checks.

Do not:
- weaken tests;
- suppress errors without justification;
- change unrelated code;
- upgrade dependencies opportunistically;
- expand feature scope.

Report:
- root cause;
- files changed;
- verification result.
```

---

# 39. Codex Prompt — Scope Drift Check

```text
Review the current diff only for scope drift.

Feature:
[FEATURE]

Approved Step:
[STEP]

Read the step's:
- objective;
- technical scope;
- explicit non-scope;
- acceptance checks.

For every changed file classify:

REQUIRED
SUPPORTING
SUSPICIOUS
OUT OF SCOPE

Explain SUSPICIOUS and OUT OF SCOPE items.

Check especially for:
- future-step implementation;
- unrelated refactors;
- dependency changes;
- generated-file noise;
- broad formatting;
- extra settings;
- extra UI;
- new abstractions not required by the plan.

Do not modify files.
```

---

# 40. Codex Prompt — Add a Durable Guardrail

Use only after a review identifies a repeatable problem.

```text
We observed this repeated implementation problem:

[PROBLEM]

Before editing AGENTS.md or tooling:

1. verify this is a reusable repository-wide pattern;
2. identify whether the best enforcement is:
   - AGENTS.md;
   - formatter/linter;
   - static analysis;
   - test helper;
   - hook/CI;
   - ADR;
3. prefer machine-enforced guardrails when reliable;
4. keep agent instructions short and objective;
5. do not encode one-off feature behavior globally.

Propose the smallest durable guardrail.

If implementation of the guardrail is already authorized and in-scope, apply it
and run its verification.

Otherwise record the proposal for review.
```

---

# 41. AI LMS Implementation Checklist

Use this supplement only where relevant to the selected step.

---

## 41.1 Multi-tenancy

- [ ] tenant context is derived from trusted membership/resource ownership;
- [ ] user-supplied tenant IDs are not blindly trusted;
- [ ] DB/RLS layer enforces tenant isolation where designed;
- [ ] background tasks preserve tenant identity;
- [ ] vector queries include tenant/course filters;
- [ ] storage paths/policies are tenant-safe;
- [ ] tests attempt cross-tenant access.

---

## 41.2 Course content

- [ ] draft/published status is respected;
- [ ] generated content does not auto-publish unless approved;
- [ ] source provenance is preserved;
- [ ] deleting/changing a source follows approved lifecycle behavior;
- [ ] learners cannot access authoring-only source material.

---

## 41.3 Uploaded books/documents

- [ ] supported type validated;
- [ ] maximum size enforced;
- [ ] unsafe filename/path handling avoided;
- [ ] parsing failures are explicit;
- [ ] tenant ownership is attached before processing;
- [ ] async status is visible when required;
- [ ] retries do not create duplicate resources.

---

## 41.4 RAG / AI companion

- [ ] retrieval restricted to permitted corpus;
- [ ] tenant/course/lesson scope is correct;
- [ ] source text is treated as untrusted data;
- [ ] missing evidence follows approved behavior;
- [ ] citations resolve to authorized sources;
- [ ] answer does not reveal another tenant's content;
- [ ] eval regression cases pass.

---

## 41.5 AI course generation

- [ ] input source validated;
- [ ] generation job is idempotent if required;
- [ ] lifecycle state is valid;
- [ ] model output schema validated;
- [ ] module/lesson hierarchy validated;
- [ ] human review requirement preserved;
- [ ] partial generation failure handled;
- [ ] regeneration semantics match the plan;
- [ ] cost/usage captured if required.

---

## 41.6 Assessments

- [ ] practice vs graded semantics preserved;
- [ ] attempt limits enforced server-side;
- [ ] answer visibility follows rules;
- [ ] AI companion cannot bypass protected assessment rules;
- [ ] grade-changing actions have approved authority;
- [ ] instructor override is audited if required;
- [ ] concurrent submissions handled where relevant.

---

## 41.7 Notifications

- [ ] event is emitted only after valid state change;
- [ ] duplicate notification risk considered;
- [ ] failed delivery does not corrupt domain state;
- [ ] real external sends are not triggered during tests;
- [ ] tenant/user recipient resolution is authorized.

---

# 42. Small Focused Commits

A good implementation branch can still use multiple local commits.

Prefer commits representing meaningful progress:

```text
test: define course-generation lifecycle behavior
feat: implement generation lifecycle state
test: add cross-tenant generation coverage
fix: enforce tenant-scoped generation access
```

Avoid:

```text
stuff
more stuff
fix
try again
final final
```

Repository commit conventions take precedence.

---

## 42.1 Commit gate

Before a local commit:

- targeted tests should pass;
- diff should be understood;
- no unrelated files should be staged.

Do not stage with a broad command blindly when the workspace contains unrelated changes.

---

# 43. What Implementation Must Not Absorb From Later Workflows

The Implement workflow should not become Code Review, Merge, and Deploy all at once.

---

## Belongs here

- implementation;
- tests;
- self-review;
- local independent AI review;
- scope validation;
- verification;
- progress tracking.

---

## Belongs in Code Review

- formal merge recommendation;
- deeper cross-cutting review;
- review by independent reviewer/agent;
- security/performance review depth appropriate to risk;
- requested changes;
- approval/rejection.

---

## Belongs in Merge / Deploy

- final merge gate;
- protected-branch operations;
- production migration execution;
- deployment;
- environment changes;
- production smoke tests;
- rollback decision;
- post-deploy monitoring.

---

# 44. Failure Recovery

Implementation is not always linear.

---

## 44.1 If tests reveal the plan is wrong

Do not change tests to match the implementation.

Determine whether:

- test misunderstood the plan;
- plan has a product contradiction;
- repository architecture invalidates a technical decision.

If material, return to Plan Feature.

---

## 44.2 If a new dependency appears necessary

Before adding it:

1. confirm existing code cannot reasonably solve the requirement;
2. verify the dependency is allowed;
3. verify current official documentation/security/maintenance status when material;
4. update the approved technical decision if this is a major dependency.

Do not install first and justify later.

---

## 44.3 If implementation becomes much larger than expected

Stop at a coherent state.

Inspect why:

- hidden prerequisite;
- poor step decomposition;
- unexpected legacy architecture;
- scope creep;
- data migration complexity.

Split/replan instead of pushing through an unreviewable diff.

---

## 44.4 If external service is unavailable

Use the approved local/mocked strategy.

Do not remove error handling or hardcode success.

Record live integration verification as pending when necessary.

---

## 44.5 If environment prevents full verification

Run every check that can be run.

Record:

- exact blocked command;
- cause;
- what remains unverified.

Do not report `READY FOR CODE REVIEW` if the blocked verification is a required implementation gate unless repository policy explicitly allows the exception.

---

# 45. Anti-Patterns This Workflow Prevents

---

## "Implement the whole feature"

Problem:

- giant diff;
- difficult review;
- scope creep;
- tests written after implementation;
- hidden architecture decisions.

Use one approved step.

---

## "Tests pass, so we're done"

Problem:

Tests may not cover:

- tenant leakage;
- wrong architecture;
- unsafe logs;
- extra scope;
- AI quality;
- misleading UI.

Use the full Implementation Gate.

---

## "Let's improve nearby code while here"

Problem:

Changes become difficult to attribute and review.

Record tech debt separately.

---

## "The agent added a package because it was easier"

Problem:

Dependencies become architecture decisions by accident.

Require approved dependency additions.

---

## "The UI hides the button, so authorization is handled"

Problem:

Client controls are not a security boundary.

Enforce trusted/server-side authorization.

---

## "The LLM response looks good"

Problem:

One example is not an AI evaluation.

Use the approved eval set and deterministic contract tests.

---

## "Change the test until it passes"

Problem:

The test becomes evidence of the implementation rather than the requirement.

Validate test intent against the feature plan.

---

## "Update spec.md to match what we built"

Problem:

Implementation becomes the source of truth.

Return material behavior changes to planning.

---

# 46. Recommended Codex Skill Packaging

This workflow is packaged as `.agents/skills/implement-ai-lms-feature`. The generic
structure below is retained as design background; it does not name an additional
active repository skill.

```text
.agents/
└── skills/
    └── implement-feature-step/
        ├── SKILL.md
        ├── references/
        │   ├── implementation-gate.md
        │   ├── tdd-loop.md
        │   ├── ai-lms-checklist.md
        │   ├── local-review-template.md
        │   └── implementation-status-template.md
        └── scripts/
            ├── verify-step.sh            # optional
            └── scope-diff.sh             # optional
```

Keep executable scripts:

- read-only or non-destructive by default;
- repository-specific;
- explicit about failures.

---

## Example `SKILL.md` frontmatter

```yaml
---
name: implement-feature-step
description: >
  Implement one approved Plan Feature step using tests-first development,
  repository guardrails, scoped changes, security/tenant validation,
  AI evaluations where applicable, local diff review, and a final
  READY FOR CODE REVIEW gate. Use after the Feature Planning Gate passes.
---
```

---

# 47. Recommended AGENTS.md Implementation Section

Adapt this to the actual repository.

```markdown
## Implementation workflow

For non-trivial product features:

1. Require an approved Plan Feature artifact.
2. Implement one approved implementation step at a time.
3. Read the applicable feature/test artifacts before editing.
4. Use tests-first development for planned behavior.
5. Confirm new tests fail for the intended reason before implementing.
6. Make the minimum coherent change required for the selected step.
7. Reuse existing architecture and project dependencies.
8. Do not implement future steps early.
9. Enforce auth/tenant rules at trusted boundaries.
10. Run the repository's required formatter, lint, type/static analysis,
    tests, and build checks.
11. Run approved AI evals when AI behavior changes.
12. Inspect the complete diff before declaring the step done.
13. Never weaken/delete tests merely to make checks pass.
14. Never merge or deploy as part of implementation unless a separate workflow
    explicitly authorizes it.

If repository reality materially contradicts an approved feature decision,
stop implementation and return to Plan Feature.
```

---

# 48. Recommended CI Relationship

Local implementation and CI should reinforce each other.

```text
Codex local loop
    ↓
local required checks
    ↓
Code Review
    ↓
remote CI
    ↓
Merge Gate
```

Do not rely exclusively on CI to discover obvious local failures.

Do not rely exclusively on local checks for merge safety.

---

# 49. Implementation Status State Machine

Recommended states:

```text
PLANNED
  ↓
ELIGIBLE
  ↓
TESTS_RED
  ↓
IMPLEMENTING
  ↓
TESTS_GREEN
  ↓
VERIFYING
  ↓
LOCAL_REVIEW
  ↓
FIXING_REVIEW
  ↓
READY_FOR_CODE_REVIEW
```

Exceptional:

```text
BLOCKED_PLAN
BLOCKED_ENVIRONMENT
BLOCKED_DEPENDENCY
BLOCKED_SECURITY
```

Avoid ambiguous:

```text
almost done
mostly complete
should work
```

---

# 50. Definition of Done — Implement Workflow

Implementation is done only when:

- [ ] Feature Planning Gate passed.
- [ ] One implementation step was selected.
- [ ] Repository instructions were loaded.
- [ ] Relevant existing architecture was inspected.
- [ ] Workspace/branch was verified.
- [ ] Unrelated local changes were preserved.
- [ ] Baseline verification was recorded.
- [ ] Step contract was reconfirmed.
- [ ] Required tests were created/validated first.
- [ ] RED was confirmed for the correct reason.
- [ ] Minimum approved behavior was implemented.
- [ ] GREEN was confirmed.
- [ ] Refactor preserved behavior.
- [ ] Data/migration behavior was validated where relevant.
- [ ] Authorization was validated.
- [ ] Tenant isolation was validated where relevant.
- [ ] Input boundaries were validated.
- [ ] Privacy/security requirements were validated.
- [ ] AI software correctness was tested where relevant.
- [ ] AI quality evals passed where relevant.
- [ ] User journey was checked where relevant.
- [ ] Formatting passed.
- [ ] Lint passed.
- [ ] Type/static analysis passed where required.
- [ ] Required tests passed.
- [ ] Build passed where required.
- [ ] Full diff was inspected.
- [ ] No unapproved scope exists.
- [ ] Local AI review completed.
- [ ] No Critical findings remain.
- [ ] No Error findings remain.
- [ ] Required Warning findings were resolved/accepted.
- [ ] Final verification reran after review fixes.
- [ ] Durable implementation status was updated.
- [ ] Implementation summary was prepared.
- [ ] No production deployment occurred.
- [ ] No merge occurred.
- [ ] Status is **READY FOR CODE REVIEW**.

---

# 51. Full Development Pipeline After This Workflow

```text
┌──────────────────────────┐
│ 1. PLAN PRODUCT          │
│                          │
│ spec.md                  │
│ features.md              │
│ product decisions        │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 2. PLAN FEATURE          │
│                          │
│ feature.md               │
│ technical decisions      │
│ implementation plan      │
│ test plan / AI eval plan │
│ step prompts             │
└────────────┬─────────────┘
             │
             │ READY FOR IMPLEMENTATION
             ▼
┌──────────────────────────┐
│ 3. IMPLEMENT             │
│                          │
│ one step                 │
│ RED → GREEN → REFACTOR   │
│ security / tenant checks │
│ AI evals                 │
│ guardrails               │
│ local review             │
└────────────┬─────────────┘
             │
             │ READY FOR CODE REVIEW
             ▼
┌──────────────────────────┐
│ 4. CODE REVIEW           │
│                          │
│ correctness              │
│ security                 │
│ architecture             │
│ scope                    │
│ test quality             │
│ merge assessment         │
└────────────┬─────────────┘
             │
             │ APPROVED
             ▼
┌──────────────────────────┐
│ 5. MERGE / DEPLOY        │
│                          │
│ merge gate               │
│ production migration     │
│ deployment               │
│ smoke verification       │
│ rollback readiness       │
│ monitoring               │
└──────────────────────────┘
```

---

# 52. How This Improves the Supplied Implementation Workflow

The supplied implementation lessons establish the important foundations:

- add coding guardrails before AI generates substantial code;
- use `AGENTS.md` to define project conventions;
- write tests before implementation;
- automate checks with hooks;
- improve guardrails when review exposes recurring mistakes;
- keep changes in small, focused branches/PRs;
- save progress so work can resume across sessions;
- use a separate AI review pass;
- turn findings into checklists.

This Codex workflow preserves those principles and adds:

1. a formal **implementation eligibility gate**;
2. a strict **one approved feature step** execution boundary;
3. explicit Codex autonomy/approval rules;
4. baseline verification before edits;
5. a required **RED → GREEN → REFACTOR** proof loop;
6. scope-drift diff inspection;
7. multi-tenant/RLS implementation validation;
8. AI correctness separate from AI quality evaluation;
9. source-grounding and prompt-injection checks;
10. production-action boundaries;
11. structured implementation status for resumability;
12. formal local-review severity;
13. durable-guardrail promotion rules;
14. a final `READY FOR CODE REVIEW` state.

---

# 53. Reference Basis

This workflow was developed from the supplied Implementation workflow material,
especially its themes of:

- guardrails before AI-generated code;
- agent navigation and permissions;
- `AGENTS.md`;
- tests before implementation;
- hooks;
- iterative guardrail refinement;
- small focused branches;
- resumable saved plans;
- local AI code review;
- checklists.

Related external references:

- Unlearn skills:
  https://github.com/unlearndev/skills

- Unlearn agent starters:
  https://github.com/unlearndev/agent-starters

- OpenAI Codex developer documentation:
  https://developers.openai.com/codex/

- OpenAI Codex use cases:
  https://developers.openai.com/codex/use-cases

- OpenAI model/prompting guidance:
  https://developers.openai.com/api/docs/guides/latest-model

The implementation workflow should be updated when the project's actual
repository conventions or toolchain change. Project instructions and tested
repository commands always take precedence over generic examples in this file.

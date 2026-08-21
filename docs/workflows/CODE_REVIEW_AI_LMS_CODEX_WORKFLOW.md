# Code Review — AI LMS / Codex Workflow

> **Purpose:** Perform an independent, evidence-based review of one implementation branch or pull request after the **Implement** workflow returns `READY FOR CODE REVIEW`, and determine whether the change is safe, correct, scoped, testable, secure, and ready to enter **Merge / Deploy**.
>
> **Workflow position:**  
> `Plan Product → Plan Feature → Implement → Code Review → Merge / Deploy`
>
> **Review boundary:** The reviewer evaluates and reports. The reviewer does **not** silently redesign the feature, merge the branch, deploy, run production migrations, or hide defects by changing requirements.
>
> **Terminal states:**  
> `APPROVED FOR MERGE`  
> `CHANGES REQUIRED`  
> `BLOCKED`

---

## Repository-specific application

Follow [the repository workflow authority](README.md). Review one independent PR at
its exact `headRefOid`; do not review a mutable working directory or another agent's
branch. Use `gh pr view`, `gh pr diff`, and `gh pr checks`, then record the verdict
with `gh pr review` or, when all agents share one GitHub identity, a PR comment plus
the required distinct human/GitHub approval.

The active ruleset separately requires `quality`, `rls`, `e2e-f001`, and
`documentation` from GitHub Actions on the latest base. Green checks do not replace
review, and a repository-role bypass does not convert a same-identity comment into the
required distinct approval.

An agent never reviews its own PR and never pushes fixes to the author's branch. Four
implementation lanes may continue while a different lane is reviewed. A new push
invalidates the prior reviewed SHA and requires re-review. `docs/plan`, the approved
product contract, issue, and PR contract define expected behavior.

For a defect or performance PR, also follow the evidence contract in the
[Debugging and Performance workflow](DEBUGGING_PERFORMANCE_AI_LMS_CODEX_WORKFLOW.md).
Review must verify the reported behavior was actually reproduced and its cause proven,
or that the optimization targets a measured bottleneck with equivalent before/after
scenarios. Green CI and suspicious-looking code are not substitutes for that evidence.

---

# 1. Why This Workflow Exists

AI-generated code often looks polished before it is trustworthy.

Clean syntax, confident naming, and a green test suite can hide:

- missing error paths;
- unbounded input;
- calls to APIs that do not exist or behave differently;
- destructive state mutations;
- assumed dependencies;
- authorization gaps;
- tenant leaks;
- weak tests;
- hidden side effects;
- oversized abstractions;
- unnecessary dependencies;
- RAG scope leaks;
- prompt-injection risks;
- AI outputs that are syntactically valid but educationally wrong.

The Code Review workflow is therefore not:

> "Read the diff and say whether it looks good."

It is a structured interrogation of the change.

---

# 2. Full Development Pipeline

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
└────────────┬─────────────┘
             │ READY FOR IMPLEMENTATION
             ▼
┌──────────────────────────┐
│ 3. IMPLEMENT             │
│                          │
│ tests first              │
│ RED → GREEN → REFACTOR   │
│ guardrails               │
│ local review             │
└────────────┬─────────────┘
             │ READY FOR CODE REVIEW
             ▼
┌──────────────────────────┐
│ 4. CODE REVIEW           │
│                          │
│ triage                   │
│ First Five               │
│ structured review        │
│ ZOMBIES                  │
│ side effects             │
│ security                 │
│ tests                    │
│ dependencies             │
│ AI/RAG review            │
└────────────┬─────────────┘
             │ APPROVED FOR MERGE
             ▼
┌──────────────────────────┐
│ 5. MERGE / DEPLOY        │
│                          │
│ merge gate               │
│ migration gate           │
│ deployment               │
│ smoke verification       │
│ monitoring / rollback    │
└──────────────────────────┘
```

---

# 3. Required Inputs

The formal Code Review workflow should receive:

```text
AGENTS.md and REVIEW_GUIDE.md             # when present
docs/workflows/README.md
docs/workflows/DEBUGGING_PERFORMANCE_AI_LMS_CODEX_WORKFLOW.md when applicable
docs/product/spec.md, features.md, and decisions.md
relevant docs/plan/ADRs
approved GitHub issue and frozen contracts
pull request body and implementation summary
exact base/head names and headRefOid
GitHub diff, reviews, and CI status
local verification/evaluation evidence
bug reproduction/root-cause/RED-to-GREEN evidence when applicable
performance scenario/baseline/before-after/guard evidence when applicable
```

For AI features, also read any approved:

```text
AI evaluation plan
prompt / model policy
RAG / retrieval design
privacy policy
content provenance rules
assessment integrity rules
```

---

# 4. What Code Review Produces

The default artifact is a `gh pr review` tied to the exact reviewed SHA. Add a small
repository evidence record only when the definition of done requires durable evidence
beyond GitHub's review and CI history.

A formal review report should include:

1. review scope;
2. base/head identifiers;
3. risk triage;
4. verified findings;
5. missing or weak tests;
6. AI-specific findings where relevant;
7. merge-blocking items;
8. non-blocking items;
9. final verdict.

---

# 5. Review Independence

The formal reviewer should ideally use:

- a fresh Codex context;
- a different model instance;
- a different human reviewer;
- or a deliberately reset review session.

The reviewer must not assume that implementation decisions are correct merely because the implementation agent made them.

---

## 5.1 Reviewer stance

The reviewer should:

- verify claims;
- distrust plausible-looking code until traced;
- prefer evidence over intuition;
- inspect behavior, not style alone;
- focus review effort by risk;
- avoid false positives;
- avoid inventing requirements;
- distinguish merge blockers from preferences.

---

## 5.2 Reviewer must not

The reviewer must not:

- rewrite requirements to match the code;
- mark speculative concerns as facts;
- approve merely because tests pass;
- reject merely because code differs from personal preference;
- review generated files line-by-line unless they contain unexpected changes;
- merge;
- deploy;
- modify production data;
- run production migrations.

---

# 6. Source-of-Truth Hierarchy During Review

Use this precedence:

1. repository-wide and nested `AGENTS.md`
2. `docs/workflows/README.md`
3. `docs/product/spec.md`
4. approved product decisions and derived features
5. relevant accepted ADRs and `docs/plan` contracts
6. approved GitHub issue, frozen contracts, and acceptance/test plan
7. implementation summary and PR description
8. existing architecture and established code behavior
9. actual diff and verification evidence
10. reviewer inference

Important:

> The diff is evidence of what was implemented. It is not the source of truth for what should have been implemented.

---

# 7. Review Verdicts

Use only:

```text
APPROVED FOR MERGE
CHANGES REQUIRED
BLOCKED
```

---

## 7.1 APPROVED FOR MERGE

Use when:

- no Critical findings remain;
- no Error findings remain;
- required tests and checks pass;
- scope is correct;
- security/tenant behavior is acceptable;
- AI requirements pass where applicable;
- no unresolved blocker prevents merge.

Warnings may remain only when explicitly non-blocking and documented.

---

## 7.2 CHANGES REQUIRED

Use when:

- the implementation is reviewable;
- the plan is still valid;
- defects can be fixed inside the approved feature/step;
- at least one merge-blocking finding exists.

The branch returns to **Implement**.

---

## 7.3 BLOCKED

Use when review cannot responsibly continue because of a material upstream problem, such as:

- feature plan contradicts product spec;
- base branch is ambiguous;
- diff is incomplete or corrupted;
- required dependency/API behavior cannot be verified;
- implementation requires an unapproved product decision;
- tenant/security architecture is unresolved;
- a major migration strategy is undefined;
- required AI evaluation cannot be executed or interpreted.

`BLOCKED` normally returns to Plan Feature or project planning, not ordinary implementation.

---

# 8. Finding Severity Model

Use five levels.

---

## 8.1 Critical

Immediate merge blocker with severe impact.

Examples:

- cross-tenant data exposure;
- authentication bypass;
- privilege escalation;
- destructive data loss;
- leaked production secret;
- payment/grade corruption;
- arbitrary code execution;
- AI tool action can perform unauthorized consequential writes;
- RAG can retrieve another tenant's private course content.

---

## 8.2 Error

Merge blocker because required behavior is incorrect or unsafe.

Examples:

- requirement implemented incorrectly;
- required authorization missing;
- state transition invalid;
- external API call is broken;
- missing required failure handling;
- wrong migration behavior;
- major test gap for required behavior;
- course generation can publish without required approval.

---

## 8.3 Warning

Material risk that may become a blocker depending on context.

Examples:

- fragile concurrency handling;
- unclear retry semantics;
- maintainability issue likely to produce bugs;
- unnecessary complexity;
- weak observability;
- dependency concern;
- incomplete edge-case protection not currently in acceptance criteria.

Warnings must explain why they are blocking or non-blocking.

---

## 8.4 Suggestion

Optional improvement.

Examples:

- clearer naming;
- simpler expression;
- small test readability improvement;
- documentation improvement.

Suggestions do not block merge.

---

## 8.5 Nitpick

Very small style/readability preference.

Nitpicks do not block merge and should be used sparingly.

---

# 9. Finding Quality Standard

Every formal finding must contain:

```text
Severity
File:line
What
Why
Evidence
Minimal direction
```

Recommended format:

```markdown
### [ERROR] Cross-tenant course lookup bypasses tenant scope

**Location:** `path/file.ts:88`

**What:** The lookup filters by course ID but not organization ownership.

**Why:** A user who knows another tenant's course ID can retrieve data outside
their organization.

**Evidence:** The route accepts the ID, the query is unscoped, and no RLS check
covers this table in the inspected migration/policy.

**Direction:** Use the approved tenant-scoped access path or add the missing
trusted authorization boundary.
```

---

## 9.1 Verify before flagging

Before filing a finding:

### Assumed dependency

Confirm the file/class/config really is missing.

### External API call

Check the actual installed SDK version, local type definitions, package source,
or current official documentation when material.

### Input validation

Inspect validators, schema, server boundary, DB constraint, and relevant middleware.

### Error handling

Check whether a global handler, framework mechanism, queue retry policy, or
transaction already handles the failure correctly.

### State mutation

Trace actual readers/writers and downstream effects.

### Security

Verify whether the trusted layer already enforces the protection.

If it cannot be verified, phrase it as a review question only when the missing
information genuinely needs author clarification. Do not invent a defect.

---

# 10. Review Overview

```text
Phase 0   Review eligibility
Phase 1   Establish base/head and diff
Phase 2   Read product/feature intent
Phase 3   Reverse-engineer implemented intent
Phase 4   Triage by feature area and risk
Phase 5   First Five
Phase 6   Structured review map
Phase 7   Types and interfaces
Phase 8   Data flow
Phase 9   Business logic
Phase 10  Edge cases
Phase 11  Claim → Verify → Trace
Phase 12  ZOMBIES adversarial review
Phase 13  Side-effect sweep
Phase 14  Security review
Phase 15  Multi-tenant / RLS review
Phase 16  AI / RAG / agent review
Phase 17  Test-quality review
Phase 18  Dependency review (WARM)
Phase 19  Data / migration review
Phase 20  External integration review
Phase 21  Performance / concurrency / reliability review
Phase 22  UI / UX / accessibility review
Phase 23  Scope and architecture review
Phase 24  Automated review / CI reconciliation
Phase 25  Review findings consolidation
Phase 26  Fix checklist handoff
Phase 27  Re-review
Phase 28  Review-learning loop
Phase 29  Code Review Gate
```

---

# 11. Phase 0 — Review Eligibility

## Goal

Verify that formal review should begin.

---

## Checks

- Implement workflow status is `READY FOR CODE REVIEW`.
- Exact branch/PR is identified.
- Base branch is identified.
- Feature/step is identified.
- Planning artifacts are available.
- Implementation summary exists.
- Required CI/local verification evidence exists or its absence is documented.

---

## Prompt

```text
Begin formal Code Review for:

Feature: [FEATURE]
Implementation Step: [STEP]
Base: [BASE]
Head/Branch/PR: [HEAD]

Before reviewing code:

1. Read implementation-status.md.
2. Confirm status is READY FOR CODE REVIEW.
3. Confirm the base/head identifiers.
4. Confirm the selected feature and step.
5. Confirm planning artifacts exist.
6. Confirm the implementation summary exists.
7. Identify missing evidence that would prevent a responsible review.

Return:
READY TO REVIEW
or
BLOCKED

Do not review code yet if blocked.
```

---

# 12. Phase 1 — Establish the Actual Diff

## Goal

Review the branch that exists, not the branch described by the author.

---

## Required Git evidence

For a GitHub PR, establish remote evidence first:

```text
gh pr view <PR> --json baseRefName,headRefName,headRefOid,files,commits,reviews,statusCheckRollup
gh pr diff <PR>
gh pr checks <PR> --required
```

Record `headRefOid` as the reviewed SHA. In an isolated review worktree, supplement
that evidence with:

```text
git diff <base>...HEAD
git diff --name-status <base>...HEAD
git log <base>..HEAD
git merge-base <base> HEAD
git status
```

Use repository-equivalent commands when needed. Never switch the author's worktree or
reuse another implementation agent's checkout for review.

Three-dot diff is usually appropriate for "changes introduced by this branch
since divergence."

---

## Check

- unexpected commits;
- unrelated files;
- deleted files;
- generated files;
- lockfile changes;
- migration files;
- configuration changes;
- secret-like files;
- build artifacts.

---

## Stop condition

If there are no changes:

```text
BLOCKED — no reviewable diff
```

unless the task is explicitly to review an existing feature area rather than a branch.

---

# 13. Phase 2 — Read Product and Feature Intent

## Goal

Know what "correct" means before judging implementation.

---

## Read

```text
spec.md
features.md
feature.md
technical-decisions.md
implementation-plan.md
test-plan.md
implementation-status.md
```

Also read relevant ADRs / REVIEW_GUIDE / nested AGENTS.md.

---

## Extract

```markdown
## Review Contract

### Intended behavior
- ...

### Required security / tenancy
- ...

### Required failure behavior
- ...

### Required AI behavior
- ...

### Explicit non-scope
- ...

### Required tests
- ...

### Required implementation constraints
- ...
```

Do not treat implementation details from the PR description as requirements
unless they are approved elsewhere.

---

# 14. Phase 3 — Reverse-Engineer the Implemented Intent

## Goal

Explain what the code actually does without using the author's description.

This catches cases where the branch and the plan have diverged.

---

## Prompt

```text
Using only the actual diff and surrounding repository code, explain in simple
points what this branch changes.

Do not judge quality yet.

For each behavior:
- identify the entry point;
- identify the important state/data mutation;
- identify the output/side effect.

Then compare this reverse-engineered behavior to the approved feature step.

List:
MATCH
EXTRA
MISSING
DIFFERENT

Do not propose fixes yet.
```

---

## Important signal

If the reviewer cannot state the implementation intent clearly, that is a
review risk.

Complexity may be hiding:

- mixed responsibilities;
- hidden side effects;
- unrelated scope;
- excessive abstraction.

---

# 15. Phase 4 — Triage the Diff by Risk

## Goal

Spend deep-review effort where blast radius is highest.

---

## Group by behavior / feature area

Good groups:

```text
Course Authorization
Source Document Upload
Generation Lifecycle
AI Retrieval
Assessment Submission
Notification Delivery
Schema and RLS
```

Bad groups:

```text
Controllers
TypeScript Files
Python
Components
```

---

## Risk tiers

### High

Always treat as High when it touches:

- authentication;
- authorization;
- permissions;
- tenant isolation;
- learner records;
- grades;
- payments;
- billing;
- sensitive personal data;
- secrets/tokens;
- production-impacting migrations;
- AI tool execution with consequential actions;
- vector/retrieval tenant boundaries.

Bump risk when:

- complex branching;
- external service calls;
- async jobs;
- large generated change;
- destructive mutation;
- concurrency;
- data migration.

### Medium

Examples:

- validation;
- route handlers;
- state management;
- non-sensitive mutations;
- notifications;
- ordinary integrations.

### Low

Examples:

- styles;
- copy changes;
- low-impact config;
- boilerplate;
- non-behavioral refactor.

---

## Review effort

Default:

```text
High   → deep review
Medium → structured scan + First Five
Low    → targeted red-flag scan
Skip   → generated files unless unexpected
```

---

# 16. Phase 5 — Run the First Five

The first review pass checks five AI failure patterns.

---

## 16.1 Error Handling

Look for:

- empty catches;
- swallowed exceptions;
- silent null fallback;
- failed jobs with no visible state;
- broad catch returning success;
- provider errors ignored;
- transaction failures partially applied.

Do not flag when the repository/framework already provides correct failure behavior.

---

## 16.2 Input Boundaries

Look for:

- missing type validation;
- missing length limits;
- unbounded arrays;
- unbounded pagination;
- large prompt/document inputs;
- unsafe URLs;
- invalid IDs;
- duplicate submissions;
- empty collections;
- invalid lifecycle values.

Check actual validator/schema/DB constraints before filing.

---

## 16.3 External Calls

Verify:

- method exists;
- signature matches installed version;
- timeout;
- failure handling;
- retry behavior;
- request shape;
- response shape;
- authentication;
- idempotency where applicable.

For changing APIs/SDKs, verify against the installed version or current official docs.

---

## 16.4 State Mutations

Look for:

- destructive delete;
- overwrite;
- cascade impact;
- hidden mutation in helper;
- partial update;
- missing transaction;
- duplicate state transition;
- unexpected side effects.

Trace downstream users before flagging.

---

## 16.5 Assumed Dependencies

Confirm:

- imported files exist;
- config keys exist;
- env variables are documented;
- routes exist;
- migrations exist;
- services are registered;
- types/classes exist;
- queue/job infrastructure exists;
- feature flags exist.

---

## First Five output

Only report genuine concerns.

Quality over quantity.

---

# 17. Phase 6 — Build the Structured Review Map

## Goal

Do not read the diff top-to-bottom.

Within each behavioral feature area, review in this order:

```text
1. Types & Interfaces
2. Data Flow
3. Business Logic
4. Edge Cases
```

---

## Why this order

A bad type or contract invalidates downstream reasoning.

A bad data flow makes correct-looking business logic operate on the wrong state.

Business logic is reviewed after boundaries are understood.

Edge cases are reviewed last after the normal path is clear.

---

# 18. Phase 7 — Types and Interfaces Review

## Ask

- What data enters?
- What data exits?
- What is nullable?
- What is optional?
- Which enums/states exist?
- Are schemas and types aligned?
- Are DB constraints aligned?
- Does serialized API output match frontend expectations?
- Does AI structured output match its validator?
- Do SDK types match installed versions?

---

## AI LMS examples

Review:

```text
CourseGenerationStatus
CoursePublicationStatus
OrganizationId / CourseId ownership
SourceDocument metadata
Lesson hierarchy schema
AssessmentResult shape
Citation reference shape
AI response schema
```

---

## Claim → Verify → Trace

Example:

**Claim:** `CourseGenerationResult` always has modules.

**Verify:** Does the validator require a non-empty array?

**Trace:** What happens when the model returns zero modules?

---

# 19. Phase 8 — Data Flow Review

## Trace

```text
input
  ↓
validation
  ↓
authorization
  ↓
transformation
  ↓
domain operation
  ↓
persistence
  ↓
external calls
  ↓
response / UI
```

---

## Look for

- unvalidated user input crossing trusted boundaries;
- tenant ID supplied by user instead of derived from trusted context;
- course ID losing organization scope;
- source document content reaching AI without intended filtering;
- raw provider response persisted without validation;
- frontend trusting data the server should derive;
- sensitive content sent to analytics/logs;
- stale state across async boundaries.

---

# 20. Phase 9 — Business Logic Review

## Ask

- Does the implementation satisfy acceptance criteria?
- Are domain state transitions valid?
- Is behavior missing?
- Is extra behavior present?
- Are authorization rules part of domain behavior where required?
- Are feature non-goals preserved?
- Are retries / duplicates handled as specified?
- Are AI actions at the approved autonomy level?

---

## LMS examples

Check:

- unpublished generated courses remain inaccessible to learners;
- instructors cannot mutate courses outside their organization;
- learner attempt limits are enforced;
- grading authority is correct;
- deleting a source behaves according to content lifecycle rules;
- generation retries do not create duplicate courses;
- AI companion does not access assessment answers when prohibited.

---

# 21. Phase 10 — Edge Cases Review

Focus on:

- null;
- empty;
- zero;
- one;
- maximum;
- just-over-maximum;
- duplicate;
- retry;
- timeout;
- invalid state;
- deleted dependency;
- changed permission;
- stale session;
- concurrent action;
- partial job;
- provider outage.

This phase feeds directly into ZOMBIES.

---

# 22. Phase 11 — Claim → Verify → Trace

Apply this to every high-risk block.

---

## Claim

State plainly what the code claims to do.

Example:

> Only instructors in the course's organization can trigger generation.

---

## Verify

Check actual:

- middleware;
- authorization policy;
- DB/RLS;
- query scope;
- background job context;
- service credential behavior.

---

## Trace

Ask:

> What happens if the input or context is wrong?

Examples:

- another tenant's ID;
- deleted course;
- stale permission;
- background retry after membership removal;
- service-role DB client bypassing RLS.

---

## Reviewer rule

Do not accept names as proof.

A function called:

```text
authorizeCourseAccess()
```

does not prove correct authorization.

Read what it does.

---

# 23. Phase 12 — ZOMBIES Review

Use ZOMBIES to identify high-value adversarial tests.

```text
Z — Zero
O — One
M — Many
B — Boundaries
I — Interfaces
E — Exceptions
S — Simple
```

Skip categories that do not apply.

---

## 23.1 Zero

Examples:

- no modules;
- zero learners;
- empty upload;
- empty AI retrieval result;
- no citations;
- zero attempts remaining.

---

## 23.2 One

Examples:

- one lesson;
- one citation;
- one learner;
- one retry;
- one source chunk.

---

## 23.3 Many

Examples:

- many modules;
- pagination;
- bulk enrollments;
- concurrent generation;
- many citations;
- repeated requests;
- large file sets.

---

## 23.4 Boundaries

Examples:

- max upload size;
- token/context limit;
- just-over-limit string;
- exact attempt limit;
- rate limit threshold;
- course/module limits;
- timeout boundary.

Use actual values from code/config where possible.

---

## 23.5 Interfaces

Review contracts at boundaries:

- HTTP request/response;
- queue payload;
- DB row;
- SDK call;
- webhook;
- AI structured output;
- frontend/backend contract.

---

## 23.6 Exceptions

Examples:

- expired auth;
- invalid state;
- provider error;
- missing source;
- duplicate request;
- malformed model output;
- storage outage.

---

## 23.7 Simple

Verify the ordinary user journey still works.

---

## ZOMBIES finding rule

A missing test is a merge blocker only when the behavior is important enough
that failure would materially violate the feature contract, security, data
integrity, or reliability requirements.

---

# 24. Phase 13 — Side-Effect Sweep

## Goal

Find behavior hidden in places where reviewers may not expect it.

---

## Search for side-effect indicators

Conceptually:

```text
write
save
create
update
delete
remove
send
email
notify
dispatch
emit
publish
push
charge
grade
upload
index
embed
```

Use repository-appropriate searches.

---

## High-risk hiding places

- observers;
- event listeners;
- middleware;
- model hooks;
- helpers;
- validators;
- getters/setters;
- background jobs;
- retries;
- AI tool wrappers.

---

## For every side effect ask

### Intentional?

Does this function own this responsibility?

### Idempotent?

What happens when executed twice?

### Guarded?

If it fails, is system state consistent?

### Authorized?

Does the side effect occur under the correct actor/tenant?

### Observable?

Will operators/users know it failed where required?

---

## LMS examples

Review duplicate:

- enrollment;
- email;
- AI generation;
- indexing;
- publishing;
- grading;
- analytics events.

---

# 25. Phase 14 — Security Review

Use the source five-check security model, expanded for the AI LMS.

---

## 25.1 User input / injection

Review:

- query inputs;
- HTML rendering;
- Markdown rendering;
- file metadata;
- URLs;
- SQL/filter construction;
- AI prompt construction;
- document-derived instructions;
- tool arguments.

---

## 25.2 Overly permissive auth

Review:

- public routes;
- middleware;
- CORS where relevant;
- API keys;
- service roles;
- anonymous access;
- object-level access.

---

## 25.3 Hardcoded secrets

Search changed code/config for:

- tokens;
- API keys;
- credentials;
- service role keys;
- private URLs;
- signed secrets.

Do not print discovered secrets in the report.

---

## 25.4 Rate limiting / abuse

Review high-cost or attackable surfaces:

- login;
- password/reset;
- OTP;
- AI chat;
- generation;
- uploads;
- public search;
- invitation;
- webhook;
- assessment submission.

Do not require rate limiting where risk does not justify it.

---

## 25.5 Authentication ≠ Authorization

Check resource-level access.

Example:

```text
Authenticated user
    ≠
Authorized user for this organization/course/document
```

---

# 26. Phase 15 — Multi-Tenant / Supabase / RLS Review

> Required for tenant-owned data.

## Goal

Prove organization isolation at every relevant layer.

---

## Review

- tenant ownership column;
- foreign-key relationship;
- RLS enabled where required;
- SELECT policy;
- INSERT policy;
- UPDATE policy;
- DELETE policy;
- storage policy;
- service-role usage;
- server query scope;
- vector metadata filtering;
- background jobs;
- realtime subscriptions.

---

## Cross-tenant attack cases

Attempt conceptually or through tests:

```text
Tenant A reads Tenant B record
Tenant A updates Tenant B record
Tenant A deletes Tenant B record
Tenant A uploads into Tenant B path
Tenant A retrieves Tenant B vector chunk
Tenant A subscribes to Tenant B realtime data
```

---

## Service-role warning

Using a privileged Supabase client can bypass RLS.

If service-role access is used:

- scope must be explicit;
- tenant identity must be trusted;
- authorization must be performed before privileged query;
- tests must cover cross-tenant attempts.

---

# 27. Phase 16 — AI / RAG / Agent Review

> Required whenever AI behavior changed.

---

# 27.1 AI purpose

Verify the implementation still matches the approved AI purpose.

Do not allow feature drift such as:

```text
approved:
AI drafts a course

implemented:
AI automatically publishes the course
```

---

# 27.2 AI autonomy

Confirm:

- suggest-only;
- draft;
- reversible action;
- consequential action;

matches the plan.

Any increase in autonomy is a product-level change.

---

# 27.3 RAG isolation

Verify:

- organization filter;
- course filter;
- module/lesson filter where required;
- source authorization;
- metadata filter;
- vector namespace strategy;
- no fallback to unauthorized corpus.

---

# 27.4 Prompt injection

Review whether uploaded/retrieved content can override system intent.

Check:

- source text is treated as data;
- tools are constrained;
- system instructions stay higher priority;
- user content cannot request unauthorized data/tool access;
- model output is not blindly executed.

---

# 27.5 Grounding

Verify:

- retrieval evidence exists;
- answer generation receives approved sources;
- insufficient evidence follows policy;
- citations are generated/validated;
- source IDs are authorized.

---

# 27.6 Structured output

Check:

- schema validation;
- malformed output handling;
- enum bounds;
- list limits;
- hierarchy validation;
- retry/failure behavior.

Do not trust JSON merely because it parses.

---

# 27.7 AI provider error handling

Review:

- timeout;
- rate limit;
- safety refusal;
- malformed response;
- partial stream;
- tool-call error;
- retry exhaustion.

---

# 27.8 AI cost / abuse

Review when required:

- max input;
- max output;
- concurrency;
- retry count;
- regeneration;
- per-user/tenant usage;
- logging/metrics.

---

# 27.9 AI eval evidence

A green unit suite does not prove AI quality.

Check required eval results for:

- groundedness;
- correctness;
- citations;
- missing-evidence behavior;
- tenant/source isolation;
- prompt-injection resistance;
- educational usefulness.

---

# 28. Phase 17 — Review AI-Generated Tests

A passing suite can still be weak.

Review test quality deliberately.

---

## 28.1 Tautological tests

Bad pattern:

- mock returns `X`;
- assertion checks result is `X`;
- implementation behavior is barely exercised.

Ask:

> If the production code were broken, would this test fail?

---

## 28.2 Happy-path-only tests

Look for absence of:

- invalid input;
- unauthorized access;
- tenant attack;
- provider failure;
- duplicate request;
- boundary values;
- concurrency.

---

## 28.3 Implementation-coupled tests

Bad tests break on harmless refactors but survive wrong user behavior.

Prefer behavioral contracts.

---

## 28.4 Snapshot / copy-paste tests

Large nearly identical snapshots can produce the appearance of coverage without
meaningful behavioral protection.

---

## Three test questions

For each important test:

1. What behavior does this verify?
2. If I broke the feature, would this catch it?
3. Is this testing the code or merely the mock?

---

# 29. Phase 18 — Dependency Review With WARM

Trigger whenever the PR adds a dependency or materially changes one.

```text
W — Worth it?
A — Alive?
R — Right-sized?
M — Maintained securely?
```

---

## 29.1 Worth it?

Ask:

- Does the dependency solve a substantial problem?
- Could existing project tooling already solve it?
- Is this a trivial wrapper around native functionality?

Do not use arbitrary line-count rules as absolute policy.

---

## 29.2 Alive?

Verify material maintenance signals:

- recent releases;
- recent commits;
- maintainer activity;
- compatibility with current runtime/framework.

Use primary sources when verifying current dependency status.

---

## 29.3 Right-sized?

Ask:

- Are we importing an entire framework for one helper?
- Does the dependency add runtime/bundle complexity?
- Is a smaller approved option available?

---

## 29.4 Maintained securely?

Run or inspect the repository's approved audit tooling.

Examples:

```text
npm audit
pnpm audit
pip-audit
composer audit
```

Use the real ecosystem/tooling.

---

## Dependency finding rule

Do not reject dependencies because they are unfamiliar.

Reject or block based on verified:

- security;
- abandonment;
- incompatibility;
- unnecessary attack surface;
- violation of approved technical decisions.

---

# 30. Phase 19 — Data and Migration Review

Review every schema change carefully.

---

## Check

- migration order;
- forward behavior;
- backfill;
- defaults;
- nullability;
- data loss;
- constraint changes;
- index;
- foreign key;
- lock/runtime risk;
- rollback strategy;
- RLS/policy;
- generated type updates;
- existing data compatibility.

---

## High-risk migration examples

- drop column;
- rename without compatibility window;
- enum narrowing;
- rewriting large table;
- changing ownership/tenant key;
- policy removal;
- cascade delete;
- non-null without backfill.

These often require stronger Merge/Deploy planning.

---

# 31. Phase 20 — External Integration Review

For every changed integration:

- provider;
- endpoint;
- SDK method;
- request shape;
- response shape;
- auth;
- timeout;
- retry;
- idempotency;
- webhook verification;
- duplicate webhook behavior;
- failure mapping;
- PII/data sent externally.

---

## Current API verification

When a finding depends on current SDK/API behavior:

- inspect installed package version;
- inspect official documentation/source for that version or current compatible behavior;
- do not rely on memory.

---

## AI LMS integrations may include

- OpenAI;
- Supabase;
- PayMongo;
- Resend;
- Pinecone;
- Upstash;
- Sentry;
- PostHog;
- Vercel;
- Cloudflare.

Only review integrations touched by the change.

---

# 32. Phase 21 — Reliability, Concurrency, and Performance Review

Apply proportional effort.

---

## Reliability

Check:

- retry;
- idempotency;
- partial failure;
- transaction boundary;
- stale state;
- job restart;
- duplicate webhook;
- duplicate click;
- provider timeout.

---

## Concurrency

Ask:

- Can two users update same record?
- Can job run twice?
- Can same generation be started twice?
- Can assessment submit twice?
- Can publish/review race?
- Are unique constraints sufficient?
- Is optimistic/pessimistic locking needed according to design?

Do not introduce complex locking unless risk justifies it.

---

## Performance

Look for obvious regressions:

- N+1;
- unbounded list;
- loading entire document into memory unnecessarily;
- repeated embedding/model calls;
- missing index on new high-volume lookup;
- repeated external request;
- client rendering massive payload.

Only block when impact is material.

For a performance-labeled change, code inspection alone is insufficient. Confirm the
same representative scenario, data, tool, warm-up policy, and metric were used before
and after; the improvement exceeds measurement noise; and correctness, tenant/RLS,
privacy, cost, memory, accessibility, and applicable AI quality remain acceptable.

For a defect fix, confirm the regression test represented the report, failed for the
right reason before the fix, the root-cause explanation matches the traced execution
path, and the patch fixes that cause rather than merely hiding its symptom.

---

# 33. Phase 22 — UI / UX / Accessibility Review

Apply when UI changed.

---

## Review behavior

- loading;
- empty;
- success;
- failure;
- retry;
- permission denied;
- disabled states;
- duplicate submit;
- async state;
- stale page;
- refresh;
- navigation;
- mobile layout;
- obvious keyboard/accessibility issues.

---

## Important

A polished UI must not hide broken backend behavior.

A hidden button is not authorization.

---

# 34. Phase 23 — Scope and Architecture Review

## Goal

Ensure the implementation is no larger than the approved step.

---

## Compare diff to

- objective;
- technical scope;
- explicit non-scope;
- feature non-goals;
- approved dependencies.

---

## Flag

- future-step code;
- unrelated refactor;
- unexpected package;
- new generic abstraction;
- extra settings;
- extra endpoint;
- new admin page;
- extra automation;
- architecture replacement;
- product behavior not in spec.

---

## Architecture consistency

Ask:

- Did implementation reuse existing pattern?
- Did it bypass domain/service/action pattern?
- Did it create duplicate abstractions?
- Did it move logic to the wrong layer?
- Did it weaken trusted boundaries?

Differences are not automatically defects.

The reviewer must explain why the difference matters.

---

# 35. Phase 24 — Automated Review and CI Reconciliation

Automated review is a filter, not final authority.

Possible automated checks:

- First Five;
- secret scanning;
- dependency audit;
- lint;
- typecheck;
- unit/integration tests;
- SAST;
- migration checks;
- AI-generated PR triage;
- AI review comments.

---

## Reviewer responsibility

For every automated finding:

- verify it;
- discard false positives;
- escalate real issues.

For every green check:

- understand what it does **not** prove.

---

## CI mismatch

If local and CI results differ:

- inspect environment/version differences;
- do not choose the result you prefer;
- resolve before approval if required check is unstable or red.

---

# 36. Phase 25 — Consolidate Findings

Do not dump raw notes.

Deduplicate findings that share one root cause.

---

## Example

Instead of five comments:

```text
missing tenant filter in route
missing tenant filter in service
missing tenant filter in retrieval
missing cross-tenant test
service client uses admin key
```

A clearer root finding may be:

```text
[CRITICAL] Tenant boundary is not enforced for course retrieval.

Evidence:
- route accepts arbitrary course ID;
- service uses privileged client;
- query does not derive organization scope;
- RLS is bypassed;
- no cross-tenant test exists.
```

Then list required remediation points.

---

## Finding output order

```text
Critical
Error
Warning
Suggestion
Nitpick
```

Within a level, order by blast radius.

---

# 37. Formal Code Review Report Template

```markdown
# Code Review — [Feature / Step]

## Verdict
CHANGES REQUIRED

## Scope
- Base:
- Head:
- Feature:
- Step:
- Reviewer:
- Review date:

## Risk Triage
### High
- ...
### Medium
- ...
### Low
- ...
### Skipped / Generated
- ...

## Findings

### Critical
#### CR-001 — [Title]
**Location:** `file:line`
**What:** ...
**Why:** ...
**Evidence:** ...
**Direction:** ...

### Error
...

### Warning
...

### Suggestion
...

### Nitpick
...

## Test Review
- ...

## Security / Tenant Review
- ...

## AI / RAG Review
- Not applicable / ...

## Dependency Review
- No new dependencies / ...

## Required Changes
- [ ] CR-001 ...
- [ ] ER-001 ...

## Non-Blocking Follow-Ups
- ...

## Final Assessment
CHANGES REQUIRED
```

Omit empty severity sections.

---

# 38. Phase 26 — Create the Fix Checklist

When verdict is `CHANGES REQUIRED`, produce a concrete checklist.

---

## Checklist rules

Only include:

- Critical;
- Error;
- blocking Warning;
- specifically accepted required cleanup.

Do not force suggestions/nitpicks into blocking work.

---

## Template

```markdown
# Code Review Fix Checklist — [Feature / Step]

## Blocking

### Critical
- [ ] CR-001 — ...

### Error
- [ ] ER-001 — ...

### Required Warnings
- [ ] WR-001 — ...

## Required Verification After Fixes
- [ ] targeted tests
- [ ] security/tenant tests
- [ ] relevant AI evals
- [ ] lint/typecheck/static analysis
- [ ] final diff review
- [ ] formal re-review
```

The branch returns to **Implement**.

---

# 39. Phase 27 — Re-Review After Fixes

## Goal

Verify fixes without assuming they solved the original issue.

---

## Read

- original review;
- fix checklist;
- new diff since review;
- complete branch diff;
- relevant tests/check results.

---

## For each finding

Mark:

```text
RESOLVED
PARTIALLY RESOLVED
NOT RESOLVED
SUPERSEDED
```

---

## Re-review rule

A fix can introduce a new defect.

Therefore:

1. verify targeted fix;
2. inspect changed area for regression;
3. run relevant First Five / security checks again;
4. inspect complete diff for scope drift.

---

## Prompt

```text
Re-review the branch after code review fixes.

Read the original code-review.md and fix checklist.

For each blocking finding:
- verify the actual code change;
- verify tests/evidence;
- mark RESOLVED / PARTIAL / NOT RESOLVED / SUPERSEDED.

Then review only newly changed code deeply plus the complete branch diff for
new Critical/Error regressions.

Do not approve based solely on author statements.
```

---

# 40. Phase 28 — Turn Reviews Into Better Future Output

Review should improve the system, not just one PR.

Use two durable knowledge layers.

---

## 40.1 Agent rules

Recurring generation mistakes belong in the project agent rules when they are:

- general;
- repeatable;
- objectively useful.

Examples:

```text
Never use an empty catch block.
Do not introduce model observers without explicit architectural approval.
All tenant-owned server mutations require trusted tenant authorization.
Do not send raw source documents to analytics/logs.
```

Keep rules concise.

---

## 40.2 REVIEW_GUIDE.md

This is for reviewers.

It should answer:

> "I am reviewing this area. What should I pay special attention to?"

Example:

```markdown
## AI Retrieval
- Verify organization/course filters at both retrieval and source resolution.
- Verify privileged DB clients do not bypass tenant authorization.
- Check that retrieved document text is treated as untrusted data.

## Assessments
- Verify graded attempts cannot be modified outside approved override paths.
- Verify AI companion access cannot expose protected answers.

## Source Documents
- Verify source content is not exposed directly to learners unless explicitly allowed.
```

---

## 40.3 Do not create a bug-history dump

Remove stale review warnings once architecture makes them impossible.

The guide should remain short and useful.

---

# 41. Phase 29 — Code Review Gate

A branch is approved only when the gate passes.

---

## 41.1 Review scope

- [ ] Base and head are verified.
- [ ] Diff is complete.
- [ ] Feature/step is identified.
- [ ] Planning artifacts were read.
- [ ] Implementation intent was reverse-engineered.
- [ ] Scope matches approved step.

---

## 41.2 First Five

- [ ] Error handling reviewed.
- [ ] Input boundaries reviewed.
- [ ] External calls verified.
- [ ] State mutations traced.
- [ ] Assumed dependencies verified.

---

## 41.3 Structured review

- [ ] Types/interfaces reviewed.
- [ ] Data flow traced.
- [ ] Business logic compared to requirements.
- [ ] Edge cases reviewed.
- [ ] Claim → Verify → Trace applied to high-risk logic.

---

## 41.4 Adversarial review

- [ ] Relevant ZOMBIES cases reviewed.
- [ ] Side effects swept.
- [ ] Duplicate/retry behavior checked.
- [ ] Concurrency reviewed where relevant.

---

## 41.5 Security

- [ ] Input/injection risks reviewed.
- [ ] Authentication reviewed.
- [ ] Authorization reviewed.
- [ ] Secrets reviewed.
- [ ] Rate/abuse controls reviewed where relevant.
- [ ] Object-level access reviewed.
- [ ] Sensitive logging reviewed.

---

## 41.6 Multi-tenancy

Where applicable:

- [ ] tenant ownership is explicit;
- [ ] RLS/policies are correct;
- [ ] service-role bypass is controlled;
- [ ] storage is tenant-safe;
- [ ] vector retrieval is tenant-safe;
- [ ] background jobs retain tenant scope;
- [ ] cross-tenant tests exist.

---

## 41.7 AI

Where applicable:

- [ ] AI purpose matches plan;
- [ ] AI autonomy matches plan;
- [ ] retrieval scope matches plan;
- [ ] grounding behavior is correct;
- [ ] citations are safe/correct;
- [ ] prompt injection boundary is preserved;
- [ ] structured output is validated;
- [ ] provider failures are handled;
- [ ] AI eval evidence is acceptable;
- [ ] no cross-tenant/source leakage exists.

---

## 41.8 Tests

- [ ] Important tests prove behavior.
- [ ] Tests are not tautological.
- [ ] Tests are not only happy path.
- [ ] Tests are not excessively implementation-coupled.
- [ ] Security/tenant cases are covered.
- [ ] failure paths are covered.
- [ ] required AI evals exist.

---

## 41.9 Dependencies

Where applicable:

- [ ] new dependency is justified;
- [ ] maintenance is verified;
- [ ] size/scope is reasonable;
- [ ] security audit is acceptable;
- [ ] dependency matches approved architecture.

---

## 41.10 Data and migrations

Where applicable:

- [ ] migration is safe;
- [ ] existing data compatibility considered;
- [ ] destructive behavior is understood;
- [ ] RLS/policy changes are correct;
- [ ] deployment implications are documented for Merge/Deploy.

---

## 41.11 Automated checks

- [ ] required CI is green;
- [ ] required local checks are accounted for;
- [ ] automated review findings are triaged;
- [ ] no required check is unexplained/red.

---

## 41.12 Finding gate

For approval:

```text
Critical = 0
Error    = 0
Blocking Warning = 0
```

Suggestions and Nitpicks do not block.

---

## Gate output

Return exactly one:

```text
APPROVED FOR MERGE
```

```text
CHANGES REQUIRED
```

or:

```text
BLOCKED
```

---

# 42. Master Codex Prompt — Formal Code Review

Use this as the full formal review prompt.

```text
You are the FORMAL CODE REVIEWER for an AI-enabled LMS.

You did not implement this change.

Your job is to review the actual branch/PR independently and return one verdict:

APPROVED FOR MERGE
CHANGES REQUIRED
BLOCKED

You must NOT:
- merge;
- deploy;
- run production migrations;
- change production data;
- rewrite requirements to match implementation;
- invent defects without verification.

==================================================
REVIEW TARGET
==================================================

Feature:
[FEATURE]

Implementation Step:
[STEP]

Base:
[BASE]

Head / Branch / PR:
[HEAD]

==================================================
SOURCE OF TRUTH
==================================================

Read in this order:

1. docs/product/spec.md
2. approved product decisions / ADRs
3. feature.md
4. technical-decisions.md
5. implementation-plan.md
6. test-plan.md
7. features.md
8. AGENTS.md / REVIEW_GUIDE.md
9. existing architecture
10. implementation summary
11. actual branch diff

The implementation does not define the requirement.

==================================================
PHASE 0 — ELIGIBILITY
==================================================

Read implementation-status.md.

Confirm:
- READY FOR CODE REVIEW;
- base/head are known;
- feature/step are known;
- required artifacts exist.

If review evidence is materially incomplete, return BLOCKED.

==================================================
PHASE 1 — ACTUAL DIFF
==================================================

Inspect:
- merge-base;
- git log;
- name-status;
- full three-dot diff;
- working tree status.

Identify:
- added;
- modified;
- deleted;
- migrations;
- dependencies;
- generated files;
- config;
- unexpected scope.

Do not review only the PR description.

==================================================
PHASE 2 — REVIEW CONTRACT
==================================================

Read the product/feature planning docs.

Extract:
- intended behavior;
- security/tenant rules;
- failure behavior;
- AI behavior;
- explicit non-scope;
- required tests;
- architecture constraints.

==================================================
PHASE 3 — REVERSE-ENGINEER IMPLEMENTATION
==================================================

From the code alone, identify what behavior the branch actually implements.

Compare with approved behavior.

Classify:
MATCH
EXTRA
MISSING
DIFFERENT

Any material EXTRA/MISSING/DIFFERENT item should be investigated.

==================================================
PHASE 4 — TRIAGE
==================================================

Group changed files by behavior/feature area.

Tier:
HIGH
MEDIUM
LOW
SKIP

High includes auth, authorization, tenant isolation, learner/grade data,
sensitive data, destructive mutations, privileged AI actions, critical
migrations, and cross-tenant retrieval.

Spend most review depth on High.

==================================================
PHASE 5 — FIRST FIVE
==================================================

Review:

1. Error Handling
2. Input Boundaries
3. External Calls
4. State Mutations
5. Assumed Dependencies

Before flagging:
- verify missing dependency;
- verify external API/signature;
- inspect actual validation;
- inspect framework/global error behavior;
- trace state consumers.

Do not report speculative defects as facts.

==================================================
PHASE 6 — STRUCTURED REVIEW ORDER
==================================================

Within each feature area review:

1. Types & Interfaces
2. Data Flow
3. Business Logic
4. Edge Cases

Do not simply read the diff top-to-bottom.

==================================================
PHASE 7 — CLAIM → VERIFY → TRACE
==================================================

For every high-risk block:

CLAIM
State what it claims to do.

VERIFY
Check whether the actual implementation enforces that behavior.

TRACE
Follow invalid input, failure, unauthorized input, stale state, duplicate
execution, and relevant cross-tenant paths.

==================================================
PHASE 8 — ZOMBIES
==================================================

Apply relevant:

Zero
One
Many
Boundaries
Interfaces
Exceptions
Simple

Identify missing high-value test coverage.

Use real boundaries from code/config where possible.

==================================================
PHASE 9 — SIDE EFFECTS
==================================================

Sweep changed code and relevant surrounding code for:

save/create/update/delete/send/dispatch/emit/publish/upload/index/embed/etc.

For each important side effect check:
- intentional;
- idempotent;
- guarded;
- authorized;
- observable.

Pay special attention to:
- observers;
- listeners;
- middleware;
- helpers;
- background jobs.

==================================================
PHASE 10 — SECURITY
==================================================

Review:
- untrusted input/injection;
- overly permissive auth;
- hardcoded secrets;
- abuse/rate controls where relevant;
- authentication vs authorization;
- IDOR;
- sensitive logging;
- external data leakage.

Never include a discovered secret value in the report.

==================================================
PHASE 11 — MULTI-TENANCY / RLS
==================================================

If tenant-owned data is touched, verify:
- trusted tenant context;
- RLS/policies;
- server authorization;
- privileged client/service-role use;
- storage scope;
- background jobs;
- realtime;
- vector metadata filters;
- cross-tenant tests.

Treat cross-tenant exposure as Critical.

==================================================
PHASE 12 — AI / RAG / AGENT
==================================================

If AI behavior is touched, verify:
- AI purpose;
- autonomy level;
- context/source scope;
- tenant/course retrieval boundary;
- prompt injection boundary;
- grounding;
- citations;
- structured output validation;
- missing-evidence behavior;
- provider failure;
- cost/usage controls where required;
- human review;
- AI eval results.

Unit tests alone do not prove AI quality.

==================================================
PHASE 13 — TEST QUALITY
==================================================

Review important tests for:
- tautology;
- happy-path-only coverage;
- implementation coupling;
- copy/paste/snapshot weakness.

Ask:
1. What behavior does this verify?
2. If the feature broke, would it fail?
3. Is it testing code or the mock?

==================================================
PHASE 14 — DEPENDENCIES
==================================================

For new/changed dependencies apply WARM:

W — Worth it?
A — Alive?
R — Right-sized?
M — Maintained securely?

Verify material maintenance/API facts from installed versions or primary sources.

==================================================
PHASE 15 — DATA / MIGRATIONS
==================================================

Review:
- data loss;
- backfill;
- null/default;
- constraints;
- indexes;
- FK;
- table lock/runtime;
- rollback;
- RLS;
- existing record compatibility;
- deployment implications.

==================================================
PHASE 16 — EXTERNAL INTEGRATIONS
==================================================

Verify changed providers:
- request;
- response;
- auth;
- timeout;
- retry;
- idempotency;
- webhook validation;
- duplicate handling;
- PII exposure.

==================================================
PHASE 17 — RELIABILITY / PERFORMANCE
==================================================

Review where relevant:
- race conditions;
- duplicate job;
- duplicate submission;
- stale state;
- retries;
- partial failure;
- N+1;
- unbounded lists;
- repeated AI calls;
- obvious indexing needs.

Do not block on theoretical micro-optimization.

==================================================
PHASE 18 — UI / UX
==================================================

If user-facing:
- loading;
- empty;
- success;
- error;
- retry;
- denied;
- disabled;
- async;
- duplicate submission;
- accessibility basics;
- mobile/responsive where relevant.

Remember: hidden UI is not authorization.

==================================================
PHASE 19 — SCOPE / ARCHITECTURE
==================================================

Compare the complete diff to:
- selected step;
- technical scope;
- explicit non-scope;
- product non-goals.

Flag:
- future-step code;
- unrelated refactor;
- unapproved dependency;
- unnecessary abstraction;
- extra endpoint/UI/settings;
- architecture replacement;
- product behavior outside spec.

==================================================
PHASE 20 — CI / AUTOMATION
==================================================

Inspect required:
- lint;
- typecheck;
- static analysis;
- tests;
- build;
- security;
- dependency audit;
- AI evals.

Verify automated findings instead of copying them blindly.

A green check does not prove logic correctness.

==================================================
PHASE 21 — FINDINGS
==================================================

Use severities:

Critical
Error
Warning
Suggestion
Nitpick

Every real finding must include:

- ID;
- severity;
- file:line;
- What;
- Why;
- Evidence;
- Minimal direction.

Do not create findings for pure personal preference.

Deduplicate findings by root cause.

==================================================
PHASE 22 — VERDICT
==================================================

APPROVED FOR MERGE only when:

Critical = 0
Error = 0
Blocking Warning = 0

and required:
- tests;
- CI;
- security;
- tenant checks;
- AI evals;
- migration review;

are acceptable.

Use CHANGES REQUIRED when defects can be fixed inside the approved implementation.

Use BLOCKED when a material planning/evidence problem prevents responsible review.

Do not merge or deploy.
```

---

# 43. Codex Prompt — First Five Only

```text
Run a First Five review against [BASE]...HEAD.

Check only:

1. Error Handling
2. Input Boundaries
3. External Calls
4. State Mutations
5. Assumed Dependencies

Verify each concern before flagging it.

Do not report suspicion alone.

For each finding include:
- category;
- severity;
- file:line;
- one-sentence problem;
- evidence.

Do not perform the full code review.
```

---

# 44. Codex Prompt — Triage Only

```text
Triage the current branch against [BASE].

Group changed files by behavior/feature area.

Assign:
HIGH
MEDIUM
LOW
SKIP

High:
- auth/authz;
- tenant isolation;
- user/learner/grade/payment data;
- sensitive data;
- destructive mutations;
- critical migrations;
- AI tool execution;
- cross-tenant retrieval.

Bump risk for:
- complex branching;
- external services;
- large AI-generated changes;
- async jobs;
- concurrency.

Return a risk map only.
Do not perform the review.
```

---

# 45. Codex Prompt — ZOMBIES Only

```text
Apply the ZOMBIES heuristic to [FEATURE/DIFF].

Use only relevant:

Zero
One
Many
Boundaries
Interfaces
Exceptions
Simple

Suggest only tests that would catch a real bug or document important behavior.

Use actual limits/statuses/config values from the repository when possible.

Do not write tests.
Do not give implementation advice.
```

---

# 46. Codex Prompt — Side-Effect Audit

```text
Audit the changed feature for important side effects.

Search relevant changed/surrounding code for:
- create/save/write;
- update;
- delete/remove;
- send/notify;
- dispatch/emit;
- publish;
- upload;
- index/embed;
- billing/grading mutations.

Pay special attention to:
- observers;
- event listeners;
- middleware;
- helpers;
- jobs.

For every meaningful side effect assess:

Intentional?
Idempotent?
Guarded?
Authorized?
Observable?

Report only verified concerns with file:line evidence.
```

---

# 47. Codex Prompt — Security Review

```text
Security-review the current feature diff.

Prioritize:

1. untrusted input / injection;
2. overly permissive authentication/access;
3. hardcoded secrets;
4. missing abuse/rate controls where material;
5. authentication without object-level authorization;
6. tenant isolation;
7. sensitive logging;
8. privileged service credentials;
9. file upload abuse;
10. prompt injection / AI tool abuse where relevant.

Verify protections in surrounding middleware, policies, RLS, validators, and
trusted service layers before flagging.

Use:
Critical
Error
Warning

Only report security-relevant findings.
```

---

# 48. Codex Prompt — AI / RAG Review

```text
Review only AI/RAG behavior in this branch.

Read the approved AI feature contract.

Verify:

- AI purpose;
- autonomy;
- tenant/course source boundary;
- retrieval metadata filters;
- prompt-injection boundary;
- grounding;
- citations;
- insufficient-evidence behavior;
- structured output validation;
- retry/provider failures;
- human approval;
- cost/usage limits;
- AI eval coverage/results.

Check whether privileged DB/vector access could bypass tenant isolation.

Treat cross-tenant source leakage as Critical.

Do not review unrelated code.
```

---

# 49. Codex Prompt — Test Quality Review

```text
Review the tests introduced or changed by this branch.

For each important test ask:

1. What behavior does it verify?
2. Would it fail if the feature broke?
3. Is it testing production behavior or merely its own mocks?

Flag:

- tautological tests;
- happy-path-only coverage for high-risk behavior;
- implementation-coupled tests;
- copy/paste/snapshot coverage that proves little;
- missing authorization/tenant tests;
- missing failure tests;
- missing AI eval coverage required by plan.

Do not demand 100% coverage.
Focus on risk and required behavior.
```

---

# 50. Codex Prompt — Dependency WARM Review

```text
Review every new or materially changed dependency in this diff.

Apply WARM:

W — Worth it?
A — Alive?
R — Right-sized?
M — Maintained securely?

Inspect:
- actual usage;
- existing alternatives already in repo;
- installed/runtime compatibility;
- current maintenance from primary sources when material;
- repository audit tooling.

Do not reject a dependency merely because it is unfamiliar.

Report only material findings.
```

---

# 51. Codex Prompt — Re-Review Fixes

```text
Re-review fixes for:

[REVIEW FILE]
[FINDING IDS]

Do not assume the fixes are correct.

For each original finding:

1. read original evidence;
2. inspect the fix diff;
3. verify behavior;
4. verify required tests/checks;
5. classify:
   RESOLVED
   PARTIALLY RESOLVED
   NOT RESOLVED
   SUPERSEDED

Then inspect newly changed code for new Critical/Error regressions.

Return updated verdict:
APPROVED FOR MERGE
CHANGES REQUIRED
BLOCKED
```

---

# 52. Automated PR Review Strategy

Automated review can provide baseline coverage on every PR.

Recommended automation categories:

```text
Triage
First Five
Secret scanning
Dependency audit
Lint/typecheck/tests
SAST
AI review comment
```

---

## 52.1 Automation is not approval

Automated review should not automatically merge merely because:

```text
0 AI comments
all tests green
```

Manual/formal logic review remains necessary for:

- architecture;
- business correctness;
- tenant isolation;
- AI behavior;
- nuanced security;
- product scope.

---

## 52.2 Automation permissions

PR review automation should use least privilege.

Prefer read-only repository access plus only the narrow permission required to
write review comments/status.

Do not expose broad production secrets to review jobs.

---

# 53. REVIEW_GUIDE.md Recommended Structure

```markdown
# Review Guide

## General
- Run First Five before deep review.
- Review High-risk behavioral areas before Low-risk files.
- Verify claims before filing findings.

## Authentication & Authorization
- Verify object-level authorization, not login alone.
- Check privileged/service clients do not bypass approved access rules.

## Multi-Tenancy
- Verify tenant scope at server, DB/RLS, storage, jobs, and vector retrieval.

## Source Documents
- Verify learner access cannot expose authoring-only source material.
- Verify source removal/update follows the approved lifecycle.

## AI Retrieval
- Verify organization/course metadata filters.
- Treat retrieved text as untrusted data.
- Verify citation source authorization.

## AI Course Generation
- Verify generated content stays draft until approved.
- Verify malformed model output cannot persist invalid hierarchy.

## Assessments
- Verify attempt and grade rules server-side.
- Verify AI companion cannot expose protected assessment answers.

## External Integrations
- Verify retries, idempotency, timeout, and provider failure behavior.

## Migrations
- Verify compatibility, RLS, data-loss risk, and deployment implications.
```

Keep it concise.

---

# 54. Recommended Codex Skill Packaging

This workflow is packaged as `.agents/skills/review-ai-lms-pr`. The generic structure
below is retained as design background; it does not name an additional active
repository skill.

```text
.agents/
└── skills/
    └── code-review/
        ├── SKILL.md
        ├── references/
        │   ├── first-five.md
        │   ├── review-order.md
        │   ├── zombies.md
        │   ├── side-effects.md
        │   ├── security.md
        │   ├── ai-rag-review.md
        │   ├── test-quality.md
        │   ├── warm.md
        │   ├── severity.md
        │   └── code-review-gate.md
        └── scripts/
            ├── diff-summary.sh
            ├── dependency-diff.sh
            └── review-context.sh
```

---

## Example `SKILL.md` frontmatter

```yaml
---
name: code-review
description: >
  Perform an independent evidence-based review of an implementation branch or PR.
  Triage by risk, run First Five, review Types→Data Flow→Business Logic→Edge Cases,
  apply Claim→Verify→Trace and ZOMBIES, audit side effects, security, tenancy,
  AI/RAG behavior, test quality, dependencies, migrations, scope, and CI, then
  return APPROVED FOR MERGE, CHANGES REQUIRED, or BLOCKED.
---
```

---

# 55. Recommended AGENTS.md Review Section

```markdown
## Code Review

Formal code review is independent from implementation.

Before approval:

1. Compare the actual branch diff to the approved feature step.
2. Run the First Five.
3. Triage review effort by risk.
4. Review Types → Data Flow → Business Logic → Edge Cases.
5. Apply Claim → Verify → Trace to high-risk behavior.
6. Review relevant ZOMBIES boundaries.
7. Audit side effects.
8. Review authorization and tenant isolation.
9. Review AI/RAG grounding and evals when AI behavior changes.
10. Review test quality, not only test results.
11. Review new dependencies.
12. Verify migrations/data changes.
13. Confirm required CI/checks.

Do not report speculative defects as facts.
Verify findings before blocking merge.

Formal verdicts:
- APPROVED FOR MERGE
- CHANGES REQUIRED
- BLOCKED
```

---

# 56. Code Review Anti-Patterns

---

## Reading the diff top-to-bottom

Problem:

Important security/type/data-flow issues receive no priority.

Use structured order and risk triage.

---

## Reporting every suspicion

Problem:

False positives destroy reviewer trust.

Verify before flagging.

---

## Treating style as correctness

Problem:

A reviewer may block safe code because it differs from personal preference.

Use Suggestions/Nitpicks for preference.

---

## Trusting function names/comments

Problem:

AI can generate confident names for incorrect behavior.

Trace actual code.

---

## Trusting green tests

Problem:

AI-generated tests can be tautological or incomplete.

Review test quality.

---

## Ignoring hidden side effects

Problem:

A helper may save/send/delete unexpectedly.

Run side-effect sweep.

---

## Assuming authenticated means authorized

Problem:

IDOR and cross-tenant access remain possible.

Check resource-level permission.

---

## Reviewing only application code

Problem:

Migration/policy/config/dependency changes may carry the highest risk.

Review the whole branch by blast radius.

---

## Reviewing generated files deeply

Problem:

Time is spent on low-value machine output.

Skip unless unexpected change indicates a real problem.

---

## Auto-fixing during review

Problem:

Reviewer becomes implementer, loses separation, and may hide evidence.

Formal review should report first.

Fixes return to Implement.

---

# 57. AI LMS High-Risk Review Checklist

Use when applicable.

---

## Organization / Tenant

- [ ] tenant ID is trusted/derived correctly;
- [ ] cross-tenant read blocked;
- [ ] cross-tenant write blocked;
- [ ] service role is constrained;
- [ ] background jobs remain tenant-scoped;
- [ ] realtime/storage/vector data remain tenant-scoped.

---

## Course Lifecycle

- [ ] draft/published state correct;
- [ ] learner visibility correct;
- [ ] author permissions correct;
- [ ] archive/delete behavior correct;
- [ ] versioning behavior correct.

---

## Source Documents

- [ ] file validation;
- [ ] ownership;
- [ ] private content access;
- [ ] parsing failure;
- [ ] deletion/update lifecycle;
- [ ] no unauthorized raw-source exposure.

---

## AI Generation

- [ ] valid source scope;
- [ ] structured output validation;
- [ ] idempotency;
- [ ] partial failure;
- [ ] retry;
- [ ] human review;
- [ ] no automatic publication unless approved;
- [ ] cost/usage limits.

---

## RAG / Companion

- [ ] source retrieval authorization;
- [ ] tenant/course filters;
- [ ] missing-evidence behavior;
- [ ] citations;
- [ ] prompt injection;
- [ ] no protected assessment leakage;
- [ ] eval results.

---

## Assessment

- [ ] attempt rules;
- [ ] grade rules;
- [ ] answer visibility;
- [ ] instructor override;
- [ ] audit trail;
- [ ] duplicate/concurrent submission;
- [ ] AI restrictions.

---

# 58. Formal Definition of Done

Code Review is complete only when:

- [ ] Review eligibility confirmed.
- [ ] Actual base/head diff inspected.
- [ ] Product/feature intent read.
- [ ] Implemented intent reverse-engineered.
- [ ] Risk triage completed.
- [ ] First Five completed.
- [ ] Types/interfaces reviewed.
- [ ] Data flow traced.
- [ ] Business logic reviewed.
- [ ] Edge cases reviewed.
- [ ] Claim → Verify → Trace applied to high-risk behavior.
- [ ] Relevant ZOMBIES scenarios reviewed.
- [ ] Side effects audited.
- [ ] Security reviewed.
- [ ] Tenant/RLS reviewed where applicable.
- [ ] AI/RAG reviewed where applicable.
- [ ] Test quality reviewed.
- [ ] Dependencies reviewed where applicable.
- [ ] Data/migrations reviewed where applicable.
- [ ] External integrations reviewed where applicable.
- [ ] Reliability/concurrency/performance reviewed where material.
- [ ] Defect reproduction, root cause, and RED-to-GREEN evidence verified where applicable.
- [ ] Performance baseline, equivalent after-measurement, and guardrail verified where applicable.
- [ ] UI behavior reviewed where applicable.
- [ ] Scope/architecture checked.
- [ ] CI/automated review evidence reconciled.
- [ ] Findings are verified and deduplicated.
- [ ] Findings have severity and evidence.
- [ ] Critical count is known.
- [ ] Error count is known.
- [ ] Blocking Warning count is known.
- [ ] Final verdict issued.
- [ ] No merge/deploy action occurred.

The branch may enter **Merge / Deploy** only when the verdict is:

```text
APPROVED FOR MERGE
```

---

# 59. How This Workflow Builds on the Supplied Code Review Material

The supplied Code Review material contributes the core review toolkit:

- **First Five** for Error Handling, Input Boundaries, External Calls, State Mutations, and Assumed Dependencies.
- **Structured review order**: Types & Interfaces → Data Flow → Business Logic → Edge Cases.
- **Claim → Verify → Trace** for interrogating behavior.
- **ZOMBIES** for adversarial test design.
- **Reverse-engineering intent** when the reviewer did not write the code.
- **Risk triage** to focus review effort.
- **Side-effect sweeps** to uncover hidden writes, sends, and state changes.
- **Five security checks** for common AI-generated vulnerabilities.
- **AI-generated test review** to detect false confidence.
- **WARM** for dependency choices.
- **Automated PR review** as a baseline filter, not a substitute for human/formal logic review.
- **Rules + REVIEW_GUIDE.md** so recurring findings improve future generations.
- **Close-the-loop review** where one PR passes through the entire toolkit.

This Codex workflow turns those techniques into one formal, gated review process
for an AI-enabled, multi-tenant LMS.

---

# 60. Final Workflow Chain

```text
PLAN PRODUCT
    ↓
Product Planning Gate

PLAN FEATURE
    ↓
Feature Planning Gate
    ↓
READY FOR IMPLEMENTATION

IMPLEMENT
    ↓
Implementation Gate
    ↓
READY FOR CODE REVIEW

CODE REVIEW
    ↓
Code Review Gate
    ↓
APPROVED FOR MERGE

MERGE / DEPLOY
    ↓
Production Verification Gate
```

The next workflow should consume only branches that have passed:

```text
APPROVED FOR MERGE
```

and own all protected-branch, production migration, deployment, smoke-test,
rollback, and post-deployment monitoring responsibilities.

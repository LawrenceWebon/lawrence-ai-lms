# Plan Feature — AI LMS / Codex Workflow

> **Purpose:** Turn one approved item from `features.md` into a standalone, implementation-ready feature specification that Codex can safely execute step-by-step without inventing product scope, architecture, permissions, AI behavior, or tests.
>
> **Planning boundary:** This workflow plans **one feature at a time**. It may inspect the repository, validate architecture, research official technical documentation, define technical decisions, create implementation steps, and write tests/prompts. It does **not** implement the production feature.
>
> **Required predecessor:** The **Plan Product** workflow should already have produced an approved `spec.md` and `features.md`.
>
> **Next workflow:** A feature moves to **Implement** only after the Feature Planning Gate passes.

---

## Repository-specific application

Follow [the repository workflow authority](README.md). For this repository,
`docs/plan` is the product and architecture source; the `docs/product` and
`docs/features` paths below are optional templates, not required parallel authorities.

Plan Feature must produce a dependency graph of independently reviewable GitHub
issues, not one long serial checklist. Freeze shared API/event/job/DTO fixtures first,
then create up to four issues with exclusive path ownership, one linked branch and
worktree per agent, and one PR per issue. Only real dependencies may block a lane.
Shared migrations, OpenAPI/generated clients, lockfiles, composition files, CI, and
the documentation manifest have one named integration owner.

Use `gh issue create` and `gh issue develop` as specified in `README.md`. The focused
PDF-to-course MVP and its explicit non-goals are authoritative for this planning pass.

---

# 1. What This Workflow Produces

For a small project, the minimum artifact can remain a single feature file:

```text
/docs/features/
└── feature-[feature-slug].md
```

For an AI LMS or any non-trivial feature, the recommended structure is:

```text
/docs/features/[NN]-[feature-slug]/
├── feature.md                  # Canonical feature specification
├── technical-decisions.md      # Feature-specific technical decisions + rationale
├── implementation-plan.md      # Ordered, reviewable implementation steps
├── test-plan.md                # Tests and AI evals defined before implementation
├── readiness-audit.md          # Final feature planning / implementation readiness audit
└── prompts/
    ├── step-01-tests.md
    ├── step-01-implement.md
    ├── step-02-tests.md
    ├── step-02-implement.md
    └── ...
```

If you prefer to keep the workflow simple, all sections may live inside:

```text
feature-[feature-slug].md
```

The workflow below supports both formats.

---

## 1.1 Source-of-truth hierarchy

When planning a feature, use the following precedence:

1. latest explicit project-owner instruction
2. `/docs/workflows/README.md`
3. `/docs/README.md` and `/docs/plan/00-product-vision.md`
4. relevant accepted ADRs and `/docs/plan/` contracts
5. the selected GitHub issue and frozen feature contracts
6. existing production code and migrations as evidence of current implementation
7. mockups, diagrams, tickets, and supporting notes
8. generated implementation plans, tests, and agent prompts

### Important rule

A feature spec may add **detail**, but it must not silently change the product.

If detailed feature planning reveals that the global product spec is wrong, incomplete, or contradictory:

1. record the conflict;
2. propose the narrow plan-level change;
3. update the affected authoritative `docs/plan` sections after approval;
4. synchronize the GitHub issues/contracts; and
5. then continue feature planning.

Do not let `feature.md` become a hidden replacement for `spec.md`.

---

# 2. Codex Agent Operating Rules

These rules apply throughout Plan Feature.

---

## 2.1 Read before designing

Before proposing a feature solution, Codex must inspect the relevant context.

At minimum:

1. Read repository `AGENTS.md`.
2. Read any more-specific nested `AGENTS.md` affecting the target area.
3. Read `/docs/product/spec.md`.
4. Read `/docs/product/features.md`.
5. Read `/docs/product/decisions.md` if present.
6. Read `/docs/product/open-questions.md` if present.
7. Identify the selected feature and its dependency order.
8. Inspect the repository areas likely affected by the feature.
9. Inspect existing tests for nearby behavior.
10. Inspect architecture/ADR documents if present.
11. Inspect relevant database migrations/schema definitions.
12. Inspect existing auth, authorization, tenancy, validation, error handling, and external-service patterns.
13. Inspect already-implemented prerequisite features.

Do not design a parallel architecture when the repository already has an approved pattern.

---

## 2.2 Planning only — do not implement

During Plan Feature, Codex may:

- inspect files;
- search code;
- run read-only repository commands;
- inspect migrations and tests;
- research official documentation;
- create or update planning Markdown files;
- create non-functional diagrams or pseudocode when necessary for understanding;
- identify candidate files/modules likely to be touched.

Codex must not:

- write production feature code;
- create migrations;
- modify schemas;
- install packages;
- change runtime configuration;
- add API routes;
- create production UI components;
- modify deployment infrastructure;
- commit or push implementation work.

The purpose is to make the later implementation predictable.

---

## 2.3 Preserve product intent

The selected item from `features.md` is not an invitation to redesign the product.

Codex must:

- preserve the feature's user-facing intent;
- pull in relevant product constraints from `spec.md`;
- keep product-wide non-goals intact;
- respect existing user roles and permissions;
- respect MVP boundaries;
- preserve approved AI behavior;
- preserve tenant isolation;
- preserve content ownership and privacy requirements.

If the feature cannot be implemented without changing one of these, surface the conflict instead of silently changing it.

---

## 2.4 Separate four kinds of information

Every important statement should be identifiable as one of:

- **Existing fact** — verified from the repository or approved documents.
- **Approved decision** — explicitly chosen for this product/feature.
- **Assumption** — temporary planning assumption that still needs validation.
- **Open question** — unresolved item that could materially change the implementation.

Never present an unverified assumption as an existing repository fact.

---

## 2.5 Existing architecture vs new technical decision

Technical planning must explicitly distinguish:

### Existing constraints

Examples:

- the repo already uses Supabase Auth;
- RLS is already the tenant isolation boundary;
- the app already uses a specific service layer;
- the project already has an event/job pattern;
- tests already use a particular framework;
- file uploads already use a specific storage abstraction.

### New decisions

Examples:

- this feature needs an async generation job;
- this feature introduces a course-generation state machine;
- this feature requires a new vector index namespace strategy;
- this feature requires a new permission;
- this feature requires a new external integration.

New technical decisions require rationale.

---

## 2.6 Verify fast-changing technical information

When the feature plan depends on current behavior of:

- OpenAI / another AI provider;
- Supabase;
- Vercel;
- PayMongo;
- Resend;
- Cloudflare;
- PostHog;
- Sentry;
- Upstash;
- Pinecone;
- Next.js;
- React;
- database extensions;
- SDKs;
- libraries;
- authentication providers;
- external APIs;

verify the material claim against current **official documentation** or another primary source before locking the decision.

Record only feature-relevant findings.

Do not dump vendor documentation into the feature spec.

---

## 2.7 Do not over-plan file-by-file implementation too early

The feature spec should first establish:

1. behavior;
2. boundaries;
3. technical decisions;
4. failure behavior;
5. acceptance criteria;
6. tests;
7. implementation steps.

Only then may it identify probable files or code areas.

Avoid brittle plans such as:

> "Create `FooService.ts` with exactly these 14 methods"

unless the repository already has a pattern requiring that structure.

---

## 2.8 Prefer reversible decisions

When two technical choices both satisfy the requirement:

- prefer the simpler option;
- prefer the option already used by the repository;
- prefer a reversible choice;
- avoid adding a dependency when existing infrastructure is sufficient;
- avoid building a generalized framework for one feature.

---

## 2.9 No speculative extras

Codex may identify useful future enhancements, but they must be placed under:

```markdown
## Future / Explicitly Out of Scope
```

They must not appear in implementation steps.

---

# 3. Feature Planning Principles for an AI LMS

Not every LMS feature needs every section below. Apply only the sections relevant to the selected feature.

However, if a feature touches AI, content generation, uploaded documents, student data, assessments, organization data, or permissions, these checks are mandatory.

---

## 3.1 User and tenant boundary

Determine:

- who can initiate the feature;
- which organization/tenant owns resulting data;
- who can view it;
- who can edit it;
- who can delete it;
- whether platform admins can access it;
- whether a user belonging to multiple organizations needs an organization context;
- whether records may ever cross tenants;
- what authorization must be enforced server-side.

For multi-tenant LMS features, tenant isolation is a requirement, not an implementation afterthought.

---

## 3.2 Content ownership and provenance

If the feature creates, imports, transforms, or retrieves educational content, define:

- source owner;
- source document/course;
- organization owner;
- generated-vs-human-authored status;
- provenance requirements;
- versioning expectations;
- source removal behavior;
- publication/approval state;
- whether copied source text may be exposed to learners.

---

## 3.3 AI source grounding

If AI generates or answers from course material, define:

- allowed knowledge sources;
- retrieval scope;
- whether the current course/module/lesson restricts context;
- whether external model knowledge is allowed;
- required citations/source references;
- behavior when evidence is insufficient;
- behavior when sources conflict;
- hallucination/fallback behavior.

Do not leave this to implementation-time prompt engineering.

---

## 3.4 AI autonomy level

For every AI action, classify the feature:

### Level 0 — Suggest only
AI proposes content. Human performs the action.

### Level 1 — Generate draft
AI creates editable draft content. Human approval is required.

### Level 2 — Execute reversible action
AI may perform a low-risk reversible action with authorization.

### Level 3 — Execute consequential action
AI affects grades, publication, enrollment, billing, permissions, or permanent records.

Level 3 requires explicit product approval and stronger controls.

For an LMS, default high-impact educational records to human-controlled behavior unless the product spec explicitly says otherwise.

---

## 3.5 AI output lifecycle

If AI output is persisted, define:

- draft state;
- review state;
- approved/published state;
- rejected state;
- regeneration behavior;
- edit-after-generation behavior;
- versioning;
- what happens to learner-visible content when the source changes;
- whether old AI output is invalidated.

---

## 3.6 AI evaluation

A normal unit/integration test is not enough to validate probabilistic behavior.

For AI features, define both:

### Software correctness tests

Examples:

- authorization;
- correct tenant scope;
- request validation;
- persistence;
- retries;
- failure handling;
- citations rendered;
- no unsupported destructive action.

### AI quality evaluations

Examples:

- grounding accuracy;
- citation correctness;
- relevance;
- answer refusal when evidence is missing;
- course-generation completeness;
- educational usefulness;
- assessment answer correctness;
- safe handling of adversarial content;
- prompt-injection resistance where applicable.

---

## 3.7 Cost and rate boundaries

If a feature invokes AI or another metered service, define product/technical boundaries for:

- maximum request size;
- supported file size;
- supported page/token limits;
- concurrency;
- regeneration;
- retry limits;
- per-user or per-tenant limits;
- cancellation;
- budget/usage observability.

Do not implement "unlimited" AI behavior accidentally.

---

## 3.8 Long-running operations

Course generation, document parsing, embedding, indexing, and bulk generation may not be safe as a synchronous web request.

The feature plan should determine whether the operation is:

- synchronous;
- asynchronous;
- streaming;
- resumable;
- cancellable.

If asynchronous, define user-visible states and failure behavior before implementation.

---

## 3.9 Assessment integrity

For quiz/exam/assessment features, define:

- whether the activity is practice or graded;
- attempt limits;
- answer visibility;
- grading authority;
- AI assistance restrictions;
- instructor overrides;
- version changes after attempts exist;
- audit requirements.

Do not let an AI companion inadvertently defeat assessment rules.

---

# 4. Workflow Overview

```text
Plan Product approved
        │
        ▼
Select one feature from features.md
        │
        ▼
Phase 0  Initialize feature planning
        │
        ▼
Phase 1  Extract feature into standalone spec
        │
        ▼
Phase 2  Repository reconnaissance
        │
        ▼
Phase 3  Clarify behavior + acceptance criteria
        │
        ▼
Phase 4  Dependency and impact analysis
        │
        ▼
Phase 5  Lock technical decisions
        │
        ▼
Phase 6  AI-specific architecture decisions (when applicable)
        │
        ▼
Phase 7  Security / permissions / tenancy / privacy
        │
        ▼
Phase 8  Failure states + edge cases
        │
        ▼
Phase 9  Scope-creep / non-goals test
        │
        ▼
Phase 10 Break feature into reviewable implementation steps
        │
        ▼
Phase 11 Define step contracts + acceptance checks
        │
        ▼
Phase 12 Write test plan before production code
        │
        ▼
Phase 13 Create Codex test prompts
        │
        ▼
Phase 14 Create Codex implementation prompts
        │
        ▼
Phase 15 Preview how Codex would build it
        │
        ▼
Phase 16 Feature readiness audit
        │
        ▼
Phase 17 Sync product docs if necessary
        │
        ▼
Feature Planning Gate
        │
        ▼
Implement workflow
```

---

# 5. Phase 0 — Initialize Feature Planning

## Goal

Confirm that the selected feature exists, product planning is stable enough, and prerequisites are understood.

---

## Inputs

Required:

```text
/docs/product/spec.md
/docs/product/features.md
```

Recommended:

```text
/docs/product/decisions.md
/docs/product/open-questions.md
/docs/product/product-audit.md
AGENTS.md
```

---

## Actions

Codex should:

1. identify the exact feature in `features.md`;
2. record its feature number/name;
3. identify prerequisite features;
4. confirm whether those prerequisites are planned or implemented;
5. check for global open questions affecting this feature;
6. identify the likely repository subsystem;
7. create the feature planning location;
8. do not begin implementation.

---

## Prompt

```text
We are starting the Plan Feature workflow for:

[FEATURE NAME]

Before designing the feature:

1. Read AGENTS.md and applicable nested instructions.
2. Read docs/product/spec.md completely.
3. Read docs/product/features.md completely.
4. Read docs/product/decisions.md and docs/product/open-questions.md if present.
5. Locate this exact feature in features.md.
6. Identify its dependencies and any unresolved product questions that materially affect it.
7. Report any blocker that would make detailed feature planning unreliable.

Do not implement anything.

If no blocker exists, initialize the feature planning document/folder and continue.
```

---

## Exit criteria

- selected feature is unambiguous;
- global product documents exist;
- blockers are identified;
- prerequisite features are known;
- feature planning location exists.

---

# 6. Phase 1 — Give Every Feature Its Own Spec

## Goal

Extract one feature into a clean standalone specification without prematurely designing the technical solution.

---

## Required feature structure

Start with:

```markdown
# [Feature Name]

## Status
Planning

## Product Reference
- Feature ID:
- Source: `docs/product/features.md`
- Product spec: `docs/product/spec.md`

## Summary
A short plain-English summary of the feature and why it exists.

## Actors
Who uses or is affected by this feature.

## Goals
Outcomes this feature must achieve.

## Non-Goals
Things this feature is explicitly not trying to solve.

## User Flow
The expected user journey.

## Functional Requirements
Observable behavior required from the feature.

## Acceptance Criteria
Testable product-level outcomes.

## Dependencies
Product or technical prerequisites.

## Constraints
Known product, business, security, AI, or platform restrictions.

## Assumptions
Temporary assumptions that still need validation.

## Open Questions
Only unresolved questions that materially affect the feature.
```

At this phase, do **not** add low-level architecture.

---

## Improved extraction prompt

```text
Extract the feature "[FEATURE NAME]" from docs/product/features.md into a
standalone feature specification.

Use docs/product/spec.md as the product source of truth.

Also read docs/product/decisions.md and docs/product/open-questions.md if present.

Pull in only information that directly affects this feature, including:

- actors and permissions
- relevant user flows
- goals and non-goals
- requirements
- product constraints
- AI behavior requirements
- privacy/security requirements
- dependencies
- assumptions
- edge cases already defined by the product spec
- relevant success criteria

Do not invent functionality.

Do not design the implementation yet.

Do not add:
- schemas
- migrations
- API endpoints
- file paths
- class names
- packages
- queue design
- low-level architecture

Structure the document as:

# [Feature Name]
## Status
## Product Reference
## Summary
## Actors
## Goals
## Non-Goals
## User Flow
## Functional Requirements
## Acceptance Criteria
## Dependencies
## Constraints
## Assumptions
## Open Questions
```

---

## Remove unnecessary sections

Use:

```text
Review this feature spec for sections or details that do not directly help
define this feature.

Remove unrelated product material and duplicate information.

Do not remove a product constraint merely because it is cross-cutting if the
constraint materially affects this feature.
```

---

## Exit criteria

A developer unfamiliar with the broader product should understand:

- who uses the feature;
- why it exists;
- what it does;
- what success looks like;
- what it must not do.

---

# 7. Phase 2 — Repository Reconnaissance Before Technical Decisions

## Goal

Learn how the existing application actually works before choosing a feature architecture.

This is one of the most important additions for Codex.

---

## Why this phase exists

A feature document alone cannot tell Codex:

- current folder architecture;
- existing domain models;
- database naming conventions;
- existing RLS patterns;
- auth conventions;
- validation patterns;
- job/queue patterns;
- state management conventions;
- API style;
- test style;
- existing abstractions;
- already-installed dependencies.

Without reconnaissance, the agent may create a technically reasonable but incompatible parallel solution.

---

## Inspect only relevant areas

Codex should not read the entire repository indiscriminately.

Start with:

1. root project structure;
2. `AGENTS.md`;
3. dependency manifests;
4. architecture/ADR docs;
5. feature-adjacent code;
6. data models/migrations;
7. authorization policies;
8. test setup;
9. external integration wrappers;
10. config/env examples relevant to the feature.

---

## Reconnaissance report format

Add a section:

```markdown
## Existing Architecture Relevant to This Feature

### Existing patterns to reuse
- ...

### Existing data/entities involved
- ...

### Existing authorization/tenant boundaries
- ...

### Existing integrations
- ...

### Existing test conventions
- ...

### Existing dependencies that already solve part of this feature
- ...

### Potential conflicts / legacy constraints
- ...

### Unknowns requiring verification
- ...
```

---

## Prompt

```text
Before making technical decisions for this feature, inspect the repository.

Focus only on architecture relevant to [FEATURE NAME].

Determine:

1. Existing modules/components that solve adjacent problems.
2. Existing data models and migrations this feature depends on.
3. Current authentication and authorization patterns.
4. Tenant-isolation mechanisms.
5. Existing validation and error-handling patterns.
6. Existing background-job / asynchronous-processing patterns.
7. Existing external service wrappers.
8. Existing UI/component conventions relevant to this flow.
9. Existing test frameworks, fixtures, factories, and test organization.
10. Existing logging/observability conventions.
11. Existing dependencies we should reuse rather than duplicate.
12. Any existing architecture that conflicts with the current feature idea.

Do not modify production files.

Add a concise "Existing Architecture Relevant to This Feature" section to the
feature plan.

Clearly label:
- verified existing behavior;
- inferred behavior;
- unresolved architecture questions.
```

---

## Exit criteria

Technical planning is grounded in the real repository rather than a generic architecture.

---

# 8. Phase 3 — Clarify Behavior and Acceptance Criteria

## Goal

Remove ambiguity from the user-facing behavior before adding technical detail.

---

## Questions Codex should test

For the primary flow:

- What starts the feature?
- Who is allowed to start it?
- What does the user provide?
- What does the system validate?
- What happens next?
- What state changes?
- What does the user see?
- What constitutes completion?
- Can the action be retried?
- Can it be cancelled?
- Can it be edited or reversed?
- Who is notified?
- What happens on failure?

---

## Acceptance criteria style

Prefer behavior statements.

Example:

```markdown
### Acceptance Criteria

- An instructor with course-edit permission can upload an approved source document.
- A learner cannot initiate course generation.
- The user can see when generation is queued, processing, completed, or failed.
- A failed generation can be retried without creating duplicate course structures.
- Generated content remains unpublished until an authorized reviewer approves it.
```

Avoid implementation statements like:

```text
Use Redis to store status.
```

That belongs under technical decisions.

---

## Prompt

```text
Review this feature as a product behavior contract.

Find every vague requirement where two competent developers could implement
different behavior.

For each material ambiguity:
- explain the ambiguity;
- propose the smallest reasonable choices;
- resolve it from the existing product spec when possible;
- otherwise record it as an open question.

Then strengthen the User Flow, Functional Requirements, and Acceptance Criteria.

Acceptance criteria must be observable and testable.

Do not make low-level technical decisions yet.
```

---

## Exit criteria

Two independent implementers reading the feature should produce substantially the same user behavior.

---

# 9. Phase 4 — Dependency and Impact Analysis

## Goal

Understand what this feature relies on and what it may affect.

---

## Dependency types

### Product dependencies

Examples:

- organization membership;
- course authoring;
- learner enrollment;
- role management.

### Data dependencies

Examples:

- users;
- organizations;
- courses;
- lessons;
- source documents;
- enrollment records.

### Technical dependencies

Examples:

- auth;
- storage;
- AI provider;
- vector search;
- email;
- background jobs.

### Operational dependencies

Examples:

- secret/configuration;
- webhook registration;
- scheduled job;
- provider account.

---

## Impact areas

Identify whether this feature affects:

- existing schema;
- authorization;
- tenant policies;
- existing API contracts;
- existing UI navigation;
- analytics;
- notifications;
- billing/usage;
- data retention;
- compliance;
- AI costs;
- course lifecycle;
- student records.

---

## Prompt

```text
Perform dependency and impact analysis for this feature.

Create:

## Dependency Map
### Product dependencies
### Data dependencies
### Technical dependencies
### External service dependencies

## Impact Analysis
List existing behaviors or subsystems this feature may change or depend on.

For each dependency classify it as:
- already implemented;
- planned prerequisite;
- new requirement;
- uncertain.

Do not create implementation steps yet.
```

---

## Exit criteria

There are no hidden prerequisite systems waiting to surprise implementation.

---

# 10. Phase 5 — Lock In Technical Decisions Before Codex Makes Them

## Goal

Define the architecture decisions that materially affect how this feature will be implemented.

---

## Technical section template

```markdown
## Technical Design Constraints

### Existing architecture to reuse
- ...

### New technical decisions
- ...

### Data model impact
- ...

### Authorization model
- ...

### API / server interaction
- ...

### Async / job behavior
- ...

### UI state model
- ...

### External integrations
- ...

### Observability
- ...

### Performance / limits
- ...

### Technical non-goals
- ...
```

Do not force every heading when it is irrelevant.

---

## Technical decisions should answer "what", not over-specify "how"

Good:

> Course-generation requests will be asynchronous because source parsing and AI generation may exceed normal request lifetimes.

Too early:

> Create `CourseGenerationOrchestrator.ts`, `GenerationQueue.ts`, exactly four event classes, and twelve private methods.

---

## Technical assumption test

Use:

```text
Pretend you are about to implement this feature using only the current feature
document and repository.

List every technical decision you would still have to invent yourself.

For each decision, classify it:

- already constrained by the repository;
- already constrained by spec.md;
- safe implementation detail;
- important decision we should lock before implementation.

Do not implement anything.
```

Then decide the important ones.

---

## Specific mechanism question

Use:

```text
Explain how you currently intend to implement [MECHANISM].

Cover:
- why this fits the existing repository;
- alternatives you considered;
- tradeoffs;
- failure behavior;
- whether it adds a dependency;
- whether the decision is reversible.

Do not write production code.
```

---

## Decision record

For meaningful decisions, add:

```markdown
### TD-[N]: [Decision]

**Status:** Approved / Proposed  
**Decision:** ...  
**Reason:** ...  
**Alternatives considered:** ...  
**Tradeoffs:** ...  
**Revisit when:** ...
```

---

## Exit criteria

Codex should not need to invent a major architectural direction while implementing the feature.

---

# 11. Phase 6 — AI-Specific Technical Decisions

> Apply this phase when the feature invokes an LLM, embedding model, reranker, vector database, AI tool, AI-generated content, or AI-based evaluation.

## Goal

Move AI behavior out of vague prompt text and into explicit feature contracts.

---

## 11.1 AI input contract

Define:

- allowed inputs;
- maximum input size;
- expected source types;
- tenant scope;
- user-provided instructions;
- system-provided context;
- unsupported inputs.

---

## 11.2 Retrieval contract

If RAG is involved, define at a design level:

- corpus being searched;
- tenant/course isolation;
- retrieval scope;
- metadata filters;
- citation/source expectations;
- behavior when no relevant evidence exists.

Detailed chunk sizes and retrieval hyperparameters can remain implementation-level unless they materially affect product behavior.

---

## 11.3 Model/provider policy

Define whether the feature:

- uses the product-wide default model/provider;
- requires a specific capability;
- can fall back to another model;
- needs structured output;
- needs tool/function calls;
- needs streaming;
- needs multimodal input.

Avoid hardcoding a model in feature docs unless the product genuinely requires that model.

---

## 11.4 Structured output

For machine-consumed AI output, define the logical result contract.

Example:

```text
Course generation must return a validated hierarchy:
Course
  -> Modules
      -> Lessons
```

Do not rely on free-form prose if downstream application logic needs structure.

---

## 11.5 AI failure policy

Define behavior for:

- provider timeout;
- rate limit;
- malformed output;
- partial generation;
- unsafe output;
- missing grounding;
- unavailable retrieval;
- retry exhaustion;
- provider outage.

---

## 11.6 AI prompt-injection boundary

For features processing uploaded or retrieved text, decide:

- whether source content is treated as data rather than authority;
- which instructions have higher priority;
- whether retrieved content may request tool actions;
- what tools the AI may use;
- what sensitive data it may access.

---

## 11.7 AI observability

Define what should be observable without storing unnecessary sensitive content:

- request/result status;
- latency;
- provider/model;
- token/usage or cost estimate where available;
- failure category;
- generation version;
- user feedback;
- eval outcome.

---

## AI planning prompt

```text
This feature includes AI behavior.

Add an AI Technical Contract covering:

1. AI purpose.
2. AI autonomy level.
3. Allowed context/sources.
4. Tenant/course retrieval boundary.
5. Input limits.
6. Output contract.
7. Citation/grounding requirements.
8. Behavior when evidence is missing.
9. Provider/model capability requirements.
10. Structured-output requirements.
11. Retry/failure behavior.
12. Prompt-injection/tool boundaries.
13. Persisted AI metadata.
14. Observability/cost requirements.
15. Human review requirements.
16. AI quality evaluation requirements.

Do not implement prompts or production AI code yet.
```

---

## Exit criteria

The implementation agent should not decide important AI trust behavior on its own.

---

# 12. Phase 7 — Security, Permissions, Tenancy, and Privacy Review

## Goal

Define security boundaries before implementation.

---

## Required review areas

### Authentication

- must the actor be signed in?
- are service-to-service calls involved?

### Authorization

- what explicit permission is required?
- is role alone sufficient?
- is resource ownership checked?

### Tenant isolation

- how is organization context determined?
- can object IDs be used to access another tenant?
- are background tasks tenant-scoped?

### Input validation

- file type;
- file size;
- text length;
- identifiers;
- URLs;
- pagination;
- free-form prompts.

### Data privacy

- personal information;
- learner records;
- instructor data;
- uploaded copyrighted/private content;
- AI provider transmission.

### State mutation

- what records can be created/changed/deleted?
- which actions need auditability?
- which destructive actions are reversible?

---

## Security prompt

```text
Threat-review this feature before implementation.

Focus on realistic feature-specific risks:

- authentication
- authorization
- tenant isolation
- insecure direct object reference
- input validation
- file upload abuse
- prompt injection if AI is involved
- unintended source-document disclosure
- destructive state mutation
- privilege escalation
- webhook/API trust boundaries
- secret exposure
- sensitive logging
- learner-record privacy

For each concern:
1. identify the asset;
2. identify the actor/threat;
3. define the required guardrail;
4. state how we will test it.

Do not produce generic security boilerplate.
Do not implement fixes.
```

---

## Exit criteria

Feature security behavior is explicit and testable.

---

# 13. Phase 8 — Failure States and Edge Cases

## Goal

Plan failure behavior before happy-path implementation hides it.

---

## Failure categories

### User/input failures

- missing fields;
- wrong format;
- oversized upload;
- duplicate request;
- unauthorized action;
- invalid state transition.

### External failures

- AI provider unavailable;
- storage unavailable;
- email provider unavailable;
- vector DB unavailable;
- payment provider unavailable.

### Async failures

- job never starts;
- job retries;
- partial completion;
- duplicate delivery;
- worker restart;
- stale status.

### Data lifecycle failures

- source deleted;
- course archived;
- learner removed;
- organization disabled;
- permissions change during processing.

### Concurrency failures

- same content edited simultaneously;
- repeated button click;
- duplicate webhook;
- two generation jobs for the same resource.

---

## Prompt

```text
Poke holes in this feature.

Walk through the feature from start to finish and identify failure states,
edge cases, retries, duplicate actions, stale state, concurrency issues, and
dependency outages.

For each important case specify:

- trigger;
- expected system behavior;
- user-visible behavior;
- whether retry is safe;
- whether the operation must be idempotent;
- whether cleanup/rollback is required;
- test coverage required.

Add only realistic cases that matter for this feature.
```

---

## Exit criteria

Implementation steps do not cover only the happy path.

---

# 14. Phase 9 — Choose What Is Out of Scope

## Goal

Prevent Codex from adding common "helpful" functionality that was never requested.

---

## Scope-creep test

Prompt:

```text
If you were implementing this feature, what reasonable or helpful additions
might you be tempted to include even though they are not required?

Examples may include:
- additional settings
- generic abstractions
- bulk operations
- advanced filters
- exports
- extra roles
- notifications
- AI regeneration controls
- new dependencies
- extra admin screens
- generalized workflow engines

List them only.
Do not add them to the feature.
```

---

## Convert decisions into constraints

Then:

```text
Review the possible scope-creep items.

Add all rejected items to:

## Explicitly Out of Scope

Be specific enough that the implementation agent knows not to build them.

Also add any packages, services, architecture patterns, or abstractions that
are explicitly prohibited for this feature.

Do not remove functionality already required by spec.md.
```

---

## Example

```markdown
## Explicitly Out of Scope

- Bulk course generation.
- Automatic publication of AI-generated courses.
- Cross-organization sharing.
- A generic workflow-engine dependency.
- Learner access to raw uploaded source documents.
- Automatic switching to arbitrary AI providers.
```

---

## Exit criteria

The feature has a clear stopping point.

---

# 15. Phase 10 — Break the Feature Into Reviewable Implementation Steps

## Goal

Turn the approved feature design into logical, deployable, independently reviewable steps.

---

## Good implementation-step characteristics

A step should be:

- coherent;
- independently understandable;
- testable;
- reviewable;
- reasonably reversible;
- dependent only on earlier steps;
- large enough to deliver meaningful structure/behavior;
- small enough that a reviewer can understand the diff.

---

## Avoid two extremes

### Too large

> Implement course generation.

### Too small

> Create interface.  
> Add one enum.  
> Add one helper.  
> Add one test.

Prefer meaningful slices.

---

## Example AI LMS decomposition

For "Generate Course From Uploaded Book":

```text
Step 1 — Establish generation domain/state and authorization boundaries
Step 2 — Accept and validate source material for generation
Step 3 — Create asynchronous generation lifecycle
Step 4 — Parse/index the source through the approved ingestion pipeline
Step 5 — Generate validated draft course structure from grounded source
Step 6 — Present generation status and draft review UI
Step 7 — Allow authorized review/edit/approval
Step 8 — Add failure recovery, observability, and usage controls
```

Exact decomposition depends on the existing codebase.

## Parallel issue graph

After identifying the ordered implementation steps, group independent steps into no
more than four concurrently active GitHub issues. This graph, rather than the list
order alone, controls execution.

```markdown
| Issue | Agent | Objective | Owned paths | Frozen contracts/fixtures | Depends on | Shared owner | Acceptance commands | PR order |
|---|---|---|---|---|---|---|---|---|
| #123 | A | PDF upload lifecycle | ... | upload DTO v1 | contract freeze | schema owner | ... | 1 |
| #124 | B | PDF extraction worker | ... | ingestion job v1 + golden PDF | contract freeze | job schema owner | ... | 2 |
| #125 | C | Course generation | ... | normalized book/course draft v1 | contract freeze | AI schema owner | ... | 3 |
| #126 | D | Review/publication API | ... | course draft v1 | contract freeze | course migration owner | ... | 4 |
```

An issue is parallel-ready only when its paths do not overlap another active issue,
its contract and fixtures are usable without sibling code, and its focused tests can
run independently. Otherwise declare the dependency and integration order explicitly.
Create and link branches with the `gh` CLI workflow in [README.md](README.md).

---

## Prompt

```text
Add an "Implementation Steps" section.

Break this feature into ordered implementation steps.

Rules:

- Follow actual repository dependencies.
- Reuse existing architecture.
- Each step should be large enough to add meaningful behavior.
- Each step should be small enough for a comfortable code review.
- Each step must be testable.
- Earlier steps may establish foundations needed by later steps.
- Include security/authorization work in the step where the behavior is introduced.
- Include failure behavior in the appropriate step, not as an afterthought.
- Do not create speculative abstractions.
- Do not implement anything.

For each step include:
- Objective
- User/system capability added
- Dependencies
- Technical scope
- Explicit non-scope
- Acceptance checks
```

---

## Exit criteria

The feature can be implemented sequentially without requiring Codex to redesign it mid-stream.

---

# 16. Phase 11 — Define a Contract for Every Implementation Step

## Goal

Make each implementation step safe to hand to a fresh Codex context.

---

## Step template

```markdown
## Step [N] — [Name]

### Objective
What this step accomplishes.

### Depends On
Earlier steps / existing systems.

### Behavior Added
Observable behavior introduced.

### Technical Scope
The architectural areas this step may change.

### Likely Repository Areas
Probable modules/directories, based on reconnaissance.

### Data Impact
New/changed persisted state, if any.

### Authorization / Tenant Rules
Required security behavior.

### Error / Failure Behavior
What happens when this step fails.

### Explicit Non-Scope
What this step must not implement yet.

### Tests Required Before/With Implementation
High-level tests.

### Acceptance Checks
What must be true before moving to the next step.
```

---

## Important

"Likely Repository Areas" is guidance, not permission to ignore better-localized architecture discovered during implementation.

If implementation reveals a material mismatch, Codex must stop and update the plan instead of improvising a new architecture.

---

# 17. Phase 12 — Write the Test Plan Before Production Code

## Goal

Define what correct behavior means before Codex writes the implementation that tests will validate.

---

## Why this matters

When an AI agent writes implementation and tests at the same time without an independent behavior contract, it can create tests that merely confirm its own incorrect interpretation.

The test plan must derive from:

1. `spec.md`;
2. the feature spec;
3. acceptance criteria;
4. security boundaries;
5. failure requirements.

Not from implementation code that does not exist yet.

---

## Test categories

Use only relevant categories.

### Unit tests

For pure domain rules or transformations.

### Integration tests

For:

- database behavior;
- authorization;
- storage;
- job processing;
- API boundaries;
- service integration wrappers.

### End-to-end tests

For critical user journeys.

### Authorization / tenancy tests

Mandatory for tenant-sensitive behavior.

### Failure-path tests

For realistic dependency and state failures.

### Idempotency/concurrency tests

When duplicate or parallel actions are possible.

### AI evaluation tests

For probabilistic AI behavior.

---

## Test-plan format

```markdown
# Test Plan — [Feature Name]

## Test Strategy

## Step 1
### Required tests
- ...

## Step 2
### Required tests
- ...

## Security / Authorization Tests
- ...

## Failure / Recovery Tests
- ...

## End-to-End Scenarios
- ...

## AI Evaluations
- ...

## Manual Verification
- ...

## Tests Explicitly Not Required
- ...
```

---

## Prompt

```text
Create the test plan for this feature BEFORE production implementation.

For every implementation step, add a concise bulleted list of tests.

Tests must come from:
- feature requirements;
- acceptance criteria;
- permissions;
- tenant isolation;
- failure behavior;
- technical contracts.

Prefer behavior-focused tests.

Include:
- happy path;
- authorization failures;
- tenant isolation where applicable;
- invalid input;
- important external failure;
- state transition rules;
- retries/idempotency when applicable.

If the feature includes AI, separately define deterministic software tests and
probabilistic AI evaluations.

Do not write implementation code.
```

---

# 18. Phase 12A — AI Evaluation Plan

> Required only for AI features.

## Goal

Define what "good AI behavior" means before prompts/models are tuned around implementation.

---

## AI eval dataset categories

Create representative examples for:

- normal expected inputs;
- sparse/insufficient source material;
- conflicting source material;
- malformed source content;
- long source content;
- irrelevant questions;
- adversarial/prompt-injection content;
- cross-course or cross-tenant leakage attempts;
- ambiguous learner questions;
- unsupported answers;
- subject-specific difficult examples.

---

## Evaluation dimensions

Choose relevant metrics:

- groundedness;
- citation correctness;
- completeness;
- relevance;
- educational quality;
- answer correctness;
- refusal correctness;
- structure validity;
- hallucination rate;
- safety;
- tenant/source isolation;
- latency/cost thresholds.

---

## AI eval prompt

```text
Create an AI evaluation plan for this feature.

Do not test only whether the API call succeeds.

Define:
1. representative evaluation cases;
2. expected behavior;
3. failure examples;
4. scoring dimensions;
5. pass/fail thresholds where a deterministic threshold is meaningful;
6. human-review criteria where automated grading is insufficient;
7. regression cases that should be retained after bugs are found.

Keep software tests separate from AI-quality evaluations.
```

---

# 19. Phase 13 — Generate Codex Prompts to Write Tests First

## Goal

Create step-specific prompts that tell Codex to implement the approved tests without production feature code.

---

## Test prompt template

```markdown
# Codex Prompt — [Feature] — Step [N] Tests

You are working on Implementation Step [N] of [FEATURE].

## Read first

Read:
- AGENTS.md
- docs/product/spec.md
- docs/product/features.md
- [feature plan path]
- [test plan path]

Then inspect the repository areas referenced by the step.

## Task

Implement ONLY the tests required for Step [N].

Use the repository's existing test framework and conventions.

The tests must express the approved behavior independently of the production
implementation.

## Required coverage

[TEST BULLETS]

## Constraints

- Do not implement production feature code.
- Do not weaken an assertion just to make a test pass.
- Do not invent behavior not present in the feature plan.
- Do not modify unrelated tests.
- Preserve tenant/auth boundaries.
- Reuse existing fixtures/factories/patterns where appropriate.

## Verification

Run the narrowest relevant test command.

Expected outcome before implementation:
- new tests may fail because the feature does not exist;
- existing unrelated tests must not regress.

Report:
1. tests added;
2. expected failures;
3. any plan/repository contradiction discovered.
```

---

## Prompt generator

```text
Generate a Codex test-writing prompt for Implementation Step [N].

The prompt must require Codex to read:
- AGENTS.md;
- spec.md;
- features.md;
- this feature spec;
- the test plan.

It must tell Codex to write only the approved tests for that step and not the
production implementation.

Use the repository's existing testing conventions.
```

---

# 20. Phase 14 — Generate Codex Implementation Prompts

## Goal

Produce a constrained implementation prompt for each approved step.

---

## Implementation prompt template

```markdown
# Codex Prompt — [Feature] — Step [N] Implementation

Implement only Implementation Step [N] for [FEATURE].

## Read first

Read:
- AGENTS.md and applicable nested instructions
- docs/product/spec.md
- docs/product/features.md
- [feature plan path]
- [technical decisions path]
- [implementation plan path]
- [test plan path]

Inspect the existing repository implementation relevant to this step before
making changes.

## Objective

[STEP OBJECTIVE]

## Required behavior

[BEHAVIOR]

## Technical constraints

[APPROVED TECHNICAL DECISIONS]

## Security / tenant constraints

[SECURITY RULES]

## Failure behavior

[FAILURE RULES]

## Tests that define this step

[TESTS]

## Explicit non-scope

[NON-SCOPE]

## Implementation rules

- Implement only this step.
- Reuse existing repository patterns.
- Do not redesign approved architecture.
- Do not add dependencies unless explicitly approved in the feature plan.
- Do not implement future steps early.
- Do not weaken or delete tests to make the implementation pass.
- Do not change product behavior beyond the approved feature spec.
- If repository reality materially contradicts the plan, stop and report the contradiction instead of improvising.

## Verification

Run:
1. tests specific to the step;
2. relevant adjacent tests;
3. lint/typecheck/build commands required by AGENTS.md.

Report:
- files changed;
- behavior implemented;
- tests run and results;
- deviations from plan;
- unresolved concerns.
```

---

## Prompt generator

```text
Generate a Codex implementation prompt for Implementation Step [N].

Use the approved feature spec, technical decisions, implementation plan, and
test plan.

The prompt must:
- constrain Codex to this step only;
- require repository reconnaissance before edits;
- state required behavior;
- include security/tenant rules;
- include error behavior;
- include explicit non-scope;
- require existing tests plus step tests to pass;
- prohibit inventing new product behavior;
- instruct Codex to stop if repository reality materially contradicts the plan.
```

---

# 21. Phase 15 — Preview How Codex Will Build Each Step

## Goal

Test the plan before spending implementation effort.

This is a dry run.

---

## Prompt

```text
Do not implement this step.

Pretend you are Codex about to execute Implementation Step [N].

Based on:
- AGENTS.md;
- repository structure;
- spec.md;
- features.md;
- feature.md;
- technical decisions;
- test plan;

describe:

1. repository areas you expect to inspect;
2. existing patterns you expect to reuse;
3. changes you expect to make;
4. state/data changes;
5. tests you expect to satisfy;
6. error paths you expect to implement;
7. technical decisions that are still underspecified;
8. anything you would otherwise have to invent.

Flag anything that could cause scope drift or architectural inconsistency.

Do not write code.
```

---

## Review the preview

If the dry run says:

> "I would choose a queue provider"

but the queue provider should be predetermined, the plan is not ready.

If it says:

> "I would create a generic workflow engine"

when one is not required, strengthen the non-goals.

If it cannot identify tenant boundaries, fix the feature spec.

---

## Exit criteria

The predicted implementation matches your intended architecture and scope.

---

# 22. Phase 16 — Feature Preflight / Readiness Audit

## Goal

Perform a final hostile review of the plan before code.

---

## Audit dimensions

### 22.1 Product consistency

- Does it match `spec.md`?
- Does it preserve the feature entry in `features.md`?
- Does it preserve product non-goals?

### 22.2 Repository compatibility

- Does it reuse current architecture?
- Does it duplicate an existing abstraction?
- Does it assume nonexistent modules?
- Does it use current project conventions?

### 22.3 Input boundaries

- Are sizes/formats/types bounded?
- Are user inputs validated?
- Are AI inputs bounded?
- Are uploads bounded?

### 22.4 External calls

- Are external dependencies identified?
- Is failure behavior defined?
- Are retries safe?
- Are timeouts/rate limits considered?

### 22.5 State mutations

- Are state transitions explicit?
- Are destructive actions controlled?
- Is rollback/cleanup defined where needed?

### 22.6 Assumed dependencies

- Does the plan rely on classes/routes/tables/services that may not exist?
- Were they verified?

### 22.7 Authorization and tenancy

- Is every protected action scoped correctly?
- Are cross-tenant attacks included in tests?

### 22.8 AI behavior

If applicable:
- is grounding defined?
- is insufficient-evidence behavior defined?
- is output validation defined?
- is human review defined?
- are evals defined?
- are prompt injection boundaries defined?

### 22.9 Testability

- Does every requirement map to a test or deliberate manual/eval check?
- Are failure paths tested?
- Are tests independent enough to catch incorrect implementation?

### 22.10 Step quality

- Is each step reviewable?
- Are dependencies ordered?
- Are steps too large?
- Are future steps leaking into earlier steps?

---

## Audit prompt

```text
Perform a final Feature Planning Readiness Audit.

Be skeptical.

Review:
- spec.md
- features.md
- this feature spec
- technical decisions
- implementation steps
- test plan
- repository evidence

Check:

1. product contradictions;
2. vague behavior;
3. unapproved scope;
4. hidden dependencies;
5. architecture invented without repository evidence;
6. missing validation/input boundaries;
7. missing external-call failure behavior;
8. unsafe state mutations;
9. assumed/nonexistent dependencies;
10. auth/tenant gaps;
11. privacy/security gaps;
12. AI grounding/evaluation gaps;
13. missing tests;
14. overly large implementation steps;
15. steps that implement later scope early.

For every finding classify:
- BLOCKER
- IMPORTANT
- NICE TO HAVE

Do not invent new product features as fixes.

Write the result to readiness-audit.md.
```

---

# 23. Phase 17 — Synchronize Product Documents When Necessary

## Goal

Prevent feature planning from diverging from product planning.

---

## When sync is required

Update product documents when feature planning discovers an approved change to:

- user behavior;
- role/permission model;
- feature scope;
- product-wide technical constraint;
- AI behavior;
- tenant model;
- product non-goal;
- prerequisite feature;
- feature ordering.

---

## Sync rule

Never simply edit `feature.md` and leave contradictions upstream.

Use:

```text
Compare the finalized feature plan against docs/product/spec.md and
docs/product/features.md.

Identify any approved feature-planning decisions that changed product-level
behavior.

Do not automatically widen product scope.

For each discrepancy:
- show the product document text;
- show the feature-plan decision;
- state whether the feature plan should be changed or product docs should be synced.

After the direction is approved, update only the affected sections and preserve
unrelated content.
```

---

# 24. Feature Planning Gate

A feature may move to **Implement** only when this gate passes.

---

## 24.1 Product gate

- [ ] Feature exists in approved `features.md`.
- [ ] Feature is consistent with `spec.md`.
- [ ] Goals and non-goals are explicit.
- [ ] Primary user flow is explicit.
- [ ] Acceptance criteria are testable.
- [ ] No unresolved product question blocks implementation.

---

## 24.2 Architecture gate

- [ ] Relevant repository architecture was inspected.
- [ ] Existing patterns to reuse are documented.
- [ ] Major new technical decisions are approved.
- [ ] Dependencies are verified.
- [ ] No unnecessary new package/service is required.
- [ ] Technical decisions are compatible with prerequisite features.

---

## 24.3 Security gate

- [ ] Authentication requirement is explicit.
- [ ] Authorization rules are explicit.
- [ ] Tenant isolation is explicit where relevant.
- [ ] Input boundaries are defined.
- [ ] Sensitive data handling is defined.
- [ ] Destructive state changes are understood.

---

## 24.4 Reliability gate

- [ ] Important failure states are defined.
- [ ] External service failures are handled.
- [ ] Retry behavior is defined where necessary.
- [ ] Duplicate/concurrent action behavior is defined where necessary.
- [ ] Async state is defined where necessary.

---

## 24.5 AI gate

For AI features:

- [ ] AI purpose and autonomy level are explicit.
- [ ] Source/grounding boundary is explicit.
- [ ] Output contract is explicit.
- [ ] Missing-evidence behavior is explicit.
- [ ] Human review requirements are explicit.
- [ ] AI failure policy is explicit.
- [ ] Prompt-injection/tool boundary is explicit.
- [ ] AI evaluation plan exists.
- [ ] Usage/cost limits are considered.

---

## 24.6 Test gate

- [ ] Test plan exists before production implementation.
- [ ] Each implementation step has tests.
- [ ] Security/tenancy tests exist where relevant.
- [ ] Failure tests exist.
- [ ] End-to-end critical path is defined.
- [ ] AI evals exist separately from normal tests where relevant.

---

## 24.7 Implementation-step gate

- [ ] Steps are in dependency order.
- [ ] Each step is reviewable.
- [ ] Each step has explicit non-scope.
- [ ] Each step has acceptance checks.
- [ ] Test prompts can be generated independently.
- [ ] Implementation prompts can be generated independently.
- [ ] A dry run does not reveal major decisions Codex still has to invent.

---

## Gate prompt

```text
Evaluate this feature against the Feature Planning Gate.

Return one status:

READY FOR IMPLEMENTATION
or
NOT READY

If NOT READY, list only blocking items and the minimum planning change required.

Do not implement the feature.
```

---

# 25. Handoff to Implement

## Handoff package

The Implement workflow receives:

```text
docs/product/spec.md
docs/product/features.md
docs/features/[feature]/feature.md
docs/features/[feature]/technical-decisions.md
docs/features/[feature]/implementation-plan.md
docs/features/[feature]/test-plan.md
docs/features/[feature]/readiness-audit.md
docs/features/[feature]/prompts/
AGENTS.md
```

If using the single-file format:

```text
docs/product/spec.md
docs/product/features.md
docs/features/feature-[feature].md
AGENTS.md
```

---

## Handoff rule

Implementation proceeds **one approved step at a time**.

Recommended loop:

```text
Step N test prompt
      ↓
review tests
      ↓
Step N implementation prompt
      ↓
run verification
      ↓
code review
      ↓
approve step
      ↓
Step N+1
```

Do not hand Codex the entire feature with:

> "Implement everything."

unless the feature is genuinely very small.

---

# 26. Master Codex Prompt — Run the Entire Plan Feature Workflow

Use this when you want Codex to plan one feature from start to finish.

```text
You are responsible for PLAN FEATURE only.

Selected feature:

[FEATURE NAME]

Project type:
AI-enabled LMS

Your job is to turn the selected feature from features.md into an
implementation-ready feature plan.

DO NOT implement production code.

==================================================
SOURCE OF TRUTH
==================================================

Read in this order:

1. AGENTS.md and applicable nested AGENTS.md files
2. docs/product/spec.md
3. docs/product/decisions.md if present
4. docs/product/features.md
5. docs/product/open-questions.md if present
6. existing architecture / ADR documents
7. repository code relevant to this feature
8. existing tests relevant to this feature

If documents conflict:

spec.md
> approved product decisions
> approved feature spec
> features.md
> existing implementation evidence
> generated plans/prompts

A feature plan may add detail but may not silently change product scope.

==================================================
OPERATING RULES
==================================================

- Planning only.
- Do not implement production code.
- Do not create migrations.
- Do not install dependencies.
- Do not alter runtime configuration.
- Do not create APIs/UI/business logic.
- Do not silently change product behavior.
- Reuse existing repository patterns.
- Distinguish existing architecture from new decisions.
- Verify fast-changing vendor/library assumptions using current official docs.
- Prefer simple and reversible decisions.
- Do not create speculative abstractions.
- Do not invent future features.
- If an important product contradiction is discovered, record it rather than
  silently resolving it.
- Ask only questions that materially change scope, security, permissions,
  AI behavior, data model, or implementation architecture.
- For minor uncertainty, choose a conservative assumption and record it.

==================================================
PHASE 0 — INITIALIZE
==================================================

Locate [FEATURE NAME] in features.md.

Identify:
- feature number;
- dependencies;
- prerequisite feature status;
- relevant product constraints;
- product-level open questions.

If a blocking product question exists, record it.

==================================================
PHASE 1 — STANDALONE FEATURE SPEC
==================================================

Create the feature plan using:

# [Feature Name]
## Status
## Product Reference
## Summary
## Actors
## Goals
## Non-Goals
## User Flow
## Functional Requirements
## Acceptance Criteria
## Dependencies
## Constraints
## Assumptions
## Open Questions

Pull relevant requirements from spec.md and features.md.

Do not add technical design yet.

==================================================
PHASE 2 — REPOSITORY RECONNAISSANCE
==================================================

Inspect only repository areas relevant to this feature.

Determine:

- existing architecture to reuse;
- adjacent implemented features;
- data entities/migrations;
- auth/authorization conventions;
- tenant isolation;
- input-validation patterns;
- background-job/async patterns;
- external-integration wrappers;
- UI conventions;
- test conventions;
- observability conventions;
- existing dependencies;
- legacy constraints.

Add:

## Existing Architecture Relevant to This Feature

Clearly distinguish verified evidence from inference.

==================================================
PHASE 3 — BEHAVIOR CLARITY
==================================================

Review the feature for ambiguity.

Strengthen:
- user flow;
- functional requirements;
- acceptance criteria.

Acceptance criteria must describe observable behavior.

Do not introduce implementation details merely to remove ambiguity.

==================================================
PHASE 4 — DEPENDENCIES / IMPACT
==================================================

Create:

## Dependency Map
### Product dependencies
### Data dependencies
### Technical dependencies
### External service dependencies

## Impact Analysis

Classify each dependency:
- implemented;
- planned prerequisite;
- new requirement;
- uncertain.

==================================================
PHASE 5 — TECHNICAL DECISIONS
==================================================

Determine which technical choices are already constrained by the repo and which
must be newly decided.

Add:

## Technical Design Constraints

Include only relevant subsections:

- Existing architecture to reuse
- New technical decisions
- Data model impact
- Authorization model
- API/server interaction
- Async/job behavior
- UI state model
- External integrations
- Observability
- Performance/limits
- Technical non-goals

For meaningful new decisions document:

TD-[N]
Status
Decision
Reason
Alternatives considered
Tradeoffs
Revisit when

Do not over-specify class names or file structure unless existing architecture
requires it.

==================================================
PHASE 6 — AI TECHNICAL CONTRACT
==================================================

If this feature uses AI, RAG, embeddings, generated content, or model calls,
define:

- AI purpose;
- autonomy level;
- allowed context/sources;
- retrieval boundary;
- tenant/course isolation;
- input limits;
- output contract;
- structured-output requirement;
- citations/grounding;
- insufficient-evidence behavior;
- human review;
- provider/model capability requirement;
- failure/retry behavior;
- prompt-injection boundary;
- persisted AI metadata;
- observability;
- cost/usage limits;
- AI quality evaluation requirements.

Do not implement prompts/models.

==================================================
PHASE 7 — SECURITY / PRIVACY
==================================================

Threat-review:

- authentication;
- authorization;
- tenant isolation;
- object ownership;
- input boundaries;
- file uploads;
- prompt injection;
- data disclosure;
- state mutation;
- privilege escalation;
- sensitive logging;
- learner/content privacy.

Convert realistic risks into explicit requirements and tests.

==================================================
PHASE 8 — FAILURES / EDGE CASES
==================================================

For each material failure define:

- trigger;
- system behavior;
- user-visible behavior;
- retry;
- idempotency;
- rollback/cleanup;
- test required.

Include relevant:
- invalid inputs;
- external outages;
- partial processing;
- concurrency;
- duplicate actions;
- stale state;
- lifecycle changes.

==================================================
PHASE 9 — SCOPE CONTROL
==================================================

List useful additions an AI coding agent might be tempted to add.

Reject anything not approved.

Create:

## Explicitly Out of Scope

Include prohibited:
- features;
- settings;
- abstractions;
- dependencies;
- services;
- admin surfaces;
- automation.

==================================================
PHASE 10 — IMPLEMENTATION STEPS
==================================================

Break the feature into ordered, reviewable steps.

Each step must include:

## Step [N] — [Name]
### Objective
### Depends On
### Behavior Added
### Technical Scope
### Likely Repository Areas
### Data Impact
### Authorization / Tenant Rules
### Error / Failure Behavior
### Explicit Non-Scope
### Tests Required Before/With Implementation
### Acceptance Checks

Steps must:
- follow dependencies;
- be meaningful;
- be reviewable;
- be testable;
- avoid future-step leakage.

==================================================
PHASE 11/12 — TEST PLAN BEFORE CODE
==================================================

Create a high-level test plan BEFORE production implementation.

For each step define appropriate:
- unit tests;
- integration tests;
- authorization tests;
- tenant isolation tests;
- failure tests;
- idempotency/concurrency tests;
- end-to-end tests.

If AI is involved, separately define AI evaluations for:
- groundedness;
- correctness;
- citation quality;
- missing-evidence handling;
- safety;
- source/tenant isolation;
- structured output;
- educational quality.

==================================================
PHASE 13 — TEST PROMPTS
==================================================

For every step generate a test-writing Codex prompt.

The test prompt must:
- read all source documents;
- inspect the current repo;
- implement only step tests;
- not implement production code;
- use existing test conventions;
- not weaken assertions;
- report contradictions.

==================================================
PHASE 14 — IMPLEMENTATION PROMPTS
==================================================

For every step generate an implementation Codex prompt.

The prompt must include:
- objective;
- required behavior;
- approved technical constraints;
- security/tenant rules;
- failure behavior;
- tests;
- explicit non-scope;
- required verification.

Tell the implementation agent:
- implement only this step;
- reuse existing patterns;
- do not add unapproved dependencies;
- do not implement later steps;
- do not change product behavior;
- stop if repository reality materially contradicts the plan.

==================================================
PHASE 15 — DRY RUN
==================================================

Simulate how Codex would implement each step WITHOUT editing code.

Identify:
- areas it would inspect;
- patterns reused;
- probable changes;
- tests;
- remaining decisions it would have to invent.

Resolve important remaining decisions.

==================================================
PHASE 16 — READINESS AUDIT
==================================================

Audit for:

- product contradiction;
- vague behavior;
- scope creep;
- hidden dependencies;
- architecture assumptions;
- input boundaries;
- external-call failures;
- unsafe state mutation;
- nonexistent assumed dependencies;
- auth/tenant gaps;
- privacy/security gaps;
- AI grounding/eval gaps;
- missing tests;
- oversized implementation steps;
- future-step leakage.

Classify:
BLOCKER
IMPORTANT
NICE TO HAVE

==================================================
PHASE 17 — SYNC
==================================================

Compare finalized feature details to spec.md and features.md.

If feature planning produced an APPROVED product-level change, update the
affected upstream docs so there are no contradictions.

Do not widen scope silently.

==================================================
FINAL GATE
==================================================

Return:

READY FOR IMPLEMENTATION

only if:

- behavior is unambiguous;
- acceptance criteria are testable;
- repository architecture was inspected;
- major technical decisions are locked;
- dependencies are known;
- security and tenant boundaries are explicit;
- failure behavior is defined;
- AI behavior/evals are defined where applicable;
- implementation steps are reviewable;
- tests exist for every step;
- dry run reveals no material decision the implementation agent still has to invent.

Otherwise return:

NOT READY

and list only the blocking issues.

Do not implement the feature.
```

---

# 27. Recommended Codex Skill Packaging

Once this workflow works well manually, make it a reusable Codex skill.

Recommended structure:

```text
.agents/
└── skills/
    └── plan-feature/
        ├── SKILL.md
        ├── references/
        │   ├── feature-template.md
        │   ├── implementation-step-template.md
        │   ├── test-plan-template.md
        │   ├── ai-feature-checklist.md
        │   └── feature-gate.md
        └── scripts/
            └── optional-read-only-audit-scripts
```

Keep `SKILL.md` focused on routing and workflow.

Put large templates/checklists in `references/`.

---

## Example SKILL.md frontmatter

```yaml
---
name: plan-feature
description: >
  Turn one approved feature from features.md into a standalone, repository-aware,
  implementation-ready feature plan with technical decisions, scope boundaries,
  ordered implementation steps, tests-first planning, AI evaluation requirements,
  and Codex step prompts. Use after product planning and before implementation.
---
```

---

## Recommended root AGENTS.md routing guidance

```markdown
## Development workflow

Use the project workflow in this order:

1. Plan Product
2. Plan Feature
3. Implement
4. Code Review
5. Merge / Deploy

### Feature planning

Before implementing a non-trivial product feature:

- require an approved product spec and features list;
- run the Plan Feature workflow;
- inspect existing repository architecture before proposing new architecture;
- define tests before production implementation;
- implement one approved feature step at a time.

Do not let implementation silently change product requirements.
```

---

# 28. Alignment With the Unlearn Workflow

This workflow preserves the strongest concepts from the Unlearn Plan Feature lessons:

### Original concept: Give every feature its own spec

Preserved and strengthened with:

- product source-of-truth hierarchy;
- acceptance criteria;
- dependencies;
- assumptions;
- explicit synchronization rules.

### Original concept: Lock technical decisions before AI makes them

Preserved and strengthened with:

- repository reconnaissance first;
- existing-vs-new decisions;
- technical decision records;
- primary-source verification for changing APIs/libraries;
- architecture compatibility checks.

### Original concept: Choose what is out of scope

Preserved and strengthened with:

- explicit scope-creep simulation;
- technical non-goals;
- prohibited dependencies/abstractions;
- no future-step leakage.

### Original concept: Break the feature into reviewable steps

Preserved and strengthened with:

- dependency-aware steps;
- step contracts;
- security/error behavior per step;
- explicit acceptance checks;
- clean handoff to code review.

### Original concept: Preview how AI will build each step

Preserved and strengthened with:

- dry-run repository analysis;
- remaining-decision detection;
- architecture drift detection;
- stop-on-contradiction rule.

### Original concept: Write tests before features

Preserved and strengthened with:

- behavior-derived tests;
- auth/tenant tests;
- failure/idempotency tests;
- tests-only Codex prompts;
- AI-quality evals separate from deterministic software tests.

---

# 29. How This Fits the Full Workflow

```text
┌──────────────────────┐
│ 1. PLAN PRODUCT      │
│ spec.md              │
│ features.md          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 2. PLAN FEATURE      │
│ feature.md           │
│ decisions            │
│ implementation steps │
│ test plan / evals    │
│ step prompts         │
└──────────┬───────────┘
           │ Feature Planning Gate
           ▼
┌──────────────────────┐
│ 3. IMPLEMENT         │
│ tests first          │
│ one step at a time   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 4. CODE REVIEW       │
│ correctness          │
│ security             │
│ scope                │
│ architecture         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 5. MERGE / DEPLOY    │
│ preflight            │
│ ship gate            │
│ verification         │
└──────────────────────┘
```

---

# 30. Final Definition of Done

Plan Feature is complete only when all of the following are true:

- [ ] One feature has its own standalone specification.
- [ ] The feature preserves the approved product intent.
- [ ] Product goals and feature non-goals are explicit.
- [ ] User flows are unambiguous.
- [ ] Functional requirements are clear.
- [ ] Acceptance criteria are testable.
- [ ] The existing repository architecture was inspected.
- [ ] Existing patterns to reuse are documented.
- [ ] Dependencies are known and classified.
- [ ] Major technical decisions are explicit.
- [ ] New decisions include rationale.
- [ ] No unnecessary new framework/package/service is assumed.
- [ ] Authorization requirements are explicit.
- [ ] Tenant isolation is explicit where relevant.
- [ ] Input boundaries are explicit.
- [ ] Privacy/data-handling requirements are explicit.
- [ ] Failure paths are defined.
- [ ] Retry/idempotency behavior is defined where necessary.
- [ ] AI grounding and autonomy are explicit where applicable.
- [ ] AI failure behavior is explicit where applicable.
- [ ] AI evals are defined where applicable.
- [ ] Scope creep has been tested.
- [ ] Explicit non-scope is documented.
- [ ] The feature is divided into reviewable implementation steps.
- [ ] Every step has a clear contract.
- [ ] A test plan exists before production implementation.
- [ ] Every step has tests.
- [ ] Step-specific Codex test prompts can be generated.
- [ ] Step-specific Codex implementation prompts can be generated.
- [ ] A dry run reveals no major technical decision the agent must invent.
- [ ] The readiness audit has no blockers.
- [ ] `spec.md`, `features.md`, and the feature plan do not contradict each other.
- [ ] Feature Planning Gate returns **READY FOR IMPLEMENTATION**.

Only then should the feature enter the **Implement** workflow.

---

# 31. Reference Basis

This workflow is adapted from the ideas in:

- Unlearn skills repository:
  https://github.com/unlearndev/skills

- Unlearn `feature-generator` skill:
  https://github.com/unlearndev/skills/blob/main/skills/feature-generator/SKILL.md

- Unlearn `first-five` review skill:
  https://github.com/unlearndev/skills/blob/main/skills/first-five/SKILL.md

It is additionally designed for Codex using the current OpenAI guidance around
repository instructions, plan-first workflows, and reusable skills:

- Codex best practices:
  https://developers.openai.com/codex/learn/best-practices

- Codex `AGENTS.md`:
  https://developers.openai.com/codex/agent-configuration/agents-md

- Codex skills:
  https://developers.openai.com/codex/build-skills

The AI LMS additions are intentionally feature-focused: source grounding,
tenant boundaries, AI autonomy, evaluation, content provenance, long-running
generation, assessment integrity, and AI usage/cost controls are planned before
implementation rather than left for the coding agent to infer.

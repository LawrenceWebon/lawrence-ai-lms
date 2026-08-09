# Plan Product — AI LMS / Codex Workflow

> **Purpose:** Turn an incomplete AI LMS idea, notes, screenshots, diagrams, transcripts, research, or existing project documents into a build-ready product specification that a Codex-based AI development agent can safely and consistently use as the source of truth.
>
> **Planning boundary:** This workflow plans the product. It does **not** implement production features. Coding starts only after the Product Planning Gate passes and the work is handed to the **Plan Feature** workflow.

---

## Repository-specific application

Follow [the repository workflow authority](README.md) before this generic guide.
This LMS has a concise product contract under `docs/product` backed by the detailed
baseline in `docs/plan`. Maintain those files; do not recreate or expand them for a
routine feature. Use Plan Product only when the owner changes product scope. The
current scope promotes PDF upload-to-course generation into the core MVP while leaving
commerce, AI companion/RAG, and advanced LMS capabilities out of scope.

Any planning work is delivered through a focused GitHub issue and PR using the `gh`
CLI lifecycle in `README.md`. Product planning does not occupy or block unrelated
implementation lanes after its affected contracts are frozen.

---

## 1. What This Workflow Produces

The Plan Product workflow should finish with the following artifacts:

```text
/docs/product/
├── spec.md                  # Canonical product specification — source of truth
├── features.md              # Derived feature inventory in dependency order
├── decisions.md             # Important decisions and rationale
├── open-questions.md        # Unresolved product decisions and owners/status
├── product-audit.md         # Final gap, consistency, risk, and readiness audit
└── mockups/                 # Optional low-fidelity planning mockups/wireframes
```

Optional repository-level Codex setup:

```text
/AGENTS.md
```

### Source-of-truth hierarchy

If two artifacts disagree, use this order:

1. `spec.md`
2. Explicitly approved entries in `decisions.md`
3. `features.md`
4. Mockups and diagrams
5. Raw notes, transcripts, screenshots, and brainstorming material

When a decision changes, update `spec.md` first, then synchronize all derived documents.

---

# 2. Codex Agent Operating Rules

These rules apply for the entire Plan Product workflow.

## 2.1 Read before writing

Before editing product documents, Codex must:

1. Read repository `AGENTS.md` and any applicable nested instructions.
2. Inspect the existing `/docs/product/` artifacts.
3. Read every supporting artifact provided for the product-planning task.
4. Determine whether a specification already exists before creating a new one.
5. Preserve approved decisions unless the user explicitly changes them.

Do not overwrite a mature specification with a freshly generated generic version.

## 2.2 Product planning only

During this workflow, do not:

- implement application features;
- create database migrations;
- create production APIs;
- add packages because they might be useful;
- silently scaffold business logic;
- introduce architecture that has not been justified by product requirements;
- convert an unresolved product question into code.

Small throwaway design artifacts or non-functional wireframes are allowed only when they help validate the specification.

## 2.3 Separate facts, decisions, assumptions, and questions

Codex must distinguish four kinds of information:

- **Fact** — explicitly provided by the user or verified from a trusted source.
- **Decision** — a choice deliberately made for this product.
- **Assumption** — a temporary working belief that has not been validated.
- **Open question** — something important enough that the product team must decide it.

Never present an assumption as a fact.

## 2.4 Do not invent product scope

Codex may recommend missing capabilities, but recommended capabilities are **not part of the product** until approved.

When discovering a possible missing feature:

1. explain the gap;
2. explain why it matters;
3. offer a small number of concrete options;
4. record the selected option;
5. update `spec.md` only after the option is accepted or after a clearly documented conservative default is appropriate.

## 2.5 Ask only high-value questions

Do not stop for every minor ambiguity.

Ask the user when the answer materially changes one or more of the following:

- product scope;
- target users;
- pricing/business model;
- permissions;
- tenant isolation;
- educational workflow;
- AI autonomy;
- source-of-truth/content ownership;
- security/privacy expectations;
- critical integration choice;
- acceptance criteria;
- MVP boundary.

For low-impact details, choose a conservative default and mark it as an assumption.

## 2.6 Verify unstable technical claims

When recommending frameworks, AI providers, model capabilities, authentication products, payment providers, hosting products, SDKs, APIs, or other fast-changing technology:

- verify against current official documentation or another primary source;
- prefer current supported approaches over remembered patterns;
- record meaningful product-impacting constraints in `spec.md` or `decisions.md`;
- avoid copying low-level implementation detail into product-facing feature descriptions.

## 2.7 Keep specifications implementation-aware, not implementation-heavy

The product spec may define technical constraints that shape the product, such as:

- required platform/runtime;
- database type;
- tenancy model;
- authentication provider;
- supported AI architecture boundaries;
- deployment environment;
- required external services;
- privacy/security requirements.

It should not become a code-level design document. Detailed schema, endpoints, classes, folder structures, queues, and implementation algorithms belong in later workflows.

---

# 3. AI LMS Planning Principles

An AI LMS needs planning beyond a conventional CRUD LMS because AI output can be probabilistic, source-dependent, expensive, and incorrect.

The planning process must explicitly cover the following product concerns.

## 3.1 Learning roles

At minimum, determine whether the product includes these actors:

- Learner / Student
- Instructor / Course Author
- Organization or School Administrator
- Platform Administrator
- Reviewer / Approver, if AI-generated courses require review
- Guest / Public Visitor, if public course discovery exists

Do not assume all administrator roles are separate. Consolidate roles when their permissions and workflows do not justify independent personas.

## 3.2 Course creation modes

Determine which modes are in scope:

1. Manual course creation
2. AI-assisted manual authoring
3. Upload/import a source document or book and generate a course structure
4. Generate modules/topics/lessons from approved source material
5. Import an existing course

For AI-generated course creation, define the approval workflow before publishing.

## 3.3 Source-grounded AI

For AI-generated educational content, define:

- what source material the AI may use;
- whether generation must be grounded only in uploaded/approved sources;
- whether external web knowledge is allowed;
- whether responses require source citations or source references;
- what happens when the source does not contain the answer;
- how conflicting sources are handled;
- who approves generated lessons before learners see them.

## 3.4 AI learning companion

For course-aware AI chat, define at product level:

- what content the companion can access;
- whether it is limited to the current course/module/lesson;
- whether it can use learner progress as context;
- whether it may generate quizzes, explanations, hints, examples, or summaries;
- whether it may give direct answers to graded work;
- what it does when confidence is low;
- how citations/source references appear;
- what conversations are retained;
- who may review conversations;
- what safety restrictions apply.

## 3.5 AI-generated assessments

If AI may generate quizzes or assessments, specify:

- supported question types;
- approval requirements;
- answer validation expectations;
- whether generated assessments can affect official grades;
- retry/regeneration behavior;
- source grounding;
- versioning after learners have attempted an assessment.

Avoid making high-stakes grading autonomous by default.

## 3.6 Multi-tenancy and institutional boundaries

If the LMS serves multiple schools, universities, training centers, review centers, or organizations, explicitly define:

- tenant ownership;
- organization membership;
- user membership in one or multiple organizations;
- course ownership;
- who can see learners and course analytics;
- cross-tenant sharing rules;
- public vs private courses;
- platform-admin access;
- data export/deletion expectations.

Tenant isolation is a product requirement, not merely a database detail.

## 3.7 AI trust and quality

The spec should identify observable quality requirements for AI experiences. Examples:

- grounded answers must reference approved source material;
- the assistant must say when the answer is not supported by available course content;
- generated course content requires human approval before publication;
- generated assessments should be reviewable and editable;
- users should be able to report a poor or unsafe AI response;
- AI actions affecting learner records need explicit authorization.

## 3.8 Rights and content ownership

For uploaded books/documents/materials, define product expectations around:

- uploader confirmation that they have permission to use the material;
- private organization-owned content vs public content;
- generated derivative course content;
- deletion behavior when a source is removed;
- whether generated content remains usable after source deletion;
- restrictions on exposing source text to other tenants or learners.

Do not assume that uploading a document grants the platform unrestricted rights to redistribute it.

---

# 4. Workflow Overview

```text
Raw Idea / Notes / Existing Docs
        ↓
1. Product Intake
        ↓
2. Evidence & Assumption Map
        ↓
3. Initial Product Sketch
        ↓
4. Draft spec.md
        ↓
5. Shape & Simplify
        ↓
6. Technical Constraints
        ↓
7. AI LMS Domain Constraints
        ↓
8. Scope / Non-Goals / Out-of-Scope
        ↓
9. User Journeys & Permission Tests
        ↓
10. AI Trust, Safety & Evaluation Plan
        ↓
11. Mockup Validation Loop
        ↓
12. Failure / Edge-Case Challenge
        ↓
13. “What Did We Miss?” Audit
        ↓
14. Final Spec Consistency Gate
        ↓
15. Generate features.md
        ↓
16. Product Planning Gate
        ↓
HANDOFF → Plan Feature
```

---

# 5. Phase 0 — Initialize Product Planning

## Goal

Make Codex understand the planning rules before it edits anything.

## Actions

1. Read `AGENTS.md`.
2. Read existing planning documents.
3. Inventory all supplied inputs.
4. Identify the current product-planning state:
   - no spec;
   - rough spec;
   - mature spec needing refinement;
   - spec and features needing synchronization.
5. Report the artifacts that will be treated as authoritative.

## Prompt

```text
We are entering the Plan Product workflow for an AI LMS.

Before creating or editing anything:
1. Read AGENTS.md and all applicable project instructions.
2. Inspect existing product-planning documents.
3. Read all supporting files I provided.
4. Identify what is fact, approved decision, assumption, and open question.
5. Tell me the current planning state and which file should be the source of truth.

Do not write production code and do not implement features during this workflow.
```

## Exit criteria

- Codex knows whether `spec.md` already exists.
- Existing decisions will not be unintentionally replaced.
- The planning boundary is explicit.

---

# 6. Phase 1 — Product Intake: Give the Agent Everything

## Goal

Capture raw material without prematurely forcing it into implementation detail.

Provide any useful source material:

- product idea;
- notes;
- meeting transcripts;
- screenshots;
- sketches;
- diagrams;
- current application screenshots;
- competitor observations;
- user complaints;
- existing README/docs;
- business rules;
- pricing ideas;
- architecture constraints already decided;
- sample books/course material;
- institutional workflows.

## Improved prompt — initial intake

```text
I want to plan an AI-powered Learning Management System.

Use everything I provide as raw planning input. Do not assume every note is an approved requirement.

First:
- inventory the inputs;
- extract explicit requirements;
- identify contradictions;
- identify important missing information;
- separate facts, decisions, assumptions, and open questions.

Then create or update /docs/product/spec.md as a rough product specification.

The specification must describe what the product should do and why. Keep low-level implementation details out unless they are hard technical constraints that materially affect product behavior.

Do not implement anything yet.
```

## Improved prompt — adding more documents

```text
I have additional product-planning material.

Read the new files and compare them against the current /docs/product/spec.md.

Update only the sections affected by the new evidence. Do not rewrite unrelated approved sections.

For every conflict:
- show the conflicting statements;
- identify which one currently appears authoritative;
- do not silently choose a new direction if the decision is product-significant.

After updating, summarize what changed, what remains uncertain, and whether any existing decision was invalidated.
```

## Exit criteria

- All supplied inputs have been considered.
- Contradictions are visible.
- A rough `spec.md` exists.

---

# 7. Phase 2 — Build the Evidence & Assumption Map

## Goal

Prevent Codex from turning plausible guesses into requirements.

For every major product area, classify the current understanding:

| Area | Fact | Decision | Assumption | Open Question |
|---|---|---|---|---|
| Target customer |  |  |  |  |
| Learner roles |  |  |  |  |
| Course authoring |  |  |  |  |
| AI course generation |  |  |  |  |
| AI companion |  |  |  |  |
| Assessments |  |  |  |  |
| Tenancy |  |  |  |  |
| Billing |  |  |  |  |
| Notifications |  |  |  |  |
| Analytics |  |  |  |  |
| Integrations |  |  |  |  |
| Security/privacy |  |  |  |  |

## Prompt

```text
Audit the current AI LMS product specification for hidden assumptions.

Create an evidence-and-assumption map for all major product areas.

For each item classify it as:
- Fact
- Approved decision
- Assumption
- Open question

Pay special attention to assumptions about:
- user roles and permissions;
- multi-tenancy;
- course ownership;
- AI-generated courses;
- AI chat behavior;
- source grounding;
- assessment grading;
- uploaded document rights;
- payments;
- notifications;
- analytics;
- organization administration.

Do not add features to spec.md in this step. Surface uncertainty first.
```

## Exit criteria

- High-impact assumptions are no longer hidden.
- Open decisions can be deliberately resolved.

---

# 8. Phase 3 — Create the Initial Structured Product Spec

## Goal

Convert raw understanding into a coherent product specification.

For an AI LMS, prefer an advanced product-spec structure because the product has multiple actors, AI behaviors, failure modes, integrations, security/privacy concerns, and cross-feature dependencies.

## Recommended `spec.md` structure

```text
# [Product Name] — Specification

## Overview
## Background & Problem Statement
## Goals
## Non-Goals
## User Roles
## User Stories
## Core Features
## User Flows
## Notifications & Emails
## Error States & Edge Cases
## Constraints
## Assumptions
## Open Questions
## Out of Scope (v1)
## Technical Stack
## Key Dependencies & Integrations
## AI Behavior & Trust Requirements
## Security & Privacy
## Success Metrics
```

### AI-specific extension

The `AI Behavior & Trust Requirements` section should cover product-level rules for:

- grounding;
- citations/source references;
- refusal/uncertainty behavior;
- human review;
- generated content approval;
- feedback/reporting;
- retention;
- AI actions that may change state;
- learner-facing boundaries.

## Prompt

```text
Using all current planning inputs, restructure /docs/product/spec.md into a complete advanced product specification for this AI LMS.

Requirements:
- plain language;
- product-focused behavior;
- explicit user roles;
- concrete goals and non-goals;
- core user journeys;
- important error and empty states;
- assumptions and open questions;
- v1 scope boundaries;
- technical constraints only where they affect the product;
- key integrations;
- AI behavior and trust requirements;
- security/privacy considerations;
- measurable success criteria.

Do not invent unapproved product features. If something appears useful but is not established, place it in open questions or recommendations rather than silently adding it to scope.
```

## Exit criteria

- A reader can explain the product without reading source notes.
- Product behavior is understandable without code.
- AI-specific behavior is explicit.

---

# 9. Phase 4 — Shape and Simplify the Specification

## Goal

Remove duplication, vague language, and unnecessary role/feature complexity.

## Audit questions

- What is missing?
- What is vague?
- What is duplicated?
- What is implementation detail disguised as a product requirement?
- Which roles can be consolidated?
- Which requirements are actually future ideas?
- Which sections contradict one another?
- Which sentences cannot be tested or observed?

## Prompts

### Consolidate roles

```text
Review the User Roles section.

Identify roles whose permissions and workflows are effectively the same. Recommend consolidation where separate roles add complexity without meaningful product value.

Do not merge roles when doing so would weaken tenant isolation, approval control, or learner/instructor separation.
```

### Remove implementation leakage

```text
Review Core Features and User Flows for implementation leakage.

Remove low-level details such as proposed database fields, table names, API routes, class names, file paths, queue names, and framework internals unless a detail represents a hard product constraint.

Preserve observable behavior and business rules.
```

### Tighten vague requirements

```text
Find vague requirements in spec.md such as “manage”, “support”, “handle”, “AI-powered”, “secure”, or “easy to use”.

Rewrite them into observable product behavior without inventing new scope.

Example: replace “AI helps learners” with the exact actions the learner can request and what the AI is allowed to return.
```

## Exit criteria

- The spec is concise enough to navigate.
- Every major requirement has observable meaning.
- Product and implementation concerns are separated.

---

# 10. Phase 5 — Add Technical Constraints From Day One

## Goal

Give Codex enough technical direction to avoid planning features that are incompatible with the intended platform, without turning the product spec into an architecture document.

## Record only meaningful constraints

Examples:

- frontend framework;
- backend platform;
- primary database;
- authentication system;
- supported deployment environment;
- payment provider;
- email provider;
- analytics/observability product;
- cache/queue constraints;
- vector retrieval requirement;
- supported AI provider/model policy;
- mobile/browser requirements;
- storage constraints.

## Prompt

```text
Add or update the Technical Stack and Key Dependencies sections of spec.md.

For each technology:
1. state its product-level purpose;
2. identify any constraint that changes product behavior;
3. distinguish “required” from “preferred” choices;
4. flag choices that still need validation.

Do not add detailed schemas, API designs, folder structures, deployment scripts, or code-level architecture.

For any current technology recommendation that is not already an approved project decision, verify it from current official documentation before recommending it.
```

## Exit criteria

- Product planning reflects real platform constraints.
- Architecture detail remains deferred to later workflows.

---

# 11. Phase 6 — Define AI LMS Product Constraints

## Goal

Make AI behavior explicit enough that future implementation does not fill gaps with unsafe or inconsistent assumptions.

## Required decisions

### Course generation

Decide:

- source types accepted;
- maximum useful scope per generation job at product level;
- whether course generation creates a draft only;
- whether instructor/admin approval is required;
- whether source references are attached to generated lessons;
- what happens if generation is incomplete;
- whether regeneration replaces or versions prior content.

### AI companion

Decide:

- scope of accessible content;
- source hierarchy;
- expected citations;
- behavior for unsupported questions;
- whether general knowledge is allowed;
- whether learner-specific context is allowed;
- whether conversations are saved;
- whether staff can inspect conversations;
- feedback/report flow.

### AI actions

Classify AI capabilities as:

- **Suggest** — AI proposes; human decides.
- **Draft** — AI creates editable content.
- **Execute with confirmation** — AI can change state only after explicit approval.
- **Autonomous** — AI may perform the action without per-action confirmation.

Use the least autonomous mode that satisfies the product requirement.

## Prompt

```text
Run an AI autonomy audit on spec.md.

For every AI capability, classify it as:
- Suggest
- Draft
- Execute with confirmation
- Autonomous

Then identify any capability where the spec does not clearly define:
- allowed sources;
- grounding requirements;
- human review;
- state-changing authority;
- failure behavior;
- feedback/reporting;
- retention/privacy.

Do not silently make high-impact autonomy decisions. Present concrete options for unresolved items.
```

## Exit criteria

- Every AI capability has an explicit autonomy level.
- AI source and approval behavior is defined.

---

# 12. Phase 7 — Tell Codex What It Must NOT Build

## Goal

Prevent scope creep and “helpful” overbuilding.

Use both:

- **Non-Goals** — things the product is not trying to become.
- **Out of Scope (v1)** — desirable capabilities intentionally deferred.

## Boundary test prompt

```text
Pretend you are the implementation agent receiving the current spec.md.

Describe exactly what you would build if you followed it literally:
- features;
- roles;
- user journeys;
- AI behaviors;
- integrations;
- notifications;
- admin capabilities;
- assumptions you would otherwise have to make.

Do not implement anything.

Highlight anything you would build that is probably accidental scope, underdefined, or broader than necessary.
```

## Update prompt

```text
Update spec.md to close the scope gaps found in the boundary test.

For each accidental capability:
- remove it;
- place it under Non-Goals; or
- defer it under Out of Scope (v1),
whichever accurately reflects the product decision.

Do not weaken explicitly approved requirements.
```

## Exit criteria

- A coding agent cannot reasonably infer major unrequested features.
- v1 boundaries are explicit.

---

# 13. Phase 8 — Validate Roles, Permissions, and User Journeys

## Goal

Test the spec from the perspective of actual users rather than feature headings.

## Minimum journeys to test for an AI LMS

When applicable:

1. Organization onboarding
2. Instructor/admin creates a course manually
3. Instructor uploads a source document and generates a draft course
4. Reviewer edits/approves generated course content
5. Learner enrolls or is assigned to a course
6. Learner opens a lesson and uses AI companion
7. Learner takes an assessment
8. Instructor reviews learner progress
9. Organization admin manages members
10. Course/source is updated after learners have started
11. Learner loses access or leaves an organization
12. Tenant/admin attempts to access another tenant’s data
13. AI cannot answer from approved source material

## Prompt

```text
Walk through the current spec as each user role.

For every primary journey:
1. state the starting condition;
2. list the steps the user takes;
3. state what the system does after each important action;
4. identify permission checks;
5. identify empty/error states;
6. identify where the journey gets ambiguous or impossible.

Do not solve gaps silently. Separate:
- spec defects;
- missing decisions;
- optional improvements.
```

## Exit criteria

- Primary journeys are complete end to end.
- Permission boundaries are visible at product level.

---

# 14. Phase 9 — Define AI Trust, Safety, and Evaluation Requirements

## Goal

Make AI quality a planned product requirement rather than a post-launch guess.

## Product-level evaluation areas

### Retrieval / grounding

- Did the AI use the correct course/source context?
- Can the response point back to supporting material?
- Does it avoid claiming support when none exists?

### Educational usefulness

- Is the explanation relevant to the learner’s current lesson?
- Is the difficulty appropriate where adaptation exists?
- Does the assistant provide hints vs direct answers according to policy?

### Course generation

- Does generated structure reflect source material?
- Are modules and lessons coherent?
- Are unsupported claims detectable during review?
- Can instructors edit before publish?

### Safety and permissions

- Can AI reveal another tenant’s content?
- Can learner AI actions change protected records?
- Can AI bypass instructor/admin approval?
- Can sensitive data appear in generated responses unexpectedly?

### Feedback loop

Define how users can:

- like/dislike or rate an AI response;
- report incorrect or unsafe output;
- provide instructor corrections;
- escalate persistent problems;
- contribute signals for future evaluation.

Feedback should not automatically become trusted training data without a separate approved policy.

## Prompt

```text
Create a product-level AI evaluation section for this LMS.

For each AI feature define:
- intended outcome;
- unacceptable failure;
- user-visible fallback behavior;
- review/approval requirement;
- feedback mechanism;
- measurable quality signal.

Keep this product-level. Do not design the evaluation code, model pipeline, or test harness yet.
```

## Exit criteria

- Each AI feature has a definition of acceptable behavior.
- Known high-impact failure modes have product fallbacks.

---

# 15. Phase 10 — Use Mockups to Expose Missing Product Decisions

## Goal

Use low-fidelity UI interpretation to test whether the specification describes the intended product.

Mockups are diagnostic artifacts, not new sources of truth.

## Good pages to mock first

For an AI LMS:

- learner dashboard;
- course page;
- lesson + AI companion;
- course authoring dashboard;
- upload-book/document course-generation flow;
- generated-course review screen;
- organization member management;
- instructor analytics/progress view.

## Prompt — generate planning mockup

```text
Using only the behavior currently defined in spec.md, create a low-fidelity planning mockup for [PAGE/FLOW].

Rules:
- do not add features because they are common in other LMS products;
- mark any UI element that requires an unstated product assumption;
- show role-specific actions only when the spec grants that capability;
- treat the mockup as a test of the specification, not a new requirement source.
```

## Prompt — compare mockup to intent

```text
Compare the generated mockup against spec.md.

List every place where the mockup had to guess.

For each guess classify it as:
- harmless UI detail;
- product decision needed;
- accidental scope.

Update spec.md only for decisions I approve.
```

## Exit criteria

- Important screens can be represented without major guessing.
- Mockup-derived assumptions are either resolved or removed.

---

# 16. Phase 11 — Poke Holes in the Plan

## Goal

Challenge the specification with realistic failure scenarios.

## Scenario families

### External dependency failure

- AI provider unavailable
- payment provider unavailable
- email provider unavailable
- storage unavailable
- vector/search service unavailable
- analytics unavailable

### Content failure

- document parsing partially fails
- source file is empty/corrupt
- unsupported language or format
- source contains contradictory information
- source is deleted after course generation

### AI failure

- answer is unsupported by source
- citations do not support the answer
- model times out
- unsafe/inappropriate response
- generated quiz contains an incorrect answer
- generated course structure is incomplete

### Permission failure

- user belongs to wrong organization
- instructor loses role mid-session
- public link exposes private content
- platform admin support access conflicts with privacy expectations

### Lifecycle failure

- course changes after learner starts
- assessment changes after submission
- organization subscription expires
- user is deleted but audit/history is needed

## Prompt

```text
Stress-test spec.md against realistic failure scenarios for an AI LMS.

Focus on:
- AI provider failure;
- source ingestion failure;
- incorrect/unsupported AI output;
- tenant-boundary violations;
- permission changes;
- course version changes;
- assessment version changes;
- notification failure;
- payment/subscription state changes if billing is in scope.

For each scenario tell me:
1. what the current spec implies;
2. what is undefined;
3. the user impact;
4. 2–3 concrete product-policy options when a decision is needed.

Do not invent an implementation solution unless the product behavior depends on it.
```

## Exit criteria

- Critical failure behavior is intentional, not accidental.

---

# 17. Phase 12 — Ask “What Might We Have Missed?”

## Goal

Find omissions after the product has already been constrained.

## Prompt

```text
Perform a missing-requirements audit on the current AI LMS spec.

Do not brainstorm random features.

Look specifically for omissions that would cause:
- a broken user journey;
- ambiguous permissions;
- data isolation problems;
- AI trust or grounding problems;
- inability to recover from failures;
- unclear course/content lifecycle;
- unclear learner-progress behavior;
- operational ambiguity;
- privacy/security ambiguity;
- unmeasurable success criteria.

For every finding provide:
- the gap;
- why it matters;
- severity: Blocking / Important / Optional;
- 2–3 choosable resolutions.

Present Blocking items first.
```

## Decision prompt

```text
Take the Blocking and Important findings one at a time.

For each finding:
- give me 2–3 concrete options;
- explain the product tradeoff briefly;
- recommend one default;
- wait for the decision before treating it as approved scope.

After all decisions, update spec.md and decisions.md, then remove resolved items from open-questions.md.
```

## Exit criteria

- No Blocking product gap remains unresolved without being explicitly accepted as a known risk.

---

# 18. Phase 13 — Final Spec Audit and Synchronization

## Goal

Make `spec.md` internally consistent before deriving the development roadmap.

## Audit dimensions

### Completeness

- goals map to features;
- user roles map to permissions;
- primary journeys map to features;
- AI features have trust/quality rules;
- failure states are defined where high impact;
- integrations have a product purpose.

### Consistency

- same feature has same behavior everywhere;
- terminology is stable;
- role names do not drift;
- v1 scope does not contradict Core Features;
- assumptions do not appear elsewhere as facts;
- open questions are not silently treated as decisions.

### Traceability

For every core feature, Codex should be able to answer:

- Which goal does it support?
- Which role uses it?
- Which user journey includes it?
- What important constraints apply?
- What defines success?

## Prompt

```text
Run a final product-spec audit on /docs/product/spec.md.

Check:
- completeness;
- contradictions;
- duplicate requirements;
- undefined terminology;
- unresolved assumptions treated as facts;
- role/permission inconsistencies;
- AI behavior inconsistencies;
- missing error/empty states;
- scope leakage;
- goals without supporting features;
- features without a clear goal or user need;
- success metrics that cannot be connected to goals.

Create /docs/product/product-audit.md with findings grouped as:
- BLOCKER
- IMPORTANT
- OPTIONAL
- PASS

Do not modify spec.md during the audit. After the audit, apply only approved or unambiguous corrections and re-run the audit.
```

## Exit criteria

- Zero unresolved BLOCKER findings, unless explicitly accepted and documented.
- `spec.md` is internally consistent.

---

# 19. Phase 14 — From Spec to Features

## Goal

Generate the high-level feature roadmap without designing implementation internals.

`features.md` is derived from `spec.md`. It must never become an independent source of new product scope.

## Required format per feature

```text
## N. Feature Name

Short description of what the feature does and who it is for.

**Why it exists**
Which product goal/user need this feature supports.

**User flow**
1. ...
2. ...
3. ...

**UI overview**
What the user sees or interacts with.

**Dependencies**
Other product features that must exist first.

**Product constraints**
Important non-implementation rules from spec.md.
```

## Ordering rules

Order features for successful implementation, not marketing importance:

1. Product/account/tenant foundation required by later workflows
2. Authentication and membership capabilities
3. Core course/content lifecycle
4. Learner course consumption
5. Assessments/progress
6. AI content-generation capabilities
7. AI learning companion
8. Instructor/admin workflows
9. Notifications and supporting cross-cutting product behavior
10. Analytics/operational product capabilities

The exact order must come from actual dependencies in `spec.md`.

## Prompt

```text
Read /docs/product/spec.md as the single source of truth and create /docs/product/features.md.

For each feature include:
- feature name;
- short description;
- why it exists / mapped product goal;
- user flow;
- UI overview;
- product dependencies;
- key product constraints.

Rules:
- use only capabilities clearly supported by spec.md;
- do not invent features;
- keep content product-focused;
- do not include database schemas, table names, file paths, classes, API endpoints, or implementation algorithms;
- arrange features in dependency-aware implementation order suitable for an AI coding agent.

After generating features.md, run a two-way coverage check:
1. every core spec feature appears in features.md;
2. every features.md item is justified by spec.md.

Report discrepancies instead of silently changing scope.
```

## Exit criteria

- `features.md` is fully traceable to `spec.md`.
- Feature order is dependency-aware.

---

# 20. Phase 15 — Synchronize Spec and Features

## Goal

Prevent planning drift.

## Rules

When `spec.md` changes:

- update only affected entries in `features.md`;
- add/remove/reorder features only when the spec requires it;
- do not rewrite unrelated features.

When someone proposes a change directly in `features.md`:

- treat it as a proposed product change;
- verify that `spec.md` supports it;
- if not, update `spec.md` only after the product decision is approved.

## Prompt

```text
Synchronize spec.md and features.md without introducing new scope.

First produce a discrepancy report with:
- spec requirement missing from features;
- feature not supported by spec;
- conflicting behavior;
- inconsistent terminology;
- dependency-order problem.

Then fix unambiguous synchronization issues.

For changes that alter product behavior or scope, stop and present them as decisions rather than choosing silently.
```

---

# 21. Phase 16 — Product Planning Gate

The product is ready for **Plan Feature** only when this gate passes.

## Required gate

### Product clarity

- [ ] Product problem and target users are clear.
- [ ] Goals are outcomes, not a feature wish list.
- [ ] Non-goals are explicit.
- [ ] v1 scope is bounded.

### User model

- [ ] User roles are defined.
- [ ] Organization/tenant behavior is defined if applicable.
- [ ] Important permission boundaries are defined.
- [ ] Primary user journeys are complete.

### Course model

- [ ] Course ownership and lifecycle are defined.
- [ ] Manual vs AI-assisted course creation is defined.
- [ ] Publishing/approval behavior is defined.
- [ ] Source document lifecycle is defined.

### AI behavior

- [ ] Every AI capability has an autonomy level.
- [ ] Grounding/source rules are explicit.
- [ ] Human review is defined where needed.
- [ ] Unsupported-answer behavior is defined.
- [ ] Feedback/report behavior is defined.
- [ ] Product-level quality signals are defined.

### Failure behavior

- [ ] High-impact external-service failures have product behavior.
- [ ] Source-ingestion failures have product behavior.
- [ ] AI failure/uncertainty has user-visible behavior.
- [ ] Permission and tenant failure cases are covered.

### Consistency

- [ ] No BLOCKER remains in `product-audit.md`.
- [ ] `features.md` contains no unsupported scope.
- [ ] `spec.md` and `features.md` use consistent terminology.
- [ ] Open questions are clearly separated from approved scope.

### Build handoff

- [ ] Features are ordered by dependency.
- [ ] The first feature can be planned without inventing product requirements.
- [ ] Technical constraints needed for feature planning are recorded.
- [ ] No implementation has been accidentally started during Plan Product.

## Gate prompt

```text
Run the Product Planning Gate for this AI LMS.

Return exactly:
1. PASS or BLOCKED
2. Blocking items
3. Important non-blocking risks
4. First recommended feature to send into the Plan Feature workflow and why it is dependency-safe

Do not implement the feature.
```

---

# 22. Handoff to Plan Feature

When the Product Planning Gate passes, create a compact handoff for the next workflow.

## Handoff package

```text
Product source of truth: /docs/product/spec.md
Derived roadmap:        /docs/product/features.md
Decisions:              /docs/product/decisions.md
Open questions:         /docs/product/open-questions.md
Audit:                  /docs/product/product-audit.md
Selected next feature:  [Feature N — Name]
```

## Handoff prompt

```text
Product planning is complete.

Prepare a Plan Feature handoff for [FEATURE NAME].

Use spec.md as the source of truth and features.md as the derived roadmap.

Include:
- product goal supported;
- actors involved;
- user journey touched;
- product constraints;
- AI-specific behavior, if any;
- relevant decisions;
- relevant unresolved questions;
- dependencies already required;
- explicit out-of-scope behavior for this feature.

Do not design or implement the feature in this step. The output should be the clean starting context for the separate Plan Feature workflow.
```

---

# 23. Master Codex Prompt — Run the Entire Plan Product Workflow

Use the following as the main prompt when starting product planning with Codex.

```text
You are the product-planning agent for an AI-powered Learning Management System.

Your job is to turn the product material I provide into a build-ready product plan that another Codex agent can implement later without inventing requirements.

PLANNING BOUNDARY
- This workflow is Plan Product only.
- Do not implement production features.
- Do not create migrations, APIs, business logic, or production integrations.
- Do not install packages just because they may be useful.
- Do not silently scaffold the application.
- The workflow ends with a validated product plan and a handoff to Plan Feature.

BEFORE EDITING
1. Read AGENTS.md and applicable nested instructions.
2. Inspect /docs/product/ and identify existing planning artifacts.
3. Read every planning input I provide: notes, screenshots, diagrams, transcripts, research, and existing docs.
4. Identify the current planning state.
5. Preserve approved decisions and existing mature content.

SOURCE OF TRUTH
- /docs/product/spec.md is the canonical product source of truth.
- /docs/product/features.md is derived from spec.md and must not introduce independent scope.
- decisions.md records approved decisions and rationale.
- open-questions.md records unresolved product decisions.
- mockups are validation aids, not requirement sources.

INFORMATION DISCIPLINE
For important information, distinguish:
- Fact
- Approved decision
- Assumption
- Open question

Never present an assumption as a fact.
Never add a recommended feature to product scope unless it is approved or unambiguously required by an existing approved requirement.

QUESTION POLICY
Ask questions only when the answer materially affects scope, roles, permissions, tenancy, AI behavior, content ownership, payments, critical integrations, security/privacy, or the MVP boundary.
For low-impact details, choose a conservative default and label it as an assumption.

TECHNOLOGY POLICY
Keep the product spec implementation-aware but not implementation-heavy.
When a fast-changing technical recommendation is required, verify it against current official documentation before recommending it.
Do not place table schemas, endpoints, classes, file paths, or implementation algorithms in product feature descriptions.

AI LMS REQUIREMENTS
Explicitly plan, where applicable:
- Learner, instructor/course author, organization admin, platform admin, reviewer, and guest roles.
- Multi-tenant organization boundaries.
- Manual course creation.
- AI-assisted course creation.
- Uploading a book/document and generating modules, topics, and lessons.
- Human review and approval before generated learning content is published.
- Source grounding and citation/reference behavior.
- AI learning companion boundaries.
- Assessment generation and grading authority.
- Course and assessment version/lifecycle behavior.
- Uploaded-content ownership and deletion expectations.
- AI feedback/reporting.
- Security/privacy expectations.
- Product-level AI quality and fallback behavior.

AI AUTONOMY
Classify every AI capability as one of:
- Suggest
- Draft
- Execute with confirmation
- Autonomous

Use the least autonomous level that still satisfies the approved product requirement. Do not silently choose a high-autonomy mode.

WORKFLOW
Run these stages in order:

1. Product Intake
   - inventory inputs;
   - extract explicit requirements;
   - find contradictions;
   - create/update rough spec.md.

2. Evidence & Assumption Map
   - expose facts, decisions, assumptions, and open questions;
   - especially inspect AI and multi-tenant assumptions.

3. Structured Specification
   - create/refine an advanced spec containing overview, problem, goals, non-goals, roles, stories, features, flows, notifications, errors/edge cases, constraints, assumptions, open questions, v1 out-of-scope, technical stack, dependencies/integrations, AI behavior/trust, security/privacy, and success metrics.

4. Shape & Simplify
   - remove duplication;
   - consolidate unnecessary roles;
   - replace vague wording with observable behavior;
   - remove implementation leakage.

5. Technical Constraints
   - record required/preferred product-shaping technologies and integrations;
   - verify unstable recommendations using official sources.

6. AI LMS Constraint Audit
   - define course-generation rules;
   - define AI companion boundaries;
   - define source grounding;
   - define human approval;
   - define AI autonomy;
   - define assessment authority;
   - define content lifecycle/rights expectations.

7. Scope Boundary Test
   - explain what an implementation agent would build from the spec;
   - find accidental scope;
   - strengthen Non-Goals and Out of Scope (v1).

8. User Journey & Permission Test
   - walk the major journeys end to end;
   - find impossible or ambiguous steps;
   - test tenant and role boundaries.

9. AI Trust & Evaluation Requirements
   - define intended outcome, unacceptable failure, fallback, approval, feedback, and measurable quality signal for each AI capability.

10. Mockup Validation
    - generate low-fidelity planning mockups for important pages/flows when useful;
    - identify where the UI had to guess;
    - do not treat mockup guesses as requirements.

11. Failure & Edge-Case Challenge
    - test external dependency failures, source-ingestion failures, AI failures, permission problems, and lifecycle/version changes.

12. Missing-Requirements Audit
    - find omissions that would break journeys, permissions, tenant isolation, AI trust, content lifecycle, recovery, privacy/security, or measurement;
    - label findings Blocking / Important / Optional.

13. Final Spec Audit
    - check completeness, consistency, traceability, terminology, role permissions, AI rules, scope boundaries, and unresolved assumptions;
    - create product-audit.md;
    - do not proceed while unresolved BLOCKER findings remain unless I explicitly accept them.

14. Generate features.md
    - derive features only from spec.md;
    - include name, description, mapped goal, user flow, UI overview, dependencies, and product constraints;
    - order by implementation dependency;
    - run two-way coverage between spec.md and features.md.

15. Product Planning Gate
    - return PASS or BLOCKED;
    - list blockers and important risks;
    - identify the first dependency-safe feature to send to Plan Feature;
    - do not implement it.

CHANGE CONTROL
Whenever product scope or behavior changes:
1. update spec.md first;
2. record important rationale in decisions.md;
3. update/remove resolved open questions;
4. synchronize features.md;
5. rerun the relevant audit;
6. summarize exactly what changed.

OUTPUT STYLE
- Be concise but complete.
- Prefer concrete behavior over generic product language.
- Do not pad documents with common LMS features that were never approved.
- Surface contradictions instead of hiding them.
- Label uncertainty.
- Keep recommendations separate from approved scope.
- Preserve unaffected approved content when editing existing documents.

Start by reading the repository instructions and all provided product-planning material. Then report the current planning state before making substantive changes.
```

---

# 24. Recommended Codex Skill Packaging

Once this workflow is stable, package it as a reusable Codex skill instead of pasting the master prompt repeatedly.

Suggested structure:

```text
.agents/
└── skills/
    └── plan-product/
        ├── SKILL.md
        ├── references/
        │   ├── ai-lms-planning-checklist.md
        │   └── product-planning-gate.md
        └── templates/
            ├── spec-template.md
            ├── features-template.md
            ├── decisions-template.md
            └── product-audit-template.md
```

Suggested skill description:

```yaml
name: plan-product
description: >
  Turn a vague product idea or existing planning material into a validated,
  build-ready product specification and dependency-ordered feature roadmap.
  Use for new product planning, AI LMS planning, refining spec.md, testing
  scope boundaries, auditing assumptions and AI behavior, generating features.md,
  or preparing a product for the Plan Feature workflow. Do not implement features.
```

### Root `AGENTS.md` routing guidance

Keep the permanent repository rule short. For example:

```text
## Product planning

When work changes product scope, user behavior, roles, permissions, AI behavior,
or MVP boundaries, use the plan-product workflow before implementation.

/docs/product/spec.md is the canonical product source of truth.
features.md is derived and must not introduce independent scope.
Do not begin implementation while the Product Planning Gate is BLOCKED.
```

---

# 25. Alignment With the Unlearn Workflow

This updated workflow keeps the strongest ideas from the Unlearn material:

- start from messy raw inputs;
- create a structured spec;
- refine assumptions and remove unnecessary scope;
- add technical constraints early;
- explicitly define what not to build;
- use mockups to discover ambiguity;
- challenge the plan with scenarios;
- ask what was missed;
- derive `features.md` from `spec.md`;
- order features for implementation.

It adds controls needed for an AI LMS and for a more autonomous coding agent:

- explicit source-of-truth hierarchy;
- fact/decision/assumption/open-question discipline;
- product-level tenant isolation;
- AI autonomy classification;
- grounding and source rules;
- human approval requirements;
- AI evaluation criteria;
- content ownership/lifecycle planning;
- two-way spec/features traceability;
- formal Product Planning Gate;
- clean handoff to Plan Feature instead of starting implementation inside Plan Product.

---

# 26. Final Definition of Done

**Plan Product is DONE only when:**

1. A coherent `spec.md` exists and is the canonical product source of truth.
2. The product problem, users, goals, and v1 boundaries are clear.
3. AI LMS behaviors are explicit enough that an implementation agent does not need to invent policy.
4. Major assumptions and unresolved decisions are visible.
5. Critical user journeys, permissions, tenant boundaries, failure paths, and AI fallbacks are intentional.
6. Product-level AI quality expectations are defined.
7. `features.md` contains only spec-backed scope and is in dependency order.
8. `product-audit.md` has no unresolved BLOCKER finding unless explicitly accepted.
9. The Product Planning Gate returns **PASS**.
10. The selected next feature is handed to **Plan Feature** without implementation beginning prematurely.

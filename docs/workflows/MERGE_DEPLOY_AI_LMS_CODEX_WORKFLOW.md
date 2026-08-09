# Merge & Deploy — AI LMS / Codex Workflow

> **Purpose:** Safely move an approved AI LMS change from `APPROVED FOR MERGE` through production preflight, merge, deployment, controlled activation, live QA, monitoring, rollback readiness, release documentation, and a final verified production state.
>
> **Workflow position:**  
> `Plan Product → Plan Feature → Implement → Code Review → Merge / Deploy`
>
> **Entry requirement:** The exact release candidate must have formal Code Review verdict `APPROVED FOR MERGE`.
>
> **Terminal states:**
> - `DEPLOYED AND VERIFIED`
> - `DEPLOYED DARK`
> - `ROLLED BACK`
> - `BLOCKED`

---

## Repository-specific application

Follow [the repository workflow authority](README.md). Parallel development ends in
independent PRs; an integration owner merges them one at a time in the declared
dependency order. Before each merge, verify the exact reviewed `headRefOid`, required
checks, approvals, mergeability, migrations/contracts, and any integration retest.

Use `gh pr checks` and SHA-locked `gh pr merge --match-head-commit` with the
repository-approved merge strategy. Never use `--admin`, bypass protection, merge an
agent's own unreviewed PR, or treat merge permission as deployment authorization.
After each merge, remaining PRs incorporate the new base, rerun checks, and receive
review for their new SHA. This serializes shared integration, not implementation.

---

# 1. Core Principle

Reviewed code is not the same thing as production-ready code.

A change may still require:

- database migrations;
- new production environment variables;
- secrets;
- email provider configuration;
- worker or scheduler changes;
- webhook registration;
- storage policies;
- feature flags;
- AI provider access;
- vector-index changes;
- observability;
- QA accounts;
- rollback preparation.

The production workflow must derive those requirements from the **actual release diff**, not from memory.

---

# 2. Release State Machine

```text
APPROVED_FOR_MERGE
        ↓
PREFLIGHT_READY
        ↓
SHIP_GATE_PASS
        ↓
CI_GREEN
        ↓
MERGED
        ↓
PRODUCTION_READY
        ↓
DEPLOYING
        ↓
DEPLOYED_DARK
        ↓
QA_PASSED
        ↓
ACTIVATING
        ↓
DEPLOYED_AND_VERIFIED
```

Exceptional states:

```text
BLOCKED_PREFLIGHT
BLOCKED_CI
BLOCKED_CONFIG
BLOCKED_MIGRATION
BLOCKED_SECURITY
DEPLOY_FAILED
QA_FAILED
ROLLED_BACK
HOTFIX_REQUIRED
```

Never use vague release states such as:

```text
probably live
almost deployed
looks good
```

---

# 3. Required Inputs

Recommended inputs:

```text
AGENTS.md and REVIEW_GUIDE.md              # when present
docs/workflows/README.md
docs/product/spec.md, features.md, and decisions.md
relevant docs/plan/ADRs
approved GitHub issue and PR
formal review of the current headRefOid
required GitHub checks and integration order

Production:
├── environment
├── database
├── environment variables
├── secrets
├── workers / schedulers
├── external integrations
├── AI / RAG services
├── feature flags
├── observability
└── rollback mechanism
```

---

# 4. Outputs

Release evidence follows `docs/evidence/README.md` and the relevant runbooks. Typical
small records are:

```text
docs/evidence/[release-or-pr]/
├── production-preflight.md
├── rollback-plan.md
├── production-qa.md
└── deployment-record.md
```

Optional project-level artifacts:

```text
CHANGELOG.md
docs/releases/[version].md
GitHub release notes
runbook updates
```

---

# 5. Production Authority Rules

Merge and deployment are consequential actions.

Codex should distinguish between **preparation** and **execution**.

## Allowed by default for preparation

Codex may:

- inspect the release diff;
- inspect CI;
- generate preflight;
- generate Ship Gate results;
- prepare migration commands;
- prepare environment/config checklist;
- prepare QA checklist;
- prepare rollback plan;
- prepare release notes;
- prepare changelog;
- update non-sensitive documentation;
- inspect non-destructive health information when authorized.

## Requires explicit authorization or approved automation

Codex must not assume permission to:

- merge to protected branch;
- force-push;
- deploy production;
- run production migrations;
- modify production environment variables;
- restart production services;
- rotate secrets;
- change DNS;
- enable a feature globally;
- modify production data;
- change IAM/service permissions;
- publish a release.

## Never silently

Never silently:

- bypass failing CI;
- override branch protection;
- deploy an unreviewed SHA;
- disable RLS;
- remove auth;
- expose secrets;
- run destructive migration without plan;
- activate a risky feature before QA;
- skip smoke tests because build/deploy succeeded.

---

# 6. Workflow Overview

```text
Phase 0   Release eligibility
Phase 1   Verify exact release diff
Phase 2   Generate production preflight
Phase 3   Run Ship Gate
Phase 4   Inventory production dependencies
Phase 5   Verify environment and secrets
Phase 6   Verify migrations
Phase 7   Verify auth / RLS / tenancy
Phase 8   Verify external services
Phase 9   Verify AI / RAG production readiness
Phase 10  Verify workers / schedulers
Phase 11  Verify observability
Phase 12  Create rollback plan
Phase 13  Run CI / merge gate
Phase 14  Merge
Phase 15  Choose deployment strategy
Phase 16  Deploy dark / limited
Phase 17  Run production smoke tests
Phase 18  Run feature QA
Phase 19  Run security / tenant QA
Phase 20  Run AI / RAG production QA
Phase 21  Activate gradually
Phase 22  Monitor
Phase 23  Rollback decision gate
Phase 24  Final production verification
Phase 25  Generate changelog
Phase 26  Generate release notes
Phase 27  Sync documentation
Phase 28  Record deployment
Phase 29  Production Verification Gate
```

---

# 7. Phase 0 — Release Eligibility

## Goal

Only formally approved code enters the release pipeline.

## Checks

Confirm:

- `code-review.md` verdict is `APPROVED FOR MERGE`;
- reviewed SHA is known;
- current PR/branch SHA is known;
- current SHA matches reviewed SHA or all changes since review were formally re-reviewed;
- required CI checks are known;
- target environment is known;
- no unresolved Critical/Error review issue remains.

## Reviewed SHA rule

If:

```text
reviewed SHA != current release candidate SHA
```

then classify the difference:

- already re-reviewed fix;
- merge-base sync only;
- generated metadata only;
- new behavioral code.

Any unreviewed behavioral code returns to Code Review.

## Prompt

```text
Begin Merge / Deploy for:

Feature: [FEATURE]
PR: [PR]
Reviewed SHA: [SHA]
Target: [ENVIRONMENT]

Verify:
1. formal review = APPROVED FOR MERGE;
2. current head SHA;
3. whether reviewed and current code match;
4. required CI;
5. release target;
6. unresolved blockers.

Return:
ELIGIBLE FOR RELEASE PIPELINE
or
BLOCKED

Do not merge or deploy yet.
```

---

# 8. Phase 1 — Verify Exact Release Diff

## Goal

Know exactly what production is about to receive.

Inspect:

```text
git merge-base
git log
git diff --name-status
git diff
```

Compare the correct range, such as:

```text
base...approved-branch
previous-release-tag..candidate
production-sha..candidate
```

Identify:

- app code;
- database migrations;
- environment/config references;
- secrets references;
- workers/jobs;
- scheduled tasks;
- email;
- payments;
- storage;
- auth;
- dependencies;
- AI/RAG;
- feature flags;
- monitoring;
- docs.

The **release diff** drives the rest of the workflow.

---

# 9. Phase 2 — Production Preflight From the Diff

## Goal

List everything production needs beyond merging the code.

Typical categories:

```text
Database
Environment Variables
Secrets
Feature Flags
Email
Payments
Storage
Queues / Workers
Schedulers / Cron
Webhooks
AI Provider
Vector Database
Redis / Cache
Observability
Analytics
Deployment Platform
Backfills
External Accounts
Permissions
QA Preconditions
Rollback Preconditions
```

Omit empty categories.

## Example

```text
new environment variable
    → configure production value

new migration
    → execute production migration

new queue job
    → ensure worker consumes queue

changed queue code
    → ensure worker gets new release

new webhook
    → configure provider callback

new AI model
    → verify production account access

new vector metadata
    → verify index compatibility

feature flag
    → define safe production default
```

## Template

```markdown
# Production Preflight — [Release]

## Database
- [ ] ...

## Environment / Secrets
- [ ] ...

## Workers / Schedulers
- [ ] ...

## External Services
- [ ] ...

## AI / RAG
- [ ] ...

## Feature Flags
- [ ] ...

## Observability
- [ ] ...

## QA Preconditions
- [ ] ...

## Rollback Preconditions
- [ ] ...
```

## Prompt

```text
Read the exact release diff and create production-preflight.md.

List only production actions justified by the diff.

Inspect for:
- migrations;
- config;
- env vars;
- secrets;
- email;
- payments;
- workers;
- schedules;
- storage;
- webhooks;
- AI providers/models;
- vector DB;
- Redis/cache;
- observability;
- feature flags;
- infrastructure;
- backfills;
- QA;
- rollback.

Do not deploy.
```

---

# 10. Phase 3 — Ship Gate

## Goal

Block anything that must not ship.

Check the release diff for:

### Secrets

- API keys;
- passwords;
- tokens;
- private keys;
- service-role secrets;
- webhook secrets.

Never print secret values in output.

### Debug code

Examples:

```text
dd()
dump()
var_dump()
print_r()
console.log()
debugger
pdb
temporary debug output
```

Use project context; legitimate production logging is not automatically a blocker.

### Temporary bypasses

Examples:

- disabled auth;
- disabled RLS;
- forced admin;
- fake provider;
- test user bypass;
- hardcoded localhost;
- validation bypass.

### Accidental artifacts

Examples:

- DB dump;
- exported user data;
- archive;
- large binary;
- screenshot with secrets;
- model file;
- generated build output prohibited by repository policy.

## Output

Only:

```text
PASS
```

or:

```text
BLOCK
```

with exact evidence.

## Prompt

```text
Run Ship Gate on the release candidate.

BLOCK only verified items that must not ship:
- secrets;
- debug code;
- temporary security bypass;
- local/test hardcoding;
- DB dumps;
- accidental binary/large files;
- repository-prohibited generated files.

Return:

PASS

or

BLOCK
- file:line/path — reason

Do not merge or deploy.
```

---

# 11. Phase 4 — Production Dependency Inventory

For every new or changed dependency/service determine:

```text
Already available in production?
Requires configuration?
Requires credential?
Requires network access?
Requires account capability?
Requires upgrade?
Can old and new app versions coexist?
```

Classify:

```text
READY
ACTION REQUIRED
BLOCKED
```

Do not create paid services or infrastructure without authorization.

---

# 12. Phase 5 — Environment and Secret Readiness

Inventory every changed/new runtime key.

For each record:

```text
Name
Required environment(s)
Secret? yes/no
Required? yes/no
Safe default
Production owner/source
Failure behavior if missing
```

Rules:

- `.env.example` contains placeholders only;
- production secrets must not be copied into docs;
- required config should fail predictably;
- optional config requires safe default;
- feature flags should default to safer behavior.

Never:

- echo production secrets;
- store secret values in release artifacts;
- copy production secrets into preview/local without explicit need.

---

# 13. Phase 6 — Database and Migration Readiness

## Goal

Make schema changes safe across deployment.

For every migration ask:

- backward compatible?
- old app can run with new schema?
- new app can run before migration?
- default/null behavior?
- backfill?
- constraint/index?
- long table lock?
- RLS impact?
- destructive?
- rollback safe?
- backup needed?

## Prefer expand → migrate → contract

For risky changes:

```text
Release A
  add compatible schema

Release B
  use/backfill new schema

Release C
  remove old schema
```

Avoid destructive one-step transitions where possible.

## Production migration rule

Production migration is a consequential write.

Before execution require:

- approved command;
- correct target;
- expected migration list;
- backup/forward-fix plan;
- one execution owner;
- monitoring.

Never blindly rerun a failed migration.

---

# 14. Phase 7 — Authentication, RLS, and Tenant Readiness

Required when tenant-owned data changes.

Verify production:

- auth configuration;
- redirect URLs;
- tenant ownership fields;
- RLS enabled;
- SELECT/INSERT/UPDATE/DELETE policies;
- storage policies;
- realtime policies;
- service-role use constrained;
- tenant data populated;
- preview/staging configuration not mixed with production.

Prepare controlled test accounts when permitted:

```text
Tenant A instructor/admin
Tenant A learner
Tenant B instructor/admin
Tenant B learner
```

---

# 15. Phase 8 — External Service Readiness

For each touched provider verify:

- correct production account;
- production credential;
- production endpoint;
- verified domain if needed;
- webhook;
- webhook secret;
- rate limit;
- idempotency;
- sandbox/live mode;
- monitoring;
- fallback/failure behavior.

Potential AI LMS services may include:

- payment provider;
- email provider;
- AI provider;
- vector database;
- Redis/cache;
- analytics;
- error tracking;
- object storage;
- CDN/DNS;
- deployment platform.

Only include services touched by the release.

---

# 16. Phase 9 — AI / RAG Production Readiness

Required when AI behavior changes.

## AI provider

Verify:

- production credential;
- production project/account;
- model access;
- quota;
- rate limits;
- budget;
- timeout;
- retry policy;
- observability.

## Model change

Verify:

- required capabilities;
- structured output compatibility;
- tool/function behavior if used;
- context constraints;
- latency;
- cost;
- evaluation results.

## RAG

Verify:

- production index exists;
- correct embedding dimension;
- metadata compatible;
- tenant filter compatible;
- course/module/lesson filters correct;
- ingestion/backfill complete;
- deletion lifecycle works;
- no cross-tenant fallback.

## Prompt/config version

If prompts live outside code, record the exact approved prompt/config version.

---

# 17. Phase 10 — Workers, Queues, Schedulers, Async Infrastructure

Inspect changed code for:

- background jobs;
- email queue;
- embedding jobs;
- document ingestion;
- scheduled cleanup;
- cron;
- webhook consumers;
- notifications.

Verify production:

- worker exists;
- queue name correct;
- concurrency appropriate;
- required env present;
- retry/dead-letter behavior;
- scheduler registered;
- new code reaches workers;
- old/new job payload compatibility.

Remember:

```text
new web deployment
≠
background worker automatically updated
```

unless the deployment architecture guarantees it.

---

# 18. Phase 11 — Observability Readiness

Define release-specific signals.

## Application

- errors;
- request failure;
- latency;
- job failure.

## Database

- migration success;
- DB errors;
- slow query indicators;
- connection pressure.

## AI

- provider failure;
- structured-output failure;
- latency;
- token usage;
- cost;
- negative feedback.

## RAG

- empty retrieval;
- retrieval error;
- indexing error;
- tenant filter failure.

## Product

- generation success;
- enrollment;
- assessment submission;
- payment;
- email delivery.

Record release metadata:

```text
release/version
commit SHA
deploy time
feature flag state
migration version
```

---

# 19. Phase 12 — Rollback Plan

Create rollback plan **before** deployment.

## Rollback types

- application rollback;
- feature flag disable;
- configuration rollback;
- migration rollback where safe;
- forward fix;
- traffic rollback.

## Template

```markdown
# Rollback Plan — [Release]

## Trigger Conditions
- ...

## Application
- Previous known-good version:
- Rollback action:
- Verification:

## Feature Flag
- Flag:
- Safe state:

## Database
- Migration:
- Rollback safe? yes/no
- Forward-fix:
- Backup:

## External Services
- ...

## Data Recovery
- ...

## Owner
- ...

## Verification
- ...
```

## Immediate rollback/block triggers

Examples:

- cross-tenant exposure;
- auth bypass;
- data corruption;
- grade corruption;
- payment corruption;
- severe outage;
- uncontrolled AI action;
- runaway AI/provider cost.

---

# 20. Phase 13 — CI / Protected Branch Gate

Required CI may include:

- formatting;
- lint;
- typecheck;
- static analysis;
- unit tests;
- integration tests;
- E2E;
- migration checks;
- secret scan;
- dependency audit;
- SAST;
- AI eval smoke suite;
- build;
- production preflight generation;
- QA checklist generation.

Rules:

- do not bypass required checks;
- do not repeatedly rerun flaky checks until one passes without diagnosis;
- workflow/config changes must themselves be reviewed;
- PR workflows should not receive unnecessary production secrets.

---

# 21. Phase 14 — Merge

Before merge confirm:

- `APPROVED FOR MERGE`;
- reviewed SHA is current;
- Ship Gate = PASS;
- required CI green;
- production preflight ready;
- rollback plan ready;
- deployment strategy chosen.

Re-read the exact head SHA and required checks with `gh`. Use the repository's approved
strategy:

- merge commit;
- squash;
- rebase merge.

After merge record:

```text
PR
merge SHA
target branch
timestamp
release candidate version
```

Do not merge a different behavioral SHA from the one reviewed.

Default GitHub CLI sequence:

```text
REVIEWED_SHA=$(gh pr view "$PR" --repo "$REPO" --json headRefOid --jq .headRefOid)
gh pr checks "$PR" --repo "$REPO" --required --watch --fail-fast
gh pr merge "$PR" --repo "$REPO" --squash --auto --delete-branch --match-head-commit "$REVIEWED_SHA"
gh pr view "$PR" --repo "$REPO" --json state,mergedAt,mergeCommit
```

Use another merge strategy only when repository policy selects it. Never pass
`--admin`. Concurrent feature development remains parallel, but the integration owner
merges PRs one at a time and requires remaining PRs to retest after base updates.

---

# 22. Phase 15 — Choose Deployment Strategy

Use the least risky strategy appropriate to the change.

## Standard

For low-risk, backward-compatible, easy-to-rollback changes.

## Dark deployment / feature flag

Recommended for:

- new user-facing feature;
- AI feature;
- uncertain UX;
- higher-risk code.

Pattern:

```text
merge
  ↓
deploy
  ↓
flag OFF
  ↓
production QA
  ↓
internal enablement
  ↓
limited rollout
  ↓
full activation
```

## Canary

Use where infrastructure supports limited traffic/user rollout.

## Blue / Green

Use for high-risk infrastructure/application releases where parallel versions are practical.

## Maintenance window

Use when a migration or operation cannot be safely performed online.

---

# 23. Phase 16 — Deploy Dark / Limited

Deployment and activation are separate.

A feature flag should gate:

- backend behavior where consequential;
- frontend visibility;
- asynchronous side effects where needed.

A UI-only flag is not enough for dangerous backend behavior.

New high-risk features should normally default:

```text
OFF
```

or:

```text
internal only
```

until production QA passes.

---

# 24. Phase 17 — Production Smoke Tests

Smoke tests answer:

> Is production fundamentally healthy after this deployment?

Examples:

- health page/endpoint;
- authentication;
- dashboard load;
- DB access;
- critical API;
- worker health;
- key provider connectivity if required.

Keep smoke tests short.

They are not a full regression suite.

---

# 25. Phase 18 — Feature-Specific Production QA

Generate QA from the actual release.

QA should:

- cover only changed surfaces;
- use plain-English actions;
- list prerequisites;
- include happy path;
- include important permission denial;
- include tenant isolation where relevant;
- include one important failure;
- include a plausible adjacent regression.

Example:

```markdown
# Production QA — AI Course Generation

## Preconditions
- [ ] Internal instructor test account has feature enabled.
- [ ] Approved source file exists.
- [ ] Internal learner exists.
- [ ] Second tenant test account exists.

## QA
- [ ] Instructor starts generation.
- [ ] Status moves through expected lifecycle.
- [ ] Generated course remains draft.
- [ ] Instructor can review generated modules and lessons.
- [ ] Learner cannot access the draft.
- [ ] Tenant B cannot access Tenant A course.
- [ ] Invalid source produces expected failure.
- [ ] Existing manual course creation still works.
```

---

# 26. Phase 19 — Production Security and Tenant Validation

Use controlled test data only.

Where applicable verify:

```text
Tenant A authorized access → works
Tenant A unauthorized role → denied
Tenant B ID through Tenant A account → denied
direct API request → denied
hidden UI route called directly → denied
cross-tenant storage path → denied
cross-tenant vector retrieval → denied
```

Do not probe real user private data.

Any evidence of cross-tenant exposure immediately stops rollout.

---

# 27. Phase 20 — AI / RAG Production QA

Required when AI behavior changed.

## Deterministic checks

Verify:

- correct provider/model;
- correct prompt/config version;
- correct tenant/course scope;
- structured output validation;
- citations resolve;
- error handling;
- usage/cost telemetry.

## Safe AI behavior checks

Use controlled internal data.

Verify:

- grounded answer;
- insufficient-evidence behavior;
- no cross-tenant source;
- safe prompt-injection test case;
- generated course remains draft where required;
- protected assessment answer is not exposed.

Do not use real sensitive learner data for exploratory QA.

---

# 28. Phase 21 — Controlled Activation

Recommended activation ladder:

```text
OFF
  ↓
internal developer/product users
  ↓
selected tenant(s)
  ↓
small percentage
  ↓
larger percentage
  ↓
100%
```

Not every feature needs every stage.

At each stage inspect:

- error rate;
- latency;
- queues;
- DB load;
- provider failures;
- AI cost;
- user behavior;
- support incidents;
- tenant/security signals.

Stop rollout when stop conditions occur.

---

# 29. Phase 22 — Post-Activation Monitoring

Monitor the release, not just the infrastructure.

## Technical

- exceptions;
- 5xx;
- latency;
- DB;
- workers;
- queue failures.

## AI

- provider errors;
- latency;
- token usage;
- cost;
- malformed output;
- negative user feedback;
- empty retrieval.

## Product

- generation completion;
- course publish;
- enrollment;
- assessment submission;
- payment outcome;
- email delivery.

Critical signals need:

- threshold;
- owner;
- action.

---

# 30. Phase 23 — Rollback Decision Gate

Evaluate:

- user/data safety?
- tenant isolation?
- data corruption?
- critical user flow?
- failure rate?
- feature flag can contain issue?
- forward fix safer?
- migration rollback unsafe?

Decision options:

```text
CONTINUE
PAUSE ROLLOUT
DISABLE FEATURE
ROLL BACK APPLICATION
FORWARD FIX
INCIDENT RESPONSE
```

Immediate rollback/disable conditions include:

- cross-tenant leak;
- auth bypass;
- data corruption;
- payment/grade corruption;
- critical outage;
- uncontrollable AI action;
- runaway AI cost.

---

# 31. Phase 24 — Final Production Verification

Confirm:

- correct SHA live;
- application healthy;
- migration complete;
- workers healthy;
- environment/config correct;
- intended feature flag state;
- smoke tests pass;
- production QA pass;
- tenant/security QA pass;
- AI/RAG QA pass where relevant;
- monitoring normal;
- no rollback trigger.

Final successful state:

```text
DEPLOYED AND VERIFIED
```

If intentionally deployed but inactive:

```text
DEPLOYED DARK
```

---

# 32. Phase 25 — Technical Changelog

The changelog source of truth is:

```text
merged commits
merged PRs
release tags
```

Do not invent changes.

Possible categories:

```text
Features
Fixes
Security
Performance
Data / Migrations
Infrastructure
Developer Experience
Chores
```

Use only relevant categories.

Call out breaking changes and migration requirements.

---

# 33. Phase 26 — User-Facing Release Notes

Release notes are for users.

Example:

Technical:

```text
Added asynchronous tenant-scoped course generation lifecycle.
```

User-facing:

```text
Instructors can now generate a draft course from approved learning material and
review it before publishing.
```

Rules:

- plain English;
- user value;
- no internal jargon;
- omit internal refactors;
- do not claim dark features are generally available;
- do not invent.

---

# 34. Phase 27 — Documentation Sync

Update only affected docs.

Examples:

- instructor guide;
- learner guide;
- admin setup;
- environment/config documentation;
- runbook;
- API docs;
- architecture docs.

A docs agent should:

- only edit documentation;
- use release diff as evidence;
- update only changed feature pages;
- add a page only for genuinely new shipped behavior;
- avoid rewriting unrelated docs.

---

# 35. Phase 28 — Deployment Record

Template:

```markdown
# Deployment Record — [Release]

## Status
DEPLOYED AND VERIFIED

## Release
- Version:
- PR:
- Merge SHA:
- Deployment SHA:
- Environment:
- Started:
- Completed:

## Strategy
- Standard / Dark / Canary / Blue-Green / Maintenance

## Feature Flags
- Name:
- State:
- Rollout:

## Database
- Migrations:
- Result:
- Backfill:
- Result:

## Configuration
- Added/changed keys:
- Secret values: NOT RECORDED

## External Services
- ...

## Production QA
- Smoke: PASS
- Feature QA: PASS
- Tenant/security QA: PASS / N/A
- AI/RAG QA: PASS / N/A

## Observability
- Errors:
- Latency:
- Queue:
- AI usage:
- Notes:

## Rollback
- Previous known-good version:
- Required? no

## Known Issues
- None / ...

## Release Notes
- ...

## Documentation
- Updated:
```

Never record secret values.

---

# 36. Phase 29 — Production Verification Gate

A release is complete only when the gate passes.

## Code / review

- [ ] Formal Code Review = `APPROVED FOR MERGE`.
- [ ] Reviewed SHA matches release candidate.
- [ ] No unreviewed behavioral commits.
- [ ] Ship Gate = PASS.

## CI

- [ ] tests pass;
- [ ] lint/type/static checks pass;
- [ ] build passes;
- [ ] security/dependency checks pass;
- [ ] required AI evals pass;
- [ ] no unexplained required-check failure.

## Production preflight

- [ ] preflight generated from exact release diff;
- [ ] env vars ready;
- [ ] secrets ready;
- [ ] external services ready;
- [ ] workers/schedulers ready;
- [ ] feature flags ready;
- [ ] observability ready.

## Database

Where applicable:

- [ ] migration reviewed;
- [ ] compatibility understood;
- [ ] backfill plan ready;
- [ ] RLS/policies ready;
- [ ] rollback/forward-fix understood;
- [ ] production migration succeeded.

## Tenant / security

Where applicable:

- [ ] auth config correct;
- [ ] RLS enabled;
- [ ] policies correct;
- [ ] service-role usage constrained;
- [ ] cross-tenant production smoke test passed;
- [ ] storage/vector isolation passed.

## AI / RAG

Where applicable:

- [ ] production provider/model ready;
- [ ] prompt/config version correct;
- [ ] vector/index compatible;
- [ ] tenant/course filter correct;
- [ ] AI production case passed;
- [ ] missing-evidence behavior verified;
- [ ] structured output verified;
- [ ] cost/usage monitoring active.

## Deployment

- [ ] correct SHA deployed;
- [ ] deployment healthy;
- [ ] workers healthy;
- [ ] configuration loaded;
- [ ] feature flag correct.

## QA

- [ ] smoke passed;
- [ ] feature QA passed;
- [ ] tenant/security QA passed where applicable;
- [ ] AI/RAG QA passed where applicable.

## Monitoring

- [ ] errors normal;
- [ ] latency acceptable;
- [ ] queue normal;
- [ ] AI usage/cost normal where relevant;
- [ ] no security alert;
- [ ] rollout state documented.

## Rollback

- [ ] rollback plan exists;
- [ ] known-good version recorded;
- [ ] safe flag state known;
- [ ] migration rollback/forward-fix understood;
- [ ] no active rollback trigger.

## Release documentation

- [ ] deployment record complete;
- [ ] changelog updated where applicable;
- [ ] release notes accurate where applicable;
- [ ] affected docs synchronized.

Gate result:

```text
DEPLOYED AND VERIFIED
```

or:

```text
DEPLOYED DARK
```

or:

```text
ROLLED BACK
```

or:

```text
BLOCKED
```

---

# 37. Master Codex Prompt — Merge & Deploy

```text
You are responsible for the MERGE / DEPLOY workflow for an AI-enabled LMS.

You may only begin with a release candidate whose formal Code Review verdict is:

APPROVED FOR MERGE

Final states:

DEPLOYED AND VERIFIED
DEPLOYED DARK
ROLLED BACK
BLOCKED

==================================================
TARGET
==================================================

Feature / Release:
[FEATURE / RELEASE]

PR:
[PR]

Reviewed SHA:
[SHA]

Base:
[BASE]

Target Environment:
[PRODUCTION / STAGING]

==================================================
AUTHORITY
==================================================

You may safely:
- inspect diffs;
- inspect CI;
- generate production preflight;
- generate ship-gate findings;
- prepare migration/config commands;
- prepare QA;
- prepare rollback;
- prepare changelog/release notes/docs.

Do not assume permission to:
- merge protected branches;
- deploy production;
- run production migrations;
- change production env vars;
- restart services;
- enable a flag globally;
- alter DNS/IAM;
- modify production data.

Use existing approved automation when repository policy explicitly authorizes it.

Never bypass failing required checks.

==================================================
PHASE 0 — ELIGIBILITY
==================================================

Verify:
- Code Review = APPROVED FOR MERGE;
- reviewed SHA;
- current SHA;
- no unreviewed behavioral changes;
- target environment.

If mismatch requires review:
BLOCKED.

==================================================
PHASE 1 — RELEASE DIFF
==================================================

Inspect the exact production candidate.

Identify:
- app code;
- migrations;
- env/config;
- secrets references;
- workers;
- schedulers;
- storage;
- integrations;
- dependencies;
- AI/RAG;
- feature flags;
- observability.

==================================================
PHASE 2 — PRODUCTION PREFLIGHT
==================================================

Create production-preflight.md from the diff.

Include only requirements justified by the release.

Possible categories:
Database
Environment
Secrets
Workers
Schedulers
Email
Payments
Storage
Webhooks
AI
Vector DB
Redis
Observability
Feature Flags
Infrastructure
Backfills
QA
Rollback

==================================================
PHASE 3 — SHIP GATE
==================================================

Block verified:
- secrets;
- debug code;
- temporary auth/RLS bypass;
- local/test hardcoding;
- dumps;
- accidental binary/large files;
- prohibited generated artifacts.

Return PASS or BLOCK.

BLOCK stops release.

==================================================
PHASE 4 — PRODUCTION DEPENDENCIES
==================================================

For every changed dependency/service determine:
- exists?
- config?
- credential?
- account capability?
- network?
- runtime compatibility?
- upgrade?

Do not create paid resources without authorization.

==================================================
PHASE 5 — ENV / SECRETS
==================================================

Inventory required production configuration.

Never print secret values.

Confirm:
- required environment;
- safe defaults;
- production value owner/source;
- failure behavior if missing.

==================================================
PHASE 6 — DATABASE
==================================================

Review migrations for:
- backward/forward compatibility;
- backfill;
- constraints;
- indexes;
- RLS;
- lock/runtime risk;
- destructive behavior;
- rollback/forward-fix;
- execution plan.

Do not run production migrations without authorization.

==================================================
PHASE 7 — TENANCY / RLS
==================================================

If tenant data is affected verify:
- RLS;
- policies;
- storage;
- realtime;
- service-role boundaries;
- vector filters;
- background tenant context.

==================================================
PHASE 8 — EXTERNAL SERVICES
==================================================

Verify every touched provider:
- production account;
- credential;
- endpoint;
- webhook/domain;
- rate limit;
- idempotency;
- monitoring.

==================================================
PHASE 9 — AI / RAG
==================================================

For AI changes verify:
- provider/model access;
- quota/budget;
- prompt/config version;
- vector index compatibility;
- embedding compatibility;
- tenant/course filters;
- ingestion/backfill;
- AI observability;
- eval evidence.

==================================================
PHASE 10 — ASYNC
==================================================

Verify:
- worker;
- queue;
- scheduler;
- retry;
- concurrency;
- dead-letter/failure handling;
- deployment of worker code;
- old/new payload compatibility.

==================================================
PHASE 11 — OBSERVABILITY
==================================================

Define release-specific signals:
- app errors;
- latency;
- DB;
- queue;
- AI errors/cost;
- retrieval;
- product completion.

Record release SHA/time/flag state.

==================================================
PHASE 12 — ROLLBACK
==================================================

Create rollback-plan.md before deployment.

Include:
- triggers;
- previous known-good version;
- application rollback;
- feature flag safe state;
- database rollback vs forward-fix;
- external service rollback;
- verification.

==================================================
PHASE 13 — CI / MERGE GATE
==================================================

Require:
- Ship Gate PASS;
- tests;
- lint/type;
- build;
- security;
- dependency checks;
- migration checks;
- AI evals where required.

Do not bypass required checks.

==================================================
PHASE 14 — MERGE
==================================================

If authorized:
- merge using repository policy;
- record merge SHA.

Otherwise:
- report MERGE READY and stop before the write.

Never merge a behavioral SHA not covered by review.

==================================================
PHASE 15 — DEPLOY STRATEGY
==================================================

Use approved strategy:

STANDARD
DARK FEATURE FLAG
CANARY
BLUE/GREEN
MAINTENANCE WINDOW

Prefer dark/limited activation for higher-risk AI or user-facing features.

==================================================
PHASE 16 — DEPLOY
==================================================

If authorized, deploy exact approved merge/release SHA.

Record:
- SHA;
- environment;
- time;
- flag state.

Keep high-risk feature OFF/internal initially when planned.

==================================================
PHASE 17 — SMOKE
==================================================

Verify:
- app health;
- auth;
- DB;
- critical route;
- worker;
- required integration.

Stop on critical failure.

==================================================
PHASE 18 — FEATURE QA
==================================================

Generate and execute/prepare focused production QA from the release diff.

Include:
- changed happy path;
- permission denial;
- tenant isolation;
- important failure;
- adjacent regression.

==================================================
PHASE 19 — SECURITY
==================================================

For tenant-sensitive changes use controlled accounts to verify:
- unauthorized access denied;
- cross-tenant ID denied;
- direct API denied;
- storage denied;
- vector retrieval denied.

Cross-tenant exposure stops rollout immediately.

==================================================
PHASE 20 — AI / RAG QA
==================================================

For AI changes verify:
- correct model/provider;
- correct tenant/course context;
- structured output;
- citations;
- missing-evidence behavior;
- safe prompt-injection scenario;
- no cross-tenant source;
- no prohibited assessment answer leakage.

==================================================
PHASE 21 — ACTIVATE
==================================================

When flag/canary exists:

OFF
→ internal
→ selected tenant(s)
→ small percentage
→ larger percentage
→ intended full state

Inspect signals at each stage.

==================================================
PHASE 22 — MONITOR
==================================================

Inspect:
- errors;
- latency;
- DB;
- queues;
- provider errors;
- AI cost/usage;
- retrieval;
- product completion.

==================================================
PHASE 23 — ROLLBACK GATE
==================================================

Choose:

CONTINUE
PAUSE ROLLOUT
DISABLE FEATURE
ROLLBACK APPLICATION
FORWARD FIX
INCIDENT RESPONSE

Immediate stop triggers:
- tenant leak;
- auth bypass;
- data corruption;
- payment/grade corruption;
- critical outage;
- uncontrollable AI action;
- runaway AI cost.

==================================================
PHASE 24 — FINAL VERIFY
==================================================

Confirm:
- correct SHA;
- migrations complete;
- workers healthy;
- config correct;
- QA passed;
- security/tenant QA passed;
- AI/RAG QA passed;
- monitoring normal.

Return:
DEPLOYED AND VERIFIED

or if intentionally inactive:
DEPLOYED DARK

==================================================
PHASE 25 — CHANGELOG
==================================================

Generate technical changelog from merged commits/PRs only.

Never invent.

==================================================
PHASE 26 — RELEASE NOTES
==================================================

Generate user-facing notes from shipped behavior only.

Do not describe dark functionality as generally available.

==================================================
PHASE 27 — DOCS
==================================================

Update only documentation affected by shipped behavior.

==================================================
PHASE 28 — DEPLOYMENT RECORD
==================================================

Record:
- version;
- PR;
- merge SHA;
- deployment SHA;
- environment;
- strategy;
- flag state;
- migration result;
- QA;
- monitoring;
- rollback status.

Never record secret values.

==================================================
FINAL GATE
==================================================

DEPLOYED AND VERIFIED
only when all production verification gates pass.

DEPLOYED DARK
when the intended state is deployed but inactive/limited.

ROLLED BACK
when known-good production state has been restored and verified.

BLOCKED
when release safety evidence or required authorization is missing.
```

---

# 38. Recommended Codex Skills

The guarded merge portion is packaged as `.agents/skills/merge-ai-lms-pr`. The other
entries below are possible future single-purpose skills and have not been scaffolded.

```text
.agents/
└── skills/
    ├── production-preflight/
    ├── ship-gate/
    ├── qa-checklist/
    ├── changelog/
    ├── release-notes/
    └── docs-sync/
```

Each should remain single-purpose.

---

# 39. Skill — `production-preflight`

Example frontmatter:

```yaml
---
name: production-preflight
description: >
  Read the exact release diff and generate a categorized checklist of everything
  production needs beyond merging the code: migrations, configuration, secrets,
  workers, schedules, providers, AI/RAG infrastructure, feature flags,
  observability, QA prerequisites, and rollback prerequisites.
---
```

---

# 40. Skill — `ship-gate`

```yaml
---
name: ship-gate
description: >
  Scan the staged/release diff for artifacts that must not ship, including
  secrets, debug code, temporary security bypasses, local/test hardcoding,
  dumps, accidental binary/large files, and repository-prohibited generated
  artifacts. Return PASS or BLOCK.
---
```

---

# 41. Skill — `qa-checklist`

```yaml
---
name: qa-checklist
description: >
  Read the approved release diff and produce a short production QA checklist
  containing only the user-visible and high-risk behavior changed by the
  release, including permissions, tenancy, failure states, and AI/RAG checks
  where applicable.
---
```

---

# 42. Recommended AGENTS.md Release Rules

```markdown
## Merge / Deploy

Only enter Merge / Deploy after formal Code Review returns APPROVED FOR MERGE.

Before production:
1. Verify the reviewed SHA.
2. Generate production preflight from the exact release diff.
3. Run Ship Gate.
4. Require protected CI.
5. Verify environment/secrets.
6. Verify migrations and RLS.
7. Verify workers/schedulers/providers.
8. Verify AI/RAG dependencies when relevant.
9. Create rollback plan.
10. Prefer dark/limited rollout for high-risk AI or user-facing features.
11. Run production smoke tests.
12. Run focused feature QA.
13. Validate tenant isolation where relevant.
14. Validate AI/RAG behavior where relevant.
15. Monitor before widening rollout.
16. Record deployment SHA and feature-flag state.

Never bypass required CI or production gates.
Never record secret values.
```

---

# 43. Ship Gate as a Pre-Push Guardrail

A practical local flow:

```text
commit
   ↓
continue local work
   ↓
pre-push
   ↓
ship-gate
   ↓
PASS → push
BLOCK → stop
```

Project-local hook rules:

- deterministic;
- clear PASS/BLOCK;
- no destructive action;
- no production dependency;
- block only verified unsafe artifacts.

---

# 44. CI Pipeline Pattern

PR:

```text
PR opened/updated
        ↓
Tests / Lint / Type / Build
        ↓
Security / Dependency Checks
        ↓
AI Evals if relevant
        ↓
Production Preflight
        ↓
QA Checklist
        ↓
Formal Code Review
```

After merge:

```text
approved target branch
  ↓
build
  ↓
deploy
  ↓
migration gate
  ↓
dark/limited release
  ↓
production QA
  ↓
activation
  ↓
monitor
```

---

# 45. Least-Privilege CI

Where possible separate credentials:

```text
PR workflow credentials
release workflow credentials
production deployment credentials
migration credentials
```

PR workflows should not normally receive broad production write secrets.

---

# 46. Feature Flags

Feature flags are release controls, not substitutes for correctness.

A flag should have:

- safe default;
- backend enforcement where consequential;
- frontend visibility control where relevant;
- known owner;
- observable state;
- removal plan after rollout stabilizes.

Stale flags should later be removed in a separately reviewed cleanup.

---

# 47. AI LMS Release Checks

## AI Course Generation

Verify:

- upload;
- parsing;
- ingestion;
- embeddings/index;
- model call;
- structured output;
- draft state;
- review/publish control;
- retry;
- cost.

## AI Companion / RAG

Verify:

- tenant/course scope;
- lesson scope where required;
- citations;
- insufficient evidence;
- assessment answer protection;
- provider failure;
- usage limits.

## Assessments

High risk.

Verify:

- attempt rules;
- grade rules;
- auditability;
- duplicate submission;
- rollback/forward-fix if data model changes.

## Payments

Always high risk.

Verify:

- live credentials;
- webhook;
- signature verification;
- idempotency;
- amount/currency;
- duplicate callback;
- reconciliation.

## Email

Verify:

- production provider;
- domain;
- sender;
- worker;
- retries;
- controlled test recipient.

---

# 48. Common Stack Production Checklist

Use only services actually present.

## Supabase

- migrations;
- RLS;
- auth redirects;
- service role;
- storage policies;
- realtime policies;
- extensions;
- DB limits.

## Vercel

- production environment values;
- build;
- runtime;
- production deployment;
- preview/production differences.

## PayMongo

- test/live credentials;
- webhook;
- signature;
- idempotency;
- amount/currency.

## Resend

- production key;
- domain;
- sender;
- worker/queue;
- delivery failure handling.

## Cloudflare

When changed:

- DNS;
- proxy;
- cache;
- redirects;
- security rules.

## PostHog

- production project;
- event names;
- privacy;
- no sensitive content.

## Sentry

- DSN;
- environment/release;
- source maps where relevant;
- data scrubbing;
- release annotation.

## Upstash / Redis

- endpoint/token;
- environment isolation;
- TTL;
- rate limit/cache behavior.

## Pinecone / Vector Database

- index;
- dimension;
- metadata;
- tenant filter;
- ingestion/backfill;
- deletion lifecycle.

---

# 49. Changelog Automation

A release workflow may:

1. identify previous release tag;
2. collect commits/PRs since tag;
3. classify them;
4. write/update technical changelog;
5. attach changelog to release.

Source rule:

```text
only merged release evidence
```

Never include planned/unmerged work.

---

# 50. Release Notes Automation

Use the same release evidence.

Skip:

- refactors;
- internal test changes;
- CI-only changes;
- dependency updates with no user impact.

Do not overstate rollout availability.

---

# 51. Docs Automation

First deliberate bootstrap:

```text
no docs
  ↓
inspect shipped application
  ↓
create docs index + feature pages
```

Later:

```text
release diff
  ↓
update only affected docs
```

Never rewrite unrelated docs automatically.

---

# 52. Deployment Failure Protocol

If deployment fails:

1. stop activation;
2. capture exact error;
3. determine whether any new version is partially live;
4. restore known-good version when necessary;
5. verify health;
6. classify cause;
7. return to:
   - Implement for code defect;
   - Plan Feature for architecture defect;
   - Merge/Deploy for environment defect.

Do not repeatedly deploy random fixes.

---

# 53. Migration Failure Protocol

If production migration fails:

1. stop dependent rollout;
2. inspect partial state;
3. do not blindly rerun;
4. understand transaction behavior;
5. protect data;
6. apply approved rollback or forward fix;
7. verify schema;
8. verify application compatibility;
9. document outcome.

---

# 54. AI Cost Spike Protocol

If AI usage/cost spikes unexpectedly:

1. pause rollout;
2. disable feature flag if possible;
3. inspect request volume;
4. inspect retry loop;
5. inspect prompt/context size;
6. inspect duplicate jobs;
7. inspect model choice;
8. verify limits;
9. correct before reactivation.

Treat uncontrollable cost growth as a release blocker.

---

# 55. Cross-Tenant Incident Protocol

If production validation suggests cross-tenant exposure:

```text
STOP ROLLOUT
DISABLE FEATURE
PRESERVE EVIDENCE
RETURN TO SECURITY REVIEW / INCIDENT PROCESS
```

Do not continue rollout to gather more examples.

---

# 56. Rollback Verification

Rollback is not complete when the old version is merely redeployed.

Verify:

- correct SHA;
- application health;
- database compatibility;
- workers;
- feature flag;
- errors;
- data integrity;
- tenant isolation.

Then state:

```text
ROLLED BACK
```

---

# 57. Hotfix Path

Urgent production fix:

```text
incident
  ↓
minimal fix
  ↓
targeted tests
  ↓
fast independent review
  ↓
ship gate
  ↓
CI
  ↓
deploy
  ↓
smoke
  ↓
monitor
```

Urgency does not remove security or tenancy requirements.

---

# 58. Release Checklist

```markdown
# Release Checklist — [Release]

## Approval
- [ ] Code Review = APPROVED FOR MERGE
- [ ] Reviewed SHA matches candidate

## Ship Gate
- [ ] PASS

## CI
- [ ] Tests
- [ ] Lint
- [ ] Typecheck
- [ ] Static analysis
- [ ] Build
- [ ] Security
- [ ] Dependency audit
- [ ] AI evals if required

## Production Preflight
- [ ] Database
- [ ] Environment
- [ ] Secrets
- [ ] Workers
- [ ] Schedulers
- [ ] External services
- [ ] Feature flags
- [ ] AI / RAG
- [ ] Observability

## Rollback
- [ ] Plan ready
- [ ] Known-good version recorded

## Merge
- [ ] Merged
- [ ] Merge SHA recorded

## Deploy
- [ ] Correct SHA
- [ ] Healthy
- [ ] Migration succeeded
- [ ] Workers healthy
- [ ] Flag safe

## QA
- [ ] Smoke
- [ ] Feature QA
- [ ] Tenant/security QA
- [ ] AI/RAG QA

## Activation
- [ ] Internal
- [ ] Limited
- [ ] Intended full state

## Monitoring
- [ ] Errors normal
- [ ] Latency normal
- [ ] Queues normal
- [ ] AI usage normal
- [ ] Product flow normal

## Release Documentation
- [ ] Deployment record
- [ ] Changelog
- [ ] Release notes
- [ ] Docs

## Final
- [ ] DEPLOYED AND VERIFIED
```

---

# 59. Merge-Only Codex Prompt

```text
Prepare the approved PR for merge only.

Require:
- Code Review = APPROVED FOR MERGE;
- current SHA matches reviewed SHA;
- Ship Gate PASS;
- CI green;
- production preflight exists;
- rollback plan exists;
- deployment strategy documented.

Do not deploy.

If merge authorization exists, merge using repository policy and record SHA.

Otherwise stop at MERGE READY.

Return:
MERGED
or
BLOCKED
```

---

# 60. Deploy-Only Codex Prompt

```text
Deploy:

[SHA / VERSION]

to:

[ENVIRONMENT]

Before deployment verify:
- production preflight;
- migration readiness;
- env/secrets;
- providers;
- workers;
- AI/RAG dependencies;
- observability;
- rollback.

Use the approved deployment strategy.

After deployment:
- smoke;
- feature QA;
- tenant/security QA;
- AI/RAG QA;
- monitor;
- activate;
- verify.

Return:
DEPLOYED AND VERIFIED
DEPLOYED DARK
ROLLED BACK
BLOCKED
```

---

# 61. Production Preflight Prompt

```text
Generate production-preflight.md from the exact release diff.

Only include production actions supported by the release.

Potential categories:

Database
Environment / Secrets
Workers
Schedulers
Email
Payments
Storage
Webhooks
AI Provider
Vector DB
Redis / Cache
Observability
Feature Flags
Infrastructure
Backfills
QA Preconditions
Rollback Preconditions

Do not include secret values.
```

---

# 62. Production QA Prompt

```text
Create a short production QA checklist from:

- feature spec;
- implementation plan;
- release diff;
- code review;
- production preflight.

Include only changed/high-risk behavior.

Add:
- prerequisites;
- happy path;
- permission denial;
- tenant isolation if relevant;
- important failure;
- adjacent regression;
- AI/RAG behavior if relevant.

Use plain-English checkboxes.
```

---

# 63. Rollback Prompt

```text
Create rollback-plan.md before deployment.

Include:

- trigger conditions;
- previous known-good version;
- application rollback;
- feature flag safe state;
- DB rollback vs forward-fix;
- data recovery;
- worker compatibility;
- external service reversal;
- verification;
- owner.

Do not assume schema rollback is safe.
Do not perform rollback.
```

---

# 64. Changelog Prompt

```text
Generate technical changelog for this release.

Use only merged commits/PRs since previous release.

Use only relevant categories:

Features
Fixes
Security
Performance
Data / Migrations
Infrastructure
Developer Experience
Chores

Call out breaking changes and migration requirements.

Never invent.
```

---

# 65. Release Notes Prompt

```text
Generate user-facing release notes from shipped behavior only.

Rules:
- plain English;
- user value;
- no implementation jargon;
- omit internal-only changes;
- do not describe dark/limited features as generally available;
- do not invent;
- do not describe removals as additions.
```

---

# 66. Docs Sync Prompt

```text
Update documentation for this release.

Use the release diff as evidence.

Rules:
- update only affected pages;
- create a page only for a genuinely new shipped feature;
- do not rewrite unrelated docs;
- preserve current documentation style;
- do not document dark/unavailable behavior as generally available;
- do not invent.
```

---

# 67. Definition of Done

Merge / Deploy is complete only when:

- [ ] Formal Code Review approved the exact release candidate.
- [ ] Production preflight was generated from the actual diff.
- [ ] Ship Gate passed.
- [ ] Required CI passed.
- [ ] Environment values are ready.
- [ ] Secrets are ready and protected.
- [ ] Database migration plan is ready.
- [ ] RLS/tenant readiness is verified where applicable.
- [ ] External providers are ready.
- [ ] AI/RAG production dependencies are ready where applicable.
- [ ] Workers/schedulers are ready.
- [ ] Observability is ready.
- [ ] Rollback plan exists.
- [ ] Exact reviewed code was merged.
- [ ] Exact intended SHA was deployed.
- [ ] Migrations succeeded where applicable.
- [ ] Application is healthy.
- [ ] Workers are healthy.
- [ ] Feature flag state is intended.
- [ ] Smoke tests passed.
- [ ] Production QA passed.
- [ ] Tenant/security QA passed where applicable.
- [ ] AI/RAG production QA passed where applicable.
- [ ] Controlled activation reached intended level.
- [ ] Monitoring is normal.
- [ ] No rollback trigger remains.
- [ ] Deployment record is complete.
- [ ] Changelog is accurate where applicable.
- [ ] Release notes are accurate where applicable.
- [ ] Affected docs are synchronized.
- [ ] Final release state is explicit.

Successful general release:

```text
DEPLOYED AND VERIFIED
```

Valid dark release:

```text
DEPLOYED DARK
```

Safe recovery:

```text
ROLLED BACK
```

---

# 68. How This Builds on the Supplied Merging and Deploying Workflow

The supplied workflow contributes these core release ideas:

- production needs more than reviewed code;
- generate production preflight from the actual diff;
- use a Ship Gate to block unsafe artifacts;
- move checks into CI;
- separate merge from activation with feature flags;
- deploy risky features dark;
- generate focused live QA from the change;
- generate changelogs from real commits;
- generate release notes for users from the same evidence;
- keep documentation synchronized with changed behavior.

This Codex workflow preserves those ideas and adds:

- reviewed-SHA integrity;
- explicit production authority boundaries;
- schema compatibility gates;
- RLS / multi-tenant production verification;
- external-provider readiness;
- AI/RAG production readiness;
- async worker readiness;
- observability;
- rollback planning;
- controlled rollout stages;
- production security smoke tests;
- AI cost controls;
- cross-tenant incident handling;
- deployment records;
- explicit production terminal states.

---

# 69. Final End-to-End Workflow

```text
PLAN PRODUCT
    ↓
Product Planning Gate
    ↓
PLAN FEATURE
    ↓
Feature Planning Gate
    ↓
READY FOR IMPLEMENTATION
    ↓
IMPLEMENT
    ↓
Implementation Gate
    ↓
READY FOR CODE REVIEW
    ↓
CODE REVIEW
    ↓
Code Review Gate
    ↓
APPROVED FOR MERGE
    ↓
MERGE / DEPLOY
    ↓
Production Preflight
    ↓
Ship Gate
    ↓
CI / Merge
    ↓
Production Readiness
    ↓
Deploy Dark / Limited
    ↓
Production QA
    ↓
Controlled Activation
    ↓
Monitoring
    ↓
Production Verification Gate
    ↓
DEPLOYED AND VERIFIED
```

---

# 70. Recommended Repository Workflow Structure

```text
docs/
├── product/
│   ├── spec.md
│   ├── features.md
│   └── decisions.md
│
├── features/
│   └── [NN]-[feature]/
│       ├── feature.md
│       ├── technical-decisions.md
│       ├── implementation-plan.md
│       ├── test-plan.md
│       ├── implementation-status.md
│       ├── code-review.md
│       ├── production-preflight.md
│       ├── rollback-plan.md
│       ├── production-qa.md
│       └── deployment-record.md
│
└── releases/
    └── [version].md

.agents/
└── skills/
    ├── plan-product/
    ├── plan-feature/
    ├── implement-feature-step/
    ├── code-review/
    ├── production-preflight/
    ├── ship-gate/
    ├── qa-checklist/
    ├── changelog/
    ├── release-notes/
    └── docs-sync/

AGENTS.md
REVIEW_GUIDE.md
CHANGELOG.md
```

---

# 71. Final Workflow Contract

Each workflow owns a different decision boundary:

```text
Plan Product
  → what the product is

Plan Feature
  → how one feature is constrained and planned

Implement
  → how one approved step is coded

Code Review
  → whether the implementation is correct and safe

Merge / Deploy
  → whether production is ready, how the change is released, verified, and rolled back
```

No workflow should silently absorb the authority of another.

That separation is the main guardrail that allows an AI-assisted LMS engineering
workflow to move quickly without turning production release into an uncontrolled
agent action.

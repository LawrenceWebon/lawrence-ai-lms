# Debugging & Performance — AI LMS / Codex Workflow

> **Purpose:** Provide a repeatable, evidence-first workflow for debugging defects and improving performance in the AI LMS without guessing, hiding symptoms, weakening tests, breaking tenant isolation, or optimizing the wrong layer.
>
> **Workflow position:** This is a **cross-cutting workflow**. It can be entered from development, Code Review, production monitoring, support reports, or post-deployment incidents.
>
> **Core rule:**
> **Reproduce → Measure → Explain → Fix → Prove → Prevent**
>
> For performance:
>
> **Baseline → Measure → Rank → Fix One Bottleneck → Re-measure → Guard Against Regression**
>
> **Primary terminal states:**
>
> - `BUG FIX VERIFIED`
> - `PERFORMANCE FIX VERIFIED`
> - `ROOT CAUSE NOT YET PROVEN`
> - `BLOCKED`
> - `RETURN TO PLAN FEATURE`
> - `READY FOR CODE REVIEW`

---

# 1. Alignment With the AI LMS Project

This workflow is designed for the AI LMS architecture documented for the
`LawrenceWebon/lawrence-ai-lms` project.

The project documentation describes a system built around:

```text
Frontend
- Next.js App Router
- TypeScript
- Vercel

API / Domain
- FastAPI API surface
- Django domain models / migrations / admin

Data
- Supabase PostgreSQL
- Supabase Auth
- Supabase Storage
- PostgreSQL RLS

Async
- containerized Python workers
- Upstash Redis / QStash where applicable

AI / RAG
- AI model provider(s)
- Pinecone vector database
- document parsing / ingestion
- embeddings
- course generation
- grounded AI chat / learning companion
- citations
- AI evaluations

External
- PayMongo
- Resend
- Cloudflare
- PostHog
- Sentry

Testing
- pytest
- Playwright
- repository lint / type / static-analysis checks
```

## Important repository verification rule

Before executing any command, Codex must verify the **current repository**
instead of assuming these exact names or scripts still exist.

Read:

```text
AGENTS.md
package.json and package-lock.json
backend/pyproject.toml and backend/uv.lock
compose.yaml
.github/workflows/
apps/
packages/
contracts/
database/
scripts/
docs/
```

Confirm paths with `rg --files` and use the actual repository commands. A generic path
or provider example later in this guide is not evidence that the repository contains
or enables it.

Do not invent scripts such as:

```text
npm run test
pytest
supabase start
```

until the repository confirms them.

## Current repository capability boundary

This guide is cross-cutting procedure, not product-scope authority. The focused MVP is
the private, tenant-isolated PDF-to-course journey in `docs/product/spec.md` and
`docs/product/features.md`. Commerce, payments, AI companion/RAG, broad analytics,
and unapproved external providers remain deferred unless a later owner decision
enables them.

Accordingly, later PayMongo, Pinecone, RAG, chat, provider, and production-monitoring
examples are conditional lanes only. They describe how to investigate an already
approved capability; they do not authorize schema, routes, dependencies, credentials,
provider calls, production access, or real customer data. Follow the
[repository workflow authority](README.md) for issue, branch, worktree, review, merge,
and cleanup requirements.

---

# 2. Why Debugging Has Its Own Workflow

A common AI-agent failure mode is:

```text
bug report
   ↓
read nearby code
   ↓
guess likely cause
   ↓
change code
   ↓
tests green
   ↓
declare fixed
```

That is unreliable.

A green suite cannot prove a bug was fixed if the bug was never reproduced.

The correct sequence is:

```text
bug report
   ↓
reproduce the exact behavior
   ↓
encode reproduction in a failing test when possible
   ↓
trace actual root cause
   ↓
explain root cause with repository evidence
   ↓
propose smallest cause-level fix
   ↓
implement
   ↓
targeted test GREEN
   ↓
regression suite
   ↓
prevent recurrence
```

---

# 3. Why Performance Has Its Own Workflow

Another common failure mode is:

```text
page feels slow
   ↓
agent reads code
   ↓
agent guesses N+1 / caching / rendering problem
   ↓
adds optimization
   ↓
page "seems faster"
```

That is not performance engineering.

The correct sequence is:

```text
performance symptom
   ↓
define user-visible problem
   ↓
capture baseline
   ↓
instrument relevant layers
   ↓
exercise representative flow
   ↓
rank bottlenecks using evidence
   ↓
select one bottleneck
   ↓
fix it
   ↓
run the same measurement again
   ↓
compare before vs after
   ↓
add performance guardrail
```

---

# 4. Unified Evidence Rule

No debugging or performance conclusion is considered proven without evidence.

Acceptable evidence includes:

```text
failing regression test
reproducible browser/API steps
stack trace
request ID
Sentry issue/event
Supabase error code / SQLSTATE
structured logs
query timing
query count
EXPLAIN plan
pg_stat_statements
worker/job trace
AI provider response metadata
retrieval trace
token/cost/latency metrics
Playwright trace
network waterfall
Core Web Vitals
CPU / memory profile
load-test result
before/after benchmark
```

Weak evidence:

```text
"looks suspicious"
"I think this query is slow"
"probably a race condition"
"AI often does this"
"the code seems inefficient"
"it feels faster now"
```

---

# 5. Debugging and Performance Source-of-Truth Hierarchy

When debugging a planned feature:

1. `docs/product/spec.md`
2. approved feature specification
3. approved technical decisions
4. approved implementation plan
5. acceptance criteria / test plan
6. repository `AGENTS.md`
7. production/runtime evidence
8. current source code
9. failing regression test
10. reviewer/agent hypothesis

For a production-only incident, runtime evidence may reveal that implementation
does not match the intended plan.

Do not change product behavior merely because a different implementation would
make the bug easier to fix.

---

# 6. Cross-Cutting Safety Rules

During debugging and performance work:

## Do

- preserve evidence;
- use the smallest reproduction;
- isolate one hypothesis at a time;
- use controlled test data;
- preserve tenant boundaries;
- keep logs structured;
- use request/correlation IDs;
- compare before/after measurements using the same scenario;
- remove temporary instrumentation after root cause is captured unless it is promoted into proper observability.

## Do not

- debug by random code changes;
- weaken a test to make it pass;
- add broad exception swallowing;
- disable RLS;
- use production service-role access casually;
- log secrets;
- log full private book content;
- log private learner chats;
- dump raw payment information;
- expose another tenant's data while investigating;
- run destructive `EXPLAIN ANALYZE` statements on production writes;
- optimize without baseline measurements;
- combine multiple unrelated performance fixes in one benchmark.

---

# 7. Workflow Entry Points

This workflow can begin from:

```text
user bug report
support ticket
failed automated test
Code Review finding
Sentry alert
Supabase alert/log
production incident
Playwright failure
worker/job failure
AI eval regression
slow-page report
high latency
high DB CPU
high AI latency
AI cost spike
slow ingestion
slow course generation
slow search/retrieval
Core Web Vitals regression
```

---

# 8. Debugging Workflow Overview

```text
D0  Intake and severity
D1  Preserve evidence
D2  Reproduce manually
D3  Convert reproduction into failing test
D4  Confirm test represents reported behavior
D5  Trace root cause
D6  Explain cause before touching implementation
D7  Choose cause-level fix
D8  Implement minimum fix
D9  Prove regression test turns GREEN
D10 Run adjacent/full regression checks
D11 Security / tenant / AI regression checks
D12 Remove temporary instrumentation
D13 Prevent recurrence
D14 Local review
D15 Debugging Gate
```

Intermittent bug extension:

```text
Cannot reproduce
   ↓
One hypothesis
   ↓
Targeted instrumentation
   ↓
Trigger flow
   ↓
Evidence
   ↓
Hypothesis confirmed?
      ├─ no → remove logs → next hypothesis
      └─ yes → create failing test → normal debugging loop
```

---

# 9. Performance Workflow Overview

```text
P0  Define performance symptom
P1  Define metric / budget
P2  Build reproducible benchmark
P3  Capture baseline
P4  Instrument layers
P5  Exercise representative flows
P6  Produce ranked evidence report
P7  Convert report into checklist
P8  Select ONE optimization
P9  Create focused branch
P10 Re-run baseline scenario
P11 Implement minimum optimization
P12 Re-measure same scenario
P13 Compare before vs after
P14 Run correctness / regression tests
P15 Run performance regression guard
P16 Review cost / complexity tradeoff
P17 Performance Gate
```

---

# 10. D0 — Bug Intake and Severity

Create a bug record before editing code.

Recommended artifact:

```text
docs/debugging/[date]-[bug-slug].md
```

Template:

```markdown
# Bug — [Short Name]

## Status
INVESTIGATING

## Report
Original user/system report.

## Environment
- local / preview / staging / production
- app version / SHA if known
- tenant / test tenant if relevant
- browser/device if relevant

## Impact
Who is affected and what fails.

## Severity
Critical / High / Medium / Low

## Known Evidence
- ...

## Reproduction
UNKNOWN

## Root Cause
NOT PROVEN

## Fix
NOT STARTED
```

---

# 11. Severity Rules

## Critical

Examples:

- cross-tenant data exposure;
- auth bypass;
- data corruption;
- payment corruption;
- grades modified incorrectly;
- AI performs unauthorized consequential action;
- private course material leaks to another tenant.

Immediate action:

```text
contain impact
disable feature if possible
preserve evidence
enter incident process
```

## High

Examples:

- core LMS flow unavailable;
- course publishing broken;
- all enrollments failing;
- AI generation failing broadly;
- severe worker backlog.

## Medium

Examples:

- feature partially broken;
- reproducible incorrect UI state;
- retryable integration bug.

## Low

Examples:

- isolated cosmetic issue;
- low-impact edge condition.

---

# 12. D1 — Preserve Evidence

Before making changes capture:

- exact error;
- exact timestamp;
- environment;
- current SHA;
- request/correlation ID;
- user-visible behavior;
- affected tenant/resource using safe identifiers;
- relevant log event IDs;
- screenshots/traces when appropriate;
- input shape with sensitive content redacted.

Do not paraphrase errors when exact codes exist.

Examples:

```text
HTTP 401 vs 403
Postgres SQLSTATE
Supabase PostgREST error code
AI provider status/error type
worker exception class
Sentry event ID
```

---

# 13. D2 — Reproduce Before Fixing

## Goal

Trigger the problem on demand.

Use the smallest representative environment:

1. automated unit/integration test;
2. local app;
3. local Supabase stack;
4. preview/staging;
5. production controlled test only if required.

Avoid using real customer data unless incident procedures explicitly require it.

---

# 14. D3 — Turn the Bug Into a Failing Test

The preferred output of initial investigation is:

```text
FAILING REGRESSION TEST
```

not:

```text
PATCH
```

The test should encode the reported behavior.

Example structure:

```text
Given [state]
When [trigger]
Then [expected behavior]
But current implementation [fails how]
```

---

# 15. Regression-Test Prompt

```text
Here is a bug report:

[BUG REPORT]

Do NOT fix the implementation.

First:

1. Read AGENTS.md.
2. Locate the relevant feature and tests.
3. Explore the minimum code necessary to understand the behavior.
4. Reproduce the bug.
5. Write the smallest behavioral test that fails because of this bug.
6. Run only the narrowest relevant test command.
7. Explain:
   - why this test represents the reported behavior;
   - how confident you are;
   - what evidence is still missing.

Do not change production implementation code.

Return:
REPRODUCED
or
NOT YET REPRODUCED
```

---

# 16. D4 — Validate the Reproduction

A failing test is only useful if it fails for the correct reason.

Reject tests failing because of:

- wrong fixture;
- invalid import;
- stale migration;
- test environment;
- typo;
- incorrect assumption;
- unrelated existing failure.

A valid reproduction should fail at the behavior under investigation.

Record:

```markdown
## Reproduction Confidence

**Confidence:** High / Medium / Low

**Why:** ...

**Failing test:** ...

**Observed failure:** ...
```

---

# 17. D5 — Trace the Root Cause

Do not allow implementation edits yet.

Trace:

```text
entry point
   ↓
validation
   ↓
authorization
   ↓
data flow
   ↓
domain logic
   ↓
database / external call
   ↓
async side effect
   ↓
response / UI
```

For distributed AI LMS flows include:

```text
browser
  ↓
Next.js server/client
  ↓
FastAPI
  ↓
Django/domain service
  ↓
Supabase/Postgres/RLS
  ↓
worker/QStash/Redis
  ↓
Pinecone
  ↓
AI provider
```

Not every bug traverses every layer.

---

# 18. Root-Cause Prompt

```text
The regression test now reproduces the bug.

Do NOT modify production code yet.

Trace the root cause.

Requirements:

1. Read the failing test.
2. Follow the execution path through the relevant repository layers.
3. State the root cause in plain English.
4. Cite the exact repository files and lines/areas involved.
5. Explain why the observed failure occurs.
6. Separate:
   - root cause;
   - contributing factors;
   - symptoms.
7. Propose the smallest cause-level fix.
8. Explain why the proposed fix addresses the cause rather than hiding the symptom.

Do not implement the fix yet.

Return:
ROOT CAUSE PROVEN
or
ROOT CAUSE NOT YET PROVEN
```

---

# 19. Cause vs Symptom

Example pattern:

```text
Symptom:
duplicate count displayed

Weak fix:
deduplicate display result

Root cause:
two concurrent requests both create duplicate state

Cause-level fix:
enforce invariant at trusted persistence/domain boundary
and handle conflict correctly
```

For data integrity, prefer invariants enforced in the strongest appropriate layer.

Examples:

- unique constraint;
- transaction;
- atomic update;
- idempotency key;
- valid state constraint.

Do not rely only on UI double-click prevention for critical invariants.

---

# 20. D6 — Explain Before Editing

Root-cause explanation must include:

```markdown
## Root Cause

### Trigger
...

### Execution Path
...

### Failing Assumption
...

### Why It Produces the Symptom
...

### Evidence
...

### Smallest Cause-Level Fix
...

### Risks
...
```

This becomes review evidence.

---

# 21. D7 — Choose the Minimum Cause-Level Fix

Evaluate options:

```text
Does it enforce the intended invariant?
Does it preserve product behavior?
Does it preserve tenant isolation?
Does it avoid broad refactor?
Does it handle concurrency?
Does it create migration risk?
Does it affect AI autonomy?
Does it require new dependency?
```

If the fix changes a major architecture/product decision:

```text
RETURN TO PLAN FEATURE
```

---

# 22. D8 — Implement the Fix

Rules:

- one bug;
- one root cause;
- minimum coherent fix;
- regression test remains unchanged unless the test itself was proven wrong;
- no unrelated cleanup;
- no speculative refactor.

Use the normal Implement workflow guardrails.

---

# 23. D9 — Prove the Original Reproduction Is Fixed

Run the exact test that was red.

Expected:

```text
RED before
GREEN after
```

Record:

```text
command
before result
after result
```

If the test still fails, the fix is not proven.

---

# 24. D10 — Run Adjacent and Full Regression Checks

After targeted GREEN:

1. directly related tests;
2. feature tests;
3. relevant integration tests;
4. type/lint/static checks;
5. broader suite required by repository policy.

A bug fix must not create a neighboring regression.

---

# 25. D11 — Security / Tenant / AI Regression Checks

For tenant-sensitive bug:

- same-tenant authorized path;
- same-tenant unauthorized role;
- cross-tenant access;
- service-role path if involved.

For AI/RAG bug:

- grounding;
- tenant/course retrieval scope;
- citations;
- malformed output;
- missing-evidence behavior;
- prompt injection boundary;
- AI eval regression.

For payment/assessment:

- idempotency;
- duplicate submission;
- audit behavior.

---

# 26. D12 — Remove Temporary Instrumentation

Temporary instrumentation added during investigation must be:

```text
removed
```

or promoted into:

```text
structured permanent observability
```

Do not leave:

- random `console.log`;
- sensitive request dumps;
- raw prompt content;
- debug SQL;
- development tracing enabled globally.

---

# 27. D13 — Never Fix the Same Bug Twice

After the bug is fixed ask:

> What should have caught this before production?

Possible durable prevention:

```text
regression test
property/invariant test
custom lint rule
static analysis
database constraint
type constraint
AGENTS.md rule
REVIEW_GUIDE.md warning
CI check
monitoring alert
performance budget
schema policy
```

Prefer machine-enforced prevention when reliable.

---

# 28. Guardrail Promotion Rules

Promote a bug lesson only when it is reusable.

Good:

```text
All tenant-owned queries must use the approved tenant-scoped repository/service.
```

Weak:

```text
Never make the mistake from bug #184.
```

Good:

```text
Do not build internal application URLs by hand; use the repository route helper.
```

Weak:

```text
Use route helper on CourseCard.tsx line 44.
```

---

# 29. D14 — Local Review

Before declaring the bug fixed, run a focused review:

- root cause actually addressed?
- regression test meaningful?
- no symptom-only patch?
- no scope drift?
- no auth/RLS weakening?
- no debug artifacts?
- no new race?
- no performance regression?
- no AI behavior change outside plan?

Then send through normal Code Review.

---

# 30. D15 — Debugging Gate

Return `BUG FIX VERIFIED` only when:

- [ ] exact bug is reproduced;
- [ ] valid failing test exists where technically feasible;
- [ ] root cause is proven;
- [ ] root cause is documented;
- [ ] fix addresses the cause;
- [ ] targeted test changed RED → GREEN;
- [ ] adjacent tests pass;
- [ ] required full checks pass;
- [ ] tenant/security checks pass where relevant;
- [ ] AI evals pass where relevant;
- [ ] temporary instrumentation removed/promoted;
- [ ] prevention mechanism added when valuable;
- [ ] local review passes.

Otherwise:

```text
ROOT CAUSE NOT YET PROVEN
```

or:

```text
BLOCKED
```

---

# 31. Intermittent Bugs — Instrumentation Loop

When a bug cannot be reproduced, do **not** skip reproduction.

Instead use:

```text
report
  ↓
ONE hypothesis
  ↓
2–3 targeted observations/logs
  ↓
specific trigger flow
  ↓
evidence
  ↓
confirm / reject hypothesis
```

---

# 32. One-Hypothesis Rule

Do not add logs for five theories at once.

Why:

- logs become noisy;
- evidence becomes ambiguous;
- privacy risk increases;
- agent starts pattern-matching instead of testing.

Use one hypothesis per loop.

---

# 33. Intermittent Bug Prompt

```text
Users report:

[REPORT]

I cannot reproduce it.

Do not fix anything.

1. Read the relevant code.
2. Form ONE most likely hypothesis.
3. Explain why it is plausible.
4. Add only 2–3 targeted, structured, non-sensitive diagnostic events/logs.
5. Include a correlation/request ID where appropriate.
6. Tell me the exact flow that would confirm or reject the hypothesis.
7. Do not log secrets, private course content, learner chat content, payment data,
   tokens, or credentials.

After evidence is collected:
- CONFIRMED
or
- REJECTED

If rejected, remove those diagnostics before testing the next hypothesis.
```

---

# 34. Distributed Request Correlation

For bugs crossing services, carry a safe correlation ID through:

```text
browser
→ Next.js
→ API
→ worker
→ provider
```

Recommended fields:

```text
request_id
trace_id
tenant_id hash/internal safe identifier
course_id safe identifier
job_id
provider_request_id
release_sha
```

Do not include secret/session token values.

---

# 35. Supabase Debugging Lane

For Supabase-related failures identify the failing layer:

```text
Auth
Data API / PostgREST
Postgres
RLS
Storage
Realtime
Database job / webhook
connection/pooler
```

Capture exact:

```text
HTTP status
Supabase error code
Postgres SQLSTATE
request timestamp
```

Then inspect the matching logs.

Do not scan everything first.

---

# 36. RLS Bug Checklist

For unexpected 401/403/no rows:

- actor authenticated?
- JWT correct environment?
- expected tenant membership exists?
- RLS enabled?
- policy applies to operation?
- `USING` correct?
- `WITH CHECK` correct?
- ownership/tenant key correct?
- service-role client involved?
- background worker bypasses RLS?
- query runs under expected role?

Test both:

```text
authorized same tenant
unauthorized cross tenant
```

---

# 37. FastAPI / Domain Debugging Lane

Trace:

```text
router
→ input model
→ auth context
→ service/domain action
→ persistence client
→ response mapping
```

Common evidence:

- validation error;
- status mapping;
- exception trace;
- transaction boundary;
- duplicate request;
- async timeout;
- serialized response mismatch.

Keep routers thin if that is the project convention.

---

# 38. Django Domain / Migration Debugging Lane

Investigate:

- model constraints;
- transaction behavior;
- migration state;
- admin/domain invariants;
- signals/hooks if present;
- database defaults;
- unexpected cascade;
- stale generated schema/types.

Do not change already-applied shared migrations casually.

---

# 39. Worker / Async Debugging Lane

For parsing, embedding, generation, email, or background flows record:

```text
job ID
tenant ID safe identifier
source/course ID
attempt number
queue
enqueued time
started time
completed/failed time
failure class
```

Check:

- duplicate delivery;
- idempotency;
- retry;
- dead-letter/failure state;
- timeout;
- old/new payload compatibility;
- partial result persistence;
- worker version vs web version.

---

# 40. AI / RAG Debugging Lane

An AI defect can live in different layers.

Classify before fixing:

```text
retrieval defect
context assembly defect
prompt defect
model/provider defect
structured-output parser defect
business-rule defect
citation defect
post-processing defect
evaluation defect
```

Do not automatically call every wrong answer a "prompt problem."

---

# 41. AI Answer Debugging Trace

Record safe metadata:

```text
tenant/course scope
retrieval query
retrieved source IDs
retrieval scores
prompt version
model/provider
structured output schema version
provider latency
token usage
citation IDs
eval result
```

Avoid storing raw private source content unless explicitly required and safely handled.

---

# 42. Retrieval Defect Checklist

When AI answer is wrong, verify:

1. correct tenant filter;
2. correct course filter;
3. correct lesson/module filter;
4. expected source ingested?
5. correct source version?
6. embeddings generated?
7. vector metadata correct?
8. retrieval returns relevant chunks?
9. reranking correct?
10. context truncated?
11. citation mapping correct?

Only after retrieval is proven correct should prompt/model behavior become the primary suspect.

---

# 43. Structured AI Output Debugging

If course generation fails:

- provider returned response?
- valid JSON/structured payload?
- schema validation?
- enum valid?
- module count valid?
- lesson count valid?
- citation/source references valid?
- partial output?
- retry behavior?
- failure state persisted?
- user sees useful error?

Do not persist malformed content just to avoid a failure.

---

# 44. External Provider Debugging

For PayMongo, Resend, OpenAI/AI provider, Pinecone, etc.:

Capture:

```text
provider
SDK/package version
operation
HTTP status
provider request ID
safe response error metadata
timeout/retry
environment (sandbox/live)
```

Verify API assumptions against the installed version/current primary docs when material.

---

# 45. Production Error Monitoring

Production should report bugs before users need to explain them.

Sentry or equivalent should capture:

- exception;
- release SHA;
- environment;
- request/trace ID;
- route;
- worker/job;
- safe tenant context;
- breadcrumbs without sensitive content.

Do not send:

- secrets;
- payment credentials;
- full book content;
- private learner chat text;
- raw auth tokens.

---

# 46. Performance Workflow — P0: Define the Symptom

Do not begin with:

```text
"optimize the dashboard"
```

Begin with:

```text
"Instructor dashboard P95 server response is 2.4s for tenants with 5,000 learners."
```

or:

```text
"AI companion first answer takes 7.8s median."
```

or:

```text
"Course generation worker uses 1.8 GB memory for a 300-page document."
```

---

# 47. Performance Dimensions

A performance problem may involve:

## User experience

- LCP;
- INP;
- CLS;
- TTFB;
- page navigation;
- client JavaScript;
- render blocking.

## API

- request latency;
- P50/P95/P99;
- throughput;
- timeouts;
- CPU;
- memory.

## Database

- query count;
- mean/max execution;
- total query time;
- sequential scans;
- locks;
- connections;
- cache hit;
- index usage.

## Worker

- queue wait;
- processing duration;
- memory;
- retries;
- throughput.

## AI

- retrieval latency;
- embedding latency;
- model first-token latency;
- total model latency;
- tokens;
- cost/request;
- retries;
- structured-output failure.

## Vector DB

- query latency;
- filter cost;
- namespace/index;
- result count.

## External

- email;
- payment;
- webhooks;
- storage.

---

# 48. P1 — Define Metric and Performance Budget

Every performance investigation needs a metric.

Examples:

```text
Dashboard server latency P95
< 800 ms

Course list DB queries
< 20 per request

Instructor course page memory
< 256 MB under representative load

AI companion first token
< 2.5 s P50

AI companion total response
< 8 s P95

RAG retrieval
< 500 ms P95

Document ingestion
< N minutes for representative N-page document

Core Web Vitals
LCP / INP / CLS target defined by product/release policy
```

Do not use arbitrary targets when product requirements already define SLOs.

---

# 49. P2 — Build a Reproducible Performance Scenario

Document:

```markdown
## Performance Scenario

### Environment
local / staging / production read-only measurement

### Release SHA
...

### Dataset
- tenant size
- number of courses
- learners
- lessons
- documents
- source size

### User Flow
...

### Request / URL
...

### Warm-up
...

### Measurement Tool
...

### Runs
...

### Metrics
...
```

Same scenario must be used before and after the fix.

---

# 50. P3 — Capture Baseline

Baseline is mandatory.

Record:

```text
P50
P95
P99 where useful
query count
DB total time
API duration
worker duration
memory
AI latency
AI tokens/cost
Core Web Vitals
```

Do not optimize until baseline is saved.

---

# 51. P4 — Instrument Relevant Layers

Choose the smallest set of tools needed.

Potential sources:

```text
browser DevTools
Playwright trace
Vercel logs / Speed Insights
Next.js instrumentation
Sentry traces
FastAPI timing middleware / profiler
Python profiler
Supabase logs
pg_stat_statements
Supabase inspect
Postgres EXPLAIN
worker metrics
Pinecone/provider latency
PostHog product metrics
```

Use project-approved tooling first.

---

# 52. Next.js / Vercel Performance Lane

Measure both:

```text
lab
field
```

Potential evidence:

- network waterfall;
- server timing;
- bundle size;
- route rendering mode;
- LCP;
- INP;
- CLS;
- Vercel Speed Insights;
- function duration;
- logs/traces.

Do not treat Lighthouse alone as the entire user-performance picture.

---

# 53. Frontend Performance Checklist

Investigate:

- unnecessary client components;
- large JavaScript bundle;
- duplicate client requests;
- blocking third-party script;
- image size;
- font loading;
- hydration work;
- waterfall from sequential requests;
- rerenders;
- unbounded list rendering;
- lack of pagination/virtualization;
- dynamic rendering where static/cache would be safe.

Do not cache private tenant data in a shared/public scope.

---

# 54. Supabase / Postgres Performance Lane

Use evidence from:

```text
pg_stat_statements
EXPLAIN
Supabase inspect db
query logs
database reports
```

Potential inspections:

```text
long-running queries
outliers
sequential scans
index usage
unused indexes
locks
blocking
cache hit
connections
table size
index size
bloat
```

---

# 55. Safe EXPLAIN Rule

Prefer:

```text
EXPLAIN
```

for production-sensitive investigation.

Use:

```text
EXPLAIN ANALYZE
```

carefully, because it executes the query.

Never casually use `EXPLAIN ANALYZE` on production:

```text
INSERT
UPDATE
DELETE
```

unless the execution is explicitly safe and approved.

Prefer non-production for detailed plan experimentation.

---

# 56. Query Performance Report

For every DB finding record:

```markdown
### PERF-DB-[N]

**Query / operation:** ...

**Calls:** ...

**Mean:** ...

**Max:** ...

**Total:** ...

**Rows:** ...

**Plan evidence:** ...

**Likely cause:** ...

**Confidence:** High / Medium / Low

**Candidate fix:** ...

**Expected metric:** ...
```

---

# 57. RLS Performance Review

RLS can become a performance issue.

Investigate:

- policy function evaluated per row;
- missing indexes on tenant/user foreign keys;
- expensive subqueries in policy;
- function volatility;
- join patterns;
- `auth.uid()` usage pattern;
- broad scans before tenant filtering.

Any RLS optimization must preserve security semantics.

Never trade tenant isolation for speed.

---

# 58. API / FastAPI Performance Lane

Measure:

- route duration;
- serialization;
- blocking I/O;
- external calls;
- DB time;
- number of DB calls;
- middleware;
- large payload;
- sync work inside async path;
- repeated auth/tenant lookup.

Use profiling only on representative flows.

---

# 59. Django / Domain Performance Lane

Investigate:

- repeated ORM queries;
- N+1;
- missing prefetch/select;
- unbounded queryset;
- expensive admin/domain query;
- transaction duration;
- unnecessary writes;
- repeated validation;
- large serialization.

Do not introduce generic caching before understanding data freshness/tenant safety.

---

# 60. Worker Performance Lane

Measure:

```text
queue wait
job processing
parse time
embedding time
AI time
DB time
vector time
memory peak
retries
throughput
```

For ingestion:

```text
upload
  ↓
parse/OCR
  ↓
chunk
  ↓
embed
  ↓
index
  ↓
generation
```

Find the actual slow stage.

---

# 61. AI Performance Lane

AI performance must track both speed and cost.

Record:

```text
model
prompt version
input tokens
output tokens
retrieved chunks
retrieval latency
model first-token latency
total model latency
retry count
cost/request
structured-output retries
```

Do not optimize latency by silently degrading grounding or answer quality.

---

# 62. AI Performance Tradeoff Gate

Any AI performance optimization must compare:

```text
Latency
Cost
Quality
Groundedness
Citation accuracy
Safety
```

Example:

```text
reducing retrieved chunks
may improve latency
but can reduce grounding
```

Run evals after performance changes.

---

# 63. Pinecone / Vector Performance Lane

Investigate:

- index/namespace;
- metadata filter;
- top_k;
- vector dimension;
- result size;
- query latency;
- network;
- reranker latency;
- repeated queries;
- tenant filter selectivity.

Do not remove tenant filter to improve query speed.

---

# 64. Upstash / Redis / Cache Performance Lane

Before adding cache answer:

```text
What is cached?
Who owns it?
Tenant-scoped?
TTL?
Invalidation?
Stale data acceptable?
Cache stampede?
Failure fallback?
```

Caching is not automatically a safe performance fix.

---

# 65. P5 — Exercise Representative Flows

Select the important user flows.

Example AI LMS performance audit:

```text
public landing page
login
student dashboard
instructor dashboard
course list
course detail
lesson view
assessment load
assessment submit
book upload
course generation status
AI companion question
admin dashboard
```

Do not profile every page equally.

Use traffic/risk to prioritize.

---

# 66. P6 — Ranked Performance Audit

The first performance output should be a report, not code.

Template:

```markdown
# Performance Audit

## Environment
...

## Baseline
...

## Ranked Findings

### 1. [Finding]

**Layer:** Database / Frontend / API / Worker / AI / Vector / External

**Symptom:** ...

**Evidence:**
- query count:
- timing:
- memory:
- trace:

**Root performance cause:** ...

**Confidence:** High / Medium / Low

**Candidate fix:** ...

**Expected measurable impact:** ...

**Risk:** ...

### 2. ...
```

Rank by:

```text
user impact
frequency
total time
risk
cost
confidence
```

---

# 67. Performance Audit Prompt

```text
Investigate performance for:

[FLOW / SYMPTOM]

Do NOT change production code.

1. Read AGENTS.md and relevant architecture docs.
2. Build a reproducible scenario.
3. Capture baseline metrics.
4. Instrument only relevant layers.
5. Exercise the representative flow multiple times.
6. Produce a ranked report.

For each finding include:
- what's slow;
- layer;
- measured evidence;
- likely cause;
- confidence;
- candidate fix;
- expected measurable impact;
- correctness/security risk.

Do not guess based on code appearance.

Return:
PERFORMANCE BOTTLENECKS MEASURED
or
INSUFFICIENT EVIDENCE
```

---

# 68. P7 — Convert Report Into Checklist

Recommended:

```text
docs/performance/[date]-[area]-checklist.md
```

Example:

```markdown
# Performance Checklist — Instructor Dashboard

- [ ] PERF-01 — Reduce repeated enrollment query
  - Baseline:
  - Target:
  - Branch:
  - Result:

- [ ] PERF-02 — Paginate large learner list
  - Baseline:
  - Target:
  - Branch:
  - Result:
```

Work by numbered item.

---

# 69. P8 — Select One Optimization

Default rule:

```text
ONE measured bottleneck
ONE branch
ONE before/after comparison
```

Why:

- isolates effect;
- easier review;
- easier rollback;
- clearer benchmark;
- prevents overlapping fixes from hiding regressions.

---

# 70. P9 — Create Focused Branch

Use repository convention.

Example:

```text
perf/instructor-dashboard-query-count
perf/ai-chat-retrieval-latency
perf/course-ingestion-memory
```

Do not mix:

- unrelated refactor;
- dependency upgrade;
- multiple independent performance issues.

---

# 71. P10 — Reconfirm Baseline Before Editing

Before changing code rerun the benchmark.

If baseline materially differs:

- environment changed;
- data changed;
- cache state differs;
- background load differs.

Resolve measurement instability before optimizing.

---

# 72. P11 — Implement Minimum Optimization

Examples of evidence-backed fixes:

```text
pagination
index
query rewrite
prefetch/select
batch operation
safe caching
parallel independent I/O
streaming
reduce duplicate API call
reduce payload
move long work to worker
reduce unnecessary AI context
reuse embedding
fix retry loop
```

Do not choose from this list unless evidence points there.

---

# 73. P12 — Re-measure the Same Scenario

Use:

- same environment;
- same data;
- same user flow;
- same tool;
- same number of runs;
- same cache/warm-up policy.

Record raw before/after.

---

# 74. Performance Comparison Template

```markdown
## PERF-[N] Result

### Before
- P50:
- P95:
- query count:
- DB time:
- memory:
- AI latency:
- cost:

### After
- P50:
- P95:
- query count:
- DB time:
- memory:
- AI latency:
- cost:

### Change
- ...

### Correctness
PASS / FAIL

### AI Quality
PASS / FAIL / N/A

### Security / Tenant Isolation
PASS / FAIL

### Conclusion
KEEP / REVERT / INVESTIGATE
```

---

# 75. P13 — Improvement Must Be Material

A fix is not automatically good because the number moved.

Ask:

- improvement larger than measurement noise?
- does it improve the real user bottleneck?
- added complexity worth it?
- memory got worse?
- AI quality got worse?
- DB writes got slower?
- stale-cache risk introduced?
- tenant boundary preserved?

---

# 76. P14 — Correctness Regression Tests

After performance fix run:

- existing feature tests;
- relevant integration tests;
- security/tenant tests;
- AI evals if AI behavior changed;
- UI/E2E where applicable.

Performance never overrides correctness.

---

# 77. P15 — Performance Regression Guard

High-value fixes should leave a guardrail.

Options:

```text
query-count assertion
benchmark threshold
load-test threshold
memory budget
Core Web Vital alert
API latency alert
AI cost budget
worker duration budget
database index/plan check
```

Avoid brittle micro-benchmarks in noisy CI.

Use budgets where measurement is stable.

---

# 78. Query-Count Regression Tests

Good for known N+1 classes when test infrastructure supports stable counts.

Example behavior:

```text
loading 20 courses should not issue one additional query per course
```

Do not lock tests to an arbitrary count if legitimate implementation changes make it fragile.

---

# 79. Load Testing

Use staging/controlled environment for load tests.

Potential tool:

```text
k6
```

or the project-approved tool.

Test representative:

```text
concurrent learners
course page reads
AI requests
assessment submissions
uploads
```

Do not load-test production destructively.

---

# 80. Load-Test Scenario Definition

Record:

```text
virtual users
duration
ramp
dataset
read/write mix
AI calls enabled/disabled
expected P95
expected error rate
```

Be careful: full AI-provider load tests can be expensive.

Use mocks or bounded provider tests where appropriate.

---

# 81. P16 — Cost / Complexity Review

A performance fix can be technically faster but strategically worse.

Evaluate:

```text
complexity
maintenance
infrastructure cost
provider cost
cache invalidation
operational burden
security
AI quality
```

Example:

```text
Adding Redis for a 40 ms improvement
may be worse than keeping a simple DB query.
```

---

# 82. P17 — Performance Gate

Return `PERFORMANCE FIX VERIFIED` only when:

- [ ] symptom is measurable;
- [ ] baseline saved;
- [ ] bottleneck identified with evidence;
- [ ] one fix selected;
- [ ] before/after uses same scenario;
- [ ] improvement is material;
- [ ] correctness tests pass;
- [ ] tenant/security behavior preserved;
- [ ] AI quality/evals pass where relevant;
- [ ] no unacceptable cost/memory regression;
- [ ] performance guardrail added where valuable;
- [ ] diff is focused;
- [ ] ready for Code Review.

Otherwise:

```text
INSUFFICIENT EVIDENCE
```

or:

```text
REVERT / INVESTIGATE
```

---

# 83. Production Performance Investigation

For a production slowdown:

1. identify start time;
2. correlate deployment/release;
3. compare before/after telemetry;
4. identify affected tenants/routes;
5. isolate layer;
6. capture outliers;
7. determine whether feature flag can contain it;
8. reproduce safely in staging with representative data;
9. optimize through normal performance loop.

Do not profile production with invasive tooling without approval.

---

# 84. Performance Regression From Deployment

Check:

```text
new deployment SHA
new migration
new query
new RLS policy
new dependency
new third-party script
new AI model
new retrieval strategy
new worker version
traffic/data growth
```

A slowdown after deployment is not automatically caused by the most visible code change.

Use timestamps/traces.

---

# 85. Supabase Current Performance Toolkit

When available in the project/environment, use:

```text
pg_stat_statements
Supabase query performance tools
Supabase inspect db outliers
Supabase inspect db long-running-queries
Supabase inspect db seq-scans
Supabase inspect db index-usage
Supabase inspect db unused-indexes
Supabase inspect db locks
Supabase inspect db blocking
Supabase inspect db cache-hit
Supabase inspect db table-sizes
```

Verify exact CLI syntax against installed/current tooling.

---

# 86. Database Performance Safety

Do not optimize only the slowest single query.

Also inspect:

```text
high call count × moderate latency
```

because cumulative total time can dominate.

Rank by:

- total time;
- mean;
- max;
- call count;
- I/O;
- user-facing impact.

---

# 87. Connection Performance

If DB connection exhaustion appears:

- identify clients;
- inspect active/direct connections;
- inspect pooler usage;
- verify serverless connection pattern;
- verify workers;
- verify long transactions;
- verify leaked connections.

Do not simply increase connection limits without understanding why they are exhausted.

---

# 88. Core Web Vitals Lane

Track field metrics where available:

```text
LCP
INP
CLS
```

Also track:

```text
TTFB
route latency
JavaScript execution
```

Use real-user data where possible.

Lab tools remain useful for diagnosis.

---

# 89. Next.js Performance Review

Investigate project-specific patterns such as:

- Server vs Client Components;
- dynamic route rendering;
- fetch/data cache;
- route waterfalls;
- Suspense boundaries;
- images;
- fonts;
- third-party scripts;
- bundle size;
- expensive client state;
- repeated hydration.

Do not apply generic Next.js optimization blindly.

---

# 90. Performance of Multi-Tenant Queries

Always test with realistic tenant sizes.

A query that is fast for:

```text
10 learners
```

may fail at:

```text
10,000 learners
```

Representative fixture sizes should reflect expected production scale.

---

# 91. Performance of AI Course Generation

Break end-to-end latency into:

```text
upload
parse
OCR if any
chunk
embed
index
retrieve/context
AI generation
validation
persistence
```

Optimize the slowest proven stage.

---

# 92. Memory Profiling for Large Documents

Measure:

- source file size;
- page count;
- chunk count;
- peak memory;
- worker duration;
- concurrent jobs.

Look for:

- full-document copies;
- all chunks in memory;
- unnecessary parsed representation duplication;
- large AI context construction;
- unbounded batch size.

---

# 93. Performance and Backpressure

For async ingestion/generation, investigate:

- producer rate;
- queue depth;
- worker concurrency;
- provider rate limits;
- DB connections;
- retry storm;
- duplicate jobs.

Do not increase concurrency until downstream capacity is known.

---

# 94. Retry Storm Debugging

Symptoms:

- high provider calls;
- cost spike;
- queue backlog;
- duplicated logs.

Check:

- retry policy;
- non-retryable error classification;
- exponential backoff;
- idempotency;
- dead-letter behavior;
- circuit breaker if architecture supports it.

---

# 95. AI Quality Regression During Performance Optimization

If changing:

- model;
- prompt;
- context size;
- top_k;
- reranking;
- chunking;
- temperature;
- structured output;

run the approved AI eval set.

Performance result is rejected if quality falls below accepted threshold.

---

# 96. Debugging a Slow AI Answer

Trace:

```text
API request time
retrieval
reranker
context construction
provider queue/network
time to first token
generation duration
post-processing
persistence
stream to browser
```

Do not call the model "slow" until provider time is isolated from surrounding work.

---

# 97. Debugging Citations

If citations are wrong:

1. retrieved source IDs correct?
2. model received correct source mapping?
3. generated citation token maps to right source?
4. post-processing reorders sources?
5. authorization filters citation destination?
6. source version changed?

Treat citation correctness as a data-flow problem before assuming model hallucination.

---

# 98. Debugging AI Cross-Tenant Leakage

Immediate Critical process:

```text
disable affected feature/path
preserve evidence
verify vector metadata filter
verify source-resolution auth
verify service-role path
verify cache key tenant scope
verify prompt/context assembly
verify citation resolution
add cross-tenant regression test
```

Do not continue normal experimentation with real tenant data.

---

# 99. Debugging Payment Performance or Failure

For PayMongo-related behavior:

- test/live mode;
- request ID;
- idempotency;
- webhook delivery;
- signature verification;
- DB transaction;
- duplicate callback;
- reconciliation state;
- provider latency.

Never log raw card/payment credentials.

---

# 100. Debugging Email Delivery

For Resend/email:

- domain/sender;
- queue;
- worker;
- provider response;
- recipient validation;
- retry;
- duplicate send;
- suppression/bounce if available;
- notification state.

Email delivery and domain state should not corrupt core LMS transaction state.

---

# 101. Debugging Vercel/Frontend Production Differences

Compare:

```text
local
preview
production
```

Check:

- environment variables;
- runtime;
- region;
- cache;
- edge/server behavior;
- build output;
- third-party scripts;
- network/provider access.

A bug occurring only in production may be configuration/runtime, not business logic.

---

# 102. Observability Architecture

Recommended trace path:

```text
Browser
  ↓ trace/request ID
Next.js
  ↓
API
  ↓
Domain
  ↓
Postgres / Supabase
  ↓
Worker
  ↓
Vector / AI Provider
```

Not all tools need full distributed tracing initially.

Start with correlation IDs and structured events if that is what the project supports.

---

# 103. Logging Privacy Rules

Never log:

- password;
- auth token;
- API secret;
- payment secret;
- full uploaded book;
- full private chat;
- raw PII unless explicitly approved;
- model provider key.

Prefer:

```text
IDs
counts
sizes
durations
status
error class
hash/safe identifiers
```

---

# 104. Sentry Error Context

Useful safe context:

```text
release
environment
route
trace/request ID
feature
job ID
tenant safe identifier
course ID
error category
```

Avoid sensitive content.

---

# 105. PostHog Performance/Product Context

Product analytics can help answer:

```text
Which flow is slow?
How many users reach it?
Where do users abandon?
Did a performance fix improve completion?
```

Do not use analytics as a substitute for technical latency profiling.

---

# 106. Performance Prioritization Formula

A practical rank:

```text
Priority ≈
User Impact
× Frequency
× Time/Cost Wasted
× Confidence
÷ Fix Risk
```

Do not treat this as a literal numeric requirement unless the team wants one.

---

# 107. Bug Prioritization Formula

Prioritize by:

```text
security/data safety
blast radius
frequency
business importance
reproducibility
availability of containment
```

A rare cross-tenant bug outranks a frequent cosmetic issue.

---

# 108. Debugging Branch Strategy

Use a focused branch per bug when non-trivial.

Examples:

```text
fix/course-generation-duplicate-job
fix/tenant-course-access-rls
fix/ai-citation-source-map
```

Performance:

```text
perf/dashboard-n-plus-one
perf/rag-retrieval-latency
```

---

# 109. Debugging Commit Strategy

Meaningful local commits:

```text
test: reproduce duplicate course generation
fix: enforce generation idempotency
test: cover cross-tenant generation isolation
```

Avoid hiding reproduction and fix in one opaque commit when review benefits from separation.

---

# 110. Debugging Progress File

For complex incidents:

```text
docs/debugging/[bug]/status.md
```

Template:

```markdown
# Debug Status — [Bug]

## State
ROOT CAUSE NOT YET PROVEN

## Reproduction
- ...

## Failing Test
- ...

## Hypothesis
- ...

## Evidence
- ...

## Root Cause
- ...

## Fix
- ...

## Verification
- ...

## Prevention
- ...

## Next Action
- ...
```

---

# 111. Performance Progress File

```text
docs/performance/[area]/status.md
```

Template:

```markdown
# Performance Status — [Area]

## Baseline
...

## Current Ranked Finding
PERF-03

## Current Branch
...

## Before
...

## After
...

## Correctness
...

## AI Eval
...

## Decision
KEEP / REVERT / INVESTIGATE
```

---

# 112. Master Codex Prompt — Debug a Reproducible Bug

```text
You are running the DEBUGGING workflow for the AI LMS.

Bug:
[REPORT]

Do not guess and patch.

==================================================
PHASE 1 — CONTEXT
==================================================

Read:
- AGENTS.md;
- relevant feature spec;
- relevant tests;
- relevant implementation.

Identify the minimum affected subsystem.

==================================================
PHASE 2 — REPRODUCE
==================================================

Reproduce the reported behavior.

Write the smallest behavioral regression test.

Do not modify production implementation.

Run the narrow test.

Return:
REPRODUCED
or
NOT YET REPRODUCED

Explain reproduction confidence.

==================================================
PHASE 3 — ROOT CAUSE
==================================================

If reproduced:

- trace entry → validation → auth → domain → data/external/async → output;
- explain the root cause;
- cite exact repository locations;
- distinguish cause vs symptom;
- propose the smallest cause-level fix.

Do not implement until root cause is explained.

Return:
ROOT CAUSE PROVEN
or
ROOT CAUSE NOT YET PROVEN

==================================================
PHASE 4 — FIX
==================================================

Only when root cause is proven:

- implement the minimum fix;
- preserve the regression test;
- do not broaden scope;
- preserve tenant/RLS/security;
- preserve approved AI behavior.

==================================================
PHASE 5 — VERIFY
==================================================

Run:
1. original failing test;
2. related tests;
3. relevant integration;
4. lint/type/static;
5. tenant/security tests;
6. AI evals if applicable.

Record RED → GREEN evidence.

==================================================
PHASE 6 — PREVENT RECURRENCE
==================================================

Ask what durable guardrail should catch this class next time:

- test;
- constraint;
- static analysis;
- lint;
- AGENTS.md;
- CI;
- monitoring.

Add only a reusable, justified guardrail.

==================================================
FINAL
==================================================

Return:
BUG FIX VERIFIED

only when the original bug is reproduced, root cause proven, fix verified, and
required regression checks pass.

Otherwise:
ROOT CAUSE NOT YET PROVEN
or
BLOCKED.
```

---

# 113. Master Codex Prompt — Debug an Intermittent Bug

```text
You are investigating an intermittent AI LMS bug:

[REPORT]

It cannot currently be reproduced.

Do not fix it yet.

1. Read relevant code and recent changes.
2. Form ONE highest-confidence hypothesis.
3. State what evidence would confirm/reject it.
4. Add at most 2–3 targeted structured diagnostics.
5. Use safe IDs/correlation IDs.
6. Do not log secrets, private course content, private learner chat, raw payment
   data, or auth tokens.
7. Give the exact trigger flow.
8. Collect/read evidence.
9. Return:
   CONFIRMED
   or
   REJECTED.

If REJECTED:
- remove hypothesis-specific temporary diagnostics;
- form the next single hypothesis.

If CONFIRMED:
- write a failing regression test;
- continue with the normal root-cause debugging workflow.
```

---

# 114. Master Codex Prompt — Performance Audit

```text
You are running a PERFORMANCE AUDIT for the AI LMS.

Symptom:
[PERFORMANCE PROBLEM]

Do not change production code.

==================================================
CONTEXT
==================================================

Read:
- AGENTS.md;
- relevant feature architecture;
- actual project scripts;
- relevant implementation.

==================================================
SCENARIO
==================================================

Define a reproducible performance scenario:

- environment;
- SHA;
- representative tenant/data size;
- user flow;
- tool;
- warm-up/cache policy;
- metrics;
- number of runs.

==================================================
BASELINE
==================================================

Capture actual baseline.

Depending on the layer include:
- P50/P95/P99;
- query count;
- DB mean/max/total;
- memory;
- CPU;
- worker time;
- queue wait;
- retrieval time;
- AI first token/total;
- token/cost;
- Core Web Vitals.

==================================================
INSTRUMENT
==================================================

Instrument only relevant layers.

Potential:
- browser/Vercel;
- Next.js;
- API;
- domain;
- Supabase/Postgres;
- worker;
- Redis;
- Pinecone;
- AI provider.

==================================================
REPORT
==================================================

Produce ranked findings.

For each:
- layer;
- what's slow;
- evidence;
- root performance cause;
- confidence;
- candidate fix;
- expected measurable impact;
- correctness/security/AI-quality risk.

Do not implement.

Return:
PERFORMANCE BOTTLENECKS MEASURED
or
INSUFFICIENT EVIDENCE.
```

---

# 115. Master Codex Prompt — Implement One Performance Fix

```text
Implement only:

[PERF-ID]

from:

[PERFORMANCE CHECKLIST]

Before editing:
1. load the recorded baseline;
2. rerun the same scenario;
3. confirm the baseline is sufficiently stable.

Implement the smallest evidence-backed optimization.

Do not combine another independent performance fix.

After implementation:
1. rerun the exact same performance scenario;
2. record before/after;
3. run correctness tests;
4. run tenant/security checks;
5. run AI evals if AI behavior changed;
6. inspect cost/memory tradeoffs;
7. add a stable regression guard if valuable.

Return:
PERFORMANCE FIX VERIFIED
only if the improvement is measurable and correctness is preserved.

Otherwise:
REVERT / INVESTIGATE.
```

---

# 116. Codex Prompt — Supabase Performance Audit

```text
Investigate Supabase/Postgres performance for:

[FLOW]

Do not change schema or queries yet.

Use the available project/Supabase tooling to inspect:

- pg_stat_statements;
- expensive/outlier queries;
- call counts;
- mean/max/total execution time;
- sequential scans;
- index usage;
- locks/blocking;
- connection pressure;
- query plans.

Use EXPLAIN safely.
Prefer non-production for EXPLAIN ANALYZE and write operations.

For each finding:
- query/operation;
- evidence;
- plan;
- suspected cause;
- confidence;
- candidate fix;
- tenant/RLS security impact.

Return a ranked report only.
```

---

# 117. Codex Prompt — AI/RAG Debugging

```text
Investigate this AI/RAG defect:

[REPORT]

Do not assume it is a prompt problem.

Classify the defect into:

- retrieval;
- context assembly;
- prompt;
- provider/model;
- structured output;
- citation mapping;
- domain/business rule;
- evaluation.

Trace:

tenant/course authorization
→ source ingestion/version
→ embedding/index
→ retrieval
→ reranking
→ context assembly
→ model
→ output validation
→ citation resolution
→ persistence/UI

Record only safe metadata.

Do not expose private source content.

Produce:
- reproduction;
- evidence;
- root cause;
- confidence;
- regression test/eval;
- smallest fix.

Do not implement until root cause is proven.
```

---

# 118. Codex Prompt — AI Performance Audit

```text
Audit AI performance for:

[FLOW]

Do not optimize yet.

Measure:

- retrieval latency;
- reranking latency;
- context construction;
- provider/model;
- time to first token;
- total generation latency;
- input tokens;
- output tokens;
- retries;
- structured-output retries;
- cost/request;
- quality/eval result.

Produce ranked bottlenecks.

Any optimization proposal must state expected impact on:
- latency;
- cost;
- groundedness;
- correctness;
- citation quality.

Do not recommend a faster solution that violates the approved AI quality or
tenant-isolation requirements.
```

---

# 119. Recommended Codex Skill Packaging

The packages below are design examples only. They are not installed repository skills
and must not be scaffolded or treated as available without a separate approved change.

```text
.agents/
└── skills/
    ├── debug-bug/
    │   ├── SKILL.md
    │   └── references/
    │       ├── root-cause-template.md
    │       ├── regression-test.md
    │       └── ai-lms-debug-checklist.md
    │
    ├── debug-intermittent/
    │   ├── SKILL.md
    │   └── references/
    │       └── instrumentation-loop.md
    │
    ├── performance-audit/
    │   ├── SKILL.md
    │   └── references/
    │       ├── performance-report.md
    │       ├── database-performance.md
    │       ├── frontend-performance.md
    │       ├── worker-performance.md
    │       └── ai-performance.md
    │
    └── performance-fix/
        ├── SKILL.md
        └── references/
            └── performance-gate.md
```

---

# 120. Example `debug-bug` Skill Frontmatter

```yaml
---
name: debug-bug
description: >
  Turn a bug report into a reproducible failing regression test, trace and
  explain the real root cause before code changes, implement the smallest
  cause-level fix, prove RED→GREEN, run regression/security/tenant/AI checks,
  and add a durable guardrail so the same class of defect does not recur.
---
```

---

# 121. Example `performance-audit` Skill Frontmatter

```yaml
---
name: performance-audit
description: >
  Investigate an AI LMS performance problem using real measurements rather than
  code guesses. Build a reproducible benchmark, capture baseline metrics,
  instrument the relevant frontend/API/database/worker/vector/AI layers, and
  produce a ranked evidence-based report without changing production code.
---
```

---

# 122. Recommended AGENTS.md Debugging Section

```markdown
## Debugging

When fixing a non-trivial bug:

1. Reproduce the reported behavior before changing production code.
2. Prefer a failing behavioral regression test.
3. Confirm the test fails for the reported reason.
4. Explain the root cause with repository evidence before implementing.
5. Fix the cause, not only the symptom.
6. Keep the fix minimal and scoped.
7. Prove the original regression test changes RED → GREEN.
8. Run adjacent and required full checks.
9. Preserve auth, RLS, tenant isolation, and approved AI behavior.
10. Remove temporary instrumentation.
11. Add a reusable prevention guardrail when valuable.

For intermittent bugs:
- test one hypothesis at a time;
- add minimal structured diagnostics;
- use correlation IDs;
- never log secrets/private content.
```

---

# 123. Recommended AGENTS.md Performance Section

```markdown
## Performance

Do not make performance changes without measurements.

For performance work:

1. Define the user-visible symptom and metric.
2. Build a reproducible scenario.
3. Capture a baseline before editing code.
4. Instrument the relevant layer(s).
5. Produce a ranked evidence-based performance report.
6. Fix one measured bottleneck per focused branch by default.
7. Re-run the exact same benchmark after the change.
8. Record before/after metrics.
9. Run correctness, tenant/security, and AI eval checks.
10. Reject optimizations that materially degrade quality, security, or
    maintainability.
11. Add a stable performance regression guard when valuable.
```

---

# 124. Recommended REVIEW_GUIDE.md Sections

```markdown
## Bug Fixes
- Require evidence the bug was reproduced.
- Require a root-cause explanation.
- Check that the regression test would fail without the fix.
- Check for symptom-only patches.

## Performance
- Require baseline and after metrics.
- Verify the same scenario/tool/data were used.
- Check that the optimization targets the measured bottleneck.
- Check for new caching/tenant/privacy risks.
- Check AI quality after AI performance changes.

## Supabase / RLS
- Never trade RLS correctness for speed.
- Verify tenant columns and policy predicates are indexed where appropriate.
- Check privileged clients separately.

## AI / RAG
- Separate retrieval latency from model latency.
- Verify quality/evals after reducing context/retrieval.
- Verify tenant/source filters remain intact.
```

---

# 125. Debugging Anti-Patterns

## "I see the bug in the code"

Seeing suspicious code is not reproduction.

## "This fix makes the test pass"

If the test did not reproduce the user problem, that proves little.

## "Catch the exception and return null"

Silent failure hides root cause.

## "Turn off RLS to see if it works"

This changes the security model and can expose data.

## "Log the entire prompt/source document"

Debugging convenience does not override privacy.

## "Fix several likely causes"

You lose causal evidence.

---

# 126. Performance Anti-Patterns

## "Add caching"

Caching without freshness/tenant analysis can create correctness bugs.

## "Add an index to every filter"

Indexes also affect write cost and maintenance.

## "Increase database compute first"

Resource increases can hide bad queries.

## "Reduce AI context until it's fast"

May destroy groundedness.

## "Use a faster model"

May reduce quality or structured-output reliability.

## "Parallelize everything"

May exceed provider/DB limits or create concurrency defects.

## "One giant performance PR"

Makes it impossible to attribute gains.

---

# 127. Debugging + Code Review Handoff

Once a bug fix reaches:

```text
BUG FIX VERIFIED
```

create implementation summary:

```markdown
## Bug
...

## Reproduction
...

## Root Cause
...

## Fix
...

## RED → GREEN
...

## Regression Checks
...

## Prevention
...

## Review Focus
...
```

Then:

```text
READY FOR CODE REVIEW
```

---

# 128. Performance + Code Review Handoff

Once performance reaches:

```text
PERFORMANCE FIX VERIFIED
```

provide:

```markdown
## Performance Problem
...

## Baseline
...

## Bottleneck
...

## Fix
...

## Before vs After
...

## Correctness
...

## Tenant/Security
...

## AI Quality
...

## Regression Guard
...

## Review Focus
...
```

Then:

```text
READY FOR CODE REVIEW
```

---

# 129. Debugging + Deployment Handoff

If the bug was production-specific, Merge/Deploy should receive:

- reproduction;
- incident severity;
- rollback/containment state;
- fix SHA;
- required config/migration;
- production verification scenario;
- monitoring signal to watch.

A production bug is not complete when code merges.

It is complete when the failed production operation is re-run safely and the
relevant logs/metrics are clean.

---

# 130. Performance + Deployment Handoff

Merge/Deploy should receive:

```text
baseline
after target
production metric
expected rollout effect
rollback threshold
feature flag if applicable
monitoring signal
```

Validate the performance improvement in production after deployment.

Lab/staging improvement may not match real traffic.

---

# 131. Production Performance Monitoring

Recommended continuous signals:

## Frontend

- LCP;
- INP;
- CLS;
- route-level real-user performance.

## API

- P50/P95/P99;
- error rate.

## Database

- expensive query trend;
- connection usage;
- locks;
- CPU/IO.

## Worker

- queue depth;
- processing time;
- failure rate.

## AI

- latency;
- tokens;
- cost;
- failure;
- structured output;
- retrieval empty rate.

---

# 132. Performance Alert Philosophy

Alert on symptoms users care about.

Good:

```text
AI companion P95 > threshold for 15 min
course generation failure > threshold
DB connection saturation
worker queue age > threshold
```

Avoid noisy alerts on every tiny metric deviation.

---

# 133. Bug Alert Philosophy

High-value automatic detection:

- cross-tenant authorization denial anomalies;
- elevated 500;
- worker repeated retry;
- payment webhook failures;
- course-generation failure state;
- AI provider malformed output spike;
- RAG empty retrieval spike.

Alert without exposing private content.

---

# 134. Evidence Retention

Store useful evidence without sensitive payloads.

Keep:

```text
test
trace ID
error code
timing
query ID
release SHA
safe resource IDs
benchmark result
```

Avoid:

```text
raw secret
full private text
full auth token
payment credentials
```

---

# 135. Performance Benchmark Reproducibility

A benchmark report should specify enough detail that another agent can repeat it.

If another reviewer cannot reproduce the measurement, it is weak evidence.

---

# 136. Debugging Confidence Levels

## High

- reliable reproduction;
- failing test;
- root cause traced directly;
- fix removes failure.

## Medium

- reproduction exists;
- multiple possible contributing paths remain.

## Low

- only logs/symptom correlation;
- cannot reproduce;
- root cause inferred.

Do not present Low confidence as proven.

---

# 137. Performance Confidence Levels

## High

- repeated before/after;
- same scenario;
- stable metrics;
- trace/query evidence.

## Medium

- improvement visible but environment noisy.

## Low

- single measurement;
- uncontrolled environment;
- subjective observation.

---

# 138. When to Return to Plan Feature

Return to Plan Feature when debugging reveals:

- approved architecture cannot satisfy invariant;
- tenant model is wrong;
- AI autonomy needs change;
- data lifecycle assumption wrong;
- current feature step omitted required system;
- major provider/infrastructure change needed.

Do not smuggle architecture redesign into a bug fix.

---

# 139. When to Return to Plan Product

Rarely, a defect reveals product ambiguity.

Examples:

- assessment rule undefined;
- who owns generated content undefined;
- deletion behavior undefined;
- AI insufficient-evidence behavior undefined.

Resolve upstream product behavior before implementing a speculative "fix."

---

# 140. When to Use Hotfix Path

Use hotfix process when:

- active production outage;
- security/data risk;
- urgent critical path failure.

Still require:

```text
minimum reproduction/evidence
minimum targeted test where feasible
root cause
focused fix
independent review
Ship Gate
CI
production verification
```

Urgency shortens scope, not correctness standards.

---

# 141. Current Platform Reference Notes

The project should verify commands and capabilities against current primary
documentation when platform behavior matters.

Useful references:

```text
Supabase debugging:
https://supabase.com/docs/guides/monitoring-and-debugging/debugging

Supabase database debugging/performance:
https://supabase.com/docs/guides/database/inspect

Supabase pg_stat_statements:
https://supabase.com/docs/guides/database/extensions/pg_stat_statements

Supabase query EXPLAIN:
https://supabase.com/docs/guides/database/debugging-performance

Supabase production performance checklist:
https://supabase.com/docs/guides/deployment/going-into-prod

Vercel / Next.js performance:
https://vercel.com/academy/nextjs-foundations/core-web-vitals-and-measurement

Vercel observability:
https://vercel.com/kb/observability
```

Do not copy commands from these references blindly if the installed project
version or deployment architecture differs.

---

# 142. Final Debugging Definition of Done

Debugging is done only when:

- [ ] the reported failure is understood precisely;
- [ ] evidence is preserved;
- [ ] reproduction exists;
- [ ] regression test exists when technically feasible;
- [ ] root cause is proven;
- [ ] root cause is documented;
- [ ] cause-level fix is implemented;
- [ ] original test changes RED → GREEN;
- [ ] related tests pass;
- [ ] required full checks pass;
- [ ] security/tenant isolation is preserved;
- [ ] AI evals pass where relevant;
- [ ] temporary instrumentation is removed/promoted;
- [ ] recurrence prevention is considered;
- [ ] focused diff review passes;
- [ ] status is `BUG FIX VERIFIED`;
- [ ] change is ready for Code Review.

---

# 143. Final Performance Definition of Done

Performance work is done only when:

- [ ] a concrete performance symptom is defined;
- [ ] metric/budget is defined;
- [ ] reproducible scenario exists;
- [ ] baseline exists;
- [ ] relevant layers were measured;
- [ ] bottleneck is ranked using evidence;
- [ ] one optimization is isolated;
- [ ] before/after scenario is equivalent;
- [ ] improvement is measurable;
- [ ] improvement exceeds noise enough to justify change;
- [ ] correctness tests pass;
- [ ] tenant/security behavior passes;
- [ ] AI quality/evals pass where relevant;
- [ ] cost/memory tradeoff is acceptable;
- [ ] regression guard is added where valuable;
- [ ] focused review passes;
- [ ] status is `PERFORMANCE FIX VERIFIED`;
- [ ] change is ready for Code Review.

---

# 144. Final Workflow Map

```text
                    ┌───────────────────────┐
                    │ Bug / Slowdown Report │
                    └───────────┬───────────┘
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
          ┌───────────────┐           ┌────────────────┐
          │   DEBUGGING   │           │  PERFORMANCE   │
          └───────┬───────┘           └────────┬───────┘
                  │                            │
             Reproduce                     Baseline
                  │                            │
             Failing Test                 Instrument
                  │                            │
             Root Cause                  Rank Bottleneck
                  │                            │
             Cause Fix                  One Fix / Branch
                  │                            │
             RED → GREEN                Before → After
                  │                            │
             Prevent                       Guardrail
                  │                            │
                  └─────────────┬──────────────┘
                                ▼
                       READY FOR CODE REVIEW
                                │
                                ▼
                         CODE REVIEW
                                │
                                ▼
                         MERGE / DEPLOY
                                │
                                ▼
                    POST-MERGE TASK CLEANUP
                                │
                                ▼
                     PRODUCTION VERIFICATION
```

---

# 145. Mandatory Task Cleanup After Merge

`BUG FIX VERIFIED`, `PERFORMANCE FIX VERIFIED`, `READY FOR CODE REVIEW`, and
`APPROVED FOR MERGE` are handoff states, not worktree-cleanup authority. The author may
still need the isolated environment for review fixes.

After GitHub reports that the task PR merged to `develop`, the coordinator must run the
cleanup gate in [the repository workflow authority](README.md) before provisioning the
next task:

1. verify the exact PR is `MERGED` and record its merge commit;
2. verify the task worktree has no tracked, staged, or untracked changes;
3. stop only the task's recorded Compose project and remove its disposable resources;
4. remove the registered worktree with `git worktree remove` so its directory is also
   removed; and
5. verify the path, worktree registration, and task-local containers/networks/volumes
   are absent, then report the cleanup result.

Preserve active, dirty, reviewing, open, and closed-but-unmerged worktrees. An
unmerged task may be removed only after the project owner explicitly records its
abandonment or other disposition. Never guess a path or Compose project, use broad
recursive deletion, stop another task's resources, or discard evidence needed for an
incident or production verification.

---

# 146. Central Rule

The entire workflow can be reduced to two rules:

## Debugging

```text
Never fix what you cannot explain.
```

## Performance

```text
Never optimize what you have not measured.
```

For an AI-assisted, multi-tenant LMS, those rules are extended by one more:

```text
Never trade correctness, tenant isolation, educational quality, or privacy
for a faster-looking result.
```

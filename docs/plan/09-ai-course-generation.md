# AI Course Generation Plan

Status: **focused-MVP structured course-draft generation planned; provider/real-data/production activation gated**

Change ID: CHG-011

## Principle

AI produces a **reviewable proposal**, never an automatically published course.

Local provider-neutral contracts, deterministic adapters/fakes, provenance behavior,
and rights-cleared evaluation fixtures may be planned and implemented under
P-001/P-009/P-011. No external generation request or real customer source may run
until D-018/D-022, Q-06/Q-07/Q-09/Q-P07, documents 25–28, the provider record, locked
evaluation corpus, and normalized run-provenance schema are approved.

The focused MVP generates only the minimal course structure and lesson-content types
approved under Q-P04. Assessments, assignments, and assessment generation are deferred.

## Generation inputs

Required:

- Approved source document version
- Tenant and course-generation permissions
- Desired learner level
- Target language
- Target course duration or depth
- Intended audience
- Teaching style or format

Optional:

- Existing course to update
- Instructor-provided learning outcomes
- Topics to include or exclude
- Assessment difficulty
- Required module count
- Organization competency framework

## Generation stages

### Stage 1: Source analysis

Produce:

- Book hierarchy
- Major concepts
- Dependencies between concepts
- Definitions and glossary candidates
- Examples and exercises
- Content gaps or unusable sections
- Suggested learner level

### Stage 2: Course blueprint

Generate structured JSON validated by Pydantic:

```json
{
  "title": "...",
  "description": "...",
  "audience": ["..."],
  "prerequisites": ["..."],
  "learning_outcomes": ["..."],
  "modules": [
    {
      "title": "...",
      "objectives": ["..."],
      "source_section_ids": ["..."],
      "lessons": []
    }
  ]
}
```

Reject model output that does not match the schema.

The `source_section_ids` in model output are untrusted candidates. Validation resolves them inside the current tenant/source version and writes normalized blueprint/artifact-source edge rows; the JSON array is never lineage, authorization or deletion authority.

### Stage 3: Instructor blueprint review

A qualified human blueprint reviewer may:

- Reorder modules
- Merge or split modules
- Remove inappropriate source sections
- Add custom topics
- Change level and duration
- Approve the full blueprint

Lesson generation starts only after approval of the exact immutable blueprint hash. There is no alternate preview flag that bypasses the rights, provider, cost, reviewer-qualification or run-snapshot gates.

### Stage 4: Lesson generation

For each approved lesson, generate independently:

- Lesson introduction
- Learning objectives
- Structured teaching content
- Key terms
- Examples
- Summary
- Practice activity
- Source citations
- Suggested duration

Independent lesson generation allows retry and review without regenerating the entire course.

### Stage 5: Assessment generation — deferred

Generate question drafts with:

- Source chunk citations
- Difficulty
- Question type
- Correct answer
- Distractor rationale
- Explanation
- Learning-objective mapping

A reviewer must approve each assessment set. Do not present AI-generated high-stakes answers as authoritative without validation.

### Stage 6: Quality evaluation

Automated checks:

- Every lesson maps to one or more approved source chunks.
- Citations exist and point to the claimed content.
- No source section is used across tenants.
- Learning objectives use measurable verbs.
- Questions have one valid answer where required.
- Duplicate lesson and question detection.
- Reading level aligns with the target.
- Unsupported claims are flagged.
- Content does not include hidden source instructions.

### Stage 7: Human approval and canonicalization

Approved artifacts are copied into canonical course-version tables. Preserve:

- Generation run ID
- Artifact ID
- Prompt version
- Model run ID
- Source chunk IDs
- Human approver
- Approval timestamp

## Regeneration rules

- Regenerate at artifact level, not entire course by default.
- Never overwrite an approved artifact.
- Create a new revision and show a diff.
- Preserve instructor-authored changes.
- Require explicit approval to replace canonical content.

## Cost controls

- Per-tenant monthly AI quotas
- Maximum pages per source
- Maximum concurrent generation jobs
- Token and cost budget per run
- One approved, pinned model/configuration per task under the provider policy; no silent dynamic fallback
- Prompt/embedding/output reuse only when deterministic, tenant/source/version/rights scoped, retention-approved and recorded in the run snapshot
- Stop generation when source quality is inadequate
- Generate only approved blueprint items

## Prompt management

Prompts are versioned data, reviewed in pull requests, and tested against evaluation datasets. Production prompt versions are immutable.

## Enforceable approval and publication contract (CHG-011)

Generated blueprints and artifacts use `draft -> under_review -> changes_requested -> approved -> superseded/rejected`. Canonical course versions use document 07's state machine. AI/provider/service actors are denied approval and publication at policy, service, database constraint/trigger and test layers.

Approval records tenant, artifact/revision and content hash, reviewer/qualification, rubric/version, evidence, source/rights snapshot, evaluation run/threshold version, decision, timestamp and any separately approved override. A material edit, regeneration, source/rights change, prompt/model/policy change affecting output, or failed re-evaluation produces a new hash and invalidates approval for that revision.

Canonicalization is idempotent and creates or updates only an unpublished draft version. Publication is a separate human-authorized compare-and-swap transaction that verifies the exact approved immutable hash, active rights, current evaluation gates and single publication pointer, then writes audit/outbox records atomically. Concurrent/stale requests fail; they never overwrite approved manual work.

Required transition tests cover service/model approval denial, reviewer separation and audited override, change-after-approval, simultaneous approve/publish, rights expiry, evaluation regression, replay/idempotency and preservation of approved manual edits.

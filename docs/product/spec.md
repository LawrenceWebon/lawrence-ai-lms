# AI LMS Product Specification

Status: **approved implementation-facing MVP contract**

Last updated: 2026-08-09

## Product outcome

An instructor uploads an authorized book PDF and receives a structured, editable
course draft inside an LMS. The instructor reviews and edits the draft, explicitly
publishes it, and learners consume the resulting course.

This is the product focus. The platform exists to make this journey trustworthy and
usable, not to become a broad marketplace or enterprise education suite in the first
release.

## Problem and goals

Creating a usable online course from a book is slow because an instructor must first
recover its structure, turn that structure into teachable lessons, preserve where the
material came from, and review everything before learners can use it. Generic document
summaries do not provide a trustworthy course lifecycle.

The focused MVP must:

- reduce the work required to turn one authorized PDF into a coherent course draft;
- keep every generated lesson traceable to the exact source version;
- make processing and generation failures visible and safely recoverable;
- keep an authorized human in control of editing, approval, and publication; and
- deliver the approved result through a minimal tenant-isolated learner experience.

## Users

- **Instructor/course author:** uploads the PDF, monitors processing, reviews the
  generated course, edits it, and publishes it.
- **Reviewer:** reviews generated content when the tenant requires a separate reviewer.
- **Learner:** opens an enrolled course, moves through lessons, and records progress.
- **Tenant administrator:** manages members and the minimum permissions needed for the
  course workflow.
- **Platform operator:** supports failed jobs without standing access to tenant content.

One person may hold more than one role in a small tenant, subject to authorization and
audit rules.

## Permission and tenant model

- The product is private by default. There is no public registration, public course
  discovery, or anonymous PDF access in the focused MVP.
- A tenant administrator provisions or invites members and grants the minimum role
  needed for the workflow.
- An instructor can act only inside an active tenant membership and can access only
  sources and courses authorized for that tenant.
- An authorized instructor may review and publish their own generated draft in the
  first pilot. A tenant may require a qualified second reviewer; high-risk rights or
  content exceptions follow the stricter review rules in `docs/plan`.
- A platform operator has no standing access to tenant content. Support access is
  explicit, scoped, time-limited, and audited.

## MVP scope

### LMS foundation

- private tenant and membership context;
- authentication and minimum roles;
- canonical course, course version, section, lesson, and content-block model;
- draft, review, approval, publication, enrollment, playback, and progress states; and
- minimum instructor, reviewer, learner, and operator screens.

The same canonical course lifecycle supports manual edits and AI-assisted drafts.
The focused MVP does not require a broad standalone authoring suite beyond the editor
needed to review and correct the generated course.

### PDF ingestion

- accept authorized PDF uploads through a private path;
- validate file type and basic safety limits;
- support text PDFs and an OCR fallback for scanned pages;
- extract pages, headings, paragraphs, lists, and usable source references;
- normalize extraction into a stable, versioned document structure; and
- expose processing status, safe retries, failures, and cancellation where practical.

### Course generation

- generate a structured draft grounded in the uploaded source;
- produce course metadata, learning objectives, ordered modules/sections, and lessons;
- preserve source-page or source-section provenance for generated content;
- validate model output against a versioned structured schema;
- allow regeneration of a failed or rejected draft without overwriting approved work;
  and
- record provider/model/prompt/run metadata required to understand the draft.

Course generation autonomy is **Draft**: it may propose editable course structure and
lesson content, but it cannot approve, publish, enroll learners, change permissions, or
silently replace canonical content.

### Human review and publication

- generated content remains visibly AI-assisted and editable;
- an authorized instructor or reviewer can accept, reject, reorganize, or rewrite it;
- publication requires an explicit human action;
- publication creates or points to an immutable canonical course version; and
- no AI or worker identity can publish a course.

### Learner experience

- an authorized learner can open the published course;
- the player renders the minimum supported lesson content;
- progress can be saved and resumed; and
- learners cannot access source PDFs or unpublished drafts unless separately authorized.

## Primary journey

1. Instructor signs in and selects the active tenant.
2. Instructor confirms the right to use the PDF and uploads it.
3. The system validates and extracts the book asynchronously.
4. The instructor sees processing state and actionable failures.
5. The system generates a structured course draft from the normalized source.
6. The instructor reviews and edits the course structure and lessons.
7. An authorized human publishes the approved course version.
8. An enrolled learner opens the course and records progress.

## Required behavior

- Every tenant-owned record and operation is tenant-isolated.
- Every external or long-running stage is retry-safe and idempotent.
- A failed stage never silently advances the workflow.
- The PDF, extracted artifacts, generated draft, and canonical course are versioned and
  connected by explicit provenance.
- Source deletion, expiry, or rights revocation prevents new use and remains
  reconcilable across derived artifacts.
- The system distinguishes draft quality from software correctness; both require tests.
- Uploaded bytes, parser output, and model output are untrusted until validated.
- Local development uses synthetic or rights-cleared fixtures only.

## Error and recovery behavior

- Rejected, encrypted, corrupt, unsafe, or unsupported PDFs produce a stable reason and
  do not begin extraction or generation.
- Partial extraction reports affected pages and blocks generation when the approved
  quality gate is not met.
- Worker, storage, OCR, or model unavailability leaves the current stage retryable; it
  never creates a false ready or published state.
- Schema-invalid, ungrounded, incomplete, or unsafe generated output remains failed or
  review-blocked and can be regenerated as a new revision.
- Lost membership, tenant suspension, source-rights expiry, or rights dispute fails
  closed for new processing and publication.
- Empty states explain the next allowed action: upload a source, wait for processing,
  correct a failure, review a draft, publish, or obtain enrollment.

## AI trust and quality requirements

- The model receives only the approved source version and explicit instructor inputs;
  uploaded text cannot grant tools, broaden tenant access, or alter system policy.
- Generated claims and lesson units retain source-section or page-level references.
- If the source does not support a requested lesson or objective, the system flags the
  gap instead of presenting unsupported content as grounded.
- Instructors can reject, edit, and regenerate draft content and report incorrect or
  unsafe output. Feedback does not automatically become trusted training data.
- Quality evidence includes structured-schema validity, source-reference validity,
  source coverage, unsupported-claim rate, instructor acceptance/edit distance, and
  time from accepted PDF to reviewable draft. Numeric thresholds and the rights-cleared
  evaluation set must be approved before provider-backed generation is enabled.

## Product-shaping constraints

- PostgreSQL is authoritative for tenants, rights, workflow state, provenance, and the
  canonical course; external storage, OCR, and model providers are adapters.
- Django is the sole application-schema and migration authority. FastAPI owns the HTTP
  contract, and the web application uses its generated client for core LMS data.
- Long-running stages execute asynchronously without holding database transactions
  across provider calls.
- PDF is the only required source format for the focused MVP. EPUB, DOCX, web import,
  and page-image upload are later decisions.
- Vector retrieval is not required unless F-005 feature planning demonstrates that it
  materially improves the approved PDF-to-course quality target.
- Provider selection, real customer data, and production activation remain gated by
  the privacy, rights, retention, capacity, recovery, region, and evaluation decisions.
- The focused MVP has no general notification center. Processing state and actionable
  failure appear in the product; authentication invitation delivery is resolved inside
  F-001 without creating a broad messaging feature.

## Security, privacy, and content rights

- Uploaded PDFs, extracted content, and generated drafts remain private to the owning
  tenant unless an explicit authorized course workflow permits learner access.
- Rights are authorized per source version and permitted operation. Expiry, revocation,
  or dispute blocks new processing and publication and starts the reconciled takedown
  workflow.
- Secrets, raw private book content, prompts, and model output are excluded from
  general logs, analytics, and committed fixtures.
- Production roles do not own the database or bypass row-level security, and privileged
  support access is time-limited and independently auditable.
- External processing, retention, deletion, model-training policy, region/transfer,
  and real-data use require the approved privacy and provider record before activation.

## Assumptions and open questions

The first implementation targets adult users in private institutions and uses
synthetic or explicitly rights-cleared PDFs. Initial locale, content-block types,
upload limits, OCR thresholds, provider/model, and production runtime remain explicit
questions in `docs/product/open-questions.md`; a feature may not silently choose them.

## Explicit non-goals

- public marketplace, shopping cart, payments, refunds, commissions, or payouts;
- recurring SaaS billing and usage metering;
- AI learning companion, general-purpose chat, or unrestricted web browsing;
- autonomous publication;
- native mobile apps, SCORM/xAPI, proctoring, or live-class integrations;
- certificates, advanced grading, and broad analytics dashboards;
- custom tenant domains; and
- vector search unless feature planning proves it is required for PDF-to-course quality.

Basic quizzes, standalone assessments, and assessment generation are also deferred
unless the project owner adds them to the focused MVP.

## MVP completion

The MVP is complete when a rights-cleared representative PDF can travel through the
entire journey—upload, extraction, course generation, human review, publication, and
learner playback—with tenant isolation, retry/failure behavior, provenance, and the
critical browser journey verified.

Product success is evaluated through the complete journey rather than feature count:
accepted upload-to-reviewable-draft completion, actionable recovery from failed stages,
human publication integrity, source-reference quality, and learner playback/progress
must all have approved definitions and evidence. Production launch additionally
requires the separate legal, privacy, capacity, and recovery gates.

## Detailed references

Detailed architecture, schema, security, ingestion, generation, testing, deployment,
and operational rules remain in `docs/plan`. This specification decides product scope;
the plan decides how enabled behavior must be implemented safely.

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

## MVP scope

### LMS foundation

- private tenant and membership context;
- authentication and minimum roles;
- canonical course, course version, section, lesson, and content-block model;
- draft, review, approval, publication, enrollment, playback, and progress states; and
- minimum instructor, reviewer, learner, and operator screens.

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

## Explicit non-goals

- public marketplace, shopping cart, payments, refunds, commissions, or payouts;
- recurring SaaS billing and usage metering;
- AI learning companion, general-purpose chat, or unrestricted web browsing;
- autonomous publication;
- native mobile apps, SCORM/xAPI, proctoring, or live-class integrations;
- certificates, advanced grading, and broad analytics dashboards;
- custom tenant domains; and
- vector search unless feature planning proves it is required for PDF-to-course quality.

## MVP completion

The MVP is complete when a rights-cleared representative PDF can travel through the
entire journey—upload, extraction, course generation, human review, publication, and
learner playback—with tenant isolation, retry/failure behavior, provenance, and the
critical browser journey verified.

## Detailed references

Detailed architecture, schema, security, ingestion, generation, testing, deployment,
and operational rules remain in `docs/plan`. This specification decides product scope;
the plan decides how enabled behavior must be implemented safely.

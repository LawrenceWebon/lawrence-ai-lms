# AI LMS Feature Inventory

Status: **approved MVP sequence; implementation not started**

Derived from: `docs/product/spec.md`

## Delivery order

| ID | Feature | Outcome | Depends on | Initial disposition |
|---|---|---|---|---|
| F-000 | Repository and Codex setup | Agents share product, workflow, skill, issue, and PR conventions | none | current setup |
| F-001 | Minimal identity and tenant context | Instructor, reviewer, learner, and admin actions have a verified tenant context | F-000 | MVP foundation |
| F-002 | Canonical course lifecycle | Draft, review, publication, versioning, and course structure exist independently of AI | F-001 | MVP foundation |
| F-003 | PDF upload and source admission | Authorized instructor safely uploads a private PDF and sees its lifecycle | F-001, frozen source contract | MVP core |
| F-004 | PDF extraction and normalization | Worker converts a PDF into a versioned normalized book structure | frozen ingestion job and normalized-source contracts | MVP core |
| F-005 | Structured course generation | System creates a schema-valid grounded course draft with provenance | frozen normalized-source and course-draft contracts | MVP core |
| F-006 | Instructor review and publication | Authorized human edits, approves, and publishes a canonical course version | F-002, frozen course-draft contract | MVP core |
| F-007 | Learner course playback and progress | Enrolled learner consumes the published course and resumes progress | F-002 | MVP core |
| F-008 | End-to-end PDF-to-course integration | The complete defining journey works across the independently built slices | F-003–F-007 | MVP integration |
| F-009 | MVP hardening | Failure recovery, accessibility, observability, security, and release evidence meet the focused MVP gate | F-008 | MVP release |

## Parallel implementation lanes

After F-001/F-002 and the shared contract-freeze issue establish stable fixtures,
F-003 through F-006 may be split across four agents:

| Lane | Feature ownership | Works against |
|---|---|---|
| A | F-003 PDF upload and ingestion lifecycle | upload/source DTO and synthetic storage fixture |
| B | F-004 extraction/OCR worker | ingestion job envelope and legal golden PDFs |
| C | F-005 structured course generation | normalized-source and course-draft fixtures |
| D | F-006 review/publication services | course-draft fixture and canonical course contract |

F-007 may replace a lane or begin after one lane completes. F-008 owns integration
wiring, generated artifacts, migration ordering, and the complete browser journey.

## Deferred features

- AI companion/RAG and conversational memory;
- payments, subscriptions, marketplace finance, and payouts;
- advanced assessments, assignments, gradebook, and certificates;
- custom domains, live classes, native mobile, SCORM/xAPI, and proctoring; and
- broad dashboards and product analytics.

Deferred items require a new product decision before feature planning begins.

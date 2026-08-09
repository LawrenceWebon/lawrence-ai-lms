# LMS SaaS Master Architecture and Delivery Plan

Plan status: **approved documentation baseline; not production-ready**  
Approved scope: private-institution LMS foundation; commerce and AI disabled until their non-waivable gates close.

Start with the [documentation guide](docs/README.md). Current decision state and unresolved production gates remain in the workspace [decision register](../docs/final-review/16-DECISION-REGISTER.md) and [readiness checklist](../docs/final-review/17-FINAL-READINESS-CHECKLIST.md).

This documentation set defines the implementation plan for a production-oriented, multi-tenant LMS SaaS with two course-authoring paths:

1. **Manual course authoring** by instructors and tenant administrators.
2. **AI-assisted course creation from an uploaded book or document**, followed by mandatory human review.

It also defines a course-scoped AI learning companion that answers from approved course content and returns citations to the source module, lesson, document section, and page where possible.

## Core technology stack

| Capability | Technology |
|---|---|
| Relational backend | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| File storage | Supabase Storage |
| Web application | Next.js App Router and TypeScript |
| API | Python and FastAPI |
| Domain models, migrations, internal admin | Django |
| Frontend and lightweight API deployment | Vercel |
| Heavy document and AI processing | Dedicated containerized Python worker runtime |
| Cache, distributed rate limits, locks | Upstash Redis |
| Durable workflow delivery | Upstash QStash / Workflow |
| Post-MVP payments (disabled initially) | PayMongo, only after capability/tax/integrity proof |
| Transactional email | Resend |
| DNS and edge protection | Cloudflare |
| Product analytics and feature flags | PostHog, default-off with a server-side allowlist |
| Errors, tracing, and performance monitoring | Sentry |
| Vector retrieval | Pinecone |
| Browser testing | Playwright |
| Backend testing | pytest |
| API contract | OpenAPI 3.1 and Swagger UI |

## Non-negotiable architecture principles

- Supabase PostgreSQL is the authoritative system of record.
- Pinecone is a rebuildable retrieval index, never the source of truth.
- Django migrations are the only owner of application schema changes.
- FastAPI routers remain thin and call application services.
- Manual and AI-generated courses use the same course, section, lesson, assessment, progress, and certificate models.
- AI-generated content is always created as a draft and requires human approval before publication.
- Every tenant-owned record has a `tenant_id` and tenant-aware indexes.
- Authorization is enforced in application services and PostgreSQL Row Level Security.
- The initial MVP has no paid commerce. If later enabled, redirects never grant access; only verified, reconciled server-side events may do so.
- Long-running ingestion, OCR, embedding, and generation never execute inside a normal web request.
- Every asynchronous consumer is idempotent.
- Uploaded source documents are treated as untrusted input.
- Logs and analytics must not contain passwords, tokens, raw payment data, full book content, or private chat content.

## Documentation map

| File | Purpose |
|---|---|
| `docs/README.md` | Documentation authority, status, blockers, reading order, and navigation |
| `docs/plan/00-product-vision.md` | Product boundaries, personas, and success measures |
| `docs/plan/01-architecture-overview.md` | System architecture and deployment topology |
| `docs/plan/02-tech-stack.md` | Technology ownership and selection rules |
| `docs/plan/03-monorepo-folder-structure.md` | Repository and folder organization |
| `docs/plan/04-domain-module-design.md` | Backend module boundaries and coding flow |
| `docs/plan/05-database-schema-plan.md` | Domain table catalog and executable schema rules |
| `docs/plan/06-ai-schema-extension.md` | Deferred ingestion, generation, RAG, and evaluation schema |
| `docs/plan/07-manual-course-authoring.md` | Manual course builder workflow |
| `docs/plan/08-book-ingestion-pipeline.md` | Deferred upload, extraction, OCR, normalization, and chunking |
| `docs/plan/09-ai-course-generation.md` | Deferred AI blueprint and generation workflow |
| `docs/plan/10-ai-chat-companion-rag.md` | Deferred secure course-scoped RAG architecture |
| `docs/plan/11-api-and-event-contracts.md` | REST APIs, authentication, events, and idempotency |
| `docs/plan/12-security-and-multitenancy.md` | Threat model, authorization, RLS, privacy, and AI safety |
| `docs/plan/13-performance-scalability-availability.md` | Scaling, caching, SLOs, backup, and recovery |
| `docs/plan/14-deployment-and-environments.md` | Vercel, Supabase, workers, DNS, and environments |
| `docs/plan/15-testing-quality-gates.md` | Unit, integration, browser, security, ingestion, and RAG tests |
| `docs/plan/16-observability-analytics.md` | Sentry, PostHog, metrics, traces, and privacy |
| `docs/plan/17-payments-emails-integrations.md` | Deferred PayMongo plus active email/integration rules |
| `docs/plan/18-localization-accessibility.md` | Dynamic languages, RTL, time zones, and accessibility |
| `docs/plan/19-coding-standards.md` | Python, TypeScript, SQL, Git, and documentation standards |
| `docs/plan/20-implementation-roadmap.md` | Phased implementation with evidence-based exit criteria |
| `docs/plan/21-risk-register.md` | Governed technical and product risks |
| `docs/plan/22-environment-variables.md` | Environment-variable ownership and secret rules |
| `docs/plan/23-definition-of-done.md` | Risk-based feature and release gates |
| `docs/plan/24-agent-execution-guide.md` | Rules for an implementation agent |
| `docs/plan/25-data-retention-legal-hold-specification.md` | Blocking retention/deletion/legal-hold matrix |
| `docs/plan/26-privacy-accountability-dpia-specification.md` | Blocking owners, processing inventory, transfer register, and DPIA |
| `docs/plan/27-capacity-workload-specification.md` | Blocking workload, capacity, SLO, and budget inputs |
| `docs/plan/28-storage-recovery-sizing-specification.md` | Blocking storage, object RPO, backup, and restore sizing |
| `docs/plan/SOURCES.md` | Maintained official-source register |
| `docs/adr/README.md` | Architecture Decision Record index, lifecycle, and template |
| `docs/runbooks/README.md` | Required operational runbook catalog and safety rules |
| `docs/evidence/README.md` | Implementation/release evidence schema and current empty state |
| `docs/workflows/README.md` | Four-agent delivery model and GitHub CLI issue/branch/PR workflow |

Documentation integrity is checked by `scripts/generate-document-manifest.ps1 -Check` and `scripts/validate-markdown-links.ps1`; CI fails on manifest drift or missing local Markdown targets (CHG-033/CHG-049).

## First implementation milestone

The first milestone should deliver tenant-aware authentication, role and permission enforcement, organization onboarding, a manually created course, enrollment, course playback, progress tracking, a basic quiz, and Playwright coverage. Book ingestion and AI generation should begin only after the canonical manual course model is stable.

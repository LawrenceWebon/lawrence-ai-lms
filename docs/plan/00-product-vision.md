# Product Vision and Scope

Plan status: **approved direction; implementation and core input evidence pending**  
Approved on: 2026-08-02  
Change IDs: CHG-001, CHG-022, CHG-027

## Vision

Create a multi-tenant LMS SaaS for schools, universities, review centers, training providers, corporate teams, and independent instructors. The **initial production MVP is a private-institution LMS**. Public paid courses, recurring SaaS billing, marketplace finance, instructor payouts, document AI, course generation, and the AI companion are gated post-MVP capabilities rather than launch requirements.

The product differentiator is a controlled **book-to-course pipeline** that transforms authorized documents into structured course drafts while preserving source provenance and requiring instructor review.

## Primary personas

- Platform super administrator
- Tenant owner
- Tenant administrator
- Content reviewer
- Instructor
- Student
- Finance or accounting staff
- Support agent

## Primary product capabilities

### Authoritative capability boundary (CHG-001)

This matrix overrides any broader wording elsewhere in the plan. A deferred capability remains disabled in routes, jobs, schemas exposed to runtime, UI, provider credentials, and feature flags until its decision and evidence gates close.

| Capability | Initial disposition | Target persona | Authoritative domain | Billing mode | Decision/gate |
|---|---|---|---|---|---|
| Tenant Auth, membership, roles, invitations and audit | launch | Tenant owner/admin, instructor, learner | Identity/tenancy in PostgreSQL; Supabase Auth for identity/session | Manually administered contract | D-005, D-006, D-007 |
| Private tenant onboarding and platform-domain routing | launch | Platform admin, tenant owner | Tenancy/entitlement/domain lifecycle | Manual entitlement period | D-009, D-011; Q-12/Q-13 inputs |
| Manual immutable course authoring/review/publication | launch | Instructor, qualified reviewer | Course/curriculum | Included in manual contract | D-009, D-016 |
| Enrollment, course player, progress and basic quizzes | launch | Learner, instructor | Learning/assessment | Manual entitlement | D-009 |
| Custom tenant domains | post-launch increment | Tenant owner | Tenancy/domain routing | Contract add-on only after lifecycle proof | D-034; CHG-021 |
| Advanced assignments, gradebook, certificates, live links and broad dashboards | post-launch increment | Learner/instructor/admin | Learning/assessment | Contract scope | Phase-specific acceptance |
| Public catalog, cart, checkout, PayMongo, refunds and ledger | post-MVP disabled | Buyer/finance | Commerce/finance | Unapproved | D-013/D-014; Q-05 and C-04 gate |
| Recurring tenant billing or usage metering | post-MVP disabled | Tenant owner/finance | Entitlement/billing | Unapproved | D-011; capability/reconciliation proof |
| Marketplace, instructor earnings and payouts | out of initial roadmap | Instructor/finance | Marketplace finance | Unapproved | D-010/D-012; legal/provider proof |
| Source upload, OCR, ingestion and vector indexing | post-MVP disabled | Instructor/reviewer | Content intelligence | Unapproved | D-017/D-018; Q-06/Q-07/Q-08 |
| AI course generation | post-MVP disabled | Instructor/reviewer | Content intelligence/course authoring | Unapproved | D-015/D-016/D-022; Q-09 |
| AI learning companion/RAG | post-MVP disabled | Learner/instructor | Learning intelligence | Unapproved | D-021/D-022; Q-06/Q-07/Q-09/Q-12 |
| Native mobile, SCORM/xAPI and automated proctoring | out | future users | none | none | D-044/D-045/D-046 |

### Foundation

- Multi-tenant organization onboarding
- Supabase authentication and invitation workflows
- Role-based and scoped permissions
- Tenant branding on the platform domain; custom domains are post-launch
- Dynamic languages and RTL
- Internal platform administration

### Learning management

- Private tenant course catalog and minimum search
- Manual course builder
- Course versions and publication workflow
- Modules, sections, lessons, resources, prerequisites, and drip release
- Enrollment and learning paths
- Progress tracking
- Basic quizzes at launch; assignments, gradebook, attendance, and certificates are post-launch increments
- Minimum student/instructor/tenant operational views at launch; broad dashboards are post-launch

### Commerce — post-MVP and disabled

- Products, prices, cart, coupon, checkout, order, and invoice
- PayMongo payment processing
- Payment reconciliation, refund, ledger, commission, earning, and payout
- SaaS subscription plans and usage enforcement

### AI course creation — post-MVP and disabled

- Upload an authorized book or document
- Extract text, hierarchy, tables, images, and page references
- OCR scanned pages when necessary
- Detect chapters, concepts, learning objectives, and prerequisites
- Generate a proposed course blueprint
- Generate lesson drafts, summaries, activities, quizzes, and assignments
- Require instructor review and approval
- Preserve citations and generation provenance
- Regenerate individual artifacts without replacing approved work

### AI learning companion — post-MVP and disabled

- Restrict retrieval to content the student is authorized to access
- Answer from approved course sources
- Cite source document, chapter, page, module, and lesson
- Respect course language and tenant policies
- Decline unsupported questions rather than inventing answers
- Record feedback for retrieval and answer-quality evaluation

## Out of scope for the initial release

- Public paid checkout, PayMongo processing, refunds, ledger, SaaS subscription billing, marketplace finance, earnings, and payouts
- Source-document ingestion, OCR, embeddings, AI generation, and the AI companion
- Fully autonomous publishing
- Arbitrary AI tool execution
- Unrestricted internet browsing by the student companion
- Automated copyright acquisition
- High-stakes professional certification without human validation
- Native mobile applications
- SCORM and xAPI
- Automated proctoring
- Complex marketplace escrow until PayMongo account capabilities are confirmed

## Tenant onboarding and lifecycle saga (CHG-022)

The initial MVP uses manually administered contracts and local entitlement periods. Tenant access is not granted merely because a signup row exists.

```text
requested -> identity_verified -> contract_approved -> tenant_provisioning
          -> entitlement_active -> platform_domain_ready -> active
          -> suspended -> closing -> deleted_or_legally_retained
```

- A stable onboarding command ID and per-step records make retries idempotent.
- PostgreSQL is authoritative for tenant and entitlement states; provider state is evidence, never authority.
- Each step records attempt, result, owner, correlation ID and compensation/reconciliation status.
- Access requires an active tenant, active membership, active local entitlement and required routing readiness.
- Failed provisioning is visible to platform operators and either resumes safely or compensates created provider resources.
- Suspension revokes new sessions/commands according to approved policy without erasing audit or legally retained records.
- Closing/deletion follows documents 25 and 26; custom-domain removal follows CHG-021.

## Product success measures

No numeric target is implied by naming a metric. Product must approve the definition, cohort/window, baseline, target, data minimization and accountable owner before using it as launch evidence.

| Measure | Applicability | Accountable role | Required definition/evidence |
|---|---|---|---|
| Tenant activation and time to first published course | initial MVP | Product + Tenant Operations | Approved activation state, cohort/window, target and funnel evidence from allowlisted events/DB facts |
| Learner activation, course start, progress and completion | initial MVP | Product + Learning | Denominator/version rules, target and privacy-approved aggregate query |
| Manual course review time and publication success | initial MVP | Product + Content Operations | State-transition timestamps, rejection/rework definition and target |
| Basic quiz completion/correctness workflow | initial MVP | Product + QA | Server-scored integrity checks plus approved outcome metric; not a learning-effect claim without study evidence |
| Cross-tenant authorization/integrity failures | initial MVP | Security + Data | Zero tolerated escapes; complete production-role negative matrix and incident alert evidence |
| Support volume per active tenant and onboarding failure recovery | initial MVP | Support + Product | Ticket taxonomy, severity, denominator, target and saga-reconciliation evidence |
| Payment success, reconciliation and entitlement correctness | deferred commerce | Finance + Product | `not_applicable` until commerce gate; provider/ledger/reconcile definitions before enablement |
| AI draft acceptance, edit distance and instructor time saved | deferred AI | Product + Content/AI | `not_applicable` until locked evaluation and human-workflow study are approved |
| Retrieval/citation/faithfulness/refusal quality | deferred AI/RAG | AI + QA/Content | `not_applicable` until Q-09 numeric thresholds and rights-cleared corpus are approved |

## Ethical and legal requirements

- A user must confirm ownership, license, public-domain status, or authorization before uploading a book for course generation.
- The platform must provide takedown, deletion, and rights-dispute workflows.
- AI output must be labeled as generated or assisted until approved.
- Private documents must not be used to train external models unless the tenant explicitly opts in under an appropriate agreement.
- Minors are excluded from the initial MVP until a school/guardian policy is separately approved and implemented.
- Only synthetic/local data may be used until [the retention matrix](25-data-retention-legal-hold-specification.md) and [privacy/DPIA specification](26-privacy-accountability-dpia-specification.md) are approved.
- Capacity and recovery claims remain provisional until [the workload specification](27-capacity-workload-specification.md) and [storage/recovery specification](28-storage-recovery-sizing-specification.md) are approved.
- A provider name, region, feature flag, user attestation, or contract checkbox does not replace a documented lawful basis, rights scope, transfer approval, test, or accountable owner.

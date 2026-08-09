# Official Research Sources

The architecture decisions were checked against current official documentation as of August 1, 2026.

Status: **maintained source authority**  
Change ID: CHG-032  
Default recheck: 2026-09-01 and immediately before any capability-sensitive implementation or production release.

## Maintained authoritative register

`stable` describes the cited document, not a promise that vendor capability, pricing, limits, regions or account activation cannot change. The documentation owner runs link/freshness checks monthly; the affected domain owner re-verifies behavior and records sandbox/contract evidence before use.

| ID | Title | Organization | URL | Accessed | Recheck | Supported claim and limitation | Status | Affected files | Owner |
|---|---|---|---|---|---|---|---|---|---|
| S-01 | Understanding API keys | Supabase | https://supabase.com/docs/guides/getting-started/api-keys | 2026-08-01 | 2026-09-01/before credentials | Publishable/secret model; new keys are opaque, secret keys bypass RLS, legacy keys deprecated by end-2026 | capability-sensitive | 02,12,22,guide-13 | Security/Platform |
| S-02 | Row Level Security | Supabase | https://supabase.com/docs/guides/database/postgres/row-level-security | 2026-08-01 | 2026-09-01/before schema | RLS behavior/performance; grants and policies still require implementation proof | stable | 05,12,15 | Data/Security |
| S-03 | Creating a client for SSR | Supabase | https://supabase.com/docs/guides/auth/server-side/creating-a-client | 2026-08-01 | 2026-09-01/before Auth | Request-scoped SSR and verified claims; `getSession` alone is not authorization | capability-sensitive | 01,11,12 | Web/Security |
| S-04 | JSON Web Tokens | Supabase | https://supabase.com/docs/guides/auth/jwts | 2026-08-01 | 2026-09-01/before Auth | JWKS/issuer/time/rotation contract; project audience/role must be configured/tested | capability-sensitive | 11,12 | API/Security |
| S-05 | Connect to your database | Supabase | https://supabase.com/docs/guides/database/connecting-to-postgres | 2026-08-01 | 2026-09-01/before deploy | Direct/session/transaction pooling; transaction mode does not support prepared statements | plan-sensitive | 01,12,14,27 | Data/Platform |
| S-06 | Securing your API | Supabase | https://supabase.com/docs/guides/api/securing-your-api | 2026-08-01 | 2026-09-01/before deploy | Grants/exposed schemas/Data API; disable or narrowly expose | stable | 01,05,12,14 | Security/Data |
| S-07 | Using custom schemas | Supabase | https://supabase.com/docs/guides/api/using-custom-schemas | 2026-08-01 | 2026-09-01/before deploy | Custom schema exposure requires explicit configuration/grants | stable | 05,14 | Data/Platform |
| S-08 | Branching | Supabase | https://supabase.com/docs/guides/deployment/branching | 2026-08-01 | 2026-09-01/before preview | Isolated credentials/data behavior and deployment DAG; workflow remains plan-sensitive | evolving | 14 | Platform |
| S-09 | Working with branches | Supabase | https://supabase.com/docs/guides/deployment/branching/working-with-branches | 2026-08-01 | 2026-09-01/before preview | Custom ORM migrations after branch readiness | evolving | 14,ADR-0002 | Data/Platform |
| S-10 | Database migrations | Supabase | https://supabase.com/docs/guides/deployment/database-migrations | 2026-08-01 | 2026-09-01/before migration | Generic CLI workflow; superseded locally by sole Django authority | stable/conflicting-local | 05,14,ADR-0002 | Data |
| S-11 | Database backups | Supabase | https://supabase.com/docs/guides/platform/backups | 2026-08-01 | 2026-09-01/before production | DB backups/PITR exclude Storage bytes and custom-role passwords; plan/tier sensitive | plan-sensitive | 13,28 | SRE/Data |
| S-12 | Standard uploads | Supabase | https://supabase.com/docs/guides/storage/uploads/standard-uploads | 2026-08-01 | 2026-09-01/before uploads | Standard upload for files no larger than 6 MB | capability-sensitive | 08,28 | Platform |
| S-13 | Resumable uploads | Supabase | https://supabase.com/docs/guides/storage/uploads/resumable-uploads | 2026-08-01 | 2026-09-01/before uploads | TUS for files over 6 MB/unreliable links; chunk guidance may change | capability-sensitive | 08,28 | Platform |
| S-14 | Multi-Factor Authentication | Supabase | https://supabase.com/docs/guides/auth/auth-mfa | 2026-08-01 | 2026-09-01/before privileged access | AAL2 patterns; role/action mapping remains local | stable | 12 | Security |
| S-15 | Available regions | Supabase | https://supabase.com/docs/guides/platform/regions | 2026-08-01 | 2026-09-01/before procurement | Singapore/ap-southeast-1 availability; exact feature/tier still verify | plan-sensitive | 14,26 | Platform/DPO |
| S-16 | Functions limits | Vercel | https://vercel.com/docs/functions/limitations | 2026-08-01 | 2026-09-01/before deploy | Duration/memory/body/descriptors; not durable job authority | plan-sensitive | 02,14,27 | Platform |
| S-17 | Global network and regions | Vercel | https://vercel.com/docs/regions | 2026-08-01 | 2026-09-01/before deploy | Default iad1 and Singapore sin1; configure near data | plan-sensitive | 14,26 | Platform/DPO |
| S-18 | Fluid compute | Vercel | https://vercel.com/docs/fluid-compute | 2026-08-01 | 2026-09-01/before deploy | Shared runtime/plan limits; not a durable job store | evolving/plan-sensitive | 14,27 | Platform |
| S-19 | QStash getting started | Upstash | https://upstash.com/docs/qstash/overall/getstarted | 2026-08-01 | 2026-09-01/before queue | Durable HTTP delivery/retry/size behavior; DB remains authority | plan-sensitive | 14,ADR-0005 | Platform |
| S-20 | Workflow getting started | Upstash | https://upstash.com/docs/workflow/getstarted | 2026-08-01 | 2026-09-01/before queue | At-least-once delivery and DLQ | evolving | 11,14 | Platform |
| S-21 | Verify signatures | Upstash | https://upstash.com/docs/qstash/howto/signature | 2026-08-01 | 2026-09-01/before queue | Signed JWT/URL/time/raw-body hash verification | stable | 11,14 | Security/Platform |
| S-22 | Deduplication | Upstash | https://upstash.com/docs/qstash/features/deduplication | 2026-08-01 | 2026-09-01/before queue | Provider dedup window is limited; local idempotency remains required | plan-sensitive | 11,14 | Platform |
| S-23 | Dead Letter Queues | Upstash | https://upstash.com/docs/qstash/features/dlq | 2026-08-01 | 2026-09-01/before queue | Retention/replay is plan-dependent | plan-sensitive | 11,14 | Platform/SRE |
| S-24 | Queues | Upstash | https://upstash.com/docs/qstash/features/queues | 2026-08-01 | 2026-09-01/before queue | FIFO/parallelism/backpressure; failure may block queue | plan-sensitive | 14,27 | Platform/SRE |
| S-25 | Select a QStash region | Upstash | https://upstash.com/docs/qstash/howto/multi-region | 2026-08-01 | 2026-09-01/before transfer | US/EU regions only at access date; Singapore data-plane approval not implied | capability-sensitive | 14,26,ADR-0005 | DPO/Platform |
| S-26 | Implement multitenancy | Pinecone | https://docs.pinecone.io/guides/index-data/implement-multitenancy | 2026-08-01 | Before AI procurement | Namespace per tenant; tier/scale qualifications apply | plan-sensitive | 06,10 | AI/Data |
| S-27 | Data modeling | Pinecone | https://docs.pinecone.io/guides/index-data/data-modeling | 2026-08-01 | Before AI implementation | Writes/deletes eventually consistent; generation/reconcile needed | capability-sensitive | 06,08,ADR-0003 | AI/Data |
| S-28 | Create an index | Pinecone | https://docs.pinecone.io/guides/index-data/create-an-index | 2026-08-01 | Before AI procurement | Singapore needs qualifying plan; some schema choices immutable | plan-sensitive | 06,14,27 | AI/Finance |
| S-29 | Filter by metadata | Pinecone | https://docs.pinecone.io/guides/search/filter-by-metadata | 2026-08-01 | Before AI implementation | Filters narrow within namespace but do not replace DB authorization | stable | 06,10 | AI/Security |
| S-30 | Webhooks resource | PayMongo | https://docs.paymongo.com/reference/webhook-resource | 2026-08-01 | Before commerce | Retry/disable/retrieval behavior; merchant contract must be tested | capability-sensitive | 17 | Finance/API |
| S-31 | Webhook setup and management | PayMongo | https://docs.paymongo.com/docs/developer-tools-webhook-setup-management | 2026-08-01 | Before commerce | Timestamp + raw payload HMAC pattern; live headers may differ across examples | capability-sensitive | 11,17 | Security/Finance |
| S-32 | Developer Tools best practices | PayMongo | https://docs.paymongo.com/docs/developer-tools-best-practices-1 | 2026-08-01 | Before commerce | POST idempotency and raw-body/timing-safe verification | capability-sensitive | 11,17 | API/Finance |
| S-33 | Subscriptions | PayMongo | https://docs.paymongo.com/docs/payment-acceptance-subscriptions | 2026-08-01 | Before billing | Account capability/payment-method/state behavior; activation required | account-sensitive | 17,20 | Finance/Product |
| S-34 | Account capabilities | PayMongo | https://docs.paymongo.com/docs/account-settings-account-capabilities | 2026-08-01 | Before commerce/payout | Subscriptions/linked accounts need activation; written merchant proof required | account-sensitive | 00,17,20 | Finance/Legal |
| S-35 | Refunds | PayMongo | https://docs.paymongo.com/docs/payment-acceptance-refunds | 2026-08-01 | Before commerce | Paid-only/method windows/partial/balance behavior | account-sensitive | 05,17 | Finance |
| S-36 | Linked accounts | PayMongo | https://docs.paymongo.com/docs/account-settings-linked-accounts | 2026-08-01 | Before marketplace | Parent/child onboarding/capabilities; marketplace remains deferred | account-sensitive | 00,17 | Finance/Legal |
| S-37 | Account troubleshooting | PayMongo | https://docs.paymongo.com/docs/account-settings-troubleshooting | 2026-08-01 | Before commerce | Philippine withholding note effective 2026-04-01; applicability needs counsel/accounting | legal/capability-sensitive | 17,26 | Finance/Legal |
| S-38 | Idempotency keys | Resend | https://resend.com/docs/dashboard/emails/idempotency-keys | 2026-08-01 | 2026-09-01/before email | Provider window 24 hours; durable local outbox still required | capability-sensitive | 17 | Platform |
| S-39 | Managing webhooks | Resend | https://resend.com/docs/webhooks/introduction | 2026-08-01 | 2026-09-01/before email | At-least-once/out-of-order and svix-id dedup | capability-sensitive | 11,17 | Platform |
| S-40 | Email suppressions | Resend | https://resend.com/docs/dashboard/emails/email-suppressions | 2026-08-01 | 2026-09-01/before email | Bounce/complaint suppression behavior is region/provider-sensitive | capability-sensitive | 17 | Product/Platform |
| S-41 | Implementing DMARC | Resend | https://resend.com/docs/dashboard/domains/dmarc | 2026-08-01 | 2026-09-01/before domain | SPF/DKIM and staged DMARC monitoring | stable | 14,17 | Security/Platform |
| S-42 | Row security policies | PostgreSQL | https://www.postgresql.org/docs/current/ddl-rowsecurity.html | 2026-08-01 | On PostgreSQL upgrade | Owner/BYPASSRLS/FORCE/default-deny behavior | stable/versioned | 05,12,15 | Data/Security |
| S-43 | SET CONSTRAINTS | PostgreSQL | https://www.postgresql.org/docs/current/sql-set-constraints.html | 2026-08-01 | On PostgreSQL upgrade | Deferred constraints/constraint triggers for transaction integrity | stable/versioned | 05,17 | Data/Finance |
| S-44 | Writing database migrations | Django | https://docs.djangoproject.com/en/5.2/howto/writing-migrations/ | 2026-08-01 | Before framework upgrade | RunSQL/RunPython/atomic migration behavior; version-specific | stable/versioned | 05,14,ADR-0002 | Data |
| S-45 | Database transactions | Django | https://docs.djangoproject.com/en/dev/topics/db/transactions/ | 2026-08-01 | Before framework upgrade | Atomic/short/on_commit/durability; dev docs require version pin at implementation | version-sensitive | 01,04,11 | Architecture/Data |
| S-46 | Background tasks | FastAPI | https://fastapi.tiangolo.com/tutorial/background-tasks/ | 2026-08-01 | Before framework upgrade | Heavy work belongs in multi-process/queue tooling, not in-process task durability | stable | 02,14,ADR-0005 | Platform |
| S-47 | Authorization Cheat Sheet | OWASP | https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html | 2026-08-01 | Annual/ASVS update | Least privilege/default deny/complete mediation | maintained standard | 07,11,12,15 | Security |
| S-48 | Logging Cheat Sheet | OWASP | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | 2026-08-01 | Annual | Security events and exclusion/masking of secrets/PII/payment data | maintained standard | 12,16 | Security/SRE |
| S-49 | ASVS 5.0.0 | OWASP | https://github.com/OWASP/ASVS/tree/v5.0.0_release | 2026-08-01 | On new release | Versioned application-security verification baseline | stable release | 12,15,23 | Security/QA |
| S-50 | 2025 LLM risks | OWASP GenAI | https://genai.owasp.org/llm-top-10/ | 2026-08-01 | Before AI and annual | Prompt/output/vector/agency/unbounded-consumption risks; not an acceptance corpus | maintained guidance | 02,06,08,09,10 | AI/Security |
| S-51 | AI RMF Generative AI Profile | NIST | https://doi.org/10.6028/NIST.AI.600-1 | 2026-08-01 | Before AI and annual | Governance/provenance/evaluation; engineering must add product-specific thresholds | stable publication | 02,06,08,09,10 | AI/QA/Legal |
| S-52 | WCAG 2.2 | W3C | https://www.w3.org/TR/WCAG22/ | 2026-08-01 | Annual | AA target requires all A/AA criteria on complete pages; automation is insufficient | Recommendation | 15,18,23 | Accessibility/QA |
| S-53 | Data Privacy Act IRR | Philippine NPC | https://privacy.gov.ph/implementing-rules-regulations-data-privacy-act-2012/ | 2026-08-01 | Before real data and legal review | Privacy principles/rights/accountability; this plan is not legal advice | primary law/guidance | 00,12,25,26 | DPO/Legal |
| S-54 | Breach reporting | Philippine NPC | https://privacy.gov.ph/pips-and-pics/breach-reporting/ | 2026-08-01 | Before real data and legal review | 72-hour condition/process requires named DPO/counsel procedure | primary regulator | 12,16,26 | DPO/Legal/Security |
| S-55 | Hostname validation | Cloudflare | https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/domain-support/hostname-validation/ | 2026-08-01 | Before custom domains | Hostname and certificate validation are distinct and both needed | capability-sensitive | 05,14 | Platform/Security |
| S-56 | Remove custom hostnames | Cloudflare | https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/domain-support/remove-custom-hostnames/ | 2026-08-01 | Before custom domains | SaaS provider must remove churned hostnames to prevent routing/takeover issues | capability-sensitive | 05,14 | Platform/Security |

## Maintenance rules

- Link/freshness automation flags broken URLs, an exceeded recheck date, deprecated/preview status changes and entries without an owner/affected file.
- Capability owners record the exact claim checked, current plan/account/region, limitations, sandbox/contract result and decision/ADR update. A reachable URL alone is not verification.
- Deprecation, pricing, account activation, limits, region, retention/training and signature behavior are rechecked immediately before dependent implementation and production enablement.
- The table above supersedes the legacy categorized snapshot below, which remains only for historical navigation and must not be cited as current evidence.

## Supabase

- [Auth](https://supabase.com/docs/guides/auth)
- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Secure data](https://supabase.com/docs/guides/database/secure-data)
- [Storage](https://supabase.com/docs/guides/storage)
- [Storage access control](https://supabase.com/docs/guides/storage/security/access-control)
- [Database overview](https://supabase.com/docs/guides/database/overview)

## Vercel

- [Next.js on Vercel](https://vercel.com/docs/frameworks/full-stack/nextjs)
- [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Services](https://vercel.com/docs/services)
- [Vercel Queues](https://vercel.com/docs/queues)

## Upstash

- [Redis rate limiting](https://upstash.com/docs/redis/sdks/ratelimit-ts/overview)
- [QStash getting started](https://upstash.com/docs/qstash/overall/getstarted)
- [QStash background jobs](https://upstash.com/docs/qstash/features/background-jobs)
- [Workflow getting started](https://upstash.com/docs/workflow/getstarted)

## Pinecone

- [Multitenancy](https://docs.pinecone.io/guides/index-data/implement-multitenancy)
- [Metadata filtering](https://docs.pinecone.io/guides/search/filter-by-metadata)
- [Data modeling](https://docs.pinecone.io/guides/index-data/data-modeling)
- [Search overview](https://docs.pinecone.io/guides/search/search-overview)
- [Increase relevance and reranking](https://docs.pinecone.io/guides/optimize/increase-relevance)

## Document processing

- [Docling](https://docling.org/)
- [Docling CLI and OCR options](https://docling-project.github.io/docling/reference/cli/)
- [Docling full-page OCR example](https://docling-project.github.io/docling/_generated/examples/full_page_ocr/)

## PayMongo

- [Refunding transactions](https://developers.paymongo.com/v1/docs/refunding-transactions)
- [Webhook API reference](https://developers.paymongo.com/v1/reference/retrieve-a-webhook)
- [Payment splitting](https://developers.paymongo.com/docs/seeds-payment-splitting)

## Resend

- [Managing domains](https://resend.com/docs/dashboard/domains/introduction)
- [Managing webhooks](https://resend.com/docs/webhooks/introduction)
- [Receiving email](https://resend.com/docs/dashboard/receiving/introduction)

## Cloudflare

- [Cloudflare DNS](https://developers.cloudflare.com/dns/)
- [DNS records](https://developers.cloudflare.com/dns/manage-dns-records/)
- [Rate limiting rules](https://developers.cloudflare.com/waf/rate-limiting-rules/)

## PostHog

- [Product analytics](https://posthog.com/docs/product-analytics)
- [Next.js integration](https://posthog.com/docs/libraries/next-js)
- [Privacy and data collection](https://posthog.com/docs/privacy/data-collection)

## Sentry

- [Next.js tracing](https://docs.sentry.io/platforms/javascript/guides/nextjs/tracing/)
- [Next.js session replay](https://docs.sentry.io/platforms/javascript/guides/nextjs/session-replay/)
- [Django integration](https://docs.sentry.io/platforms/python/integrations/django/)
- [LLM monitoring](https://docs.sentry.io/product/llm-monitoring/getting-started/)

# Technology Stack and Ownership

Status: **approved ownership boundaries; provider/tier evidence pending**  
Change IDs: CHG-013, CHG-039, CHG-040

## Stack ownership matrix

| Technology | Primary responsibility | Must not become |
|---|---|---|
| Supabase PostgreSQL | Transactional source of truth | A loosely governed client database |
| Supabase Auth | Identity, sessions, JWTs, MFA | The complete tenant authorization model |
| Supabase Storage | Private books, lesson files, submissions, certificates | A public bucket for paid content |
| Next.js | Web UI, SSR, streaming UI | A second business-logic backend |
| FastAPI | Public application API and OpenAPI contract | A place for ORM duplication or long jobs |
| Django | Models, migrations, services, admin | A duplicate public REST stack |
| Vercel | Next.js and light FastAPI deployment | The only runtime for heavy OCR and AI jobs |
| Upstash Redis | Cache, locks, rate limits | Authoritative storage for orders or grades |
| Upstash QStash/Workflow | Candidate signed at-least-once wake-up plane; exact use remains open | A job/domain source of truth or a carrier of sensitive payloads |
| PayMongo | Post-MVP payment authorization and settlement after capability/tax proof | An enabled initial-MVP dependency or the LMS order database |
| Resend | Transactional email transport | The canonical notification record |
| Cloudflare | DNS, DNSSEC, optional WAF and edge rate limits | The only application authorization layer |
| PostHog | Approved server-side pseudonymous events and feature delivery after privacy review | Autocapture/replay by default or financial, security, grade, content, or authorization truth |
| Sentry | Errors, tracing, performance, AI run diagnostics | A store for sensitive document or chat content |
| Pinecone | Vector and lexical retrieval | The canonical content repository |
| Playwright | Cross-browser user-flow tests | Backend unit testing |
| pytest | Backend and database testing | Manual API exploration |
| Insomnia | Manual API exploration | The automated regression suite |

## Required additional component

The listed stack needs one additional runtime for production-grade book ingestion:

> **A containerized Python worker platform**, such as a managed container service.

Vercel can host FastAPI and Django through its Python runtime, but OCR, large document parsing, local models, file scanning, and long multi-step generation require a runtime with controllable CPU, memory, native packages, and execution duration.

The worker platform must support:

- Docker images
- Horizontal scaling
- Private environment variables
- HTTP job endpoints or queue polling
- Longer execution duration
- CPU and memory configuration
- Graceful shutdown
- Health checks
- Central logs

The exact provider is an infrastructure decision and can be changed without changing domain code.

It is also a blocking decision. A provider must not be placed in production configuration until ADR 0005 records a Singapore-capable benchmark, plan/tier, regional and recovery behavior, connection mode, cost envelope, deploy/drain behavior, and accountable approval. The database owns durable job state regardless of the selected wake-up/orchestration transport.

## AI provider abstraction

No LLM or embedding provider was selected in the requested stack. Implement provider interfaces:

```python
class LanguageModelGateway(Protocol):
    async def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResult: ...
    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[ChatDelta]: ...

class EmbeddingGateway(Protocol):
    async def embed(self, texts: list[str], model: str) -> list[list[float]]: ...
```

Provider-neutral design allows OpenAI, Anthropic, Google, Hugging Face, or another provider to be selected later. Store model name, provider, prompt version, token usage, cost estimate, and output checksum for every run.

### Provider admission gate (CHG-013)

AI/OCR/embedding/rerank providers and exact models are unselected and disabled. Approval is per task and requires a signed record of:

- provider/model/version and immutable configuration;
- training/secondary-use terms, retention, deletion, region, subprocessors, DPA and transfer approval;
- rights-compatible input classes and redaction/minimization;
- moderation/safety behavior, structured-output conformance and prohibited fallback behavior;
- quality against the rights-cleared locked corpus, including zero tolerance for cross-tenant retrieval and AI self-publication;
- quota, latency, availability, price, tenant budget, circuit breaker and kill switch;
- deprecation/change notice, pinned-version policy, regression trigger and exit/export plan.

No source or learner data may be transferred before D-018, Q-06, Q-07, Q-09, documents 25/26, and the provider record are approved. There is no silent provider or model fallback.

## Realtime (CHG-039)

Supabase Realtime is disabled and its schemas/channels are not exposed by default. A future feature requires an ADR naming the user value, topic/channel authorization, tenant isolation tests, rate/capacity limits, privacy/retention, reconnect/order semantics, degraded behavior, and operational owner.

## Runtime and dependency support policy (CHG-040)

- Phase 0 records supported Python, Node.js, PostgreSQL, Django, FastAPI, Next.js and SDK versions in exact lockfiles and build manifests.
- CI verifies reproducible installs, licenses, vulnerabilities, end-of-support dates, generated OpenAPI compatibility and provider contract tests.
- Security updates are assessed continuously; dependency and capability-sensitive documentation is reviewed at least monthly and before each production release.
- Breaking framework, database, auth, payment, AI, queue or provider SDK upgrades require an ADR or recorded compatibility decision, migration/rollback plan and regression evidence.
- Version examples from the 2025 Supabase guide are research inputs, not pins for this implementation.

## Selection rules

- Prefer managed services for undifferentiated infrastructure.
- Keep provider SDKs behind adapters.
- Pin SDK versions and upgrade intentionally.
- Never use provider-specific IDs as application primary keys.
- Retain provider payloads only when needed for reconciliation and redact sensitive fields.
- Every external call has timeout, retry policy, circuit breaker, and correlation ID.

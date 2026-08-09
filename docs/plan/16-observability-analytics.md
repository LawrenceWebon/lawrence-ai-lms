# Observability and Product Analytics

Status: **approved telemetry policy; event allowlist, retention, dashboards and runbooks pending**  
Change IDs: CHG-028, CHG-045

## Sentry responsibilities

Instrument:

- Next.js browser and server
- FastAPI
- Django
- Workers
- External API spans
- Database spans
- AI model and retrieval spans with redacted metadata

Every trace should include safe tags:

```text
environment
release
request_id
trace_id
tenant_pseudonym
actor_pseudonym
route
job_type
generation_run_id
document_version_id
course_id
```

Tenant/actor/course/document/run identifiers sent outside the core environment use approved keyed pseudonyms or lower-cardinality classifications when correlation does not require identity. Raw UUIDs remain personal/tenant data and are not “safe” merely because they are opaque. Do not attach full source text, prompts containing private content, chat bodies or high-cardinality identifiers without an approved purpose/retention entry. Document/generation fields are emitted only after their owning focused feature and telemetry allowlist are enabled; RAG/chat fields remain absent.

## PostHog responsibilities

PostHog is **off by default**. Autocapture and session replay are disabled. No browser event is enabled until the versioned server-side allowlist below has an approved purpose/basis, fields, retention, region/DPA, access owner and deletion behavior.

### Analytics event allowlist (CHG-028)

| Event/version | Purpose | Allowed properties | Prohibited properties | Consent/basis | Retention/deletion | Owner/status |
|---|---|---|---|---|---|---|
| None for initial scaffold | No approved analytics question yet | None | All | `TBD-BLOCKING` | Document 25 | Product/DPO pending |

Future events use pseudonymous tenant/user references and minimum categorical/technical fields. The denylist includes names/emails/phones/addresses, URLs/query strings containing identifiers, free text, course/source/lesson bodies, chat/prompts/outputs, assignment/submission content, grades/answers, payment/ledger facts, tokens/secrets, support content and raw exception/request bodies. Feature flags may change presentation or optional behavior but never authorize data, bypass a gate or control financial/publication truth.

Candidate future events—not currently approved or emitted:

- Tenant registered
- Onboarding completed
- Course draft created
- Course published
- Student enrolled
- Lesson started and completed
- Quiz submitted
- Checkout started
- Order paid
- Document uploaded
- Ingestion completed or failed
- Blueprint approved
- Generated artifact approved
- AI companion opened
- AI answer rated

Candidate future presentation/rollout flags—not capability authorization:

- AI course generation beta
- AI companion rollout
- New course builder
- New checkout
- Experimental retrieval strategy

Do not use a feature flag as the only authorization control.

A deferred capability's flag and client/server PostHog event are not provisioned until that capability gate closes. Flags may stage already-authorized code within an enabled domain; they cannot make an absent route, job, schema or provider credential available.

## Required operational metrics

### Metric and SLI specification (CHG-045)

Every production metric/SLI records: exact numerator/denominator or histogram definition, units, eligible events, exclusions, source, labels/cardinality budget, privacy class, retention, dashboard, warning/critical threshold/window, owner and linked runbook. Required coverage includes:

- user journeys and provisional 99.9% core/99.5% authoring availability;
- PostgreSQL query/lock/replication and pool usage/wait/reset/context failures;
- job arrival/claim/age/lease/retry/DLQ/reconcile by enabled stage and tenant-safe cardinality;
- provider inbox/outbox acceptance, dispatch, reducer lag, duplicate/hash conflict and reconciliation mismatch;
- future ledger imbalance/entitlement mismatch and rights-removal/vector tombstone/rebuild progress;
- AI evaluation/cost/quality only after enablement, without prompt/source/chat content;
- DB/object backup freshness, manifest mismatch, restore throughput and achieved RPO/RTO.

### API

- Request count
- Error rate
- p50, p95, p99 latency
- Authorization denials
- Database pool usage

### Workers

- Queue age
- Job duration
- Retry count
- Failure rate
- OCR pages per minute
- Embedding records per minute
- Generation token usage

### Payments

- Pending orders
- Payment success rate
- Webhook delay
- Reconciliation mismatch
- Refund failure

### AI quality

- Retrieval latency
- Citation-validity rate
- Unsupported-answer rate
- User helpfulness
- Generation acceptance rate
- Average instructor edits
- Cost per generated lesson and answer

## Alerting

Page or urgently notify on:

- Cross-tenant access anomaly
- Payment webhook signature failure spike
- Database connection exhaustion
- Queue age beyond SLO
- Worker failure spike
- Backup failure
- AI citation-validation failure spike
- High 5xx rate

Ticket or notify non-urgently on:

- Rising unsupported-answer rate
- Falling course-generation acceptance
- Increased email bounce rate
- Increased ingestion quality failures

Every alert names severity, accountable primary/backup, acknowledgement and escalation windows, exact dashboard/query, runbook, safe diagnostic fields, auto-remediation bounds and resolution/evidence requirement. Cross-tenant anomaly, privileged-access misuse, backup/restore failure, ledger imbalance, rights-removal breach and sustained auth/JWKS failure are non-suppressible without an incident record.

## Privacy controls

- Disable or mask sensitive PostHog autocapture fields.
- Mask session replay inputs and private course content.
- Use sampling for Sentry traces and replay.
- Define retention by environment.
- Provide tenant analytics opt-out where contractually required.

Sentry/logging use a field allowlist plus denylist, before-send/filter tests, sampling and pseudonymous correlation. CI and staging inject unique redaction canaries into tokens, PII, source/chat/assignment/payment fields and fail if any appears in captured logs/events. Access reviews, retention and deletion follow documents 25/26; opaque IDs are not considered anonymous merely because they lack a display name.

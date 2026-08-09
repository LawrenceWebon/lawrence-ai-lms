# Environment Variables and Secret Ownership

Status: **approved secret model; real values and rotation evidence must remain outside the repository**  
Change ID: CHG-017

This file lists categories, not real secret values.

## Public web variables

```text
NEXT_PUBLIC_APP_URL
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
NEXT_PUBLIC_SENTRY_DSN
```

Only explicitly public values may use the `NEXT_PUBLIC_` prefix.

`NEXT_PUBLIC_POSTHOG_KEY` and `NEXT_PUBLIC_POSTHOG_HOST` are absent until document 16's first event allowlist, document 25 retention and document 26 region/DPA/basis approval close. “Off by configuration” is not a reason to distribute an unapproved browser analytics key.

`NEXT_PUBLIC_SENTRY_DSN` is likewise omitted outside local synthetic testing until the Sentry project region/DPA, field allowlist, redaction canaries, sampling, retention and deletion behavior are approved. A DSN being non-secret does not authorize browser telemetry export.

## Server application

```text
APP_ENV
APP_RELEASE
APP_REGION
APP_URL
API_URL
DJANGO_SECRET_KEY
DATABASE_URL_API
DATABASE_URL_WORKER
DATABASE_URL_RECONCILER
DATABASE_URL_ANALYTICS
DATABASE_URL_MIGRATOR
DATABASE_POOL_SIZE_API
DATABASE_POOL_SIZE_WORKER
DATABASE_CONNECTION_MODE_API         # session or transaction; checked against runtime/endpoint
DATABASE_CONNECTION_MODE_WORKER      # session
DATABASE_PREPARED_STATEMENTS_API      # false for transaction pooling
DATABASE_SSLMODE                     # provider-supported verified TLS mode
SUPABASE_URL
SUPABASE_PROJECT_REF
SUPABASE_JWKS_URL
SUPABASE_JWT_ISSUER
SUPABASE_JWT_AUDIENCE_OR_ROLE
SUPABASE_SECRET_KEY_API             # only if this component needs elevated Supabase HTTP
SUPABASE_SECRET_KEY_WORKER          # only if this component needs elevated Supabase HTTP
SUPABASE_STORAGE_BUCKET_SOURCE
SUPABASE_STORAGE_BUCKET_COURSE
SUPABASE_STORAGE_BUCKET_SUBMISSIONS
```

SQL uses distinct API, worker and direct migrator DSNs/roles; it never uses an API key as a database credential. Runtime SQL roles are non-owner/non-`BYPASSRLS`. New per-component Supabase secret keys are allowed only for an enumerated elevated HTTP operation that cannot use a narrower user-scoped/signed flow; these keys still bypass RLS and must never reach a browser, log, build artifact, queue payload or general shared configuration.

The legacy `SUPABASE_SERVICE_ROLE_KEY` is prohibited for new code and must be disabled no later than 2026-12-31 and before production launch. Rotation evidence records component/secret reference, owner, issue/expiry, last use, replacement validation, revocation and emergency procedure without storing the value.

## Upstash

```text
UPSTASH_REDIS_REST_URL
UPSTASH_REDIS_REST_TOKEN
```

QStash remains unselected under D-024. These variables are absent until the transport, region/data-minimization and signature contract are approved:

```text
QSTASH_TOKEN
QSTASH_CURRENT_SIGNING_KEY
QSTASH_NEXT_SIGNING_KEY
```

## PayMongo

This entire group is absent from initial-MVP deployments and secret stores. Provision only after the commerce gate is approved.

```text
PAYMONGO_PUBLIC_KEY
PAYMONGO_SECRET_KEY
PAYMONGO_WEBHOOK_SECRET
PAYMONGO_SUCCESS_URL
PAYMONGO_CANCEL_URL
```

Secret key and webhook secret are server-only.

## Resend

Provision Resend only after transactional-email purpose/basis, region/DPA, retention, suppression, sending-domain and webhook contracts are approved for the target environment.

```text
RESEND_API_KEY
RESEND_FROM_EMAIL
RESEND_WEBHOOK_SECRET
```

## Pinecone

This entire group is absent from initial-MVP deployments and secret stores. Provision it only after the AI/rights/provider/vector gates close.

```text
PINECONE_API_KEY
PINECONE_INDEX_NAME
PINECONE_INDEX_HOST
PINECONE_API_VERSION
```

## AI providers

This entire group is absent from initial-MVP deployments and secret stores. Provision task-specific keys only after D-018/D-022 and the provider admission record are approved.

```text
LLM_PROVIDER
LLM_API_KEY
LLM_MODEL_COURSE_PLANNING
LLM_MODEL_LESSON_GENERATION
LLM_MODEL_CHAT
EMBEDDING_PROVIDER
EMBEDDING_API_KEY
EMBEDDING_MODEL
RERANK_PROVIDER
RERANK_API_KEY
RERANK_MODEL
```

## Observability

```text
SENTRY_DSN
SENTRY_AUTH_TOKEN
SENTRY_ORG
SENTRY_PROJECT
POSTHOG_API_KEY
POSTHOG_PERSONAL_API_KEY
OTEL_EXPORTER_OTLP_ENDPOINT
```

Runtime and CI credentials are separate: `SENTRY_AUTH_TOKEN` and `POSTHOG_PERSONAL_API_KEY` are deployment/administrative secrets and must not enter web/API/worker runtime unless an explicitly reviewed operation requires them. PostHog keys remain absent while analytics is unapproved; Sentry/OTel endpoints require the document 16 allowlist/redaction and documents 25/26 retention/region approval.

## Cloudflare and Vercel automation

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ZONE_ID
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
```

## Security rules

- Never commit `.env` files.
- Use different secrets in every environment.
- Rotate after staff changes or suspected disclosure.
- Use least-privilege API tokens.
- Prevent secrets from reaching build logs.
- Redact secrets from Sentry and structured logs.
- Validate required variables at startup.
- Use a managed secret store in production.
- Validate that each process receives only its allowlisted variables; API, worker, migrator, web and CI secret sets are separate.
- Test rotation with overlapping current/next credentials where supported, revoke the old credential, and alert on post-revocation use.
- Fail deployment when a legacy service-role key, wrong-environment URL/JWKS/issuer, production credential in preview, or disabled-feature credential is present.

# Payments, Email, and External Integrations

Status: **email foundation planned; paid commerce and payouts disabled post-MVP**  
Change IDs: CHG-008, CHG-024, CHG-042

## PayMongo architecture

**Non-waivable gate:** the initial MVP has no PayMongo credentials, checkout routes, webhook endpoints, paid entitlements, ledger, refunds, subscriptions, earnings or payouts. The illustrative flows below are future design inputs only. Before enablement, finance/legal must close Q-05 and the merchant must provide written/sandbox capability proof. Select one exact current PayMongo API path per use case; “checkout or intent” is not an implementable decision.

### Future normalized financial contract (CHG-008)

The provider adapter must record exact endpoint/version, merchant/environment, normalized local/provider state map, allowed transitions, event types, signature header/raw-body/timestamp/replay behavior, idempotency scope/window, retrieval/reconciliation endpoints and tested sandbox fixtures.

Webhook admission reads the raw body once, performs the live-contract timestamped HMAC/signature check with constant-time comparison, rejects replay/unknown merchant/environment/event, and reserves the provider event/body hash under a unique constraint. The reducer atomically writes accepted provider facts, an append-only balanced-per-currency ledger transaction, local entitlement-period change and outbox; redirects never fulfill.

Daily reconciliation retrieves provider authority and compares provider events/objects, local inbox/reducer state, payment/refund/settlement facts, ledger balances and entitlements. Mismatches enter an owned operator queue with severity, evidence, retry/repair/compensating-entry action and audit. Refund access treatment, disputes, settlement and any later payout require written finance/legal policy and property/concurrency tests.

### Course purchase flow

This sequence remains disabled and becomes executable only after the adapter contract names one approved endpoint/product. `selected PayMongo payment resource` below is deliberately a bound adapter operation—not a choice made at runtime.

1. Create local order in `pending_payment`.
2. Commit a provider-attempt intent and outbox using a stable idempotency key.
3. After commit, create the selected PayMongo payment resource from the server adapter.
4. Record the normalized provider observation in a new short transaction.
5. Redirect the user to the provider-authorized flow when the selected product requires it.
6. Receive, verify and persist the provider event before reduction.
7. Confirm merchant/environment, amount, currency, order and allowed transition.
8. Atomically reduce payment/order state, post balanced ledger entries, create/revoke the local entitlement period and write audit/outbox facts.
9. Send confirmation asynchronously.

Instructor earnings are not part of this single-merchant flow. They appear only if the separately deferred marketplace/payout model is approved.

### Refund flow

- Validate refundable balance under row lock.
- Create local refund request.
- Commit the refund intent, then call the selected PayMongo refund operation outside the transaction.
- Confirm provider result by retrieval or verified webhook; timeout remains `unknown` until reconciled.
- Post compensating ledger/refund-allocation entries; adjust earnings only if a separately approved marketplace model exists.
- Revoke, shorten or preserve the local entitlement/enrollment according to the written refund-access policy.
- Retain complete audit history.

### Reconciliation

Scheduled reconciliation checks:

- Pending checkout/payment attempts for the selected product
- Paid provider transactions not reflected locally
- Local paid orders missing provider confirmation
- Refund status mismatches
- Duplicate event IDs

## Marketplace payouts

The earlier manual-payout fallback is rejected and superseded: instructor earnings and payouts are outside MVP and no money is accepted on their behalf. A future feature requires linked-account capability, onboarding/KYC, merchant/beneficial-owner roles, vesting, fees/refunds/chargebacks/negative balances, settlement, withholding/invoice rules, balanced ledger design and reconciliation approval before any build.

Do not assume PayMongo split-payment or payout capabilities are available for every account. Confirm merchant approval and supported APIs before committing to automated instructor payouts.

There is no manual payout fallback. Offline/manual disbursement does not avoid ledger, tax, KYC, settlement, reconciliation or approval obligations and therefore remains prohibited until the same future gate closes.

## Resend architecture

Use Resend for:

- Authentication-related application email not already handled by Supabase
- Invitations
- Enrollment confirmation
- Assignment and quiz notifications
- Certificate delivery
- Support-ticket updates

Payment receipts/failures and tenant billing notices are added only with the paid-commerce gate. Course-generation completion/review mail is added only with the AI-generation gate. Assignment, certificate and broader support notifications follow their corresponding phase; listing a template does not enable its domain.

### Email records

Every logical notification creates:

- `notifications`
- `notification_deliveries`

Store provider email ID and webhook status. Process delivered, bounced, complained, and failed events.

### Durable email delivery contract (CHG-024)

Every logical email starts as a transactional outbox row committed with the domain event. It contains a deterministic message key, template ID/version, locale, purpose/legal basis, recipient identity reference, render-data hash, scheduling/expiry and suppression/preference decision—never unrestricted sensitive content in logs.

The dispatcher uses the deterministic Resend idempotency key but retains local deduplication beyond the provider's 24-hour window. A webhook inbox deduplicates `svix-id` and body hash. Because delivery events are at-least-once and may arrive out of order, a monotonic reducer records all observations and changes logical delivery state only under approved precedence/version rules. Retries, DLQ/replay, provider retrieval/reconciliation, hard-bounce/complaint suppression and preference changes are durable and audited.

### Domain strategy

Use an isolated sending subdomain such as:

```text
updates.example.com
```

Configure SPF, DKIM, and DMARC through Cloudflare DNS.

The initial MVP sends only from a platform-controlled subdomain with verified SPF/DKIM and staged DMARC monitoring before quarantine/reject. Tenant-branded sending domains are a separately approved/priced post-launch capability requiring ownership verification, DNS lifecycle, warm-up, suppression/reputation isolation, churn removal, support SLO and abuse response (CHG-042).

## Webhook security

For PayMongo and Resend:

- Use HTTPS.
- Verify signatures.
- Store raw payload with restricted access.
- Deduplicate provider event ID.
- Process asynchronously.
- Support replay.
- Alert on repeated signature failures.

## Integration adapter rule

External SDKs live behind interfaces. Domain services receive normalized provider results, not raw SDK response objects.

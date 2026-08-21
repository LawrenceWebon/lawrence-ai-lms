# Product Open Questions

Status: **non-blocking for repository setup; gate the named later step**

| ID | Question | Needed before | Owner | Current action |
|---|---|---|---|---|
| Q-P01 | Which exact AI provider/model will generate course drafts? | Provider-connected F-005 integration | Product/AI/Privacy | Freeze a provider-neutral structured contract first; do not select a provider during product planning. |
| Q-P02 | Which OCR engine and thresholds apply to scanned or low-quality PDFs? | Real OCR adapter in F-004 | Content/Platform/QA | Define golden PDFs and benchmark during feature planning; extraction contracts may use deterministic fixtures first. |
| Q-P03 | What initial PDF size, page, pixel, timeout, and tenant quotas should be enforced? | Local F-003 implementation; a later decision is still required for external/production enablement | Product/Platform/Security | Closed for local-only F-003 by P-013: 6 MiB, 100 pages, 25M pixels/page, 250M pixels/source, 64 MiB decoded material, 15 CPU seconds/30 wall seconds, 15-minute intent, 2 active uploads, 10 intents/30 MiB per 24h, and 20 objects/60 MiB per tenant. Do not reuse these values as production capacity evidence. |
| Q-P06 | Which persistent worker, storage protection, and production region/tier will be funded? | staging/production | Platform/SRE/Finance/Privacy | Local adapters only until the production decision closes. |
| Q-P07 | What numeric extraction, grounding, citation, coverage, and draft-quality thresholds must provider-backed generation pass? | Provider-connected F-004/F-005 integration and release | Product/Content/AI/QA | Build the rights-cleared evaluation set and approve versioned thresholds during feature planning; do not claim AI readiness without them. |
| Q-P08 | Which initial product and generated-course locales are required for the first pilot? | F-005/F-006/F-007 UI and content acceptance | Product/Content/Accessibility | Closed by P-014: exactly `en` for the initial focused pilot. Preserve Unicode, fallback/language metadata, accessibility, and RTL-ready structure; broader locale coverage requires a later decision and evidence. |

Questions are not permission to invent product behavior. Record answers in
`decisions.md`, update affected feature acceptance, and close the corresponding gate.

Closed: Q-P04 is resolved by P-012 for the first vertical slice. Q-P08 is resolved by
P-014 for the initial focused pilot.

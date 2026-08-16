# Product Open Questions

Status: **non-blocking for repository setup; gate the named later step**

| ID | Question | Needed before | Owner | Current action |
|---|---|---|---|---|
| Q-P01 | Which exact AI provider/model will generate course drafts? | Provider-connected F-005 integration | Product/AI/Privacy | Freeze a provider-neutral structured contract first; do not select a provider during product planning. |
| Q-P02 | Which OCR engine and thresholds apply to scanned or low-quality PDFs? | Real OCR adapter in F-004 | Content/Platform/QA | Define golden PDFs and benchmark during feature planning; extraction contracts may use deterministic fixtures first. |
| Q-P03 | What initial PDF size, page, pixel, timeout, and tenant quotas should be enforced? | F-003/F-004 implementation | Product/Platform/Security | Use conservative local fixtures; approve measured limits before enablement. |
| Q-P06 | Which persistent worker, storage protection, and production region/tier will be funded? | staging/production | Platform/SRE/Finance/Privacy | Local adapters only until the production decision closes. |
| Q-P07 | What numeric extraction, grounding, citation, coverage, and draft-quality thresholds must provider-backed generation pass? | Provider-connected F-004/F-005 integration and release | Product/Content/AI/QA | Build the rights-cleared evaluation set and approve versioned thresholds during feature planning; do not claim AI readiness without them. |
| Q-P08 | Which initial product and generated-course locales are required for the first pilot? | F-005/F-006/F-007 UI and content acceptance | Product/Content/Accessibility | Choose the smallest pilot locale set and preserve Unicode/localization/accessibility boundaries; do not imply broad language coverage. |

Questions are not permission to invent product behavior. Record answers in
`decisions.md`, update affected feature acceptance, and close the corresponding gate.

Closed: Q-P04 is resolved by P-012 for the first vertical slice.

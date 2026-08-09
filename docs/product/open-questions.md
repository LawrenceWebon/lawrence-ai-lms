# Product Open Questions

Status: **non-blocking for repository setup; gate the named later step**

| ID | Question | Needed before | Owner | Current action |
|---|---|---|---|---|
| Q-P01 | Which exact AI provider/model and structured-output contract will generate course drafts? | F-005 implementation | Product/AI/Privacy | Keep an adapter boundary; do not select during setup. |
| Q-P02 | Which OCR engine and thresholds apply to scanned or low-quality PDFs? | F-004 implementation | Content/Platform/QA | Define golden PDFs and benchmark during feature planning. |
| Q-P03 | What initial PDF size, page, pixel, timeout, and tenant quotas should be enforced? | F-003/F-004 implementation | Product/Platform/Security | Use conservative local fixtures; approve measured limits before enablement. |
| Q-P04 | Which lesson/content-block types must generation support in the first vertical slice? | F-002/F-005 contract freeze | Product/Content | Start with the smallest set needed for readable text courses. |
| Q-P05 | Is separate-person review required for the first pilot, or may an authorized instructor self-review? | F-006 implementation | Product/Content | Preserve role separation support; decide the pilot policy explicitly. |
| Q-P06 | Which persistent worker, storage protection, and production region/tier will be funded? | staging/production | Platform/SRE/Finance/Privacy | Local adapters only until the production decision closes. |

Questions are not permission to invent product behavior. Record answers in
`decisions.md`, update affected feature acceptance, and close the corresponding gate.

---
name: review-ai-lms-pr
description: Perform an independent evidence-based review of one AI LMS pull request at an exact head SHA. Use when an implementation PR claims READY FOR CODE REVIEW, after fixes require re-review, or when tenant isolation, PDF ingestion, AI provenance, publication controls, migrations, or tests need focused verification.
---

# Review an AI LMS Pull Request

1. Do not review your own PR or push fixes to the author's branch.
2. Read `AGENTS.md`, the product contract, approved issue and contracts, relevant plan
   and ADR sections, and `docs/workflows/CODE_REVIEW_AI_LMS_CODEX_WORKFLOW.md`.
3. Use `gh pr view`, `gh pr diff`, and `gh pr checks`; record the exact `headRefOid`.
   Use an isolated review worktree when commands must run locally.
4. Review highest-risk behavior first: authorization and tenant isolation, migrations,
   async retries and idempotency, uploaded-file handling, AI structured outputs and
   provenance, and human-only publication.
5. Verify claims against code and tests. Distinguish confirmed blockers from opinions.
6. Report findings by severity with file and line, evidence, impact, and required fix.
7. Post `CHANGES REQUIRED`, `BLOCKED`, or `APPROVED FOR MERGE` with `gh pr review`.
   When all agents share one GitHub identity, post a PR comment and require a distinct
   authorized GitHub approval.
8. Treat every new push as a new SHA requiring re-review.

Do not merge, deploy, change requirements to match the diff, or silently fix findings.

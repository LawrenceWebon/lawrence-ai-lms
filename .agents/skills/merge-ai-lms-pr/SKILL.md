---
name: merge-ai-lms-pr
description: Verify and merge one approved AI LMS pull request through protected GitHub checks. Use only after independent review approves the current head SHA and an authorized user requests merge or release preparation; use for dependency-ordered integration, not ordinary implementation or self-review.
---

# Merge an AI LMS Pull Request

1. Read `AGENTS.md`, the issue and PR, the exact-SHA review, relevant release gates,
   and `docs/workflows/MERGE_DEPLOY_AI_LMS_CODEX_WORKFLOW.md`.
2. Confirm `APPROVED FOR MERGE`, current reviewed `headRefOid`, required checks,
   resolved threads, mergeability, dependency order, migrations, generated contracts,
   rollback notes, and integration tests.
3. Stop if the SHA changed, checks are missing, a dependency is unmerged, or any
   non-waivable tenant, privacy, rights, AI-publication, migration, or recovery gate
   is unresolved for the requested environment.
4. Merge concurrent PRs one at a time with the repository-approved strategy and
   `gh pr merge --match-head-commit`. Never use `--admin` or bypass branch protection.
5. After each merge, require remaining PRs to incorporate the new base, rerun checks,
   and obtain review for their new SHA.
6. Verify GitHub reports the PR merged before cleaning a branch or worktree. Preserve
   dirty or closed-unmerged work.
7. Record PR, reviewed SHA, merge SHA, checks, strategy, timestamp, and next release
   action.

Merge permission does not imply deployment permission. Do not deploy, run production
migrations, or activate a feature without a separate explicit authorization and the
applicable release gates.

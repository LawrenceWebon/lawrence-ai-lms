---
name: merge-ai-lms-pr
description: Verify and merge one approved AI LMS pull request through protected GitHub checks, or reconcile a task PR that the project owner reports already merged to develop. Use for guarded dependency-ordered integration and automatic post-merge cleanup, independent audit, truthful status reconciliation, and next-task assessment; not ordinary implementation, self-review, or deployment.
---

# Merge an AI LMS Pull Request

1. Read `AGENTS.md`, the issue and PR, relevant review/release gates, and
   `docs/workflows/MERGE_DEPLOY_AI_LMS_CODEX_WORKFLOW.md`. Select guarded pre-merge or
   already-merged reconciliation from verified GitHub state and the owner's request.
2. For guarded pre-merge work, confirm `APPROVED FOR MERGE`, the current reviewed
   `headRefOid`, required checks, resolved threads, mergeability, dependency order,
   migrations, generated contracts, rollback notes, and integration tests.
3. Stop pre-merge work if the SHA changed, checks are missing, a dependency is
   unmerged, or any non-waivable tenant, privacy, rights, AI-publication, migration, or
   recovery gate is unresolved for the requested environment.
4. Merge concurrent PRs one at a time with the repository-approved strategy and
   `gh pr merge --match-head-commit`. Never use `--admin` or bypass branch protection.
5. After each merge, require remaining PRs to incorporate the new base, rerun checks,
   and obtain review for their new SHA.
6. When the project owner reports that a PR already merged, verify its remote merge,
   exact head and merge tree, then automatically complete the post-merge transition:
   clean only the issue-recorded worktree, Compose project, disposable volumes, and
   exact host scratch child; commission an independent exact-head audit; and remove
   the audit's isolated resources after its evidence is durable.
7. Reconcile the audit result truthfully. A clean audit marks the exact head as
   independently reviewed post-merge; confirmed blockers create or prepare focused
   remediation. Never invent a retroactive pre-merge approval, and do not treat a
   same-identity comment as a distinct GitHub approval.
8. Update affected readiness/evidence status through the normal issue/branch/PR flow,
   then assess the next dependency-ready task. Do not provision dependent
   implementation while a blocking finding or required owner disposition remains.
9. Record PR, reviewed SHA, merge SHA, checks, strategy or observed merge method,
   cleanup evidence, audit verdict, timestamp, and next release or task action.

Merge permission does not imply deployment permission. Do not deploy, run production
migrations, or activate a feature without a separate explicit authorization and the
applicable release gates.

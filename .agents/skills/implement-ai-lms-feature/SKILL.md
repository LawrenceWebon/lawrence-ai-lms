---
name: implement-ai-lms-feature
description: Implement one approved AI LMS GitHub issue in an isolated branch and worktree. Use when the user explicitly requests coding for a feature whose scope, contracts, paths, tests, and dependencies are ready; also use to resume or repair that same bounded implementation before code review.
---

# Implement an AI LMS Feature

1. Refuse to start application code unless the user requested implementation and the
   issue is `READY FOR IMPLEMENTATION`.
2. Read `AGENTS.md`, the product contract, the issue, frozen contracts, and only the
   relevant plan, ADR, workflow, and test sections.
3. Verify GitHub authentication, `origin`, default branch, branch, worktree, dirty
   state, owned paths, shared hotspots, and declared dependencies.
4. Work only in the issue's isolated worktree. Never edit another agent's branch,
   paths, database, ports, queues, buckets, or temporary resources.
5. Write or confirm focused tests before the minimum production change. Preserve the
   modular-monolith boundary, Django-only migrations, server-side tenant authority,
   idempotent async stages, provenance, and human-only publication.
6. Stage only owned paths. Do not use `git add .`, `git add -A`, force-push, rebase a
   published branch, bypass checks, or absorb unrelated cleanup.
7. Run the exact issue checks, inspect the diff, record evidence, and update the issue
   or draft PR at meaningful gates.
8. Push the issue branch and open or update a draft PR with `gh` when remote actions
   are authorized by the issue and repository workflow.
9. Return `READY FOR CODE REVIEW` with changed paths, tests, security and tenancy
   impact, migration and API impact, known limits, rollback, and exact commands.

Do not merge, deploy, modify production data, introduce unapproved providers, or
enable capabilities outside the issue.

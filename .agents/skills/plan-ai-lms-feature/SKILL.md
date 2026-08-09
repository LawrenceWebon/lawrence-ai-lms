---
name: plan-ai-lms-feature
description: Plan one focused AI LMS feature from the approved product contract and detailed plan. Use when Codex must clarify a feature, freeze contracts, define tests, split work into up to four independent GitHub issues, or decide whether a feature is ready for implementation without writing application code.
---

# Plan an AI LMS Feature

1. Read `AGENTS.md`, `docs/product/spec.md`, `docs/product/features.md`,
   `docs/product/decisions.md`, and `docs/workflows/README.md`.
2. Read only the `docs/plan` and ADR files relevant to the selected feature.
3. Confirm that the feature is in the current MVP and list explicit non-goals.
4. Record actors, user flow, authorization and tenant boundaries, failure behavior,
   acceptance criteria, and required tests.
5. Freeze the smallest API, event, job, DTO, and fixture contracts needed for parallel
   work. Do not prescribe speculative classes or frameworks.
6. Produce a dependency graph of no more than four active issues. Give every issue an
   exclusive owner, branch, worktree, path set, test commands, and PR merge order.
7. Assign one integration owner to migrations, lockfiles, settings and composition,
   OpenAPI and generated clients, CI, and other shared hotspots.
8. Use `gh issue create` and `gh issue develop` only when a GitHub `origin` and
   authenticated `gh` session exist. Otherwise prepare the issue bodies locally.
9. Return `READY FOR IMPLEMENTATION` only when each issue is independently testable
   against frozen contracts or fixtures and no material product decision is hidden.

Do not write production code, create migrations, install dependencies, select an
unapproved provider, or enable production data while using this skill.

# AI LMS Repository Guidance

## Mission

Build a focused LMS whose defining journey is:

```text
authorized book PDF
  -> safe extraction
  -> structured course draft
  -> instructor review and editing
  -> human publication
  -> learner course experience
```

Keep the product small. Commerce, marketplace payouts, recurring billing, AI chat/RAG,
custom domains, live classes, certificates, advanced grading, and broad analytics are
not part of the focused MVP unless the project owner explicitly adds them.

## Read first

Use this order:

1. latest explicit project-owner instruction;
2. `docs/product/spec.md`;
3. `docs/product/decisions.md` and `docs/product/features.md`;
4. `docs/workflows/README.md`;
5. relevant `docs/plan` files and accepted ADRs;
6. approved GitHub issue and frozen contracts;
7. existing code and tests.

When these sources conflict, stop the affected work and apply the narrowest approved
documentation correction. Do not create a convenient interpretation.

## Current repository state

The repository is in documentation and Codex-workflow setup. Do not create application
code, install dependencies, add migrations, or configure providers until the user
explicitly requests implementation and the selected issue is ready.

## Delivery workflow

- Follow `docs/workflows/README.md`.
- One issue equals one agent, branch, isolated worktree, and PR.
- Create repository worktrees only under the exact absolute
  `/home/lawrence/Project Neo/worktrees/ai-lms/` root; do not place worktrees inside
  the repository or under `/tmp`.
- Up to four independent issues may run concurrently after shared contracts freeze.
- Every issue declares owned paths, dependencies, shared hotspots, tests, and merge
  order.
- Never edit another agent's worktree, branch, paths, or local resources.
- Shared migrations, lockfiles, application composition, OpenAPI/generated clients,
  CI, and generated manifests have one integration owner.
- Use `gh` for authorized GitHub issue, branch, PR, review, check, and merge operations.
- Never use `git add .`, `git add -A`, force-push, `gh pr merge --admin`, or bypass a
  required check.
- An agent never approves or merges its own PR.
- Do not create a host `.venv` or install project Node dependencies on the host.
  Start each isolated task with `docker compose up -d --build`, then reuse that
  task's Compose services for project commands and dependency execution.

## Architecture boundaries

- Keep a modular monolith with independently deployable web, API/Admin, and worker
  process types.
- Django migrations are the only authority for application schema, grants, functions,
  and RLS objects.
- FastAPI and Django Admin adapters call shared application services; they do not
  mutate cross-domain models directly.
- Next.js uses the generated API client for core LMS data. Browser-supplied tenant IDs
  are selectors, never authorization authority.
- Re-derive identity, tenant membership, entitlement, and resource access server-side
  and enforce tenant isolation with non-owner production roles and PostgreSQL RLS.
- Do not hold database transactions across Storage, OCR, AI, vector, email, or other
  network calls.
- Async stages use durable state, idempotency, leases/checkpoints, bounded retries,
  reconciliation, and explicit failure states.
- AI output is a structured draft with immutable source and run provenance. Only an
  authorized human can approve and publish a canonical course version.

## Data and safety

- Use synthetic or rights-cleared test PDFs only until privacy, retention, capacity,
  recovery, and provider gates are approved.
- Do not commit secrets, credentials, production data, private books, prompts, chats,
  submissions, or unrestricted provider payloads.
- Treat every uploaded document and extracted string as untrusted input.
- Do not add a provider, model, queue, vector database, or production region without
  an approved feature decision.

## Planning and documentation

- Keep `docs/product/spec.md` concise and product-facing.
- Keep `docs/product/features.md` derived from the spec and ordered by dependency.
- Put detailed architecture and operational contracts in `docs/plan` and ADRs.
- Use `docs/features/_template/` only when a feature needs durable files beyond its
  GitHub issue.
- Update links and `manifest.json` whenever versioned Markdown changes.
- Use current official sources before capability-sensitive provider work.

## Verification

Before handing off documentation/setup work:

- validate local Markdown links;
- regenerate and check `manifest.json`;
- validate every changed skill with the skill validator;
- inspect `git status` and the exact diff; and
- report commands, results, known limitations, and whether any remote action occurred.

The PowerShell documentation checks are:

```text
pwsh -NoProfile -File ./scripts/generate-document-manifest.ps1 -Check
pwsh -NoProfile -File ./scripts/validate-markdown-links.ps1
```

If `pwsh` is unavailable, run an equivalent local check and rely on CI for the exact
PowerShell execution.

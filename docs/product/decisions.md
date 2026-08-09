# Product Decisions

Status: **active**

| ID | Decision | Rationale | Effect |
|---|---|---|---|
| P-001 | PDF-to-structured-course is the core MVP journey. | This is the defining product value requested by the project owner. | Ingestion and course generation move ahead of unrelated LMS breadth. |
| P-002 | Generated content is always a draft until a human publishes it. | Educational quality and source interpretation require accountable review. | AI and worker identities cannot publish. |
| P-003 | Use a private multi-tenant LMS foundation. | Tenant ownership and authorization are required without building a public marketplace. | Minimum auth, membership, roles, and tenant isolation stay in scope. |
| P-004 | Keep commerce, AI chat/RAG, and advanced LMS features outside the focused MVP. | They do not contribute to the defining journey and would delay delivery. | No routes, credentials, providers, schema, or UI for those capabilities. |
| P-005 | Use synthetic or rights-cleared local data during implementation. | Privacy, retention, capacity, recovery, and provider approvals are not production-ready. | Real customer data and production enablement remain blocked. |
| P-006 | `docs/product/spec.md` is the concise product contract; `docs/plan` holds detailed implementation constraints. | A small entry point prevents agents from loading or recreating the entire plan for every task. | Scope changes update the spec, features, affected plan sections, and decisions together. |
| P-007 | Use up to four independent issue/branch/worktree/PR lanes. | Parallel work should not create file, resource, migration, or branch collisions. | Contracts freeze first; shared hotspots have one integration owner. |
| P-008 | Store repository skills in `.agents/skills`; reserve `.codex/config.toml` for project settings. | This follows the supported Codex repository customization layout. | Skills remain discoverable without duplicating them under `.codex`. |

# Readiness Audit — F-007 Learner Course Playback and Progress

Status: **READY FOR IMPLEMENTATION AFTER THE #50 CORRECTION REVIEW AND MERGE**

- [x] Outcome and non-goals match the focused product spec and F-007 inventory.
- [x] F-001 identity/tenant and F-002 immutable publication dependencies are present.
- [x] Actors, least-privilege permissions, private learner flow, tenant/resource
  authorization, and neutral denial behavior are explicit.
- [x] P-014 records the project-owner decisions for F007-Q01, F007-Q02, F007-Q03,
  and Q-P08/F007-Q04.
- [x] Enrollment revocation is terminal; fresh re-enrollment pins the then-current
  published version and copies no historical progress.
- [x] Withdrawn or archived pins immediately return neutral
  `404 LEARNING_RESOURCE_NOT_FOUND`, remain historically durable, and never
  auto-migrate.
- [x] Progress changes only through explicit `open_lesson`, `complete_lesson`, and
  `reopen_lesson` commands; required-lesson completion and reopen semantics are fixed.
- [x] The initial focused-pilot locale is exactly `en`, while Unicode, language
  metadata, fallback, and RTL-ready structure remain preserved.
- [x] DTO, HTTP, event, and synthetic-fixture contracts are executable and retain the
  previously merged public shape.
- [x] Test planning covers contracts, policy, migrations, real PostgreSQL RLS,
  services, API/Admin, event minimization, browser, accessibility, concurrency, and
  F-001/F-002 regression behavior.
- [x] One bounded implementation issue has exclusive paths/resources and one owner for
  migrations, permission seeds, composition, OpenAPI/client, web/E2E, events, and the
  documentation manifest.
- [x] No PDF, AI, provider, vector, commerce, assessment, notification, analytics,
  real-data, or production capability is silently enabled.
- [x] Initial planning issue #45 and PR #47 are merged into `develop`.
- [ ] The pull request for correction issue #50 has an independent exact-SHA review,
  a distinct authorized approval, protected checks, and a verified merge into
  `develop`.

## Readiness verdict

No material product decision remains hidden in F-007. The accepted contract is
independently testable against frozen DTO/event schemas and synthetic fixtures, so the
feature is ready to enter implementation immediately after the #50 correction
satisfies its review, approval, check, and merge gate. Until GitHub reports that merge,
issue #46 remains `BLOCKED` and no implementation branch, worktree, or Compose project
may be created.

## Known limitations

- F-007 uses synthetic learner/course data and local infrastructure only.
- Initial locale acceptance is exactly `en`; no broader locale coverage is claimed.
- Enrollment is tenant-admin manual assignment only. Self-enrollment, catalog,
  invitations, cohorts/groups/rules, and bulk enrollment remain absent.
- The learner surface provides rich-text reading and deliberate progress only; assets,
  links, media, downloads, prerequisites, assessments, notes/bookmarks, discussions,
  certificates, notifications, and analytics remain absent.
- Retention/legal-hold, capacity, recovery, deployment, real-data, and production
  approvals remain release gates and are not claimed by this plan.

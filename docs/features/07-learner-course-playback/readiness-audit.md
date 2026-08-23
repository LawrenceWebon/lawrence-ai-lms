# Readiness Audit — F-007 Learner Course Playback and Progress

Status: **IMPLEMENTATION MERGED — POST-MERGE AUDIT CHANGES REQUIRED; #60 PENDING**

Launch transition: **READY FOR IMPLEMENTATION** was satisfied by the narrow owner
disposition before #46 resources were provisioned.

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
- [x] Correction #50 merged through PR #52 as
  `eb0fb3e808c37073e99625609c1338ce4b1ce51e`; its reviewed head has the same tree,
  protected checks passed, and its clean worktree/task-local resources were removed.
- [x] The
  [project-owner disposition](https://github.com/LawrenceWebon/lawrence-ai-lms/issues/46#issuecomment-5380754610)
  closes the PR #52 launch hold only for #46 without claiming retroactive approval.
- [x] #46 started from exact base
  `ed4670e6fa765d3edfb84610a450bef371a653ca` with its declared isolated worktree,
  Compose project, PostgreSQL port, and host scratch child.
- [x] Application commit `dd758909e3060032ecbe28f8175d3849a4c26208` has passing
  local contract, service, migration, RLS, API/Admin, architecture, generated-client,
  browser, accessibility-automation, and regression evidence.
- [x] PR #57 merged exact head
  `843d34b168f7cb0b140f7663e775585c80b35cfd` as
  `7c891c30d5281ed40eab592aa2ab4d14c0c83a33`; its configured protected checks passed,
  but GitHub records no submitted review or distinct pre-merge approval.
- [x] An independent post-merge audit reproduced an enrolled learner using
  `lms_api_runtime` to set its own enrollment to `revoked`, bypassing the tenant-admin
  service, idempotency, audit, and outbox facts, and returned `CHANGES REQUIRED`.
- [ ] Forward RLS remediation #60 is independently reviewed and merged.

## Readiness verdict

No material product decision is hidden: the merged policy contradicts the already
frozen tenant-admin-only enrollment-management contract. The independent post-merge
audit proved the production runtime lets a learner directly revoke its own enrollment.
F-007 remains merged but requires the narrow forward migration and regression evidence
in #60 before it is a clean dependency for F-008.

## Known limitations

- F-007 uses synthetic learner/course data and local infrastructure only.
- Initial locale acceptance is exactly `en`; no broader locale coverage is claimed.
- Browser accessibility evidence is automated Chromium coverage; no manual
  screen-reader or other assistive-technology interoperability claim is made.
- Enrollment is tenant-admin manual assignment only. Self-enrollment, catalog,
  invitations, cohorts/groups/rules, and bulk enrollment remain absent.
- The learner surface provides rich-text reading and deliberate progress only; assets,
  links, media, downloads, prerequisites, assessments, notes/bookmarks, discussions,
  certificates, notifications, and analytics remain absent.
- Retention/legal-hold, capacity, recovery, deployment, real-data, and production
  approvals remain release gates and are not claimed by this plan.

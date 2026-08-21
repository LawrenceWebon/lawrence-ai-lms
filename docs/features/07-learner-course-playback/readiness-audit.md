# Readiness Audit — F-007 Learner Course Playback and Progress

Status: **NOT READY FOR IMPLEMENTATION**

- [x] Outcome and non-goals match the focused product spec and F-007 inventory.
- [x] F-001 identity/tenant and F-002 immutable publication dependencies are present.
- [x] Actors, least-privilege permissions, private learner flow, tenant/resource
  authorization, and neutral denial behavior are explicit.
- [x] Enrollment pinning, dashboard/playback reads, explicit progress, concurrency,
  idempotency, audit/outbox, and no-GET-mutation behavior are proposed.
- [x] Proposed DTO, HTTP, event, and synthetic-fixture contracts are executable.
- [x] Test planning covers contracts, unit/policy, migrations, real PostgreSQL RLS,
  services, API/Admin, event minimization, browser, accessibility, concurrency, and
  F-001/F-002 regression behavior.
- [x] One bounded implementation issue has exclusive paths/resources and one owner for
  migrations, permission seeds, composition, OpenAPI/client, web/E2E, events, and the
  documentation manifest.
- [x] No PDF, AI, provider, vector, commerce, assessment, notification, analytics,
  real-data, or production capability is silently enabled.
- [ ] F007-Q01 private enrollment/re-enrollment policy is owner-approved.
- [ ] F007-Q02 withdrawn/archived pinned-version behavior is owner-approved.
- [ ] F007-Q03 explicit completion/reopen semantics are owner-approved.
- [ ] Q-P08/F007-Q04 initial locale acceptance is owner-approved.
- [ ] Planning issue #45 has independent exact-SHA review, a distinct authorized
  approval, protected checks, and a merge to `develop`.

## Readiness verdict

The feature is well-bounded and the recommended design is internally consistent, but
implementation is blocked. The four unchecked product decisions change lifecycle,
authorization-visible failure behavior, and acceptance evidence; selecting them is not
an implementation convenience. The proposed contracts are reviewable and executable,
but they are not frozen until those decisions and any resulting exact contract changes
receive owner approval and the planning PR merges.

After that merge, one vertical implementation issue may be marked
`READY FOR IMPLEMENTATION`, provision its declared branch/worktree/Compose resources
from the approved merge SHA, and implement only the owned paths in
`implementation-plan.md`.

## Known limitations

- F-007 uses synthetic learner/course data and local infrastructure only.
- The example locale `en` is fixture data, not closure of Q-P08.
- The package proposes manual assignment only; it does not approve self-enrollment,
  catalog, invitations, group/cohort rules, or bulk enrollment.
- It provides rich-text reading and deliberate progress only; assets, links, media,
  downloads, prerequisites, assessments, notes/bookmarks, discussions, certificates,
  notifications, and analytics remain absent.
- Retention/legal-hold, capacity, recovery, deployment, real-data, and production
  approvals remain release gates and are not claimed by this plan.

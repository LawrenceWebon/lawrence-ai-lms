# Implementation Plan — [Feature Name]

## Dependency graph

| Issue | Agent | Objective | Owned paths | Contracts/fixtures | Depends on | Shared owner | Merge order |
|---|---|---|---|---|---|---|---|
| `#___` | A | | | | | | |

## Issue contract

### Step/issue `#___` — [Name]

- Objective:
- Behavior added:
- Owned paths:
- Explicit non-scope:
- Data/migration impact:
- API/event/job impact:
- Authorization/tenant rules:
- Failure/retry behavior:
- Tests and exact commands:
- Evidence/handoff:

### Isolation and resources

- Branch:
- Worktree: one exact child of `/home/lawrence/Project Neo/worktrees/ai-lms/`
- Host scratch: one exact task child of `/home/lawrence/Project Neo/tmp/`
- Compose project:
- Ports/database/queue/bucket prefixes:

An issue is parallel-ready only when it can pass focused tests using frozen contracts
or synthetic fixtures without importing another agent's unmerged branch.

# F-001 Step 0 Toolchain Evidence

Status: selected and pinned for local synthetic implementation on 2026-08-10.

## Runtime and framework pins

| Component | Pin | Selection evidence |
|---|---:|---|
| Python | 3.14.7 | [Python downloads](https://www.python.org/downloads/) lists 3.14 as a supported bugfix series and 3.14.7 as the current release. |
| Node.js | 24.19.0 | [Node.js releases](https://nodejs.org/en/about/previous-releases) identifies v24 as LTS and 24.19.0 as the latest LTS release. |
| PostgreSQL | 18.4 | [PostgreSQL versioning](https://www.postgresql.org/support/versioning/) lists 18.4 as the current supported PostgreSQL 18 minor. |
| Django | 6.1 | [Django 6.1 documentation](https://docs.djangoproject.com/en/6.1/) and [release roadmap](https://www.djangoproject.com/download/6.1/roadmap/) identify the stable 2026-08-05 line and Python 3.12–3.14 support. |
| FastAPI | 0.141.1 | [PyPI project metadata](https://pypi.org/project/fastapi/) is the publisher-controlled release record. |
| Next.js | 16.3.0 | [npm registry metadata](https://registry.npmjs.org/next/latest) is the package publisher record. |
| React | 19.2.8 | [React versions](https://react.dev/versions) records the supported 19.2 line; the exact patch is locked from npm metadata. |
| TypeScript | 5.9.3 | The current stable 5.x line is the conservative compatibility baseline for the pinned Next.js ESLint/parser stack; TypeScript 7 adoption is deferred until that full toolchain is explicitly validated. |

All direct Python and JavaScript packages are exact pins in `backend/pyproject.toml`
and the workspace manifests. Transitive versions are frozen in `backend/uv.lock` and
`package-lock.json`. Preview and beta releases are excluded.

## Reproducible image inputs

| Image | Digest |
|---|---|
| `python:3.14.7-slim-bookworm` | `sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52` |
| `node:24.19.0-bookworm-slim` | `sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03` |
| `postgres:18.4-bookworm` | `sha256:882236b897e39051d2368c5ccc6cda944904723506b2dfc97f2a8f5bc9afa382` |

## Capability disposition

This selection enables only the inert web/API/Admin/test foundation. Authentication,
tenant membership, invitations, PDF processing, workers, AI, external providers,
production configuration, and real data remain absent. TD-006 becomes evidenced only
after the lockfiles and all issue #1 commands pass at the reviewed commit.

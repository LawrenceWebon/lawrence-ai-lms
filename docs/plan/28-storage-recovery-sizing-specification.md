# Storage, Egress, Backup, and Recovery Sizing Specification

Status: **BLOCKED_INPUT**  
Decision authority: D-033, D-040, D-041; Q-16/Q-19 approved direction  
Change IDs: CHG-020, CHG-025, CHG-026, CHG-029, CHG-045, CHG-046

Critical-database RPO 15 minutes and RTO 60 minutes are provisional. Accepted-upload object RTO is at most four hours. Accepted-upload object RPO, volumes, growth, egress, restore throughput, provider tiers, DR region and funded proof remain blocking inputs. Database backup must never be treated as backup of Supabase Storage object bytes.

## Accountable approvals

| Approval | Accountable owner | Required evidence | Current state |
|---|---|---|---|
| Product data-loss tolerance | `TBD-BLOCKING` | Approved object RPO by object class | missing |
| SRE recovery design | `TBD-BLOCKING` | Architecture, manifests and runbooks | missing |
| Finance/provider tier | `TBD-BLOCKING` | Funded primary/backup/egress/restore plan | missing |
| DPO/transfer approval | `TBD-BLOCKING` | Backup/DR location and subprocessor approval | missing |
| Quarterly drill approver | `TBD-BLOCKING` | Dated isolated restore report | missing |

## Twelve-month storage and traffic model

Measure each class independently; do not multiply an average file size across unlike data.

| Data/object class | Max item size/count | New items/day | Launch stored bytes/objects | Monthly growth | 12-month bytes/objects | Download/egress peak | Retention source | Restore priority | Status |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| Course metadata and relational rows | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | n/a | Document 25 | critical | blocked |
| Course assets and variants | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | high | blocked |
| Assignment submissions | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | high | blocked |
| Certificates and exports | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | high/medium | blocked |
| Source originals | AI disabled; `TBD before enablement` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | Document 25 | high | deferred |
| OCR/page images/intermediates | AI disabled; `TBD before enablement` | `TBD` | `TBD` | `TBD` | `TBD` | internal `TBD` | Document 25 | rebuildable/approved class | deferred |
| Normalized artifacts/chunks/vector manifests | AI disabled; `TBD before enablement` | `TBD` | `TBD` | `TBD` | `TBD` | internal `TBD` | Document 25 | PostgreSQL critical; vectors rebuildable | deferred |
| Logs/audit/analytics exports | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | Document 25 | security-class dependent | blocked |
| Database backups/PITR | derived from DB size/change rate | continuous | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | restore only | Document 25 | critical | blocked |
| Independent object versions/copies | derived from protected classes | continuous/batch `TBD` | `TBD-BLOCKING` | `TBD-BLOCKING` | `TBD-BLOCKING` | restore only | Document 25 | by class | blocked |

## Upload and processing quotas

Before enabling an upload class, specify and enforce per-file bytes, pages/pixels/archive expansion, files/day, bytes/day, concurrent uploads, tenant stored bytes/object count, MIME/signature allowlist, scan/parser CPU-memory-time/network limits, and exception owner. TUS is required for files over 6 MB or unreliable connections. Server code derives size, MIME, checksum, page/pixel count and object inventory from bytes; client declarations are hints only.

## Recovery objectives

| Recovery class | RPO | RTO | Current approval | Required proof |
|---|---:|---:|---|---|
| Critical PostgreSQL/Auth linkage/config metadata | 15 minutes | 60 minutes | provisional | PITR/restore tier, role-password recreation, isolated drill |
| Accepted private uploads and required published assets | `TBD-BLOCKING` | ≤ 4 hours | RTO provisional; RPO missing | independent versioned copy/export and measured restore |
| Rebuildable derivatives (thumbnails, OCR intermediates) | Derived from reprocessing cost `TBD` | `TBD-BLOCKING` | missing | rebuild benchmark and source availability |
| Pinecone vectors | PostgreSQL manifest is authority | `TBD-BLOCKING` | direction approved | full deterministic rebuild and reauthorization proof |
| Provider inbox/outbox and audit evidence | Same transaction/backup class as PostgreSQL | 60 minutes provisional | partial | replay/reconcile without duplicate side effects |
| Secrets, custom roles, bucket/policy/provider configuration | Versioned configuration plus secret-store recovery `TBD` | `TBD-BLOCKING` | missing | clean-environment recreation drill |

## Backup architecture

1. PostgreSQL uses an approved automated backup/PITR tier. Record exact coverage, retention, encryption, restore workflow and custom-role password exclusions.
2. Protected Storage objects use an independent versioned copy/export in an approved region/account. Database backups do not cover object bytes.
3. A signed/checksummed manifest maps tenant, bucket/key/version, DB record, content checksum, size, protection class, backup copy, tombstone and last verification.
4. Infrastructure/configuration recovery includes Auth settings, custom database roles/grants/password rotation, extensions, bucket/policy definitions, domains, provider webhooks, feature gates and secret references without storing secret values in the repository.
5. Pinecone is rebuilt from PostgreSQL active-generation manifests and deterministic vector IDs; it is never restored as authority.
6. Deleted or held data follows document 25 in primary, backup and restored environments.

## Isolated restore sequence

1. Declare incident/drill scope, target point, owners and write freeze/fencing strategy.
2. Provision an isolated environment with no customer traffic or outbound side effects.
3. Restore PostgreSQL/Auth/config and recreate custom roles/secrets through approved channels.
4. Restore protected objects; reconcile manifest counts, sizes and checksums against DB references.
5. Replay deletion/tombstone journal before access is enabled.
6. Rebuild derived assets and Pinecone active generation; validate citation and authorization links.
7. Run tenant-negative, course playback, upload/download, audit, job, email-suppression and data-integrity smoke tests.
8. Measure achieved RPO/RTO, missing/corrupt items, manual steps, throughput and projected full-volume duration.
9. Obtain independent approval; retain evidence and corrective actions with owners/due dates.

## Capacity and budget calculations

The approved model must include primary bytes, indexes/TOAST, object versions, backup multiplier, log/PITR growth, scan/work space, cross-region transfer, ordinary egress, restore egress, Pinecone rebuild calls, minimum restore throughput, staffing and quarterly-drill cost. Link all workload assumptions to document 27.

## Approval gate

This specification becomes `approved` only when no core row contains `TBD-BLOCKING`, an explicit accepted-upload object RPO is approved, provider tiers/regions and 12-month costs are funded, document 25 is approved, and an isolated production-volume-equivalent drill proves the objectives.


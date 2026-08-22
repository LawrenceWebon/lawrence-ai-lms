"use client";

import { type FormEvent, useMemo, useRef, useState } from "react";

import {
  ApiSourceAdmissionTransport,
  type SelectedTenant,
  type SourceAdmission,
  SourceAdmissionProblem,
  type TenantCandidate,
  type UploadIntent,
} from "./api-transport";
import styles from "./source-admission.module.css";

type Phase = "signed-out" | "select-tenant" | "workspace";
type Continuation = {
  tenantId: string;
  sourceDocumentId: string;
  sourceVersionId: string;
};

const statusLabels = {
  rights_pending: "Rights review needed",
  upload_pending: "Ready for private upload",
  quarantined: "Quarantined",
  validating: "Validating",
  admitted: "Admitted",
  rejected: "Rejected",
  cancelled: "Cancelled",
  blocked: "Blocked",
} as const;

export function SourceAdmissionExperience({ scenario }: { scenario?: string }) {
  const transport = useMemo(() => new ApiSourceAdmissionTransport(), []);
  const displayNameRef = useRef<HTMLInputElement>(null);
  const filenameRef = useRef<HTMLInputElement>(null);
  const holderRef = useRef<HTMLInputElement>(null);
  const evidenceRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>("signed-out");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenants, setTenants] = useState<TenantCandidate[]>([]);
  const [selected, setSelected] = useState<SelectedTenant | null>(null);
  const [snapshot, setSnapshot] = useState<SourceAdmission | null>(null);
  const [continuation, setContinuation] = useState<Continuation | null>(null);
  const [intent, setIntent] = useState<UploadIntent | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [declaredFilename, setDeclaredFilename] = useState("");
  const [basis, setBasis] = useState<
    "owned" | "licensed" | "written_permission" | "public_domain" | "other_documented"
  >("owned");
  const [rightsHolderName, setRightsHolderName] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [attested, setAttested] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const fixtureEnabled =
    scenario === "integration" && process.env.NEXT_PUBLIC_AI_LMS_LOCAL_F001_FIXTURE === "1";
  const canReview = selected?.permissionCodes.includes("documents.source_rights.review") ?? false;
  const canAdmit = selected?.permissionCodes.includes("documents.sources.admit") ?? false;
  const documentedBasis = ["licensed", "written_permission", "other_documented"].includes(
    basis,
  );

  function applySnapshot(next: SourceAdmission) {
    setSnapshot(next);
    setContinuation(null);
    if (next.source_version.admission_status !== "upload_pending") {
      setIntent(null);
      setFile(null);
    }
  }

  function handleFailure(error: unknown, fallback: string) {
    if (
      error instanceof SourceAdmissionProblem &&
      (error.code === "AUTHENTICATION_REQUIRED" || error.code === "ACCESS_INACTIVE")
    ) {
      transport.signOut();
      setSelected(null);
      setTenants([]);
      setSnapshot(null);
      setContinuation(null);
      setPhase("signed-out");
      setAlertMessage("Your source access is no longer active. Sign in again.");
      return;
    }
    const messages: Partial<Record<SourceAdmissionProblem["code"], string>> = {
      RESOURCE_NOT_FOUND: "That source is unavailable in this workspace.",
      RIGHTS_REQUIRED: "A separate rights reviewer must authorize storage first.",
      SEPARATE_REVIEWER_REQUIRED: "The declarant cannot review their own rights request.",
      UPLOAD_EXPIRED: "The private upload target expired. Request a new target.",
      QUOTA_REACHED: "The local source-admission quota has been reached.",
      VERSION_CONFLICT: "The source changed before this action completed. Refresh and try again.",
      REQUEST_INVALID: "The source request is invalid. Check the highlighted fields.",
      VALIDATION_UNAVAILABLE: "PDF validation is unavailable. The source remains quarantined.",
    };
    setAlertMessage(
      error instanceof SourceAdmissionProblem ? (messages[error.code] ?? fallback) : fallback,
    );
  }

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (!fixtureEnabled) {
      setAlertMessage("The local synthetic source fixture is not enabled.");
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(email) || !password) {
      setAlertMessage("Enter your email address and password.");
      return;
    }
    setBusy(true);
    setStatusMessage("Checking source access…");
    try {
      setTenants(await transport.signIn({ email, password }));
      setPassword("");
      setPhase("select-tenant");
      setStatusMessage("Access loaded. Choose a workspace.");
    } catch (error: unknown) {
      handleFailure(error, "We could not open the source workspace.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function selectTenant(tenant: TenantCandidate) {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage(`Checking ${tenant.display_name} source access…`);
    try {
      const nextSelected = await transport.selectTenant(tenant.id, tenants);
      setSelected(nextSelected);
      if (continuation !== null) {
        if (continuation.tenantId !== tenant.id) {
          setContinuation(null);
          setSnapshot(null);
        } else {
          applySnapshot(
            await transport.getAdmission(
              continuation.sourceDocumentId,
              continuation.sourceVersionId,
              continuation.tenantId,
            ),
          );
        }
      }
      setPhase("workspace");
      setStatusMessage(`${tenant.display_name} is ready for private source admission.`);
    } catch (error: unknown) {
      handleFailure(error, "That workspace is unavailable.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    setContinuation(
      snapshot === null
        ? null
        : {
            tenantId: snapshot.source_document.tenant_id,
            sourceDocumentId: snapshot.source_document.id,
            sourceVersionId: snapshot.source_version.id,
          },
    );
    transport.signOut();
    setSelected(null);
    setTenants([]);
    setEmail("");
    setPassword("");
    setSnapshot(null);
    setIntent(null);
    setFile(null);
    setDisplayName("");
    setDeclaredFilename("");
    setRightsHolderName("");
    setEvidenceReference("");
    setAttested(false);
    setPhase("signed-out");
    setStatusMessage("Signed out.");
    setAlertMessage("");
  }

  function validateDeclaration(): boolean {
    if (!displayName.trim()) {
      setAlertMessage("Complete the source declaration. Add a display name.");
      displayNameRef.current?.focus();
      return false;
    }
    if (!/^[^/\\]+\.[Pp][Dd][Ff]$/.test(declaredFilename)) {
      setAlertMessage("Complete the source declaration. Enter a PDF filename without a path.");
      filenameRef.current?.focus();
      return false;
    }
    if (documentedBasis && !rightsHolderName.trim()) {
      setAlertMessage("Documented rights require the rights holder name.");
      holderRef.current?.focus();
      return false;
    }
    if (documentedBasis && !/^[A-Za-z0-9._:-]+$/.test(evidenceReference)) {
      setAlertMessage("Documented rights require a bounded evidence reference.");
      evidenceRef.current?.focus();
      return false;
    }
    if (!attested) {
      setAlertMessage("Confirm the rights attestation before continuing.");
      return false;
    }
    return true;
  }

  async function createDeclaration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (!validateDeclaration()) {
      return;
    }
    setBusy(true);
    setStatusMessage("Recording the rights declaration…");
    try {
      const rights = {
        basis,
        attestation_version: "f003-source-rights-attestation-v1" as const,
        attested: true as const,
        ...(documentedBasis
          ? {
              rights_holder_name: rightsHolderName.trim(),
              evidence_reference: evidenceReference,
            }
          : {}),
      };
      applySnapshot(
        await transport.createAdmission({
          display_name: displayName.trim(),
          declared_filename: declaredFilename,
          rights_declaration: rights,
        }),
      );
      setStatusMessage("Rights declaration recorded. A separate reviewer must authorize storage.");
    } catch (error: unknown) {
      handleFailure(error, "The rights declaration could not be recorded.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function review(decision: "activate" | "deny" | "revoke") {
    if (snapshot === null) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Recording the human rights decision…");
    try {
      applySnapshot(await transport.review(snapshot, decision));
      setStatusMessage(
        decision === "activate"
          ? "Storage authorization activated by a separate reviewer."
          : decision === "deny"
            ? "Storage authorization denied."
            : "Rights revoked. New work is blocked and removal is reconciling.",
      );
    } catch (error: unknown) {
      handleFailure(error, "The rights decision could not be recorded.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function createIntent() {
    if (snapshot === null) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Creating a private, short-lived upload target…");
    try {
      setIntent(await transport.createUploadIntent(snapshot));
      setStatusMessage("Private upload target ready for one PDF.");
    } catch (error: unknown) {
      handleFailure(error, "A private upload target could not be created.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (intent === null || file === null) {
      setAlertMessage("Choose one synthetic or rights-cleared PDF.");
      fileRef.current?.focus();
      return;
    }
    setBusy(true);
    setStatusMessage("Uploading to private quarantine and validating server-derived bytes…");
    try {
      applySnapshot(await transport.upload(intent, file));
      setStatusMessage("Source admission validation completed.");
    } catch (error: unknown) {
      handleFailure(error, "The PDF could not be admitted.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    if (snapshot === null) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Refreshing source status…");
    try {
      applySnapshot(await transport.refresh(snapshot));
      setStatusMessage("Source status refreshed.");
    } catch (error: unknown) {
      handleFailure(error, "Source status could not be refreshed.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (snapshot === null) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Cancelling source admission…");
    try {
      applySnapshot(await transport.cancel(snapshot));
      setStatusMessage("Source admission cancelled. New upload and validation work is blocked.");
    } catch (error: unknown) {
      handleFailure(error, "Source admission could not be cancelled.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={styles.shell}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Private AI LMS</p>
        <h1>PDF source admission</h1>
        <p>
          Declare your rights, obtain separate human authorization, and validate one private PDF
          before any extraction can begin.
        </p>
      </header>

      {alertMessage ? (
        <div className={styles.alert} role="alert">
          {alertMessage}
        </div>
      ) : null}
      {statusMessage ? (
        <div className={styles.status} role="status" aria-live="polite">
          {statusMessage}
        </div>
      ) : null}

      {phase === "signed-out" ? (
        <section className={styles.card} aria-labelledby="source-sign-in-heading">
          <h2 id="source-sign-in-heading">Sign in to a source workspace</h2>
          {continuation ? (
            <p>
              Sign in as the next authorized human. The server will reauthorize the current source
              before any source details are shown, and no source state is stored in browser storage.
            </p>
          ) : null}
          <form className={styles.form} onSubmit={handleSignIn} noValidate>
            <label>
              Email address
              <input
                autoComplete="username"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Password
              <input
                autoComplete="current-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button className={styles.primaryButton} disabled={busy} type="submit">
              Open source workspace
            </button>
          </form>
        </section>
      ) : null}

      {phase === "select-tenant" ? (
        <section className={styles.card} aria-labelledby="source-workspace-heading">
          <h2 id="source-workspace-heading">Choose a workspace</h2>
          <ul className={styles.tenantList}>
            {tenants.map((tenant) => (
              <li key={tenant.id}>
                <span>{tenant.display_name}</span>
                <button
                  className={styles.secondaryButton}
                  disabled={busy}
                  onClick={() => void selectTenant(tenant)}
                  type="button"
                >
                  Select {tenant.display_name}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {phase === "workspace" && selected ? (
        <section className={styles.workspace} aria-label="Source admission workspace">
          <div className={styles.workspaceHeader}>
            <div>
              <p className={styles.eyebrow}>{selected.tenant.display_name}</p>
              <h2>Private source workflow</h2>
            </div>
            <button className={styles.secondaryButton} onClick={signOut} type="button">
              Sign out and switch user
            </button>
          </div>

          {snapshot === null ? (
            <section className={styles.card} aria-labelledby="declaration-heading">
              <h3 id="declaration-heading">Declare one PDF source</h3>
              <form className={styles.form} onSubmit={createDeclaration} noValidate>
                <label>
                  Source display name
                  <input
                    ref={displayNameRef}
                    maxLength={160}
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                  />
                </label>
                <label>
                  Declared PDF filename
                  <input
                    ref={filenameRef}
                    maxLength={255}
                    placeholder="synthetic-source.pdf"
                    value={declaredFilename}
                    onChange={(event) => setDeclaredFilename(event.target.value)}
                  />
                </label>
                <label>
                  Rights basis
                  <select
                    value={basis}
                    onChange={(event) => setBasis(event.target.value as typeof basis)}
                  >
                    <option value="owned">Owned</option>
                    <option value="licensed">Licensed</option>
                    <option value="written_permission">Written permission</option>
                    <option value="public_domain">Public domain</option>
                    <option value="other_documented">Other documented basis</option>
                  </select>
                </label>
                {documentedBasis ? (
                  <>
                    <label>
                      Rights holder name
                      <input
                        ref={holderRef}
                        maxLength={160}
                        value={rightsHolderName}
                        onChange={(event) => setRightsHolderName(event.target.value)}
                      />
                    </label>
                    <label>
                      Evidence reference
                      <input
                        ref={evidenceRef}
                        maxLength={120}
                        value={evidenceReference}
                        onChange={(event) => setEvidenceReference(event.target.value)}
                      />
                    </label>
                  </>
                ) : null}
                <label className={styles.checkLabel}>
                  <input
                    checked={attested}
                    onChange={(event) => setAttested(event.target.checked)}
                    type="checkbox"
                  />
                  I attest that this rights declaration is accurate for storing this source.
                </label>
                <button className={styles.primaryButton} disabled={busy || !canAdmit} type="submit">
                  Submit rights declaration
                </button>
              </form>
            </section>
          ) : (
            <section className={styles.card} aria-labelledby="source-status-heading">
              <div className={styles.sectionHeader}>
                <div>
                  <h3 id="source-status-heading">{snapshot.source_document.display_name}</h3>
                  <p>{snapshot.source_version.declared_filename}</p>
                </div>
                <strong className={styles.badge} data-testid="source-state">
                  {statusLabels[snapshot.source_version.admission_status]}
                </strong>
              </div>
              <dl className={styles.details}>
                <div>
                  <dt>Rights authorization</dt>
                  <dd>{snapshot.store_authorization.status}</dd>
                </div>
                <div>
                  <dt>Removal</dt>
                  <dd>{snapshot.removal.status}</dd>
                </div>
                <div>
                  <dt>Validation attempts</dt>
                  <dd>{snapshot.source_version.validation_attempt_count}</dd>
                </div>
              </dl>
              <span
                data-testid="source-identifiers"
                data-source-document-id={snapshot.source_document.id}
                data-source-version-id={snapshot.source_version.id}
                hidden
              />
              {snapshot.source_version.rejection_code ? (
                <p className={styles.rejection}>
                  Safe rejection code: <code>{snapshot.source_version.rejection_code}</code>
                </p>
              ) : null}

              {snapshot.source_version.admission_status === "rights_pending" ? (
                canReview ? (
                  <div className={styles.actions}>
                    <button
                      className={styles.primaryButton}
                      disabled={busy}
                      onClick={() => void review("activate")}
                      type="button"
                    >
                      Authorize private storage
                    </button>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy}
                      onClick={() => void review("deny")}
                      type="button"
                    >
                      Deny rights request
                    </button>
                  </div>
                ) : (
                  <p>A separate tenant rights reviewer must sign in and decide this request.</p>
                )
              ) : null}

              {snapshot.source_version.admission_status === "upload_pending" && canAdmit ? (
                intent === null ? (
                  <button
                    className={styles.primaryButton}
                    disabled={busy}
                    onClick={() => void createIntent()}
                    type="button"
                  >
                    Create private upload target
                  </button>
                ) : (
                  <form className={styles.form} onSubmit={upload}>
                    <label>
                      Synthetic or rights-cleared PDF
                      <input
                        ref={fileRef}
                        accept="application/pdf,.pdf"
                        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                        type="file"
                      />
                    </label>
                    <p className={styles.hint}>
                      Browser metadata is only a hint. The server derives checksum, media,
                      signature, page, pixel, decoded-size, and inspection evidence.
                    </p>
                    <button className={styles.primaryButton} disabled={busy} type="submit">
                      Upload and validate PDF
                    </button>
                  </form>
                )
              ) : null}

              {snapshot.store_authorization.status === "active" && canReview ? (
                <button
                  className={styles.dangerButton}
                  disabled={busy}
                  onClick={() => void review("revoke")}
                  type="button"
                >
                  Revoke source rights
                </button>
              ) : null}

              <div className={styles.actions}>
                {[
                  "rights_pending",
                  "upload_pending",
                  "quarantined",
                  "validating",
                ].includes(snapshot.source_version.admission_status) && canAdmit ? (
                  <button
                    className={styles.secondaryButton}
                    disabled={busy}
                    onClick={() => void cancel()}
                    type="button"
                  >
                    Cancel admission
                  </button>
                ) : null}
                <button
                  className={styles.secondaryButton}
                  disabled={busy}
                  onClick={() => void refresh()}
                  type="button"
                >
                  Refresh source status
                </button>
              </div>
            </section>
          )}
        </section>
      ) : null}
    </main>
  );
}

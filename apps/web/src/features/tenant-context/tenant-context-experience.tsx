"use client";

import { type FormEvent, useMemo, useRef, useState } from "react";

import {
  MockTenantContextTransport,
} from "./mock-transport";
import { ApiTenantContextTransport } from "./api-transport";
import {
  type ActiveTenant,
  TenantContextProblem,
  type TenantCandidate,
  type TenantContextTransport,
} from "./transport";
import styles from "./tenant-context.module.css";

type FieldErrors = {
  email?: string;
  password?: string;
};

type TenantContextExperienceProps = {
  scenario?: string;
};

const genericInvitationError =
  "This invitation cannot be accepted. Ask a tenant administrator for a new invitation.";

export function TenantContextExperience({ scenario }: TenantContextExperienceProps) {
  const transport = useMemo<TenantContextTransport>(() => {
    if (
      scenario === "integration" &&
      process.env.NEXT_PUBLIC_AI_LMS_LOCAL_F001_FIXTURE === "1"
    ) {
      return new ApiTenantContextTransport();
    }
    return new MockTenantContextTransport(scenario);
  }, [scenario]);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [invitationToken, setInvitationToken] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [signedIn, setSignedIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [availableTenants, setAvailableTenants] = useState<TenantCandidate[]>([]);
  const [activeTenant, setActiveTenant] = useState<ActiveTenant | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [alertMessage, setAlertMessage] = useState("");

  function resetPrivateContext(message = "") {
    transport.signOut();
    setSignedIn(false);
    setEmail("");
    setPassword("");
    setInvitationToken("");
    setFieldErrors({});
    setAvailableTenants([]);
    setActiveTenant(null);
    setStatusMessage("");
    setAlertMessage(message);
  }

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors: FieldErrors = {};
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      errors.email = "Enter a valid email address.";
    }
    if (!password) {
      errors.password = "Enter your password.";
    }

    setFieldErrors(errors);
    setAlertMessage("");
    if (Object.keys(errors).length > 0) {
      if (errors.email) {
        emailRef.current?.focus();
      } else {
        passwordRef.current?.focus();
      }
      return;
    }

    setBusy(true);
    setStatusMessage("Checking your access…");
    try {
      const tenants = await transport.signIn({ email, password });
      setAvailableTenants(tenants);
      setSignedIn(true);
      setPassword("");
      setStatusMessage(
        tenants.length === 0
          ? "No active workspaces were found."
          : "Access loaded. Choose a workspace to continue.",
      );
    } catch (error: unknown) {
      if (error instanceof TenantContextProblem && error.code === "TRANSPORT_UNAVAILABLE") {
        setAlertMessage(
          "We could not load your access. Try again without changing your sign-in details.",
        );
      } else {
        setAlertMessage("We could not sign you in with those details. Check them and try again.");
      }
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function handleTenantSelection(tenant: TenantCandidate) {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage(`Checking ${tenant.displayName} access…`);
    try {
      const selected = await transport.selectTenant(tenant.id, availableTenants);
      setActiveTenant(selected);
      setStatusMessage(`${selected.displayName} is now active.`);
    } catch {
      setActiveTenant(null);
      setStatusMessage("");
      setAlertMessage(
        "You do not have access to that workspace. Your available access has not changed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = invitationToken.trim();
    setInvitationToken("");
    setAlertMessage("");
    if (!token) {
      setAlertMessage(genericInvitationError);
      return;
    }

    setBusy(true);
    setStatusMessage("Checking the invitation…");
    try {
      const result = await transport.acceptInvitation(token);
      setStatusMessage(
        result === "accepted"
          ? "Invitation accepted. Refresh access to see any new workspace."
          : "Invitation already accepted. Refresh access to see your current workspaces.",
      );
    } catch {
      setStatusMessage("");
      setAlertMessage(genericInvitationError);
    } finally {
      setBusy(false);
    }
  }

  async function handleRefresh() {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Refreshing your access…");
    try {
      const tenants = await transport.refreshAccess(availableTenants);
      setAvailableTenants(tenants);
      setStatusMessage("Your access is up to date.");
    } catch (error: unknown) {
      resetPrivateContext(
        error instanceof TenantContextProblem && error.code === "AUTHENTICATION_REQUIRED"
          ? "Your session has expired. Sign in again."
          : "Your access is no longer active. Sign in again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={styles.shell}>
      {statusMessage ? (
        <div className={styles.statusRegion} role="status" aria-live="polite" aria-atomic="true">
          {statusMessage}
        </div>
      ) : null}
      {alertMessage ? (
        <div className={styles.alert} role="alert">
          {alertMessage}
        </div>
      ) : null}

      {!signedIn ? (
        <section className={styles.card} aria-labelledby="sign-in-heading">
          <p className={styles.eyebrow}>Private AI LMS</p>
          <h1 id="sign-in-heading">Welcome back</h1>
          <p className={styles.intro}>
            Sign in with your invited account. Workspace access is checked again after you choose it.
          </p>
          <form className={styles.form} onSubmit={handleSignIn} noValidate>
            <div className={styles.field}>
              <label htmlFor="email">Email address</label>
              <input
                ref={emailRef}
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                aria-invalid={fieldErrors.email ? "true" : "false"}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
                onChange={(event) => setEmail(event.target.value)}
              />
              {fieldErrors.email ? (
                <span className={styles.fieldError} id="email-error">
                  {fieldErrors.email}
                </span>
              ) : null}
            </div>
            <div className={styles.field}>
              <label htmlFor="password">Password</label>
              <input
                ref={passwordRef}
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                aria-invalid={fieldErrors.password ? "true" : "false"}
                aria-describedby={fieldErrors.password ? "password-error" : undefined}
                onChange={(event) => setPassword(event.target.value)}
              />
              {fieldErrors.password ? (
                <span className={styles.fieldError} id="password-error">
                  {fieldErrors.password}
                </span>
              ) : null}
            </div>
            <button className={styles.primaryButton} type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </section>
      ) : (
        <div className={styles.workspace}>
          <header className={styles.workspaceHeader}>
            <div>
              <p className={styles.eyebrow}>Authenticated workspace</p>
              <h1>Choose a workspace</h1>
              <p className={styles.intro}>
                Selection does not grant access. The service verifies your current membership every time.
              </p>
            </div>
            <div className={styles.headerActions}>
              <button
                className={styles.secondaryButton}
                type="button"
                onClick={handleRefresh}
                disabled={busy}
              >
                Refresh access
              </button>
              <button
                className={styles.secondaryButton}
                type="button"
                disabled={busy}
                onClick={() => resetPrivateContext()}
              >
                Sign out
              </button>
            </div>
          </header>

          {activeTenant ? (
            <section className={styles.activeTenant} data-testid="active-tenant" aria-labelledby="active-heading">
              <div>
                <p className={styles.eyebrow}>Active workspace</p>
                <h2 id="active-heading">{activeTenant.displayName}</h2>
                <p>Authorized actions will be rechecked by the server.</p>
              </div>
            </section>
          ) : null}

          {availableTenants.length === 0 ? (
            <section className={styles.card} aria-labelledby="empty-heading">
              <h2 id="empty-heading">No active workspaces</h2>
              <p>Ask a tenant administrator for an invitation or active membership.</p>
            </section>
          ) : (
            <section className={styles.card} aria-labelledby="workspace-list-heading">
              <h2 id="workspace-list-heading">Available workspaces</h2>
              <ul className={styles.tenantList}>
                {availableTenants.map((tenant) => (
                  <li key={tenant.id}>
                    <div>
                      <strong>{tenant.displayName}</strong>
                      <span className={styles.slug}>/{tenant.slug}</span>
                    </div>
                    <button
                      className={styles.primaryButton}
                      type="button"
                      disabled={busy}
                      onClick={() => handleTenantSelection(tenant)}
                    >
                      Select {tenant.displayName}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className={styles.card} aria-labelledby="invitation-heading">
            <h2 id="invitation-heading">Accept an invitation</h2>
            <p>Paste the single-use token from your tenant administrator. It is cleared after submission.</p>
            <form className={styles.form} onSubmit={handleInvitation}>
              <div className={styles.field}>
                <label htmlFor="invitation-token">Invitation token</label>
                <input
                  id="invitation-token"
                  name="invitation-token"
                  type="password"
                  autoComplete="off"
                  value={invitationToken}
                  onChange={(event) => setInvitationToken(event.target.value)}
                />
              </div>
              <button className={styles.primaryButton} type="submit" disabled={busy}>
                Accept invitation
              </button>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

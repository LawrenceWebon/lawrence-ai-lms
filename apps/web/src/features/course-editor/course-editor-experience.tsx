"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  ApiCourseEditorTransport,
  type CourseSnapshot,
  type CourseVersionHistory,
  type CurriculumSection,
  CourseEditorProblem,
  type TenantCandidate,
} from "./api-transport";
import { RichTextRenderer } from "./rich-text-renderer";
import styles from "./course-editor.module.css";

type Phase = "signed-out" | "select-tenant" | "editing";

const stateLabels = {
  draft: "Draft",
  under_review: "Under review",
  changes_requested: "Changes requested",
  approved: "Approved",
  scheduled: "Scheduled",
  published: "Published",
  withdrawn: "Withdrawn",
  archived: "Archived",
} as const;

function textFromSnapshot(snapshot: CourseSnapshot): string {
  const document = snapshot.sections[0]?.lessons[0]?.content_blocks[0]?.document;
  if (!document) {
    return "";
  }
  return document.content
    .flatMap((node) => {
      if (node.type === "paragraph" || node.type === "heading") {
        return node.content.map((text) => text.text);
      }
      return node.items.flatMap((item) =>
        item.content.flatMap((paragraph) => paragraph.content.map((text) => text.text)),
      );
    })
    .join("\n");
}

export function CourseEditorExperience({ scenario }: { scenario?: string }) {
  const transport = useMemo(() => new ApiCourseEditorTransport(), []);
  const slugRef = useRef<HTMLInputElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const sectionRef = useRef<HTMLInputElement>(null);
  const lessonRef = useRef<HTMLInputElement>(null);
  const lessonTextRef = useRef<HTMLTextAreaElement>(null);
  const publishDialogRef = useRef<HTMLDialogElement>(null);

  const [phase, setPhase] = useState<Phase>("signed-out");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenants, setTenants] = useState<TenantCandidate[]>([]);
  const [activeTenant, setActiveTenant] = useState<TenantCandidate | null>(null);
  const [snapshot, setSnapshot] = useState<CourseSnapshot | null>(null);
  const [history, setHistory] = useState<CourseVersionHistory | null>(null);
  const [publishedVersionId, setPublishedVersionId] = useState<string | null>(null);
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sectionTitle, setSectionTitle] = useState("");
  const [lessonTitle, setLessonTitle] = useState("");
  const [lessonText, setLessonText] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [publishConfirmation, setPublishConfirmation] = useState(false);

  const fixtureEnabled =
    scenario === "integration" && process.env.NEXT_PUBLIC_AI_LMS_LOCAL_F001_FIXTURE === "1";

  useEffect(() => {
    const dialog = publishDialogRef.current;
    if (!dialog) {
      return;
    }
    if (publishConfirmation && !dialog.open) {
      dialog.showModal();
    } else if (!publishConfirmation && dialog.open) {
      dialog.close();
    }
  }, [publishConfirmation]);

  function clearCourseFields() {
    setSnapshot(null);
    setHistory(null);
    setPublishedVersionId(null);
    setSlug("");
    setTitle("");
    setDescription("");
    setSectionTitle("");
    setLessonTitle("");
    setLessonText("");
    setPublishConfirmation(false);
  }

  function resetAccess(message: string) {
    transport.signOut();
    setPhase("signed-out");
    setEmail("");
    setPassword("");
    setTenants([]);
    setActiveTenant(null);
    clearCourseFields();
    setStatusMessage("");
    setAlertMessage(message);
  }

  function applySnapshot(next: CourseSnapshot) {
    setSnapshot(next);
    setSlug(next.course.slug);
    setTitle(next.version.title);
    setDescription(next.version.description);
    setSectionTitle(next.sections[0]?.title ?? "");
    setLessonTitle(next.sections[0]?.lessons[0]?.title ?? "");
    setLessonText(textFromSnapshot(next));
    if (next.course.current_published_version_id) {
      setPublishedVersionId(next.course.current_published_version_id);
    }
  }

  function handleFailure(error: unknown, fallback: string) {
    if (
      error instanceof CourseEditorProblem &&
      (error.code === "ACCESS_INACTIVE" || error.code === "AUTHENTICATION_REQUIRED")
    ) {
      resetAccess("Your course access is no longer active. Sign in again.");
      return;
    }
    if (error instanceof CourseEditorProblem && error.code === "VERSION_CONFLICT") {
      setAlertMessage("This version changed before your action completed. Refresh and try again.");
      return;
    }
    if (error instanceof CourseEditorProblem && error.code === "COURSE_VERSION_IMMUTABLE") {
      setAlertMessage("Published course versions are immutable. Create a new draft to edit.");
      return;
    }
    if (error instanceof CourseEditorProblem && error.code === "CONTENT_HASH_MISMATCH") {
      setAlertMessage("The reviewed content changed. Refresh before continuing.");
      return;
    }
    setAlertMessage(fallback);
  }

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (!fixtureEnabled) {
      setAlertMessage("The local synthetic authoring fixture is not enabled.");
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(email) || !password) {
      setAlertMessage("Enter your email address and password.");
      return;
    }
    setBusy(true);
    setStatusMessage("Checking course access…");
    try {
      const available = await transport.signIn({ email, password });
      setTenants(available);
      setPassword("");
      setPhase("select-tenant");
      setStatusMessage("Access loaded. Choose a workspace to continue.");
    } catch (error: unknown) {
      handleFailure(error, "We could not open the authoring workspace. Check your details.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function handleTenantSelection(tenant: TenantCandidate) {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage(`Checking ${tenant.display_name} course access…`);
    try {
      const selected = await transport.selectTenant(tenant.id, tenants);
      setActiveTenant(selected);
      setPhase("editing");
      setStatusMessage(`${selected.display_name} is ready for authoring.`);
    } catch (error: unknown) {
      handleFailure(error, "That workspace is unavailable.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  function validateCourseDetails(): boolean {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
      setAlertMessage("Complete the required course details. Use a lowercase course slug.");
      slugRef.current?.focus();
      return false;
    }
    if (!title.trim()) {
      setAlertMessage("Complete the required course details. Add a course title.");
      titleRef.current?.focus();
      return false;
    }
    if (!description.trim()) {
      setAlertMessage("Complete the required course details. Add a course description.");
      descriptionRef.current?.focus();
      return false;
    }
    return true;
  }

  async function handleCreateCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (!validateCourseDetails()) {
      return;
    }
    setBusy(true);
    setStatusMessage("Creating the draft…");
    try {
      const created = await transport.createCourse({
        slug,
        primary_locale: "en",
        title: title.trim(),
        description: description.trim(),
      });
      applySnapshot(created);
      setHistory(await transport.history(created));
      setStatusMessage(`Draft version ${created.version.version_number} created.`);
    } catch (error: unknown) {
      handleFailure(error, "The course draft could not be created.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (!snapshot || !validateCourseDetails()) {
      return;
    }
    setBusy(true);
    setStatusMessage("Saving course details…");
    try {
      const updated = await transport.updateDetails(snapshot, {
        title: title.trim(),
        description: description.trim(),
      });
      applySnapshot(updated);
      setStatusMessage("Course details saved.");
    } catch (error: unknown) {
      handleFailure(error, "Course details could not be saved.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  function validateCurriculum(): boolean {
    if (!sectionTitle.trim()) {
      setAlertMessage("Complete the curriculum. Add a section title.");
      sectionRef.current?.focus();
      return false;
    }
    if (!lessonTitle.trim()) {
      setAlertMessage("Complete the curriculum. Add a lesson title.");
      lessonRef.current?.focus();
      return false;
    }
    if (!lessonText.trim()) {
      setAlertMessage("Complete the curriculum. Add lesson text.");
      lessonTextRef.current?.focus();
      return false;
    }
    return true;
  }

  function curriculumFor(current: CourseSnapshot): CurriculumSection[] {
    const existingSection = current.sections[0];
    const existingLesson = existingSection?.lessons[0];
    const existingBlock = existingLesson?.content_blocks[0];
    return [
      {
        ...(existingSection
          ? { id: existingSection.id, expected_row_version: existingSection.row_version }
          : {}),
        title: sectionTitle.trim(),
        position: 1,
        lessons: [
          {
            ...(existingLesson
              ? { id: existingLesson.id, expected_row_version: existingLesson.row_version }
              : {}),
            title: lessonTitle.trim(),
            position: 1,
            is_required: true,
            content_blocks: [
              {
                ...(existingBlock
                  ? { id: existingBlock.id, expected_row_version: existingBlock.row_version }
                  : {}),
                kind: "rich_text",
                position: 1,
                document: {
                  type: "document",
                  content: [
                    {
                      type: "paragraph",
                      content: [{ type: "text", text: lessonText.trim(), marks: [] }],
                    },
                  ],
                },
              },
            ],
          },
        ],
      },
    ];
  }

  async function handleSaveCurriculum(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (!snapshot || !validateCurriculum()) {
      return;
    }
    setBusy(true);
    setStatusMessage("Saving curriculum…");
    try {
      const updated = await transport.replaceCurriculum(snapshot, curriculumFor(snapshot));
      applySnapshot(updated);
      setStatusMessage("Curriculum saved.");
    } catch (error: unknown) {
      handleFailure(error, "The curriculum could not be saved.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function applyTransition(
    transition: "submit_review" | "request_changes" | "approve" | "publish" | "withdraw" | "archive",
    successMessage: string,
  ) {
    if (!snapshot) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Applying the lifecycle action…");
    try {
      const updated = await transport.transition(snapshot, transition);
      applySnapshot(updated);
      if (updated.version.status === "published") {
        setPublishedVersionId(updated.version.id);
      }
      setHistory(await transport.history(updated));
      setStatusMessage(successMessage);
    } catch (error: unknown) {
      handleFailure(error, "The lifecycle action could not be completed.");
      setStatusMessage("");
    } finally {
      setBusy(false);
      setPublishConfirmation(false);
    }
  }

  async function handleSuccessor() {
    if (!snapshot) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Creating a new version draft…");
    try {
      const successor = await transport.createSuccessor(snapshot);
      applySnapshot(successor);
      setHistory(await transport.history(successor));
      setStatusMessage(`Version ${successor.version.version_number} draft created.`);
    } catch (error: unknown) {
      handleFailure(error, "A successor draft could not be created.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function refreshHistory() {
    if (!snapshot) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Refreshing version history…");
    try {
      setHistory(await transport.history(snapshot));
      setStatusMessage("Version history refreshed.");
    } catch (error: unknown) {
      if (error instanceof CourseEditorProblem && error.code === "RESOURCE_NOT_FOUND") {
        resetAccess("Your course access is no longer active. Sign in again.");
      } else {
        handleFailure(error, "Version history could not be refreshed.");
        setStatusMessage("");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={styles.shell}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Private AI LMS</p>
        <h1>Course authoring</h1>
        <p>
          Build a structured draft, review the exact content, and publish only after a human
          confirmation.
        </p>
      </header>

      {statusMessage ? (
        <div className={styles.status} role="status" aria-live="polite" aria-atomic="true">
          {statusMessage}
        </div>
      ) : null}
      {alertMessage ? (
        <div className={styles.alert} role="alert">
          {alertMessage}
        </div>
      ) : null}

      {phase === "signed-out" ? (
        <section className={styles.card} aria-labelledby="authoring-sign-in">
          <h2 id="authoring-sign-in">Open the authoring workspace</h2>
          <p>Use an invited account. Course permission is checked again for every action.</p>
          <form className={styles.form} onSubmit={handleSignIn} noValidate>
            <label>
              Email address
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button className={styles.primaryButton} type="submit" disabled={busy}>
              Open authoring workspace
            </button>
          </form>
        </section>
      ) : null}

      {phase === "select-tenant" ? (
        <section className={styles.card} aria-labelledby="tenant-selection">
          <h2 id="tenant-selection">Choose an authoring workspace</h2>
          {tenants.length ? (
            <ul className={styles.tenantList}>
              {tenants.map((tenant) => (
                <li key={tenant.id}>
                  <span>{tenant.display_name}</span>
                  <button
                    className={styles.primaryButton}
                    type="button"
                    disabled={busy}
                    onClick={() => handleTenantSelection(tenant)}
                  >
                    Select {tenant.display_name}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>No active authoring workspace is available.</p>
          )}
        </section>
      ) : null}

      {phase === "editing" && !snapshot ? (
        <section className={styles.card} aria-labelledby="create-course-heading">
          <p className={styles.eyebrow}>{activeTenant?.display_name}</p>
          <h2 id="create-course-heading">Create a course draft</h2>
          <form className={styles.form} onSubmit={handleCreateCourse} noValidate>
            <label>
              Course slug
              <input
                ref={slugRef}
                value={slug}
                pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                onChange={(event) => setSlug(event.target.value)}
              />
            </label>
            <label>
              Course title
              <input ref={titleRef} value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>
            <label>
              Course description
              <textarea
                ref={descriptionRef}
                rows={4}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>
            <button className={styles.primaryButton} type="submit" disabled={busy}>
              Create draft
            </button>
          </form>
        </section>
      ) : null}

      {phase === "editing" && snapshot ? (
        <div className={styles.editor}>
          <header className={styles.editorHeader}>
            <div>
              <p className={styles.eyebrow}>{activeTenant?.display_name}</p>
              <h2>{snapshot.version.title}</h2>
              <p>
                Version {snapshot.version.version_number} ·{" "}
                <strong data-testid="course-state">{stateLabels[snapshot.version.status]}</strong>
              </p>
            </div>
            <span
              className={styles.srOnly}
              data-testid="course-id"
              data-course-id={snapshot.course.id}
            >
              Selected course identifier
            </span>
            <span
              className={styles.srOnly}
              data-testid="published-version-id"
              data-version-id={publishedVersionId ?? ""}
            >
              Published version identifier
            </span>
          </header>

          {(snapshot.version.status === "draft" ||
            snapshot.version.status === "changes_requested") && (
            <section className={styles.card} aria-labelledby="course-details-heading">
              <h3 id="course-details-heading">Course details</h3>
              <form className={styles.form} onSubmit={handleSaveDetails} noValidate>
                <label>
                  Course slug
                  <input ref={slugRef} value={slug} readOnly aria-readonly="true" />
                </label>
                <label>
                  Course title
                  <input
                    ref={titleRef}
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                  />
                </label>
                <label>
                  Course description
                  <textarea
                    ref={descriptionRef}
                    rows={4}
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                  />
                </label>
                <button className={styles.primaryButton} type="submit" disabled={busy}>
                  Save course details
                </button>
              </form>
            </section>
          )}

          {(snapshot.version.status === "draft" ||
            snapshot.version.status === "changes_requested") && (
            <section className={styles.card} aria-labelledby="curriculum-heading">
              <h3 id="curriculum-heading">Structured curriculum</h3>
              <form className={styles.form} onSubmit={handleSaveCurriculum} noValidate>
                <label>
                  Section title
                  <input
                    ref={sectionRef}
                    value={sectionTitle}
                    onChange={(event) => setSectionTitle(event.target.value)}
                  />
                </label>
                <label>
                  Lesson title
                  <input
                    ref={lessonRef}
                    value={lessonTitle}
                    onChange={(event) => setLessonTitle(event.target.value)}
                  />
                </label>
                <label>
                  Lesson text
                  <textarea
                    ref={lessonTextRef}
                    rows={7}
                    value={lessonText}
                    onChange={(event) => setLessonText(event.target.value)}
                  />
                </label>
                <button className={styles.primaryButton} type="submit" disabled={busy}>
                  Save curriculum
                </button>
              </form>
            </section>
          )}

          <section className={styles.card} aria-labelledby="preview-heading">
            <h3 id="preview-heading">Course preview</h3>
            {snapshot.sections.length ? (
              <article className={styles.preview} aria-label="Course preview">
                {snapshot.sections.map((section) => (
                  <section key={section.id}>
                    <h4>{section.title}</h4>
                    {section.lessons.map((lesson) => (
                      <div key={lesson.id}>
                        <h5>{lesson.title}</h5>
                        {lesson.content_blocks.map((block) => (
                          <RichTextRenderer key={block.id} document={block.document} />
                        ))}
                      </div>
                    ))}
                  </section>
                ))}
              </article>
            ) : (
              <p>No curriculum has been added yet.</p>
            )}
          </section>

          <section className={styles.card} aria-labelledby="review-heading">
            <h3 id="review-heading">Review and publication</h3>
            <p>The server compares this exact version, row, and content hash at every step.</p>
            <div className={styles.actions}>
              {(snapshot.version.status === "draft" ||
                snapshot.version.status === "changes_requested") && (
                <button
                  className={styles.primaryButton}
                  type="button"
                  disabled={busy}
                  onClick={() => applyTransition("submit_review", "Exact version submitted for review.")}
                >
                  Submit exact version for review
                </button>
              )}
              {snapshot.version.status === "under_review" && (
                <>
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    disabled={busy}
                    onClick={() => applyTransition("request_changes", "Changes requested for this version.")}
                  >
                    Request changes
                  </button>
                  <button
                    className={styles.primaryButton}
                    type="button"
                    disabled={busy}
                    onClick={() => applyTransition("approve", "Reviewed version approved.")}
                  >
                    Approve reviewed version
                  </button>
                </>
              )}
              {snapshot.version.status === "approved" && (
                <button
                  className={styles.primaryButton}
                  type="button"
                  disabled={busy}
                  onClick={() => setPublishConfirmation(true)}
                >
                  Publish approved version
                </button>
              )}
              {snapshot.version.status === "published" && (
                <>
                  <button
                    className={styles.primaryButton}
                    type="button"
                    disabled={busy}
                    onClick={handleSuccessor}
                  >
                    Create version {snapshot.version.version_number + 1} draft
                  </button>
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    disabled={busy}
                    onClick={() => applyTransition("withdraw", "Published version withdrawn.")}
                  >
                    Withdraw published version
                  </button>
                </>
              )}
              {snapshot.version.status === "withdrawn" && (
                <button
                  className={styles.secondaryButton}
                  type="button"
                  disabled={busy}
                  onClick={() => applyTransition("archive", "Version archived.")}
                >
                  Archive withdrawn version
                </button>
              )}
            </div>
          </section>

          <section className={styles.card} aria-labelledby="history-heading" aria-label="Version history">
            <div className={styles.sectionHeader}>
              <div>
                <h3 id="history-heading">Version history</h3>
                <p>Newest versions appear first. Published versions remain immutable.</p>
              </div>
              <button
                className={styles.secondaryButton}
                type="button"
                disabled={busy}
                onClick={refreshHistory}
              >
                Refresh version history
              </button>
            </div>
            {history?.versions.length ? (
              <ol className={styles.historyList}>
                {history.versions.map((version) => (
                  <li key={version.id}>
                    <span>
                      <strong>Version {version.version_number}</strong> · {stateLabels[version.status]}
                    </span>
                    {version.is_current_published ? <span>Current publication</span> : null}
                  </li>
                ))}
              </ol>
            ) : (
              <p>No version history is available.</p>
            )}
          </section>
        </div>
      ) : null}

      <dialog
        ref={publishDialogRef}
        className={styles.dialog}
        aria-labelledby="publish-confirmation-heading"
        onCancel={() => setPublishConfirmation(false)}
      >
        {snapshot ? (
          <>
            <h2 id="publish-confirmation-heading">Confirm publication</h2>
            <p>
              Publish version {snapshot.version.version_number}? The published version cannot be
              edited in place.
            </p>
            <div className={styles.actions}>
              <button
                className={styles.primaryButton}
                type="button"
                disabled={busy}
                onClick={() => applyTransition("publish", "Approved version published.")}
              >
                Publish this exact version
              </button>
              <button
                className={styles.secondaryButton}
                type="button"
                disabled={busy}
                onClick={() => setPublishConfirmation(false)}
              >
                Cancel
              </button>
            </div>
          </>
        ) : null}
      </dialog>
    </main>
  );
}

"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  ApiLearnerPlaybackTransport,
  type DashboardCard,
  type LearnerDashboard,
  type LessonPlayback,
  LearnerPlaybackProblem,
  type PlaybackSnapshot,
  type ProgressCommandName,
  type TenantCandidate,
} from "./api-transport";
import styles from "./learner-playback.module.css";
import { RichTextRenderer } from "./rich-text-renderer";

type Phase = "signed-out" | "select-tenant" | "dashboard" | "player" | "unavailable";

const progressLabels = {
  not_started: "Not started",
  in_progress: "In progress",
  completed: "Completed",
} as const;

function firstLessonId(snapshot: PlaybackSnapshot): string | null {
  return snapshot.sections[0]?.lessons[0]?.id ?? null;
}

function containsLesson(snapshot: PlaybackSnapshot, lessonId: string): boolean {
  return snapshot.sections.some((section) =>
    section.lessons.some((lesson) => lesson.id === lessonId),
  );
}

function playbackUrl(enrollmentId: string, scenario?: string): string {
  const query = scenario === undefined ? "" : `?scenario=${encodeURIComponent(scenario)}`;
  return `/learner-courses/${enrollmentId}${query}`;
}

function dashboardUrl(scenario?: string): string {
  const query = scenario === undefined ? "" : `?scenario=${encodeURIComponent(scenario)}`;
  return `/learner-courses${query}`;
}

export function LearnerPlaybackExperience({
  requestedEnrollmentId,
  scenario,
}: {
  requestedEnrollmentId?: string;
  scenario?: string;
}) {
  const transport = useMemo(() => new ApiLearnerPlaybackTransport(), []);
  const alertRef = useRef<HTMLDivElement>(null);
  const dashboardHeadingRef = useRef<HTMLHeadingElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const lessonHeadingRef = useRef<HTMLHeadingElement>(null);

  const [phase, setPhase] = useState<Phase>("signed-out");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenants, setTenants] = useState<TenantCandidate[]>([]);
  const [activeTenant, setActiveTenant] = useState<TenantCandidate | null>(null);
  const [dashboard, setDashboard] = useState<LearnerDashboard | null>(null);
  const [playback, setPlayback] = useState<PlaybackSnapshot | null>(null);
  const [lesson, setLesson] = useState<LessonPlayback | null>(null);
  const [selectedEnrollmentId, setSelectedEnrollmentId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const fixtureEnabled =
    scenario === "integration" && process.env.NEXT_PUBLIC_AI_LMS_LOCAL_F001_FIXTURE === "1";

  useEffect(() => {
    if (lesson !== null) {
      lessonHeadingRef.current?.focus();
    }
  }, [lesson]);

  function focusAlert() {
    requestAnimationFrame(() => alertRef.current?.focus());
  }

  function clearPrivateContent() {
    setDashboard(null);
    setPlayback(null);
    setLesson(null);
    setSelectedEnrollmentId(null);
  }

  function resetAccess(message: string) {
    transport.signOut();
    clearPrivateContent();
    setTenants([]);
    setActiveTenant(null);
    setEmail("");
    setPassword("");
    setPhase("signed-out");
    setStatusMessage("");
    setAlertMessage(message);
    focusAlert();
    window.history.replaceState({}, "", dashboardUrl(scenario));
  }

  function showUnavailable() {
    clearPrivateContent();
    setPhase("unavailable");
    setStatusMessage("");
    setAlertMessage(
      "This learning content is unavailable. Return to your courses or ask your administrator for help.",
    );
    focusAlert();
  }

  function handleFailure(error: unknown, fallback: string) {
    if (
      error instanceof LearnerPlaybackProblem &&
      (error.code === "ACCESS_INACTIVE" || error.code === "AUTHENTICATION_REQUIRED")
    ) {
      resetAccess("Your learner access is no longer active. Sign in again.");
      return;
    }
    if (error instanceof LearnerPlaybackProblem && error.code === "RESOURCE_NOT_FOUND") {
      showUnavailable();
      return;
    }
    setAlertMessage(fallback);
    focusAlert();
  }

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAlertMessage("");
    if (!fixtureEnabled) {
      setAlertMessage("The local synthetic learner fixture is not enabled.");
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(email) || !password) {
      setAlertMessage("Enter your email address and password.");
      emailRef.current?.focus();
      return;
    }
    setBusy(true);
    setStatusMessage("Checking learner access…");
    try {
      const available = await transport.signIn({ email, password });
      setTenants(available);
      setPassword("");
      setPhase("select-tenant");
      setStatusMessage("Access loaded. Choose a workspace to continue.");
    } catch (error: unknown) {
      handleFailure(error, "We could not open your learner courses. Check your details.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function handleTenantSelection(tenant: TenantCandidate) {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage(`Checking ${tenant.display_name} learner access…`);
    try {
      const selected = await transport.selectTenant(tenant.id, tenants);
      setActiveTenant(selected);
      const loaded = await transport.dashboard();
      setDashboard(loaded);
      setPhase("dashboard");
      setStatusMessage(
        loaded.items.length === 0
          ? "Your private course list is empty."
          : `${loaded.items.length} private course${loaded.items.length === 1 ? "" : "s"} loaded.`,
      );
      if (requestedEnrollmentId !== undefined) {
        await openEnrollment(requestedEnrollmentId, false);
      } else {
        window.history.replaceState({}, "", dashboardUrl(scenario));
        requestAnimationFrame(() => dashboardHeadingRef.current?.focus());
      }
    } catch (error: unknown) {
      handleFailure(error, "That learner workspace is unavailable.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function openEnrollment(enrollmentId: string, updateUrl = true) {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Loading the pinned course version…");
    try {
      const nextPlayback = await transport.playback(enrollmentId);
      const targetLessonId =
        nextPlayback.progress.resume_lesson_id ?? firstLessonId(nextPlayback);
      if (targetLessonId === null) {
        throw new LearnerPlaybackProblem("RESOURCE_NOT_FOUND");
      }
      const nextLesson = await transport.lesson(enrollmentId, targetLessonId);
      setSelectedEnrollmentId(enrollmentId);
      setPlayback(nextPlayback);
      setLesson(nextLesson);
      setPhase("player");
      setStatusMessage(
        nextPlayback.progress.resume_lesson_id === null
          ? "Course opened. Reading alone does not change your progress."
          : "Course opened at your saved resume lesson.",
      );
      if (updateUrl) {
        window.history.pushState({}, "", playbackUrl(enrollmentId, scenario));
      }
    } catch (error: unknown) {
      handleFailure(error, "The course could not be loaded.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function loadLesson(lessonId: string) {
    if (selectedEnrollmentId === null) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Loading lesson…");
    try {
      const nextLesson = await transport.lesson(selectedEnrollmentId, lessonId);
      setLesson(nextLesson);
      setStatusMessage("Lesson loaded. Your progress has not changed.");
    } catch (error: unknown) {
      handleFailure(error, "The lesson could not be loaded.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function refreshPlayer(preferredLessonId?: string) {
    if (selectedEnrollmentId === null) {
      return;
    }
    const nextPlayback = await transport.playback(selectedEnrollmentId);
    const currentLessonId = preferredLessonId ?? lesson?.lesson.id;
    const targetLessonId =
      currentLessonId !== undefined && containsLesson(nextPlayback, currentLessonId)
        ? currentLessonId
        : (nextPlayback.progress.resume_lesson_id ?? firstLessonId(nextPlayback));
    if (targetLessonId === null) {
      throw new LearnerPlaybackProblem("RESOURCE_NOT_FOUND");
    }
    const nextLesson = await transport.lesson(selectedEnrollmentId, targetLessonId);
    setPlayback(nextPlayback);
    setLesson(nextLesson);
  }

  async function handlePlayerRefresh() {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Refreshing private course access…");
    try {
      await refreshPlayer();
      setStatusMessage("Course access and progress refreshed.");
    } catch (error: unknown) {
      handleFailure(error, "The course could not be refreshed.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function handleProgress(command: ProgressCommandName) {
    if (selectedEnrollmentId === null || lesson === null) {
      return;
    }
    const lessonId = lesson.lesson.id;
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Saving your explicit progress choice…");
    try {
      const result = await transport.progress(
        selectedEnrollmentId,
        lessonId,
        command,
        lesson.progress.row_version,
      );
      await refreshPlayer(lessonId);
      const action =
        command === "open_lesson"
          ? "Resume point saved"
          : command === "complete_lesson"
            ? "Lesson completed"
            : "Lesson reopened";
      setStatusMessage(
        `${action}. ${result.completed_required_lesson_count} of ${result.required_lesson_count} required lessons complete.`,
      );
    } catch (error: unknown) {
      if (error instanceof LearnerPlaybackProblem && error.code === "VERSION_CONFLICT") {
        try {
          await refreshPlayer(lessonId);
          setAlertMessage(
            "Progress changed in another session. We refreshed the latest saved progress; review it and try again.",
          );
          focusAlert();
        } catch (refreshError: unknown) {
          handleFailure(refreshError, "Progress changed, but the latest state could not be loaded.");
        }
      } else {
        handleFailure(error, "Your progress choice could not be saved.");
      }
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function handleDashboardRefresh() {
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Refreshing your private courses…");
    try {
      const loaded = await transport.dashboard();
      setDashboard(loaded);
      setPhase("dashboard");
      setStatusMessage(
        loaded.items.length === 0
          ? "Your private course list is empty."
          : "Your private courses are up to date.",
      );
      window.history.pushState({}, "", dashboardUrl(scenario));
      requestAnimationFrame(() => dashboardHeadingRef.current?.focus());
    } catch (error: unknown) {
      handleFailure(error, "Your private courses could not be refreshed.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  async function loadMoreCourses() {
    if (dashboard?.next_cursor === null || dashboard?.next_cursor === undefined) {
      return;
    }
    setBusy(true);
    setAlertMessage("");
    setStatusMessage("Loading more private courses…");
    try {
      const nextPage = await transport.dashboard(dashboard.next_cursor);
      setDashboard({
        ...nextPage,
        items: [...dashboard.items, ...nextPage.items],
      });
      setStatusMessage(`${nextPage.items.length} more courses loaded.`);
    } catch (error: unknown) {
      handleFailure(error, "More courses could not be loaded.");
      setStatusMessage("");
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    resetAccess("You signed out. Private course content was cleared from this page.");
  }

  return (
    <main className={styles.shell} aria-busy={busy}>
      <a className={styles.skipLink} href="#learner-content">
        Skip to learner content
      </a>

      <header className={styles.hero}>
        <p className={styles.eyebrow}>Private learner workspace</p>
        <h1>Learn at your own deliberate pace</h1>
        <p>
          Read the exact course version assigned to you. Progress changes only when you choose a
          progress control.
        </p>
      </header>

      <div className={styles.liveRegions} aria-live="polite" aria-atomic="true">
        {statusMessage ? (
          <p className={styles.status} role="status">
            {statusMessage}
          </p>
        ) : null}
        {alertMessage ? (
          <div className={styles.alert} ref={alertRef} role="alert" tabIndex={-1}>
            {alertMessage}
          </div>
        ) : null}
      </div>

      <div id="learner-content">
        {phase === "signed-out" ? (
          <section className={styles.card} aria-labelledby="learner-sign-in-heading">
            <h2 id="learner-sign-in-heading">Open your private courses</h2>
            <p>Sign in, then explicitly choose the tenant whose assignments you want to view.</p>
            <form className={styles.form} onSubmit={handleSignIn} noValidate>
              <label>
                Email address
                <input
                  autoComplete="username"
                  inputMode="email"
                  onChange={(event) => setEmail(event.target.value)}
                  ref={emailRef}
                  required
                  type="email"
                  value={email}
                />
              </label>
              <label>
                Password
                <input
                  autoComplete="current-password"
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
              </label>
              <button className={styles.primaryButton} disabled={busy} type="submit">
                Open learner courses
              </button>
            </form>
          </section>
        ) : null}

        {phase === "select-tenant" ? (
          <section className={styles.card} aria-labelledby="tenant-heading">
            <h2 id="tenant-heading">Choose a learner workspace</h2>
            {tenants.length === 0 ? (
              <div className={styles.emptyState}>
                <h3>No active learner workspaces</h3>
                <p>Ask your administrator to confirm your tenant membership.</p>
              </div>
            ) : (
              <ul className={styles.tenantList}>
                {tenants.map((tenant) => (
                  <li key={tenant.id}>
                    <span>{tenant.display_name}</span>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy}
                      onClick={() => void handleTenantSelection(tenant)}
                      type="button"
                    >
                      Select {tenant.display_name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}

        {phase === "dashboard" && dashboard !== null ? (
          <section className={styles.workspace} aria-labelledby="dashboard-heading">
            <div className={styles.workspaceHeader}>
              <div>
                <p className={styles.eyebrow}>{activeTenant?.display_name}</p>
                <h2 id="dashboard-heading" ref={dashboardHeadingRef} tabIndex={-1}>
                  Your courses
                </h2>
              </div>
              <div className={styles.actions}>
                <button
                  className={styles.secondaryButton}
                  disabled={busy}
                  onClick={() => void handleDashboardRefresh()}
                  type="button"
                >
                  Refresh courses
                </button>
                <button className={styles.textButton} disabled={busy} onClick={signOut} type="button">
                  Sign out
                </button>
              </div>
            </div>

            {dashboard.items.length === 0 ? (
              <div className={styles.emptyState}>
                <h3>No assigned courses yet</h3>
                <p>
                  Your private list is empty. A tenant administrator can assign a published course
                  when it is ready.
                </p>
              </div>
            ) : (
              <ul className={styles.courseGrid}>
                {dashboard.items.map((card) => (
                  <CourseCard
                    busy={busy}
                    card={card}
                    key={card.enrollment_id}
                    onOpen={() => void openEnrollment(card.enrollment_id)}
                  />
                ))}
              </ul>
            )}
            {dashboard.next_cursor !== null ? (
              <button
                className={styles.secondaryButton}
                disabled={busy}
                onClick={() => void loadMoreCourses()}
                type="button"
              >
                Load more courses
              </button>
            ) : null}
          </section>
        ) : null}

        {phase === "player" && playback !== null && lesson !== null ? (
          <section className={styles.workspace} aria-labelledby="course-heading">
            <div className={styles.workspaceHeader}>
              <div dir="auto" lang={playback.primary_locale}>
                <p className={styles.eyebrow}>
                  Assigned version {playback.course_version_number}
                </p>
                <h2 id="course-heading">{playback.title}</h2>
                <p>{playback.description}</p>
              </div>
              <div className={styles.actions}>
                <button
                  className={styles.secondaryButton}
                  disabled={busy}
                  onClick={() => void handleDashboardRefresh()}
                  type="button"
                >
                  Back to courses
                </button>
                <button
                  className={styles.secondaryButton}
                  disabled={busy}
                  onClick={() => void handlePlayerRefresh()}
                  type="button"
                >
                  Refresh course
                </button>
                <button className={styles.textButton} disabled={busy} onClick={signOut} type="button">
                  Sign out
                </button>
              </div>
            </div>

            <div className={styles.courseProgress} aria-label="Course progress">
              <span>{progressLabels[playback.progress.state]}</span>
              <progress
                aria-label={`${playback.progress.completed_required_lesson_count} of ${playback.progress.required_lesson_count} required lessons complete`}
                max={playback.progress.required_lesson_count}
                value={playback.progress.completed_required_lesson_count}
              />
              <span>
                {playback.progress.completed_required_lesson_count} of{" "}
                {playback.progress.required_lesson_count} required lessons
              </span>
            </div>

            <div className={styles.playerLayout}>
              <nav className={styles.outline} aria-label="Course outline">
                <h3>Course outline</h3>
                {playback.sections.map((section) => (
                  <section key={section.id} aria-labelledby={`section-${section.id}`}>
                    <h4 id={`section-${section.id}`} dir="auto">
                      {section.title}
                    </h4>
                    <ol>
                      {section.lessons.map((outlineLesson) => (
                        <li key={outlineLesson.id}>
                          <button
                            aria-current={
                              outlineLesson.id === lesson.lesson.id ? "page" : undefined
                            }
                            className={styles.lessonLink}
                            disabled={busy}
                            onClick={() => void loadLesson(outlineLesson.id)}
                            type="button"
                          >
                            <span dir="auto">{outlineLesson.title}</span>
                            <small>
                              {progressLabels[outlineLesson.progress_state]}
                              {outlineLesson.is_required ? " · Required" : " · Optional"}
                            </small>
                          </button>
                        </li>
                      ))}
                    </ol>
                  </section>
                ))}
              </nav>

              <article
                className={styles.lessonBody}
                aria-labelledby="lesson-heading"
                dir="auto"
                lang={lesson.primary_locale}
              >
                <p className={styles.lessonState}>
                  {progressLabels[lesson.lesson.progress_state]}
                  {lesson.lesson.is_required ? " · Required lesson" : " · Optional lesson"}
                </p>
                <h3 id="lesson-heading" ref={lessonHeadingRef} tabIndex={-1}>
                  {lesson.lesson.title}
                </h3>
                {lesson.lesson.content_blocks.map((block) => (
                  <div className={styles.richText} key={block.id}>
                    <RichTextRenderer document={block.document} />
                  </div>
                ))}

                <div className={styles.progressActions} aria-label="Lesson progress controls">
                  <button
                    className={styles.primaryButton}
                    disabled={busy}
                    onClick={() => void handleProgress("open_lesson")}
                    type="button"
                  >
                    {lesson.lesson.progress_state === "not_started"
                      ? "Start lesson and save resume point"
                      : "Save as resume point"}
                  </button>
                  <button
                    className={styles.secondaryButton}
                    disabled={busy}
                    onClick={() =>
                      void handleProgress(
                        lesson.lesson.progress_state === "completed"
                          ? "reopen_lesson"
                          : "complete_lesson",
                      )
                    }
                    type="button"
                  >
                    {lesson.lesson.progress_state === "completed"
                      ? "Reopen lesson"
                      : "Mark lesson complete"}
                  </button>
                </div>

                <nav className={styles.lessonNavigation} aria-label="Lesson navigation">
                  <button
                    className={styles.secondaryButton}
                    disabled={busy || lesson.previous_lesson_id === null}
                    onClick={() =>
                      lesson.previous_lesson_id === null
                        ? undefined
                        : void loadLesson(lesson.previous_lesson_id)
                    }
                    type="button"
                  >
                    Previous lesson
                  </button>
                  <button
                    className={styles.secondaryButton}
                    disabled={busy || lesson.next_lesson_id === null}
                    onClick={() =>
                      lesson.next_lesson_id === null
                        ? undefined
                        : void loadLesson(lesson.next_lesson_id)
                    }
                    type="button"
                  >
                    Next lesson
                  </button>
                </nav>
              </article>
            </div>
          </section>
        ) : null}

        {phase === "unavailable" ? (
          <section className={styles.card} aria-labelledby="unavailable-heading">
            <h2 id="unavailable-heading">Learning content unavailable</h2>
            <p>
              We did not keep the course title, lesson text, or progress on this page after access
              was lost.
            </p>
            <div className={styles.actions}>
              <button
                className={styles.primaryButton}
                disabled={busy}
                onClick={() => void handleDashboardRefresh()}
                type="button"
              >
                Return to course list
              </button>
              <button className={styles.textButton} disabled={busy} onClick={signOut} type="button">
                Sign out
              </button>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}

function CourseCard({
  busy,
  card,
  onOpen,
}: {
  busy: boolean;
  card: DashboardCard;
  onOpen: () => void;
}) {
  return (
    <li className={styles.courseCard}>
      <div dir="auto" lang={card.primary_locale}>
        <p className={styles.eyebrow}>Assigned version {card.course_version_number}</p>
        <h3>{card.title}</h3>
        <p>{card.description}</p>
      </div>
      <div className={styles.courseProgress} aria-label={`${card.title} progress`}>
        <span>{progressLabels[card.progress.state]}</span>
        <progress
          aria-label={`${card.progress.completed_required_lesson_count} of ${card.progress.required_lesson_count} required lessons complete`}
          max={card.progress.required_lesson_count}
          value={card.progress.completed_required_lesson_count}
        />
      </div>
      <button className={styles.primaryButton} disabled={busy} onClick={onOpen} type="button">
        {card.progress.resume_lesson_id === null ? "Open course" : "Resume course"}
        <span className={styles.srOnly}>: {card.title}</span>
      </button>
    </li>
  );
}

import { expect, type APIRequestContext, type Page, test } from "@playwright/test";

const alphaId = "00000000-0000-4000-8000-0000000000a1";
const betaId = "00000000-0000-4000-8000-0000000000b1";
const learnerMembershipId = "20000000-0000-4000-8000-000000000104";
const courseId = "30000000-0000-4000-8000-000000000101";
const versionOneId = "30000000-0000-4000-8000-000000000201";
const lessonOneId = "30000000-0000-4000-8000-000000000401";
const lessonTwoId = "30000000-0000-4000-8000-000000000402";

type SessionResponse = { access_token: string };
type EnrollmentResponse = {
  id: string;
  course_version_id: string;
  row_version: number;
  status: string;
};
type PlaybackResponse = {
  course_version_id: string;
  course_version_number: number;
  title: string;
  progress: { row_version: number; resume_lesson_id: string | null };
};

async function resetFixture(request: APIRequestContext) {
  const response = await request.post("/f001-api/api/integration/reset");
  expect(response.ok(), await response.text()).toBeTruthy();
}

async function session(request: APIRequestContext, email: string): Promise<SessionResponse> {
  const response = await request.post("/f001-api/api/integration/session", {
    data: { email, password: "synthetic-password" },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as SessionResponse;
}

function headers(token: string, tenantId = alphaId) {
  return {
    Authorization: `Bearer ${token}`,
    "X-Tenant-ID": tenantId,
  };
}

async function assignCourse(request: APIRequestContext): Promise<EnrollmentResponse> {
  const admin = await session(request, "alpha-admin@example.invalid");
  const response = await request.post(`/f001-api/api/v1/tenants/${alphaId}/enrollments`, {
    headers: {
      ...headers(admin.access_token),
      "Idempotency-Key": "f007-browser-assignment-0001",
    },
    data: { learner_membership_id: learnerMembershipId, course_id: courseId },
  });
  expect(response.status(), await response.text()).toBe(201);
  return (await response.json()) as EnrollmentResponse;
}

async function signIn(page: Page, email = "learner@example.invalid") {
  if (!page.url().includes("/learner-courses")) {
    await page.goto("/learner-courses?scenario=integration");
  }
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Open learner courses" }).click();
  await page.getByRole("button", { name: "Select Alpha Academy" }).click();
}

async function learnerPlayback(
  request: APIRequestContext,
  token: string,
  enrollmentId: string,
): Promise<PlaybackResponse> {
  const response = await request.get(
    `/f001-api/api/v1/tenants/${alphaId}/learner/enrollments/${enrollmentId}/playback`,
    { headers: headers(token) },
  );
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as PlaybackResponse;
}

async function progressFromAnotherSession(
  request: APIRequestContext,
  token: string,
  enrollmentId: string,
  lessonId: string,
  expectedVersion: number,
) {
  return request.post(
    `/f001-api/api/v1/tenants/${alphaId}/learner/enrollments/${enrollmentId}/progress/complete-lesson`,
    {
      headers: {
        ...headers(token),
        "Idempotency-Key": `f007-other-session-${crypto.randomUUID()}`,
      },
      data: {
        command: "complete_lesson",
        lesson_id: lessonId,
        expected_progress_row_version: expectedVersion,
      },
    },
  );
}

test.describe("F-007 private learner playback and progress", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ request }) => {
    await resetFixture(request);
  });

  test("assigns privately, resumes the pinned version, resolves a stale write, and clears revoked content", async ({
    page,
    request,
  }) => {
    const consoleMessages: string[] = [];
    page.on("console", (message) => consoleMessages.push(message.text()));

    await page.goto("/learner-courses?scenario=integration");
    await signIn(page);
    await expect(page.getByRole("heading", { name: "No assigned courses yet" })).toBeVisible();
    await expect(page.getByRole("button", { name: /enroll|join|catalog/i })).toHaveCount(0);

    const enrollment = await assignCourse(request);
    expect(enrollment.course_version_id).toBe(versionOneId);
    await page.getByRole("button", { name: "Refresh courses" }).click();
    await expect(page.getByRole("heading", { name: "Private learning foundations" })).toBeVisible();
    await page.getByRole("button", { name: /Open course/ }).click();

    await expect(page.getByText("Assigned version 1")).toBeVisible();
    await expect(page.getByRole("heading", { name: "A deliberate beginning" })).toBeVisible();
    await expect(page.getByText(/Safe <script>window.__f007Unsafe/)).toBeVisible();
    await expect(page.locator("article script")).toHaveCount(0);
    expect(await page.evaluate(() => "__f007Unsafe" in window)).toBeFalsy();

    const learner = await session(request, "learner@example.invalid");
    const readOnlySnapshot = await learnerPlayback(request, learner.access_token, enrollment.id);
    expect(readOnlySnapshot.progress.row_version).toBe(0);
    expect(readOnlySnapshot.progress.resume_lesson_id).toBeNull();

    await page.getByRole("button", { name: "Start lesson and save resume point" }).click();
    await expect(page.getByRole("status")).toContainText("Resume point saved");
    await expect(page.getByText("In progress · Required lesson")).toBeVisible();

    await page.reload();
    await expect(page.getByRole("heading", { name: "Open your private courses" })).toBeVisible();
    await signIn(page);
    await expect(page.getByRole("status")).toContainText("saved resume lesson");
    await expect(page.getByRole("heading", { name: "A deliberate beginning" })).toBeVisible();

    const otherSession = await progressFromAnotherSession(
      request,
      learner.access_token,
      enrollment.id,
      lessonOneId,
      1,
    );
    expect(otherSession.ok(), await otherSession.text()).toBeTruthy();
    await page.getByRole("button", { name: "Mark lesson complete" }).click();
    await expect(
      page.locator('[role="alert"]').filter({ hasText: "changed in another session" }),
    ).toContainText("changed in another session");
    await expect(page.getByRole("button", { name: "Reopen lesson" })).toBeVisible();

    await page.getByRole("button", { name: "Reopen lesson" }).click();
    await expect(page.getByRole("status")).toContainText("Lesson reopened");
    await page.getByRole("button", { name: "Mark lesson complete" }).click();
    await page.getByRole("button", { name: "Next lesson" }).click();
    await expect(page.getByRole("heading", { name: "Finish with intention" })).toBeVisible();
    await page.getByRole("button", { name: "Mark lesson complete" }).click();
    await expect(page.getByRole("status")).toContainText("2 of 2 required lessons complete");
    await expect(page.getByText("Completed", { exact: true }).first()).toBeVisible();
    await page.getByRole("button", { name: "Reopen lesson" }).click();
    await expect(page.getByRole("status")).toContainText("1 of 2 required lessons complete");

    const advanced = await request.post("/f001-api/api/integration/f007/publish-successor");
    expect(advanced.ok(), await advanced.text()).toBeTruthy();
    await page.getByRole("button", { name: "Refresh course" }).click();
    await expect(page.getByText("Assigned version 1")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Private learning foundations" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Private learning foundations, version two" }),
    ).toHaveCount(0);
    const pinned = await learnerPlayback(request, learner.access_token, enrollment.id);
    expect(pinned.course_version_id).toBe(versionOneId);
    expect(pinned.course_version_number).toBe(1);

    const admin = await session(request, "alpha-admin@example.invalid");
    const revoked = await request.post(
      `/f001-api/api/v1/tenants/${alphaId}/enrollments/${enrollment.id}/revoke`,
      {
        headers: {
          ...headers(admin.access_token),
          "Idempotency-Key": "f007-browser-revocation-0001",
        },
        data: {
          expected_enrollment_row_version: enrollment.row_version,
          reason_code: "ADMIN_REVOKED",
        },
      },
    );
    expect(revoked.ok(), await revoked.text()).toBeTruthy();
    await page.getByRole("button", { name: "Refresh course" }).click();
    await expect(page.getByRole("heading", { name: "Learning content unavailable" })).toBeVisible();
    await expect(page.getByText("Private learning foundations", { exact: true })).toHaveCount(0);
    await expect(page.getByText(/Safe <script>window.__f007Unsafe/)).toHaveCount(0);

    const emptyLearner = await session(request, "learner-empty@example.invalid");
    const guessed = await request.get(
      `/f001-api/api/v1/tenants/${alphaId}/learner/enrollments/${enrollment.id}/playback`,
      { headers: headers(emptyLearner.access_token) },
    );
    expect(guessed.status()).toBe(404);
    expect(await guessed.text()).not.toContain("Private learning foundations");
    const wrongTenant = await request.get(
      `/f001-api/api/v1/tenants/${betaId}/learner/enrollments/${enrollment.id}/playback`,
      { headers: headers(learner.access_token, betaId) },
    );
    expect(wrongTenant.status()).toBe(404);

    expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({
      local: 0,
      session: 0,
    });
    expect(consoleMessages.join("\n")).not.toContain("Safe <script>");
  });

  test("withdrawal makes a pinned course neutrally unavailable on the next request", async ({
    page,
    request,
  }) => {
    await assignCourse(request);
    await page.goto("/learner-courses?scenario=integration");
    await signIn(page);
    await page.getByRole("button", { name: /Open course/ }).click();
    await expect(page.getByRole("heading", { name: "A deliberate beginning" })).toBeVisible();

    const withdrawn = await request.post("/f001-api/api/integration/f007/withdraw-pinned");
    expect(withdrawn.ok(), await withdrawn.text()).toBeTruthy();
    await page.getByRole("button", { name: "Refresh course" }).click();
    await expect(page.getByRole("heading", { name: "Learning content unavailable" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "A deliberate beginning" })).toHaveCount(0);
  });

  test("supports keyboard focus, English metadata, RTL structure, and 400 percent reflow", async ({
    page,
    request,
  }) => {
    await assignCourse(request);
    await page.goto("/learner-courses?scenario=integration");
    await page.getByRole("button", { name: "Open learner courses" }).click();
    await expect(page.getByLabel("Email address")).toBeFocused();
    await expect(
      page.locator('[role="alert"]').filter({ hasText: "Enter your email address" }),
    ).toContainText("Enter your email address");

    await signIn(page);
    await page.getByRole("button", { name: /Open course/ }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator("article[lang='en']")).toHaveAttribute("dir", "auto");
    await expect(page.getByRole("navigation", { name: "Course outline" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Lesson navigation" })).toBeVisible();

    await page.evaluate(() => {
      document.documentElement.dir = "rtl";
    });
    await page.getByRole("button", { name: "Next lesson" }).click();
    await expect(page.getByRole("heading", { name: "Finish with intention" })).toBeFocused();
    await page.evaluate(() => {
      document.documentElement.dir = "ltr";
    });

    await page.emulateMedia({ forcedColors: "active", reducedMotion: "reduce" });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => {
      document.documentElement.style.zoom = "4";
    });
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
    await expect(page.getByRole("button", { name: "Previous lesson" })).toBeVisible();
    expect(lessonTwoId).not.toBe(lessonOneId);
  });
});

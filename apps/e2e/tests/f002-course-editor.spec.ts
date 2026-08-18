import { expect, type APIRequestContext, type Page, test } from "@playwright/test";

const alphaId = "00000000-0000-4000-8000-0000000000a1";
const betaId = "00000000-0000-4000-8000-0000000000b1";

type SessionResponse = { access_token: string };
type MembershipResponse = {
  id: string;
  status: string;
  row_version: number;
  role_codes: string[];
};
type CourseSnapshotResponse = {
  version: { row_version: number; title: string };
};

async function resetFixture(request: APIRequestContext) {
  const response = await request.post("/f001-api/api/integration/reset");
  expect(response.ok()).toBeTruthy();
}

async function session(request: APIRequestContext, email: string): Promise<SessionResponse> {
  const response = await request.post("/f001-api/api/integration/session", {
    data: { email, password: "synthetic-password" },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as SessionResponse;
}

async function signIn(page: Page) {
  await page.goto("/course-editor?scenario=integration");
  await page.getByLabel("Email address").fill("instructor@example.invalid");
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Open authoring workspace" }).click();
  await page.getByRole("button", { name: "Select Alpha Academy" }).click();
  await expect(page.getByRole("heading", { name: "Create a course draft" })).toBeVisible();
}

test.describe("F-002 composed course editor journey", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ request }) => {
    await resetFixture(request);
  });

  test("creates, edits, self-reviews, publishes immutable v1, and creates v2", async ({
    page,
    request,
  }) => {
    const consoleMessages: string[] = [];
    page.on("console", (message) => consoleMessages.push(message.text()));
    await signIn(page);
    await page.getByLabel("Course slug").fill("synthetic-browser-course");
    await page.getByLabel("Course title").fill("Synthetic browser course");
    await page
      .getByLabel("Course description")
      .fill("Invented browser fixture with no private source material.");
    const createResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" && response.url().endsWith(`/tenants/${alphaId}/courses`),
    );
    await page.getByRole("button", { name: "Create draft" }).click();
    const createResponse = await createResponsePromise;
    expect(createResponse.status(), await createResponse.text()).toBe(201);
    await expect(page.getByRole("status")).toContainText("Draft version 1 created");

    await page.getByLabel("Course title").fill("Synthetic browser course, reviewed");
    await page.getByRole("button", { name: "Save course details" }).click();
    await expect(page.getByRole("status")).toContainText("Course details saved");

    await page.getByLabel("Section title").fill("Safe foundations");
    await page.getByLabel("Lesson title").fill("A deterministic lesson");
    await page
      .getByLabel("Lesson text")
      .fill("Safe <script>window.__unsafe = true</script> structured text.");
    await page.getByRole("button", { name: "Save curriculum" }).click();
    const preview = page.getByRole("article", { name: "Course preview" });
    await expect(preview).toContainText(
      "Safe <script>window.__unsafe = true</script> structured text.",
    );
    await expect(preview.locator("script")).toHaveCount(0);

    await page.getByRole("button", { name: "Submit exact version for review" }).click();
    await expect(page.getByTestId("course-state")).toHaveText("Under review");
    await page.getByRole("button", { name: "Approve reviewed version" }).click();
    await expect(page.getByTestId("course-state")).toHaveText("Approved");

    await page.getByRole("button", { name: "Publish approved version" }).click();
    await expect(page.getByRole("dialog", { name: "Confirm publication" })).toBeVisible();
    const confirmPublication = page.getByRole("button", { name: "Publish this exact version" });
    await expect(confirmPublication).toBeFocused();
    await confirmPublication.click();
    await expect(page.getByTestId("course-state")).toHaveText("Published");

    const courseId = await page.getByTestId("course-id").getAttribute("data-course-id");
    const versionId = await page.getByTestId("published-version-id").getAttribute("data-version-id");
    const instructorSession = await session(request, "instructor@example.invalid");
    const publishedResponse = await request.get(
      `/f001-api/api/v1/tenants/${alphaId}/courses/${courseId}/versions/${versionId}`,
      {
        headers: {
          Authorization: `Bearer ${instructorSession.access_token}`,
          "X-Tenant-ID": alphaId,
        },
      },
    );
    expect(publishedResponse.ok()).toBeTruthy();
    const published = (await publishedResponse.json()) as CourseSnapshotResponse;
    const immutableEdit = await request.patch(
      `/f001-api/api/v1/tenants/${alphaId}/courses/${courseId}/versions/${versionId}`,
      {
        headers: {
          Authorization: `Bearer ${instructorSession.access_token}`,
          "X-Tenant-ID": alphaId,
        },
        data: {
          expected_version_row_version: published.version.row_version,
          title: "Forbidden in-place browser edit",
        },
      },
    );
    expect(immutableEdit.status()).toBe(409);
    expect((await immutableEdit.json()) as { code: string }).toMatchObject({
      code: "COURSE_VERSION_IMMUTABLE",
    });

    await page.getByRole("button", { name: "Create version 2 draft" }).click();
    await expect(page.getByTestId("course-state")).toHaveText("Draft");
    const history = page.getByRole("region", { name: "Version history" });
    await expect(history).toContainText("Version 2");
    await expect(history).toContainText("Version 1");
    await expect(history).toContainText("Published");

    const browserStorage = await page.evaluate(() => ({
      local: localStorage.length,
      session: sessionStorage.length,
    }));
    expect(browserStorage).toEqual({ local: 0, session: 0 });
    expect(consoleMessages.join("\n")).not.toContain("Safe <script>");

    const outsider = await session(request, "outsider@example.invalid");
    const guessed = await request.get(
      `/f001-api/api/v1/tenants/${alphaId}/courses/${courseId}/versions/${versionId}`,
      {
        headers: {
          Authorization: `Bearer ${outsider.access_token}`,
          "X-Tenant-ID": alphaId,
        },
      },
    );
    expect(guessed.status()).toBe(404);
    expect(await guessed.text()).not.toContain("Synthetic browser course");

    const betaGuess = await request.get(
      `/f001-api/api/v1/tenants/${betaId}/courses/${courseId}/versions/${versionId}`,
      {
        headers: {
          Authorization: `Bearer ${instructorSession.access_token}`,
          "X-Tenant-ID": betaId,
        },
      },
    );
    expect(betaGuess.status()).toBe(404);

    const admin = await session(request, "alpha-admin@example.invalid");
    const membershipsResponse = await request.get(
      `/f001-api/api/v1/tenants/${alphaId}/memberships`,
      {
        headers: {
          Authorization: `Bearer ${admin.access_token}`,
          "X-Tenant-ID": alphaId,
        },
      },
    );
    const memberships = (await membershipsResponse.json()) as MembershipResponse[];
    const instructor = memberships.find((item) => item.role_codes.includes("instructor"));
    expect(instructor).toBeDefined();
    const revoked = await request.patch(
      `/f001-api/api/v1/tenants/${alphaId}/memberships/${instructor?.id}`,
      {
        headers: {
          Authorization: `Bearer ${admin.access_token}`,
          "X-Tenant-ID": alphaId,
        },
        data: { status: "inactive", row_version: instructor?.row_version },
      },
    );
    expect(revoked.ok()).toBeTruthy();

    await page.getByRole("button", { name: "Refresh version history" }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "Your course access is no longer active" }),
    ).toContainText("Your course access is no longer active");
    await expect(page.getByText("Synthetic browser course, reviewed")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Course authoring" })).toBeVisible();
  });

  test("validation focuses the first invalid field and the editor reflows at zoom", async ({
    page,
  }) => {
    await signIn(page);
    await page.getByRole("button", { name: "Create draft" }).click();
    await expect(page.getByLabel("Course slug")).toBeFocused();
    await expect(
      page.getByRole("alert").filter({ hasText: "Complete the required course details" }),
    ).toContainText("Complete the required course details");

    await page.setViewportSize({ width: 640, height: 900 });
    await page.evaluate(() => {
      document.documentElement.style.zoom = "2";
    });
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
  });
});

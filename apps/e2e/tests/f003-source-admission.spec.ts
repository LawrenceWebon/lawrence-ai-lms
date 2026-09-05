import { readFile } from "node:fs/promises";
import path from "node:path";

import { expect, type APIRequestContext, type Page, test } from "@playwright/test";

const alphaId = "00000000-0000-4000-8000-0000000000a1";

type SessionResponse = { access_token: string };

const validPdfPath = path.resolve(
  process.cwd(),
  "../../backend/tests/documents/fixtures/synthetic-valid-one-page.pdf",
);

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

async function signIn(page: Page, email: string) {
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Open source workspace" }).click();
  await page.getByRole("button", { name: "Select Alpha Academy" }).click();
  await expect(page.getByRole("heading", { name: "Private source workflow" })).toBeVisible();
}

async function createOwnedDeclaration(page: Page, suffix: string) {
  await page.getByLabel("Source display name").fill(`Synthetic ${suffix} source`);
  await page.getByLabel("Declared PDF filename").fill(`synthetic-${suffix}.pdf`);
  await page
    .getByLabel("I attest that this rights declaration is accurate for storing this source.")
    .check();
  await page.getByRole("button", { name: "Submit rights declaration" }).click();
  await expect(page.getByTestId("source-state")).toHaveText("Rights review needed");
}

async function switchUser(page: Page, email: string) {
  await page.getByRole("button", { name: "Sign out and switch user" }).click();
  await signIn(page, email);
}

async function approveAsAdmin(page: Page) {
  await switchUser(page, "alpha-admin@example.invalid");
  await page.getByRole("button", { name: "Authorize private storage" }).click();
  await expect(page.getByTestId("source-state")).toHaveText("Ready for private upload");
}

test.describe("F-003 private PDF source admission", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ page, request }) => {
    await resetFixture(request);
    await page.goto("/source-documents?scenario=integration");
  });

  test("requires separate review, admits server-validated bytes, revokes, and hides IDORs", async ({
    page,
    request,
  }) => {
    const consoleMessages: string[] = [];
    page.on("console", (message) => consoleMessages.push(message.text()));
    await signIn(page, "instructor@example.invalid");
    await createOwnedDeclaration(page, "admitted");
    const identifiers = page.getByTestId("source-identifiers");
    const sourceDocumentId = await identifiers.getAttribute("data-source-document-id");
    const sourceVersionId = await identifiers.getAttribute("data-source-version-id");

    await approveAsAdmin(page);
    await switchUser(page, "instructor@example.invalid");
    await page.getByRole("button", { name: "Create private upload target" }).click();
    await page.getByLabel("Synthetic or rights-cleared PDF").setInputFiles({
      name: "synthetic-admitted.pdf",
      mimeType: "application/pdf",
      buffer: await readFile(validPdfPath),
    });
    await page.getByRole("button", { name: "Upload and validate PDF" }).click();
    await expect(page.getByTestId("source-state")).toHaveText("Admitted");
    await expect(page.getByText("Safe rejection code:")).toHaveCount(0);

    const outsider = await session(request, "outsider@example.invalid");
    const guessed = await request.get(
      `/f001-api/api/v1/tenants/${alphaId}/source-documents/${sourceDocumentId}/versions/${sourceVersionId}`,
      {
        headers: {
          Authorization: `Bearer ${outsider.access_token}`,
          "X-Tenant-ID": alphaId,
        },
      },
    );
    expect(guessed.status()).toBe(404);
    expect(await guessed.text()).not.toContain("Synthetic admitted source");

    await switchUser(page, "alpha-admin@example.invalid");
    await page.getByRole("button", { name: "Revoke source rights" }).click();
    await expect(page.getByTestId("source-state")).toHaveText("Blocked");
    await expect(page.getByText("pending", { exact: true })).toBeVisible();

    const browserStorage = await page.evaluate(() => ({
      local: localStorage.length,
      session: sessionStorage.length,
    }));
    expect(browserStorage).toEqual({ local: 0, session: 0 });
    expect(consoleMessages.join("\n")).not.toContain("%PDF");
  });

  test("shows deterministic rejection and cancellation states", async ({ page }) => {
    await signIn(page, "instructor@example.invalid");
    await createOwnedDeclaration(page, "cancelled");
    await page.getByRole("button", { name: "Cancel admission" }).click();
    await expect(page.getByTestId("source-state")).toHaveText("Cancelled");

    await page.reload();
    await signIn(page, "instructor@example.invalid");
    await createOwnedDeclaration(page, "rejected");
    await approveAsAdmin(page);
    await switchUser(page, "instructor@example.invalid");
    await page.getByRole("button", { name: "Create private upload target" }).click();
    await page.getByLabel("Synthetic or rights-cleared PDF").setInputFiles({
      name: "synthetic-rejected.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("synthetic non-pdf bytes"),
    });
    await page.getByRole("button", { name: "Upload and validate PDF" }).click();
    await expect(page.getByTestId("source-state")).toHaveText("Rejected");
    await expect(page.getByText("PDF_SIGNATURE_MISMATCH")).toBeVisible();
  });

  test("reauthorizes a switched user before restoring any source metadata", async ({ page }) => {
    await signIn(page, "instructor@example.invalid");
    await createOwnedDeclaration(page, "handoff-private");
    await expect(page.getByText("Synthetic handoff-private source")).toBeVisible();

    await page.getByRole("button", { name: "Sign out and switch user" }).click();
    await expect(page.getByText("Synthetic handoff-private source")).toHaveCount(0);
    await page.getByLabel("Email address").fill("learner@example.invalid");
    await page.getByLabel("Password").fill("synthetic-password");
    await page.getByRole("button", { name: "Open source workspace" }).click();
    await page.getByRole("button", { name: "Select Alpha Academy" }).click();

    await expect(page.getByText("Synthetic handoff-private source")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Sign in to a source workspace" })).toBeVisible();
    await expect(
      page.getByRole("alert").filter({ hasText: "source access is no longer active" }),
    ).toBeVisible();
  });

  test("focuses declaration errors and reflows at 200 percent", async ({ page }) => {
    await signIn(page, "instructor@example.invalid");
    await page.getByRole("button", { name: "Submit rights declaration" }).click();
    await expect(page.getByLabel("Source display name")).toBeFocused();
    await expect(
      page.getByRole("alert").filter({ hasText: "Complete the source declaration" }),
    ).toBeVisible();

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

  test("uses the generated API client without browser storage or direct data clients", async () => {
    const featureRoot = path.resolve(
      import.meta.dirname,
      "../../web/src/features/source-admission",
    );
    const source = (
      await Promise.all(
        ["api-transport.ts", "source-admission-experience.tsx"].map((file) =>
          readFile(path.join(featureRoot, file), "utf8"),
        ),
      )
    ).join("\n");

    expect(source).toContain('from "@ai-lms/api-client"');
    expect(source).not.toMatch(/@supabase|\.from\s*\(|localStorage|sessionStorage/i);
    expect(source).not.toMatch(/console\.(log|debug|info|warn|error)/);
  });
});

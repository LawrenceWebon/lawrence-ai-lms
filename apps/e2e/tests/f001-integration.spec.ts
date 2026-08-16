import { expect, type APIRequestContext, type Page, test } from "@playwright/test";

const alphaId = "00000000-0000-4000-8000-0000000000a1";
const activeInvitation = "synthetic-active-token-000000000001";

type SessionResponse = { access_token: string };
type MembershipResponse = {
  id: string;
  status: string;
  row_version: number;
  role_codes: string[];
};

async function resetFixture(request: APIRequestContext) {
  const response = await request.post("/f001-api/api/integration/reset");
  expect(response.ok()).toBeTruthy();
}

async function session(
  request: APIRequestContext,
  email: string,
): Promise<SessionResponse> {
  const response = await request.post("/f001-api/api/integration/session", {
    data: { email, password: "synthetic-password" },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as SessionResponse;
}

async function signIn(page: Page, email: string) {
  await page.goto("/tenant-context?scenario=integration");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Choose a workspace" })).toBeVisible();
}

test.describe("F-001 composed critical journey", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ request }) => {
    await resetFixture(request);
  });

  test("invitation, explicit selection, allowed read, and immediate revocation fail closed", async ({
    page,
    request,
  }) => {
    const consoleMessages: string[] = [];
    page.on("console", (message) => consoleMessages.push(message.text()));

    await signIn(page, "invitee@example.invalid");
    await expect(page.getByRole("heading", { name: "No active workspaces" })).toBeVisible();

    const tokenInput = page.getByLabel("Invitation token");
    await tokenInput.fill(activeInvitation);
    await page.getByRole("button", { name: "Accept invitation" }).click();
    await expect(page.getByRole("status")).toContainText("Invitation accepted");
    await expect(tokenInput).toHaveValue("");
    expect(page.url()).not.toContain(activeInvitation);
    expect(consoleMessages.join("\n")).not.toContain(activeInvitation);

    await page.getByRole("button", { name: "Refresh access" }).click();
    await expect(page.getByRole("button", { name: "Select Alpha Academy" })).toBeVisible();
    await expect(page.getByTestId("active-tenant")).toHaveCount(0);
    await page.getByRole("button", { name: "Select Alpha Academy" }).click();
    await expect(page.getByTestId("active-tenant")).toContainText("Alpha Academy");

    const adminSession = await session(request, "alpha-admin@example.invalid");
    const membershipsResponse = await request.get(
      `/f001-api/api/v1/tenants/${alphaId}/memberships`,
      {
        headers: {
          Authorization: `Bearer ${adminSession.access_token}`,
          "X-Tenant-ID": alphaId,
        },
      },
    );
    expect(membershipsResponse.ok()).toBeTruthy();
    const memberships = (await membershipsResponse.json()) as MembershipResponse[];
    const invited = memberships.find((item) => item.role_codes.includes("reviewer"));
    expect(invited).toBeDefined();

    const revoked = await request.patch(
      `/f001-api/api/v1/tenants/${alphaId}/memberships/${invited?.id}`,
      {
        headers: {
          Authorization: `Bearer ${adminSession.access_token}`,
          "X-Tenant-ID": alphaId,
        },
        data: { status: "inactive", row_version: invited?.row_version },
      },
    );
    expect(revoked.ok()).toBeTruthy();

    await page.getByRole("button", { name: "Refresh access" }).click();
    await expect(
      page.locator('[role="alert"]').filter({ hasText: "Your access is no longer active" }),
    ).toContainText("Your access is no longer active");
    await expect(page.getByTestId("active-tenant")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });

  test("multi-tenant switching is explicit and an outsider selector returns no tenant data", async ({
    page,
    request,
  }) => {
    await signIn(page, "instructor@example.invalid");
    await expect(page.getByTestId("active-tenant")).toHaveCount(0);
    await page.getByRole("button", { name: "Select Alpha Academy" }).click();
    await expect(page.getByTestId("active-tenant")).toContainText("Alpha Academy");
    await page.getByRole("button", { name: "Select Beta Academy" }).click();
    await expect(page.getByTestId("active-tenant")).toContainText("Beta Academy");

    const outsiderSession = await session(request, "outsider@example.invalid");
    const denied = await request.get("/f001-api/api/v1/auth-context", {
      headers: {
        Authorization: `Bearer ${outsiderSession.access_token}`,
        "X-Tenant-ID": alphaId,
      },
    });
    expect(denied.status()).toBe(404);
    const body = await denied.text();
    expect(body).toContain("TENANT_ACCESS_DENIED");
    expect(body).not.toContain("Alpha Academy");
  });
});

import { readFile } from "node:fs/promises";
import path from "node:path";

import { expect, type Page, test } from "@playwright/test";

const activeInvitation = "synthetic-active-token-000000000001";
const expiredInvitation = "synthetic-expired-token-00000000001";
const revokedInvitation = "synthetic-revoked-token-00000000001";

async function signIn(page: Page, scenario = "multi") {
  await page.goto(`/tenant-context?scenario=${scenario}`);
  await page.getByLabel("Email address").fill("instructor@example.test");
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Choose a workspace" })).toBeVisible();
}

function applicationAlert(page: Page, message: string) {
  return page.locator('[role="alert"]').filter({ hasText: message });
}

test("sign-in is labelled, validates input, announces loading, and follows keyboard order", async ({
  page,
}) => {
  await page.goto("/tenant-context");

  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByLabel("Email address").focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Password")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeFocused();

  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Enter a valid email address.")).toBeVisible();
  await expect(page.getByText("Enter your password.")).toBeVisible();
  await expect(page.getByLabel("Email address")).toHaveAttribute("aria-invalid", "true");

  await page.getByLabel("Email address").fill("instructor@example.test");
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("status")).toContainText("Checking your access");
  await expect(page.getByRole("heading", { name: "Choose a workspace" })).toBeVisible();
});

test("multiple memberships require explicit selection and allow an explicit switch", async ({ page }) => {
  await signIn(page);

  await expect(page.getByRole("button", { name: "Select Alpha Learning" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Select Beta Learning" })).toBeVisible();
  await expect(page.getByTestId("active-tenant")).toHaveCount(0);

  await page.getByRole("button", { name: "Select Alpha Learning" }).click();
  await expect(page.getByTestId("active-tenant")).toContainText("Alpha Learning");
  await page.getByRole("button", { name: "Select Beta Learning" }).click();
  await expect(page.getByTestId("active-tenant")).toContainText("Beta Learning");
});

test("a single membership still requires explicit selection", async ({ page }) => {
  await signIn(page, "single");

  await expect(page.getByRole("button", { name: "Select Alpha Learning" })).toBeVisible();
  await expect(page.getByTestId("active-tenant")).toHaveCount(0);
  await page.getByRole("button", { name: "Select Alpha Learning" }).click();
  await expect(page.getByTestId("active-tenant")).toContainText("Alpha Learning");
});

test("empty and transport-error states are actionable without enumerating tenants", async ({ page }) => {
  await page.goto("/tenant-context?scenario=auth-error");
  await page.getByLabel("Email address").fill("unknown@example.test");
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(applicationAlert(page, "We could not sign you in")).toContainText(
    "We could not sign you in with those details. Check them and try again.",
  );
  await expect(page.getByText("Alpha Learning")).toHaveCount(0);

  await signIn(page, "empty");
  await expect(page.getByRole("heading", { name: "No active workspaces" })).toBeVisible();
  await expect(page.getByText("Ask a tenant administrator for an invitation or active membership.")).toBeVisible();

  await page.goto("/tenant-context?scenario=error");
  await page.getByLabel("Email address").fill("instructor@example.test");
  await page.getByLabel("Password").fill("synthetic-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(applicationAlert(page, "We could not load your access")).toContainText(
    "We could not load your access. Try again without changing your sign-in details.",
  );
  await expect(page.getByText("Alpha Learning")).toHaveCount(0);
  await expect(page.getByText("Beta Learning")).toHaveCount(0);
});

test("invitation acceptance is neutral, duplicate-safe, and does not leak the token", async ({ page }) => {
  const consoleMessages: string[] = [];
  const requestUrls: string[] = [];
  page.on("console", (message) => consoleMessages.push(message.text()));
  page.on("request", (request) => requestUrls.push(request.url()));

  await signIn(page);
  const tokenInput = page.getByLabel("Invitation token");
  await tokenInput.fill(activeInvitation);
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await expect(page.getByRole("status")).toContainText("Invitation accepted");
  await expect(tokenInput).toHaveValue("");
  await expect(page.getByText(activeInvitation)).toHaveCount(0);
  expect(page.url()).not.toContain(activeInvitation);
  expect(consoleMessages.join("\n")).not.toContain(activeInvitation);
  expect(requestUrls.join("\n")).not.toContain(activeInvitation);

  await tokenInput.fill(activeInvitation);
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await expect(page.getByRole("status")).toContainText("Invitation already accepted");

  for (const token of [expiredInvitation, revokedInvitation, "synthetic-invalid-token"]) {
    await tokenInput.fill(token);
    await page.getByRole("button", { name: "Accept invitation" }).click();
    await expect(applicationAlert(page, "This invitation cannot be accepted")).toContainText(
      "This invitation cannot be accepted. Ask a tenant administrator for a new invitation.",
    );
    await expect(tokenInput).toHaveValue("");
    await expect(page.getByText(token)).toHaveCount(0);
  }
});

test("transport denial wins over a visible tenant selector", async ({ page }) => {
  await signIn(page, "denied");
  await page.getByRole("button", { name: "Select Alpha Learning" }).click();

  await expect(applicationAlert(page, "You do not have access to that workspace")).toContainText(
    "You do not have access to that workspace. Your available access has not changed.",
  );
  await expect(page.getByTestId("active-tenant")).toHaveCount(0);
});

test("session expiry clears active context and returns to private sign-in", async ({ page }) => {
  await signIn(page, "session-expired");
  await page.getByRole("button", { name: "Select Alpha Learning" }).click();
  await expect(page.getByTestId("active-tenant")).toContainText("Alpha Learning");

  await page.getByRole("button", { name: "Refresh access" }).click();
  await expect(applicationAlert(page, "Your session has expired")).toContainText(
    "Your session has expired. Sign in again.",
  );
  await expect(page.getByTestId("active-tenant")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
});

test("tenant-context layout reflows at a narrow viewport and 200 percent zoom", async ({ page }) => {
  await page.setViewportSize({ width: 640, height: 900 });
  await signIn(page);
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });

  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
  await expect(page.getByRole("button", { name: "Select Alpha Learning" })).toBeVisible();
});

test("lane source has no browser core-table client or persistent authorization state", async () => {
  const featureRoot = path.resolve(import.meta.dirname, "../../web/src/features/tenant-context");
  const files = [
    "tenant-context-experience.tsx",
    "transport.ts",
    "mock-transport.ts",
    "api-transport.ts",
  ];
  const source = (
    await Promise.all(files.map((file) => readFile(path.join(featureRoot, file), "utf8")))
  ).join("\n");

  expect(source).not.toMatch(/@supabase|\.from\s*\(|localStorage|sessionStorage/i);
  expect(source).not.toMatch(/console\.(log|debug|info|warn|error)/);
});

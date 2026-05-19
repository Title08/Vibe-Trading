import { expect, test } from "@playwright/test";

const sessions = [
  {
    session_id: "session-alpha",
    title: "Alpha research",
    status: "completed",
    created_at: "2026-05-20T00:00:00Z",
    updated_at: "2026-05-20T00:00:00Z",
  },
];

test("renders the main app shell", async ({ page }) => {
  await page.route("**/sessions", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: [] });
      return;
    }
    await route.fallback();
  });

  await page.goto("/agent");

  await expect(page.locator("#root")).not.toBeEmpty();
  await expect(page.getByRole("navigation")).toBeVisible();
  await expect(page.getByRole("link", { name: "Agent", exact: true })).toBeVisible();
  await expect(page.getByRole("textbox")).toBeVisible();
});

test("session actions dropdown opens, closes, and keeps rename/delete flows", async ({ page }) => {
  await page.route("**/sessions", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: sessions });
      return;
    }
    await route.fallback();
  });
  await page.route("**/sessions/**", async (route) => {
    await route.fulfill({ json: { status: "ok" } });
  });

  await page.goto("/agent");

  const sessionLink = page.getByRole("link", { name: "Alpha research" });
  await expect(sessionLink).toBeVisible();
  await sessionLink.hover();

  const actionsButton = page.getByRole("button", { name: "Session actions" });
  await actionsButton.click();
  await expect(page.getByRole("button", { name: "Rename" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Delete?" })).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Rename" })).toBeHidden();

  await sessionLink.hover();
  await actionsButton.click();
  await page.getByRole("button", { name: "Rename" }).click();
  await expect(page.getByDisplayValue("Alpha research")).toBeVisible();

  await page.keyboard.press("Escape");
  await sessionLink.hover();
  await actionsButton.click();
  await page.getByRole("button", { name: "Delete?" }).click();
  await expect(page.getByRole("button", { name: "Confirm" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();

  await page.getByRole("button", { name: "Cancel" }).click();
  await sessionLink.hover();
  await actionsButton.click();
  await page.mouse.click(20, 20);
  await expect(page.getByRole("button", { name: "Rename" })).toBeHidden();

  await sessionLink.hover();
  await actionsButton.click();
  await expect(page.getByRole("button", { name: "Rename" })).toBeVisible();
  await page.getByRole("button", { name: "Collapse" }).click();
  await expect(page.getByRole("button", { name: "Rename" })).toBeHidden();
  await expect(page.getByRole("button", { name: "Expand" })).toBeVisible();
});

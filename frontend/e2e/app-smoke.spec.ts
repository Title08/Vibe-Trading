import { expect, test } from "@playwright/test";

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

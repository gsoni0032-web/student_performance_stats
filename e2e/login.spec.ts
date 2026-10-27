import { expect, test } from "@playwright/test";

import { EMAIL, signIn } from "./helpers";

test("a wrong password is refused with a clear message, a right one opens the overview", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password").fill("definitely-not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);

  await signIn(page);
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeAttached();
});

test("visiting a page while signed out sends you to sign in", async ({ page }) => {
  await page.goto("/students");
  await expect(page).toHaveURL(/\/login$/);
});

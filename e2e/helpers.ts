import { expect, type Page } from "@playwright/test";

export const EMAIL = process.env.E2E_EMAIL ?? "admin@pathway.example";
export const PASSWORD = process.env.E2E_PASSWORD ?? "";

export async function signIn(page: Page): Promise<void> {
  if (!PASSWORD) throw new Error("Set E2E_PASSWORD to the demo account password before running the end-to-end tests.");
  await page.goto("/login");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
}

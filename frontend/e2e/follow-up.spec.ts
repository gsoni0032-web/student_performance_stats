import { expect, test } from "@playwright/test";

import { signIn } from "./helpers";

test("open a high-risk student and record a follow-up", async ({ page }) => {
  await signIn(page);
  await page.goto("/students?risk=high");

  const firstStudent = page.getByRole("table").getByRole("link").first();
  await expect(firstStudent).toBeVisible();
  await firstStudent.click();

  await expect(page.getByRole("heading", { name: "Dropout risk" })).toBeVisible();
  await expect(page.getByText("High risk").first()).toBeVisible();

  await page.getByLabel("Status").selectOption("guardian_contacted");
  await page.getByLabel("Notes").fill("Rang the guardian on Monday; agreed to review attendance in two weeks.");
  await page.getByRole("button", { name: "Save follow-up" }).click();
  await expect(page.getByText("Follow-up saved.")).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Status")).toHaveValue("guardian_contacted");
});

import { expect, test } from "@playwright/test";

import { signIn } from "./helpers";

test("lowering attendance and scores raises the predicted risk", async ({ page }) => {
  await signIn(page);
  await page.goto("/what-if?attendance=95&score=85&assignments=95&failures=0&late=0&parent=5&trend=2&grade=2");

  const probability = page.getByTestId("risk-prob");
  await expect(probability).toHaveText(/\d+%/);
  const before = Number((await probability.innerText()).replace("%", ""));

  await page.getByLabel("Attendance").fill("45");
  await page.getByLabel("Average score").fill("35");
  await page.getByLabel("Backlogs").fill("5");

  await expect.poll(async () => Number((await probability.innerText()).replace("%", ""))).toBeGreaterThan(before);
});

import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("generate a requirement-based plan, record evidence, edit a risk and export", async ({
  page,
}) => {
  await page.goto("/projects/");
  await page.getByLabel("Project name").fill(`Operations Orbit ${Date.now()}`);
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await page.getByRole("tab", { name: "Requirements", exact: true }).click();
  await page.getByLabel(/Title/).fill("Schedule launch safely");
  await page
    .getByLabel("Acceptance criteria")
    .fill("Reject conflicting launch slots");
  await page
    .getByRole("button", { name: "Add requirement", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Schedule launch safely", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("tab", { name: "Validate & Operate", exact: true })
    .click();
  await expect(page).toHaveURL(/tab=operations/);
  await page
    .getByRole("button", { name: "Generate from requirements", exact: true })
    .click();
  const row = page.getByRole("article", {
    name: "Unit: Schedule launch safely",
    exact: true,
  });
  await expect(row.locator(".operation-status")).toHaveText(
    "Proposed (not run)",
  );
  await row.getByText("Edit case / record result", { exact: true }).click();
  await row.getByLabel("Test status").selectOption("passed");
  await expect(
    row.getByRole("button", { name: "Record result", exact: true }),
  ).toBeDisabled();
  await row
    .getByLabel("Result notes (required)")
    .fill(
      "Manual domain check executed locally; conflicting slot was rejected.",
    );
  await row.getByLabel("Executed by (optional)").fill("E2E reviewer");
  await row.getByRole("button", { name: "Record result", exact: true }).click();
  await expect(row.locator(".operation-status")).toHaveText("Executed: Passed");
  await page.reload();
  await expect(row.getByText("Recorded result", { exact: true })).toBeVisible();
  const risk = page.getByRole("row").filter({
    has: page.getByRole("rowheader", {
      name: /Limited operational capacity/,
    }),
  });
  await risk.getByText("Edit risk", { exact: true }).click();
  await risk.getByLabel("Risk owner").fill("Launch team");
  await risk
    .getByRole("textbox", { name: "Mitigation", exact: true })
    .fill("Rehearse recovery and document the runbook before launch.");
  await risk.getByRole("button", { name: "Save risk", exact: true }).click();
  await expect(risk).toContainText("Launch team");
  await page.setViewportSize({ width: 1440, height: 1000 });
  const table = page.getByRole("region", { name: "Risk register table" });
  const singleLine = await table
    .locator("thead th, td:nth-child(2), td:nth-child(3), td:nth-child(4), td:nth-child(6), .risk-score")
    .evaluateAll((cells) =>
      cells.every((cell) => {
        const range = document.createRange();
        range.selectNodeContents(cell);
        return range.getClientRects().length === 1;
      }),
    );
  expect(singleLine).toBe(true);
  const downloadEvent = page.waitForEvent("download");
  await page
    .getByRole("button", {
      name: "Export operations pack (Markdown)",
      exact: true,
    })
    .click();
  const stream = await (await downloadEvent).createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const text = Buffer.concat(chunks).toString("utf8");
  expect(text).toContain("Generated deterministically from requirements");
  expect(text).toContain("Executed: 1");
  expect(text).toContain("Manual domain check executed locally");
  expect(text).toContain("Launch team");
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 360, height: 800 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    await table.evaluate((element) => {
      element.scrollLeft = element.scrollWidth;
      return element.scrollWidth > element.clientWidth && element.scrollLeft > 0;
    }),
  ).toBe(true);
});

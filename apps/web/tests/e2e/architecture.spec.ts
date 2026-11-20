import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("sample architecture explains choices and remains read-only at desktop and mobile", async ({
  page,
}) => {
  await page.goto("/projects/view/?id=sample&tab=architecture");
  await expect(page.getByRole("tab", { name: "Architecture" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(
    page.getByRole("heading", { name: "Technology recommendations" }),
  ).toBeVisible();
  await expect(page.getByText("Catalogue 2026.11.1")).toBeVisible();
  const database = page.getByRole("region", {
    name: "Database recommendation",
  });
  await expect(
    database.getByRole("heading", { name: "PostgreSQL" }),
  ).toBeVisible();
  await expect(
    database.getByRole("heading", { name: "Why this appears" }),
  ).toBeVisible();
  await expect(
    database.getByText("detected", { exact: true }).first(),
  ).toBeVisible();
  await expect(database.getByText(/discovery\./).first()).toBeVisible();
  await database.getByText("Alternatives (2)").click();
  await expect(
    database.getByRole("heading", { name: "MongoDB" }),
  ).toBeVisible();
  await expect(
    database.getByText(/Ranked below postgresql/).first(),
  ).toBeVisible();
  await expect(
    database.getByRole("heading", { name: "Trade-offs" }).first(),
  ).toBeVisible();
  const ai = page.getByRole("region", { name: "AI layer recommendation" });
  await expect(
    ai.getByText("Not recommended · Optional, may incur cost"),
  ).toBeVisible();
  await ai.getByText("Explore optional candidates").click();
  await expect(
    ai.getByText("Optional, may incur cost", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByRole("combobox")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Save inputs" })).toHaveCount(
    0,
  );
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
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});

test("owner overrides update a recommendation and Auto restores detection", async ({
  page,
}) => {
  await page.goto("/projects/");
  await page.getByLabel("Project name").fill(`Architecture e2e ${Date.now()}`);
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await page.getByRole("tab", { name: "Architecture" }).click();
  const database = page.getByRole("region", {
    name: "Database recommendation",
  });
  await expect(
    database.getByRole("heading", { name: "PostgreSQL" }),
  ).toBeVisible();
  await page.getByLabel("Data shape override").selectOption("document");
  await page.getByRole("button", { name: "Save inputs" }).click();
  await expect(
    page.getByText("Inputs saved. Recommendations updated."),
  ).toBeVisible();
  await expect(
    database.getByRole("heading", { name: "MongoDB" }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Data shape override")).toHaveValue("document");
  await expect(
    database.getByRole("heading", { name: "MongoDB" }),
  ).toBeVisible();
  await page.getByLabel("Data shape override").selectOption("auto");
  await page.getByRole("button", { name: "Save inputs" }).click();
  await expect(
    database.getByRole("heading", { name: "PostgreSQL" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 360, height: 800 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

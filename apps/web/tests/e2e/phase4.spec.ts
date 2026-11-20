import { expect, test, type Download, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function markdown(download: Download) {
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8");
}

async function accessibleAndFits(page: Page) {
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
  await page.setViewportSize({ width: 1280, height: 900 });
}

test("owner specifies, persists edits, exports complete Markdown and plans with dependency gating", async ({
  page,
}, testInfo) => {
  test.slow();
  const name = `Phase 4 Orbit ${Date.now()}`;
  await page.goto("/projects/");
  await page.getByLabel("Project name").fill(name);
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await page.getByRole("tab", { name: "Specs", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate specifications", exact: true })
    .click();
  await expect(page.getByLabel("Artefact title")).toHaveValue(
    "Product requirements document",
  );
  await page
    .getByLabel("Problem", { exact: true })
    .fill("Reviewed launch coordination problem");
  await page
    .getByRole("button", { name: "Save artefact", exact: true })
    .click();
  await expect(page.getByText("Artefact saved.")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Problem", { exact: true })).toHaveValue(
    "Reviewed launch coordination problem",
  );
  await page
    .getByRole("button", { name: "Regenerate specifications", exact: true })
    .click();
  await expect(page.getByText(/Specifications generated/)).toBeVisible();
  await expect(page.getByLabel("Problem", { exact: true })).toHaveValue(
    "Reviewed launch coordination problem",
  );
  const token = await page.evaluate(() =>
    localStorage.getItem("buildwise.project-token"),
  );
  const id = new URL(page.url()).searchParams.get("id");
  const response = await page.request.get(
    `http://localhost:8000/api/v1/projects/${id}/artefacts`,
    { headers: { "X-Project-Token": token! } },
  );
  expect(response.ok()).toBe(true);
  const artefacts = (await response.json()) as {
    title: string;
    sections: { heading: string; body: string }[];
  }[];
  expect(artefacts).toHaveLength(13);
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download all artefacts .md", exact: true })
    .click();
  const specs = await markdown(await download);
  expect(specs).toContain(name);
  expect(specs).toContain("Reviewed launch coordination problem");
  for (const artefact of artefacts) {
    expect(specs).toContain(artefact.title);
    for (const section of artefact.sections) {
      expect(specs).toContain(section.heading);
      expect(specs).toContain(section.body);
    }
  }
  await accessibleAndFits(page);
  await page.screenshot({
    path: testInfo.outputPath("specs-full-page.png"),
    fullPage: true,
  });
  await page.getByRole("tab", { name: "Plan", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate plan", exact: true })
    .click();
  await expect(page.getByLabel("Status for T-001")).toHaveValue("ready");
  await page.getByLabel("Status for T-003").selectOption("in_progress");
  await expect(
    page.getByRole("article", { name: /^T-003:/ }).getByRole("alert"),
  ).toContainText("all dependencies must be done");
  await expect(page.getByLabel("Status for T-003")).toHaveValue("backlog");
  await page.getByLabel("Status for T-001").selectOption("done");
  await expect(page.getByText("T-001 status updated.")).toBeVisible();
  await page.getByLabel("Status for T-002").selectOption("in_progress");
  await expect(page.getByText("T-002 status updated.")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Status for T-002")).toHaveValue("in_progress");
  const planDownload = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export plan Markdown", exact: true })
    .click();
  const plan = await markdown(await planDownload);
  for (const value of [
    name,
    "T-001",
    "T-002",
    "T-003",
    "T-004",
    "in_progress",
    "Acceptance criteria",
    "Implementation notes",
    "Dependencies:",
  ])
    expect(plan).toContain(value);
  await page.getByRole("button", { name: "Edit T-002", exact: true }).click();
  await accessibleAndFits(page);
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement)
      document.activeElement.blur();
    window.scrollTo(0, 0);
  });
  await page.screenshot({
    path: testInfo.outputPath("plan-full-page.png"),
    fullPage: true,
  });
});

test("sample Specs and Plan are public, read-only, accessible and fit at 360px", async ({
  page,
}) => {
  for (const tab of ["specs", "plan"]) {
    await page.goto(`/projects/view/?id=sample&tab=${tab}`);
    await expect(
      page.getByRole("tab", {
        name: tab === "specs" ? "Specs" : "Plan",
        exact: true,
      }),
    ).toHaveAttribute("aria-selected", "true");
    await expect(
      page.getByRole("heading", {
        name: tab === "specs" ? "Specifications" : "Build plan",
        exact: true,
      }),
    ).toBeVisible();
    if (tab === "specs")
      await expect(
        page.getByRole("region", { name: "Selected artefact" }),
      ).toBeVisible();
    else
      await expect(
        page.getByRole("heading", {
          name: "Dependency validation",
          exact: true,
        }),
      ).toBeVisible();
    await expect(page.getByRole("textbox")).toHaveCount(0);
    await expect(page.getByRole("combobox")).toHaveCount(0);
    await expect(
      page.getByRole("button", {
        name: /Generate|Regenerate|Overwrite|Add ADR|Save artefact|Add task|Edit T-|Delete T-/,
      }),
    ).toHaveCount(0);
    await accessibleAndFits(page);
  }
});

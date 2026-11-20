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
  for (const [label, answer] of [
    ["Problem statement", "Overlapping launches delay operators."],
    ["Target users", "Launch operators"],
    ["Goals", "Resolve conflicts before release"],
    ["Constraints", "One engineer; free hosting only"],
    ["Integrations", "Calendar export"],
    ["Open questions", "What is the approval window?"],
  ]) {
    await page.getByLabel(label).fill(answer);
    await page.getByRole("button", { name: "Save and continue" }).click();
  }
  await expect(page.getByRole("heading", { name: "Project brief" })).toBeVisible();
  await expect(page.getByText("Overlapping launches delay operators.")).toBeVisible();
  await page.getByRole("tab", { name: "Requirements" }).click();
  await page.getByLabel("Title").fill("Reject overlapping launches");
  await page.getByLabel("Priority").selectOption("P0");
  await page.getByLabel("Acceptance criteria").fill("An overlapping launch is rejected");
  await page.getByRole("button", { name: "Add requirement" }).click();
  await expect(page.getByRole("heading", { name: "Reject overlapping launches" })).toBeVisible();
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
  const foundation = page.getByRole("article", { name: /^T-001:/ });
  await expect(foundation).not.toContainText("Project:");
  await expect(foundation).not.toContainText("Design guidance:");
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
  await page
    .getByText("Implementation notes for T-001", { exact: true })
    .click();
  await page
    .getByText("Implementation notes for T-004", { exact: true })
    .click();
  const deployment = page.getByRole("article", { name: /^T-004:/ });
  await expect(
    deployment
      .getByRole("listitem")
      .filter({ hasText: "See: Deployment plan, Observability plan" }),
  ).toBeVisible();
  expect(plan).toContain("- See: Deployment plan, Observability plan");
  expect(plan).not.toContain("Design guidance:");
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
  await page.getByRole("tab", { name: "Overview" }).click();
  const packDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export project pack (Markdown)", exact: true }).click();
  const pack = await markdown(await packDownload);
  for (const value of [
    "Overlapping launches delay operators.",
    "Reviewed launch coordination problem",
    "An overlapping launch is rejected",
    "Technology recommendations",
    "Technical design document",
    "User stories",
    "Build plan",
  ]) expect(pack).toContain(value);
  await page.goto("/");
  const recent = page.getByRole("region", { name: "Recent projects" });
  await expect(recent.getByRole("link", { name })).toBeVisible();
  await expect(recent).toContainText("Stage: Build plan");
});

test("a first-time visitor can follow the walkthrough and export the sample without a token", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Open sample project" })).toBeVisible();
  await page.getByRole("link", { name: "Read the demo walkthrough" }).click();
  await expect(page.getByRole("heading", { name: "Public demo walkthrough" })).toBeVisible();
  await page.getByRole("link", { name: "Review proposed tests" }).click();
  await expect(page.getByRole("tab", { name: "Testing" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: "Test plan" })).toBeVisible();
  await page.getByRole("tab", { name: "Overview" }).click();
  await expect(page.getByRole("note")).toContainText("Illustrative sample, read-only");
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export project pack (Markdown)", exact: true }).click();
  const download = await pending;
  expect(download.suggestedFilename()).toBe("buildwise-project-pack.md");
  const pack = await markdown(download);
  for (const value of [
    "Restaurant Booking",
    "Project brief",
    "Technology recommendations",
    "Technical design document",
    "Tenant data isolation",
    "User stories",
    "Acceptance criteria",
    "Build plan",
    "Risk register",
  ]) expect(pack).toContain(value);
  expect(await page.evaluate(() => localStorage.getItem("buildwise.project-token"))).toBeNull();
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

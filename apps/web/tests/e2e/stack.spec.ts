import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const pages = [
  ["/", "Dashboard", "Build with a clearer picture."],
  ["/projects/", "Projects", "Projects"],
  ["/catalogue/", "Technology catalogue", "Technology catalogue"],
  ["/guides/", "Engineering guides", "Engineering guides"],
  ["/observability/", "Observability demo", "Observability demo"],
  ["/docs/", "Documentation", "Documentation"],
];

test("real API health and readiness", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("All systems ready")).toBeVisible();
  await expect(
    page.getByText("API responding · Database connected"),
  ).toBeVisible();
});

test("dashboard detects an outage and recovers without reloading", async ({
  page,
}) => {
  await page.clock.install();
  let offline = false;
  let failedProbes = 0;
  await page.route("**/health", async (route) => {
    if (!offline) return route.continue();
    failedProbes++;
    await route.fulfill({
      status: 503,
      headers: { "Access-Control-Allow-Origin": "http://localhost:3000" },
      json: {
        error: {
          code: "unavailable",
          message: "Simulated outage",
          correlation_id: "outage-test",
        },
      },
    });
  });
  await page.goto("/");
  await expect(page.getByText("All systems ready")).toBeVisible();
  offline = true;
  await page.clock.fastForward(30000);
  await expect(page.getByText("Waking the API")).toBeVisible();
  for (let attempt = 2; attempt <= 4; attempt++) {
    await page.clock.fastForward(5000);
    await expect.poll(() => failedProbes).toBe(attempt);
    await page.clock.runFor(100);
  }
  await expect(page.getByText("API currently unavailable")).toBeVisible();
  offline = false;
  await page.clock.fastForward(30000);
  await expect(page.getByText("All systems ready")).toBeVisible();
});

test("create, edit and resume a browser-owned project through the real stack", async ({
  page,
}) => {
  await page.goto("/projects/");
  await expect(page.getByText("No projects yet")).toBeVisible();
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(page.getByText("Enter a project name.")).toBeVisible();
  const name = `Browser integration ${Date.now()}`;
  await page.getByLabel("Project name").fill(name);
  await page
    .getByLabel("Description")
    .fill("Created through the static frontend and FastAPI.");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(page).toHaveURL(/\/projects\/view\/\?id=.+&tab=discovery/);
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  expect(
    await page.evaluate(() => localStorage.getItem("buildwise.project-token")),
  ).toMatch(/^[A-Za-z0-9_-]{43}$/);

  await page.getByLabel(/Problem statement/).fill("Bookings are lost.");
  await page.getByRole("button", { name: /Save and continue/ }).click();
  await expect(
    page.getByRole("heading", { name: /Step 2 of 7/ }),
  ).toBeVisible();
  await page.getByLabel(/Target users/).fill("Owners\nDiners");
  await page.getByRole("button", { name: /Save draft/ }).click();
  await expect(page.getByText("Progress saved.")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel(/Target users/)).toHaveValue("Owners\nDiners");

  await page.getByRole("tab", { name: "Requirements" }).click();
  await page.getByLabel(/Title/).fill("Book a table online");
  await page.getByLabel("Acceptance criteria").fill("Booking is confirmed");
  await page.getByRole("button", { name: "Add requirement" }).click();
  await expect(
    page.getByRole("heading", { name: "Book a table online" }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "Overview" }).click();
  await expect(page.getByText("2/6 steps")).toBeVisible();
  const renamed = `${name} renamed`;
  await page.getByLabel(/Project name/).fill(renamed);
  await page.getByLabel("Status").selectOption("active");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Project saved.")).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { level: 1, name: renamed }),
  ).toBeVisible();
  await page.getByRole("link", { name: "All projects" }).click();
  await expect(page.getByRole("link", { name: renamed })).toBeVisible();
});

test("illustrative sample project is read-only", async ({ page }) => {
  await page.goto("/projects/");
  await page.getByRole("link", { name: "View sample project" }).click();
  await expect(page.getByRole("note")).toContainText("read-only");
  await expect(page.getByText("6/6 steps")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save changes" })).toHaveCount(
    0,
  );
  await page.getByRole("tab", { name: "Requirements" }).click();
  await expect(
    page.getByRole("heading", { name: "Diner books a table online" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /^Edit/ })).toHaveCount(0);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});

test("keyboard skip-link reaches main content", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
});

for (const [path, label, heading] of pages) {
  test(`${label}: navigation, accessibility and 360px layout`, async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: label, exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`${path === "/" ? "/" : path}$`));
    await expect(
      page.getByRole("heading", { level: 1, name: heading, exact: true }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("navigation")
        .getByRole("link", { name: label, exact: true }),
    ).toHaveAttribute("aria-current", "page");
    if (path === "/" || path === "/observability/")
      await expect(page.getByText("All systems ready")).toBeVisible();
    if (path === "/projects/")
      await expect(page.getByText("No projects yet")).toBeVisible();
    if (path === "/catalogue/")
      await expect(
        page.getByRole("heading", { name: "PostgreSQL", exact: true }),
      ).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.screenshot({
      path: `test-results/${label.replaceAll(" ", "-").toLowerCase()}-desktop.png`,
      fullPage: true,
    });
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
    await page.screenshot({
      path: `test-results/${label.replaceAll(" ", "-").toLowerCase()}-360.png`,
      fullPage: true,
    });
  });
}

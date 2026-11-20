import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OperationsPanel } from "@/components/operations";
import { api, ApiError, type Operations, type TestCase } from "@/lib/api";
import * as downloads from "@/lib/download";

const meta = {
  project_id: "p1",
  source: "generated" as const,
  edited: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const proposed: TestCase = {
  ...meta,
  id: "t1",
  category: "unit",
  title: "Validate booking rules",
  description: "Reject conflicting bookings",
  rationale: "Requirement: Book a table (P0).",
  status: "proposed",
  result_notes: "",
  executed: false,
};
const data: Operations = {
  test_cases: [
    proposed,
    {
      ...proposed,
      id: "t2",
      category: "integration",
      title: "Persist booking",
      status: "passed",
      executed: true,
      result_notes: "pytest run 42: success",
      executed_at: "2026-01-01T12:00:00Z",
      executed_by: "Reviewer",
    },
  ],
  risks: [
    {
      ...meta,
      id: "r1",
      title: "Provider outage",
      description: "Email unavailable",
      category: "operational",
      likelihood: 3,
      impact: 4,
      score: 12,
      status: "open",
      owner: "",
      mitigation: "Retry deliveries",
      rationale: "Discovery integrations: Email provider",
    },
  ],
  slos: [
    {
      ...meta,
      id: "s1",
      name: "Availability",
      sli: "Successful requests / requests",
      target: "99.5%",
      window: "28 days",
      alert: "Multi-window burn-rate alert",
      rationale: "scale=small",
      status: "suggested",
    },
  ],
};

beforeEach(() => {
  localStorage.setItem("buildwise.project-token", "a".repeat(43));
  vi.spyOn(api, "operations").mockResolvedValue(data);
});

it("groups cases, distinguishes proposed and executed, and displays risks and SLOs", async () => {
  render(<OperationsPanel projectId="p1" readOnly={false} />);
  const unit = await screen.findByRole("region", { name: "Unit tests" });
  expect(
    within(unit).getByText("Proposed (not run)", { selector: "span" }),
  ).toBeVisible();
  expect(within(unit).getByText(/Requirement: Book a table/)).toBeVisible();
  const integration = screen.getByRole("region", { name: "Integration tests" });
  expect(
    within(integration).getByText("Executed: Passed", { selector: "span" }),
  ).toBeVisible();
  expect(
    within(integration).getByText("pytest run 42: success", { selector: "p" }),
  ).toBeVisible();
  expect(screen.getByRole("table")).toHaveTextContent("Provider outage");
  expect(
    screen.getByRole("article", { name: "Availability" }),
  ).toHaveTextContent("99.5%");
  expect(
    screen.getByRole("link", { name: /Open deployment plan/ }),
  ).toHaveAttribute(
    "href",
    expect.stringContaining("tab=specs&artefact=deployment"),
  );
});

it("requires notes when recording a result and displays server 422 messages", async () => {
  const user = userEvent.setup();
  const save = vi
    .spyOn(api, "updateTest")
    .mockRejectedValue(
      new ApiError(
        "Passed or failed tests require non-empty result_notes",
        undefined,
        [],
        422,
      ),
    );
  render(<OperationsPanel projectId="p1" readOnly={false} />);
  const row = await screen.findByRole("article", { name: proposed.title });
  await user.click(within(row).getByText("Edit case / record result"));
  await user.selectOptions(within(row).getByLabelText("Test status"), "passed");
  expect(
    within(row).getByRole("group", { name: "Record result" }),
  ).toBeVisible();
  expect(
    within(row).getByRole("button", { name: "Record result" }),
  ).toBeDisabled();
  expect(within(row).getByLabelText("Result notes (required)")).toBeRequired();
  await user.type(
    within(row).getByLabelText("Result notes (required)"),
    "Executed locally: all assertions pass",
  );
  await user.click(within(row).getByRole("button", { name: "Record result" }));
  expect(save).toHaveBeenCalledWith(
    expect.any(String),
    "p1",
    "t1",
    expect.objectContaining({
      status: "passed",
      result_notes: "Executed locally: all assertions pass",
    }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Passed or failed tests require non-empty result_notes",
  );
});

it.each([true, false])(
  "is read-only for sample or missing token (sample=%s)",
  async (readOnly) => {
    if (!readOnly) localStorage.clear();
    render(<OperationsPanel projectId="p1" readOnly={readOnly} />);
    await screen.findByRole("article", { name: proposed.title });
    expect(
      screen.queryByRole("button", {
        name: /Regenerate|Generate from requirements/,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Edit case / record result"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Edit risk")).not.toBeInTheDocument();
    expect(screen.queryByText("Edit SLO")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Export operations pack (Markdown)" }),
    ).toBeEnabled();
  },
);

it("handles empty/load errors, generates and confirms replacement, exports CSV", async () => {
  const user = userEvent.setup();
  vi.mocked(api.operations)
    .mockRejectedValueOnce(new ApiError("Unavailable"))
    .mockResolvedValueOnce({ test_cases: [], risks: [], slos: [] });
  vi.spyOn(api, "generateOperations").mockResolvedValue({
    ...data,
    test_cases: [{ ...proposed, edited: true }],
  });
  vi.spyOn(api, "operationsExport").mockResolvedValue(
    "title,status\nCase,proposed",
  );
  const download = vi
    .spyOn(downloads, "downloadCsv")
    .mockImplementation(() => {});
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<OperationsPanel projectId="p1" readOnly={false} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Unavailable");
  await user.click(screen.getByRole("button", { name: "Retry loading" }));
  await screen.findByText(/No test cases yet/);
  await user.click(
    screen.getByRole("button", { name: "Generate from requirements" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Replace edited rows…" }),
  );
  expect(api.generateOperations).toHaveBeenCalledTimes(1);
  confirm.mockReturnValue(true);
  await user.click(
    screen.getByRole("button", { name: "Replace edited rows…" }),
  );
  expect(api.generateOperations).toHaveBeenLastCalledWith(
    expect.any(String),
    "p1",
    true,
  );
  await user.click(
    screen.getByRole("button", { name: "Export test plan CSV" }),
  );
  expect(download).toHaveBeenCalledWith(
    "title,status\nCase,proposed",
    "test-plan.csv",
  );
});

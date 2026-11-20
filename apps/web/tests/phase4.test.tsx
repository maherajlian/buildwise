import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Specifications } from "@/components/specifications";
import { BuildPlan } from "@/components/build-plan";
import { Workspace } from "@/components/workspace";
import { api, ApiError } from "@/lib/api";
import * as downloads from "@/lib/download";
import { artefact, plan } from "./phase4-fixtures";
import { navigation } from "./navigation";

beforeEach(() => {
  vi.spyOn(api, "artefacts").mockResolvedValue([artefact]);
  vi.spyOn(api, "plan").mockResolvedValue(plan);
  vi.spyOn(downloads, "downloadMarkdown").mockImplementation(() => {});
});

it("retries Specs load errors, generates from empty context and displays save errors", async () => {
  const user = userEvent.setup();
  vi.mocked(api.artefacts)
    .mockRejectedValueOnce(new ApiError("Specs unavailable"))
    .mockResolvedValueOnce([]);
  vi.spyOn(api, "generateArtefacts").mockResolvedValue([artefact]);
  vi.spyOn(api, "updateArtefact").mockRejectedValue(
    new ApiError("Cannot save artefact"),
  );
  render(<Specifications projectId="p1" readOnly={false} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Specs unavailable",
  );
  await user.click(screen.getByRole("button", { name: "Retry loading" }));
  await screen.findByText(/No specifications yet/);
  await user.click(
    screen.getByRole("button", {
      name: "Generate specifications",
    }),
  );
  await screen.findByLabelText("Artefact title");
  await user.click(screen.getByRole("button", { name: "Save artefact" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Cannot save artefact",
  );
});

it("renders Specs, edits and saves sections and downloads token-authenticated Markdown", async () => {
  const user = userEvent.setup();
  const save = vi
    .spyOn(api, "updateArtefact")
    .mockResolvedValue({ ...artefact, edited: true, updated_at: "later" });
  vi.spyOn(api, "artefactMarkdown").mockResolvedValue("# Orbit\nProblem");
  vi.spyOn(api, "allArtefactsMarkdown").mockResolvedValue(
    "# Orbit\nAll sections",
  );
  render(<Specifications projectId="p1" readOnly={false} />);
  await user.clear(await screen.findByLabelText("Problem"));
  await user.type(screen.getByLabelText("Problem"), "Reviewed problem");
  expect(
    screen.getByRole("heading", { name: "Markdown preview · unsaved draft" }),
  ).toBeVisible();
  expect(
    within(screen.getByRole("region", { name: "Markdown preview" })).getByText(
      "Reviewed problem",
    ),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Save artefact" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Artefact saved");
  expect(save).toHaveBeenCalledWith(expect.any(String), "p1", "a1", {
    title: artefact.title,
    sections: [
      { ...artefact.sections[0], body: "Reviewed problem" },
      artefact.sections[1],
    ],
  });
  expect(screen.getAllByText("Edited").length).toBeGreaterThan(0);
  expect(
    screen.getByRole("heading", { name: "Markdown preview" }),
  ).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Download this artefact .md" }),
  );
  expect(api.artefactMarkdown).toHaveBeenCalledWith(
    expect.any(String),
    "p1",
    "a1",
  );
  await user.click(
    screen.getByRole("button", { name: "Download all artefacts .md" }),
  );
  expect(downloads.downloadMarkdown).toHaveBeenLastCalledWith(
    "# Orbit\nAll sections",
    "specifications.md",
  );
});

it("generates, confirms destructive regeneration, adds and deletes ADRs", async () => {
  const user = userEvent.setup();
  const generate = vi
    .spyOn(api, "generateArtefacts")
    .mockResolvedValue([artefact]);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  vi.spyOn(api, "createADR").mockResolvedValue({
    ...artefact,
    id: "adr1",
    kind: "adr",
    title: "Storage decision",
    edited: true,
  });
  vi.spyOn(api, "deleteArtefact").mockResolvedValue(undefined);
  render(<Specifications projectId="p1" readOnly={false} />);
  await user.click(
    await screen.findByRole("button", { name: "Regenerate specifications" }),
  );
  expect(generate).toHaveBeenLastCalledWith(expect.any(String), "p1", false);
  await user.click(
    screen.getByRole("button", { name: "Overwrite edited artefacts…" }),
  );
  expect(generate).toHaveBeenCalledTimes(1);
  confirm.mockReturnValue(true);
  await user.click(
    screen.getByRole("button", { name: "Overwrite edited artefacts…" }),
  );
  expect(generate).toHaveBeenLastCalledWith(expect.any(String), "p1", true);
  await user.type(screen.getByLabelText("New ADR title"), "Storage decision");
  await user.click(screen.getByRole("button", { name: "Add ADR" }));
  expect(await screen.findByLabelText("Artefact title")).toHaveValue(
    "Storage decision",
  );
  await user.click(screen.getByRole("button", { name: "Delete ADR" }));
  expect(api.deleteArtefact).toHaveBeenCalledWith(
    expect.any(String),
    "p1",
    "adr1",
  );
});

it("shows readable sample Specs and Plan without writes or tokens", async () => {
  const user = userEvent.setup();
  const { unmount } = render(<Specifications projectId="p1" readOnly />);
  await screen.findByRole("region", { name: "Selected artefact" });
  expect(api.artefacts).toHaveBeenCalledWith(undefined, "p1");
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Generate|ADR/ }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByText("Generated project context"));
  expect(screen.getByText(/Orbit — Coordinate launches/)).toBeVisible();
  unmount();
  render(<BuildPlan projectId="p1" readOnly />);
  await screen.findByText("T-001: Setup");
  expect(api.plan).toHaveBeenCalledWith(undefined, "p1");
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Generate|Edit|Add|Delete/ }),
  ).not.toBeInTheDocument();
});

it("edits task planning fields and saves; status validation errors stay inline; exports", async () => {
  const user = userEvent.setup();
  const update = vi.spyOn(api, "updateTask").mockResolvedValue(plan.tasks[0]);
  vi.spyOn(api, "planMarkdown").mockResolvedValue("# Orbit — Build plan");
  render(<BuildPlan projectId="p1" readOnly={false} />);
  await user.click(await screen.findByRole("button", { name: "Edit T-001" }));
  await user.clear(screen.getByLabelText("Task title"));
  await user.type(screen.getByLabelText("Task title"), "Reviewed setup");
  await user.selectOptions(
    screen.getByLabelText("Priority", { exact: true }),
    "P2",
  );
  await user.selectOptions(
    screen.getByLabelText("Dependencies (select multiple)"),
    "t2",
  );
  await user.clear(
    screen.getByLabelText("Implementation notes", { exact: true }),
  );
  await user.type(
    screen.getByLabelText("Implementation notes", { exact: true }),
    "Human notes",
  );
  await user.click(screen.getByRole("button", { name: "Save task" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Task saved");
  expect(update).toHaveBeenCalledWith(
    expect.any(String),
    "p1",
    "t1",
    expect.objectContaining({
      title: "Reviewed setup",
      priority: "P2",
      depends_on: ["t2"],
      implementation_notes: "Human notes",
      acceptance_criteria: ["Checks pass"],
    }),
  );
  update.mockRejectedValueOnce(
    new ApiError(
      "T-002: all dependencies must be done before in_progress",
      undefined,
      [],
      422,
    ),
  );
  await user.selectOptions(
    screen.getByLabelText("Status for T-002"),
    "in_progress",
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "all dependencies must be done",
  );
  expect(screen.getByLabelText("Status for T-002")).toHaveValue("backlog");
  await user.click(
    screen.getByRole("button", { name: "Export plan Markdown" }),
  );
  expect(downloads.downloadMarkdown).toHaveBeenCalledWith(
    "# Orbit — Build plan",
    "build-plan.md",
  );
});

it("handles empty/error states, retries and creates and deletes tasks", async () => {
  const user = userEvent.setup();
  vi.mocked(api.plan)
    .mockRejectedValueOnce(new ApiError("Plan unavailable"))
    .mockResolvedValueOnce({
      epics: [],
      tasks: [],
      validation: { valid: true, errors: [] },
    });
  vi.spyOn(api, "generatePlan").mockResolvedValue(plan);
  vi.spyOn(api, "createTask").mockResolvedValue(plan.tasks[0]);
  vi.spyOn(api, "deleteTask").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<BuildPlan projectId="p1" readOnly={false} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Plan unavailable",
  );
  await user.click(screen.getByRole("button", { name: "Retry loading" }));
  await screen.findByText(/No tasks yet/);
  await user.click(screen.getByRole("button", { name: "Generate plan" }));
  await screen.findByText("T-001: Setup");
  await user.click(screen.getByRole("button", { name: "Add task" }));
  await user.type(screen.getByLabelText("Task title"), "New work");
  await user.click(screen.getByRole("button", { name: "Create task" }));
  expect(api.createTask).toHaveBeenCalledWith(
    expect.any(String),
    "p1",
    expect.objectContaining({ title: "New work" }),
  );
  await screen.findByText("Task added.");
  await user.click(screen.getByRole("button", { name: "Delete T-001" }));
  expect(api.deleteTask).toHaveBeenCalledWith(expect.any(String), "p1", "t1");
});

it.each(["specs", "plan"])(
  "supports the %s workspace deep link",
  async (tab) => {
    navigation.params = new URLSearchParams(`id=sample&tab=${tab}`);
    vi.spyOn(api, "sample").mockResolvedValue({
      id: "p1",
      name: "Orbit",
      description: "Sample",
      is_sample: true,
      status: "active",
      created_at: "now",
      updated_at: "now",
    });
    render(<Workspace />);
    expect(
      await screen.findByRole("tab", {
        name: tab === "specs" ? "Specs" : "Plan",
      }),
    ).toHaveAttribute("aria-selected", "true");
    await screen.findByRole("heading", {
      name: tab === "specs" ? "Specifications" : "Build plan",
    });
  },
);

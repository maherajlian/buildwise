import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Workspace } from "@/components/workspace";
import {
  api,
  ApiError,
  type Discovery,
  type Project,
  type ProjectOverview,
  type Requirement,
} from "@/lib/api";
import { navigation } from "./navigation";

const project: Project = {
  id: "p1",
  name: "Booking platform",
  description: "Tables",
  status: "draft",
  is_sample: false,
  created_at: "2026-11-20T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
};
const steps = [
  { id: "problem", title: "Problem", fields: ["problem_statement"] },
  { id: "users", title: "Users", fields: ["target_users", "user_needs"] },
];
const emptyAnswers = {
  problem_statement: "",
  target_users: [],
  user_needs: [],
  goals: [],
  success_metrics: [],
  in_scope: [],
  out_of_scope: [],
  constraints: [],
  integrations: [],
  assumptions: [],
  risks: [],
  open_questions: [],
};
const discovery: Discovery = {
  answers: emptyAnswers,
  current_step: "problem",
  steps,
  completed_steps: [],
  updated_at: null,
};
const overview: ProjectOverview = {
  project,
  discovery_steps: ["problem", "users"],
  discovery_completed: [],
  discovery_updated_at: null,
  requirements: {
    total: 0,
    functional: 0,
    non_functional: 0,
    proposed: 0,
    confirmed: 0,
    deferred: 0,
    p0: 0,
  },
  open_questions: [],
  assumptions: [],
  missing: ["Discovery: Problem"],
};
const requirement: Requirement = {
  id: "r1",
  project_id: "p1",
  type: "functional",
  title: "Book a table",
  description: "",
  priority: "P0",
  status: "proposed",
  acceptance_criteria: ["Booking confirmed"],
  created_at: "2026-11-20T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
};

function open(query: string) {
  navigation.params = new URLSearchParams(query);
}

describe("project workspace", () => {
  beforeEach(() => {
    vi.spyOn(api, "overview").mockResolvedValue(overview);
  });
  it("edits a project and shows server field errors", async () => {
    open("id=p1");
    vi.spyOn(api, "project").mockResolvedValue(project);
    const update = vi
      .spyOn(api, "updateProject")
      .mockRejectedValueOnce(
        new ApiError("description: too long", "c1", [
          {
            field: "description",
            message: "String should have at most 10000 characters",
          },
        ]),
      )
      .mockResolvedValueOnce({ ...project, name: "Renamed", status: "active" });
    const user = userEvent.setup();
    render(<Workspace />);
    const name = await screen.findByLabelText(/Project name/);
    expect(await screen.findByText("Discovery: Problem")).toBeInTheDocument();
    await user.clear(name);
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(
      await screen.findByText("Enter a project name."),
    ).toBeInTheDocument();
    expect(update).not.toHaveBeenCalled();
    await user.type(name, "Renamed");
    await user.selectOptions(screen.getByLabelText("Status"), "active");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(
      await screen.findByText("String should have at most 10000 characters"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Renamed" }),
    ).toBeInTheDocument();
    expect(update).toHaveBeenLastCalledWith(expect.any(String), "p1", {
      name: "Renamed",
      description: "Tables",
      status: "active",
    });
    expect(screen.getByText("Project saved.")).toBeInTheDocument();
  });
  it("deletes a project after confirmation", async () => {
    open("id=p1");
    vi.spyOn(api, "project").mockResolvedValue(project);
    const remove = vi.spyOn(api, "deleteProject").mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<Workspace />);
    await user.click(
      await screen.findByRole("button", { name: /Delete project/ }),
    );
    await user.click(screen.getByRole("button", { name: "Confirm delete" }));
    expect(remove).toHaveBeenCalledWith(expect.any(String), "p1");
    expect(navigation.push).toHaveBeenCalledWith("/projects/");
  });
  it("explains a missing project", async () => {
    open("id=gone");
    vi.spyOn(api, "project").mockRejectedValue(
      new ApiError("Project not found", "nf", [], 404),
    );
    render(<Workspace />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "expired after 30 days",
    );
  });
  it("saves discovery progress and resumes on the saved step", async () => {
    open("id=p1&tab=discovery");
    vi.spyOn(api, "project").mockResolvedValue(project);
    vi.spyOn(api, "discovery").mockResolvedValue(discovery);
    const save = vi.spyOn(api, "saveDiscovery").mockResolvedValue({
      ...discovery,
      answers: { ...emptyAnswers, problem_statement: "No-shows" },
      current_step: "users",
      completed_steps: ["problem"],
      updated_at: "2026-11-20T01:00:00Z",
    });
    const user = userEvent.setup();
    render(<Workspace />);
    await user.type(
      await screen.findByLabelText(/Problem statement/),
      " No-shows ",
    );
    await user.click(screen.getByRole("button", { name: /Save and continue/ }));
    expect(
      await screen.findByRole("heading", { name: "Step 2 of 3: Users" }),
    ).toBeInTheDocument();
    expect(save).toHaveBeenCalledWith(expect.any(String), "p1", {
      answers: { ...emptyAnswers, problem_statement: "No-shows" },
      current_step: "users",
    });
    await user.type(screen.getByLabelText(/Target users/), "Owners\n\nDiners");
    await user.click(screen.getByRole("button", { name: /Save draft/ }));
    expect(save).toHaveBeenLastCalledWith(expect.any(String), "p1", {
      answers: expect.objectContaining({ target_users: ["Owners", "Diners"] }),
      current_step: "users",
    });
    expect(screen.getByRole("tab", { name: "Discovery" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
  it("adds, edits and validates requirements", async () => {
    open("id=p1&tab=requirements");
    vi.spyOn(api, "project").mockResolvedValue(project);
    vi.spyOn(api, "requirements").mockResolvedValue([]);
    const create = vi
      .spyOn(api, "createRequirement")
      .mockResolvedValue(requirement);
    const update = vi
      .spyOn(api, "updateRequirement")
      .mockResolvedValue({ ...requirement, status: "confirmed" });
    const user = userEvent.setup();
    render(<Workspace />);
    expect(await screen.findByText("No requirements yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add requirement" }));
    expect(screen.getByText("Enter a title.")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText(/Title/), "Book a table");
    await user.selectOptions(screen.getByLabelText("Priority"), "P0");
    await user.type(
      screen.getByLabelText("Acceptance criteria"),
      "Booking confirmed",
    );
    await user.click(screen.getByRole("button", { name: "Add requirement" }));
    expect(create).toHaveBeenCalledWith(expect.any(String), "p1", {
      type: "functional",
      title: "Book a table",
      description: "",
      priority: "P0",
      status: "proposed",
      acceptance_criteria: ["Booking confirmed"],
    });
    const item = (
      await screen.findByRole("heading", { name: "Book a table" })
    ).closest("li") as HTMLElement;
    await user.click(
      within(item).getByRole("button", { name: "Edit Book a table" }),
    );
    await user.selectOptions(screen.getByLabelText("Status"), "confirmed");
    await user.click(screen.getByRole("button", { name: "Save requirement" }));
    expect(update).toHaveBeenCalledWith(
      expect.any(String),
      "p1",
      "r1",
      expect.objectContaining({ status: "confirmed" }),
    );
    expect(await screen.findByText("confirmed")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Show"), "non_functional");
    expect(screen.getByText("No matching requirements")).toBeInTheDocument();
  });
  it("shows the sample read-only", async () => {
    open("id=sample&tab=requirements");
    vi.spyOn(api, "sample").mockResolvedValue({
      ...project,
      id: "s1",
      name: "Sample (illustrative sample)",
      is_sample: true,
    });
    vi.spyOn(api, "requirements").mockResolvedValue([requirement]);
    render(<Workspace />);
    expect(await screen.findByRole("note")).toHaveTextContent(
      "Illustrative sample, read-only",
    );
    expect(await screen.findByText("Book a table")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Edit/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Add a requirement")).not.toBeInTheDocument();
  });
});

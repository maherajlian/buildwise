import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Projects } from "@/components/projects";
import { api, ApiError, type Project } from "@/lib/api";
import { getProjectToken } from "@/lib/token";

const project: Project = {
  id: "one",
  name: "Booking platform",
  description: "A useful system",
  status: "draft",
  is_sample: false,
  created_at: "2026-11-20T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
};
describe("projects", () => {
  it("shows an empty workspace and creates a browser-owned project", async () => {
    vi.spyOn(api, "projects").mockResolvedValue({
      items: [],
      next_cursor: null,
    });
    vi.spyOn(api, "createProject").mockResolvedValue(project);
    const user = userEvent.setup();
    render(<Projects />);
    expect(await screen.findByText("No projects yet")).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Project name/), project.name);
    await user.click(screen.getByRole("button", { name: "Create project" }));
    expect(
      await screen.findByRole("heading", { name: project.name }),
    ).toBeInTheDocument();
    expect(api.createProject).toHaveBeenCalledWith(
      expect.stringMatching(/^[A-Za-z0-9_-]{43}$/),
      {
        name: project.name,
        description: "",
      },
    );
    expect(screen.getByLabelText(/Project name/)).toHaveValue("");
  });
  it("loads existing projects and another page", async () => {
    getProjectToken();
    vi.spyOn(api, "projects")
      .mockResolvedValueOnce({ items: [project], next_cursor: "next" })
      .mockResolvedValueOnce({
        items: [{ ...project, id: "two", name: "Second project" }],
        next_cursor: null,
      });
    render(<Projects />);
    expect(
      await screen.findByRole("heading", { name: project.name }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(
      await screen.findByRole("heading", { name: "Second project" }),
    ).toBeInTheDocument();
    expect(api.projects).toHaveBeenLastCalledWith(expect.any(String), "next");
    expect(
      screen.queryByRole("button", { name: "Load more" }),
    ).not.toBeInTheDocument();
  });
  it("shows standard load errors and lets the user retry", async () => {
    getProjectToken();
    vi.spyOn(api, "projects")
      .mockRejectedValueOnce(new ApiError("Database unavailable", "load-id"))
      .mockResolvedValueOnce({ items: [], next_cursor: null });
    render(<Projects />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Database unavailable",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("load-id");
    await userEvent.click(
      screen.getByRole("button", { name: "Retry loading projects" }),
    );
    expect(await screen.findByText("No projects yet")).toBeInTheDocument();
  });
  it("preserves form input on a create error and shows its correlation ID", async () => {
    vi.spyOn(api, "projects").mockResolvedValue({
      items: [],
      next_cursor: null,
    });
    vi.spyOn(api, "createProject").mockRejectedValue(
      new ApiError("Try again", "create-id"),
    );
    render(<Projects />);
    await screen.findByText("No projects yet");
    await userEvent.type(screen.getByLabelText(/Project name/), project.name);
    await userEvent.click(
      screen.getByRole("button", { name: "Create project" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("create-id");
    expect(screen.getByLabelText(/Project name/)).toHaveValue(project.name);
  });
  it("explains why an empty project name cannot be created", async () => {
    vi.spyOn(api, "projects").mockResolvedValue({
      items: [],
      next_cursor: null,
    });
    const create = vi.spyOn(api, "createProject");
    render(<Projects />);
    await screen.findByText("No projects yet");
    await userEvent.type(screen.getByLabelText(/Project name/), "   ");
    await userEvent.click(
      screen.getByRole("button", { name: "Create project" }),
    );
    expect(
      await screen.findByText("Enter a project name."),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Project name is required.",
    );
    expect(screen.getByLabelText(/Project name/)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(create).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("button", { name: "Retry loading projects" }),
    ).not.toBeInTheDocument();
  });
  it("links to project workspaces and the sample", async () => {
    getProjectToken();
    vi.spyOn(api, "projects").mockResolvedValue({
      items: [project],
      next_cursor: null,
    });
    render(<Projects />);
    expect(
      await screen.findByRole("link", { name: project.name }),
    ).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/projects\/view\/?\?id=one$/),
    );
    expect(
      screen.getByRole("link", { name: "View sample project" }),
    ).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/projects\/view\/?\?id=sample$/),
    );
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Architecture } from "@/components/architecture";
import { Workspace } from "@/components/workspace";
import { api, ApiError } from "@/lib/api";
import { inputs, recommendations } from "./recommendation-fixtures";
import { navigation } from "./navigation";

beforeEach(() => {
  vi.spyOn(api, "recommendations").mockResolvedValue(recommendations);
  vi.spyOn(api, "recommendationInputs").mockResolvedValue(inputs);
});

describe("Architecture", () => {
  it("explains positive/negative rules, sources, evidence, alternatives and optional AI", async () => {
    const user = userEvent.setup();
    render(<Architecture projectId="p1" readOnly />);
    expect(await screen.findByText("Catalogue 2026.11.2")).toBeInTheDocument();
    expect(screen.getByText("a".repeat(64))).toBeInTheDocument();
    expect(screen.getByText(recommendations.disclaimer)).toBeInTheDocument();
    expect(screen.getByText(recommendations.notes[0])).toBeInTheDocument();
    expect(screen.getAllByText("Positive matches").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Negative matches").length).toBeGreaterThan(0);
    for (const source of ["explicit", "detected", "default"])
      expect(screen.getAllByText(source).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("“A low budget for launch”").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("discovery.constraints[0]").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText(/verify pricing/).length).toBeGreaterThan(0);
    expect(
      screen.getByText("Not recommended · Optional, may incur cost"),
    ).toBeInTheDocument();
    await user.click(screen.getByText("Alternatives (1)"));
    expect(
      screen.getByText("Ranked below postgresql: score 0 versus 15."),
    ).toBeVisible();
    expect(
      screen.getByText("Document relationships require care."),
    ).toBeVisible();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Save inputs" }),
    ).not.toBeInTheDocument();
  });
  it("saves overrides, integrations and Auto, then refreshes recommendations", async () => {
    const save = vi
      .spyOn(api, "saveRecommendationInputs")
      .mockResolvedValue(inputs);
    const user = userEvent.setup();
    render(<Architecture projectId="p1" readOnly={false} />);
    await user.selectOptions(
      await screen.findByLabelText("Budget override"),
      "zero",
    );
    await user.selectOptions(
      screen.getByLabelText("Integrations override"),
      "explicit",
    );
    await user.click(screen.getByLabelText("email", { exact: true }));
    await user.click(screen.getByRole("button", { name: "Save inputs" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Inputs saved. Recommendations updated.",
    );
    expect(save).toHaveBeenLastCalledWith(expect.any(String), "p1", {
      budget: "zero",
      integrations: ["email"],
    });
    expect(api.recommendations).toHaveBeenCalledTimes(2);
    await user.selectOptions(screen.getByLabelText("Budget override"), "auto");
    await user.selectOptions(
      screen.getByLabelText("Integrations override"),
      "auto",
    );
    await user.click(screen.getByRole("button", { name: "Save inputs" }));
    expect(save).toHaveBeenLastCalledWith(expect.any(String), "p1", {});
  });
  it("handles load errors, retry, save errors and empty results", async () => {
    vi.mocked(api.recommendations).mockRejectedValueOnce(
      new ApiError("API unavailable"),
    );
    const user = userEvent.setup();
    render(<Architecture projectId="p1" readOnly={false} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "API unavailable",
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByLabelText("Budget override");
    vi.spyOn(api, "saveRecommendationInputs").mockRejectedValueOnce(
      new ApiError("Cannot save inputs"),
    );
    await user.click(screen.getByRole("button", { name: "Save inputs" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cannot save inputs",
    );
    vi.mocked(api.recommendations).mockResolvedValue({
      ...recommendations,
      recommendations: [],
      notes: [],
    });
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByText("No recommendations available for these inputs."),
    ).toBeInTheDocument();
  });
  it("supports the workspace deep link and keyboard tab navigation", async () => {
    navigation.params = new URLSearchParams("id=sample&tab=architecture");
    vi.spyOn(api, "sample").mockResolvedValue({
      id: "s1",
      name: "Sample",
      description: "Read only",
      status: "active",
      is_sample: true,
      created_at: "2026-11-20",
      updated_at: "2026-11-20",
    });
    vi.spyOn(api, "requirements").mockResolvedValue([]);
    const user = userEvent.setup();
    render(<Workspace />);
    await screen.findByRole("heading", { name: "Technology recommendations" });
    const tabs = screen.getByRole("tablist");
    const tab = within(tabs).getByRole("tab", { name: "Architecture" });
    expect(tab).toHaveAttribute("aria-selected", "true");
    tab.focus();
    await user.keyboard("{ArrowLeft}");
    expect(
      within(tabs).getByRole("tab", { name: "Requirements" }),
    ).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(tab).toHaveFocus();
    expect(navigation.replace).toHaveBeenLastCalledWith(
      "/projects/view/?id=sample&tab=architecture",
      { scroll: false },
    );
  });
});

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TechnologyCatalogue } from "@/components/catalogue";
import { api, ApiError } from "@/lib/api";
import { catalogue } from "./recommendation-fixtures";

describe("technology catalogue", () => {
  it("reads the catalogue and renders categories, review dates and trade-offs", async () => {
    vi.spyOn(api, "catalogue").mockResolvedValue(catalogue);
    render(<TechnologyCatalogue />);
    expect(await screen.findByText("Catalogue 2026.11.2")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "PostgreSQL" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "AI layer" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Last reviewed:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Strengths").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Constraints").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/verify pricing/).length).toBeGreaterThan(0);
  });
  it("shows a recoverable error and an empty catalogue", async () => {
    vi.spyOn(api, "catalogue")
      .mockRejectedValueOnce(new ApiError("Catalogue unavailable"))
      .mockResolvedValue({ ...catalogue, categories: [], entries: [] });
    const user = userEvent.setup();
    render(<TechnologyCatalogue />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Catalogue unavailable",
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByText("No technologies available yet."),
    ).toBeInTheDocument();
  });
});

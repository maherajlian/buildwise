import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ApiStatus } from "@/components/api-status";
import { api, ApiError } from "@/lib/api";
describe("API status", () => {
  it("shows checking until both health and database respond", async () => {
    let ready!: (value: Record<string, string>) => void;
    vi.spyOn(api, "health").mockResolvedValue({ status: "ok" });
    vi.spyOn(api, "ready").mockImplementation(
      () =>
        new Promise((resolve) => {
          ready = resolve;
        }),
    );
    render(<ApiStatus />);
    expect(screen.getByText("Checking API status")).toBeInTheDocument();
    ready({ status: "ready" });
    expect(await screen.findByText("All systems ready")).toBeInTheDocument();
  });
  it("explains cold starts and recovers on a bounded retry", async () => {
    vi.spyOn(api, "health").mockResolvedValue({ status: "ok" });
    vi.spyOn(api, "ready")
      .mockRejectedValueOnce(new ApiError("Unavailable"))
      .mockResolvedValue({ status: "ready" });
    render(<ApiStatus retryMs={50} />);
    expect(await screen.findByText("Waking the API")).toBeInTheDocument();
    expect(screen.getByText(/Free tier can take ~1 min/)).toBeInTheDocument();
    expect(await screen.findByText("All systems ready")).toBeInTheDocument();
    expect(api.ready).toHaveBeenCalledTimes(2);
  });
  it("stops automatic retries and displays the correlation ID", async () => {
    vi.spyOn(api, "health").mockResolvedValue({ status: "ok" });
    vi.spyOn(api, "ready").mockRejectedValue(
      new ApiError("Service unavailable", "correlation-123"),
    );
    render(<ApiStatus attempts={2} retryMs={1} />);
    await waitFor(() =>
      expect(screen.getByText("API currently unavailable")).toBeInTheDocument(),
    );
    expect(screen.getByText(/correlation-123/)).toBeInTheDocument();
    expect(api.ready).toHaveBeenCalledTimes(2);
  });
  it("aborts requests when unmounted", () => {
    let signal: AbortSignal | undefined;
    vi.spyOn(api, "health").mockImplementation((s) => {
      signal = s;
      return new Promise(() => {});
    });
    vi.spyOn(api, "ready").mockImplementation(() => new Promise(() => {}));
    const view = render(<ApiStatus />);
    view.unmount();
    expect(signal?.aborted).toBe(true);
  });
});

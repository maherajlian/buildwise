import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
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
  it("bounds each retry burst and displays the correlation ID", async () => {
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

  describe("visible-page monitoring", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.spyOn(document, "hidden", "get").mockReturnValue(false);
      vi.spyOn(api, "health").mockResolvedValue({ status: "ok" });
      vi.spyOn(api, "ready").mockResolvedValue({ status: "ready" });
    });
    afterEach(() => vi.useRealTimers());

    async function advance(ms = 0) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(ms);
      });
    }

    it("rechecks ready status, bounds retries, and recovers without manual Retry", async () => {
      render(<ApiStatus attempts={2} retryMs={1000} />);
      await advance();
      expect(screen.getByText("All systems ready")).toBeInTheDocument();
      vi.mocked(api.ready).mockRejectedValue(new ApiError("Database offline"));
      await advance(29999);
      expect(api.ready).toHaveBeenCalledTimes(1);
      await advance(1);
      expect(screen.getByText("Waking the API")).toBeInTheDocument();
      await advance(1000);
      expect(screen.getByText("API currently unavailable")).toBeInTheDocument();
      expect(api.ready).toHaveBeenCalledTimes(3);
      vi.mocked(api.ready).mockResolvedValue({ status: "ready" });
      await advance(30000);
      expect(screen.getByText("All systems ready")).toBeInTheDocument();
      expect(api.ready).toHaveBeenCalledTimes(4);
    });

    it("does not probe while hidden, resumes on visibility/focus, and cleans up", async () => {
      const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(true);
      const view = render(<ApiStatus />);
      await advance(90000);
      expect(api.health).not.toHaveBeenCalled();
      hidden.mockReturnValue(false);
      fireEvent(document, new Event("visibilitychange"));
      await advance();
      expect(screen.getByText("All systems ready")).toBeInTheDocument();
      hidden.mockReturnValue(true);
      fireEvent(document, new Event("visibilitychange"));
      fireEvent(window, new Event("focus"));
      await advance(90000);
      expect(api.health).toHaveBeenCalledTimes(1);
      hidden.mockReturnValue(false);
      fireEvent(document, new Event("visibilitychange"));
      await advance();
      expect(api.health).toHaveBeenCalledTimes(2);
      fireEvent(window, new Event("focus"));
      await advance();
      expect(api.health).toHaveBeenCalledTimes(3);
      view.unmount();
      fireEvent(window, new Event("focus"));
      fireEvent(document, new Event("visibilitychange"));
      await advance(90000);
      expect(api.health).toHaveBeenCalledTimes(3);
      expect(vi.getTimerCount()).toBe(0);
    });

    it("waits for both probes to settle and coalesces focus events", async () => {
      let finishHealth!: (value: Record<string, string>) => void;
      vi.mocked(api.health).mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finishHealth = resolve;
          }),
      );
      vi.mocked(api.ready).mockRejectedValue(new ApiError("Offline"));
      render(<ApiStatus timeoutMs={120000} />);
      fireEvent(window, new Event("focus"));
      fireEvent(document, new Event("visibilitychange"));
      await advance(60000);
      expect(api.health).toHaveBeenCalledTimes(1);
      expect(api.ready).toHaveBeenCalledTimes(1);
      await act(async () => {
        finishHealth({ status: "ok" });
      });
      expect(screen.getByText("Waking the API")).toBeInTheDocument();
    });

    it("ignores a hidden probe's stale result and resumes after it settles", async () => {
      let finish!: (value: Record<string, string>) => void;
      let signal: AbortSignal | undefined;
      vi.mocked(api.ready).mockImplementationOnce((s) => {
        signal = s;
        return new Promise((resolve) => {
          finish = resolve;
        });
      });
      render(<ApiStatus />);
      const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(true);
      fireEvent(document, new Event("visibilitychange"));
      expect(signal?.aborted).toBe(true);
      hidden.mockReturnValue(false);
      fireEvent(document, new Event("visibilitychange"));
      fireEvent(window, new Event("focus"));
      expect(api.ready).toHaveBeenCalledTimes(1);
      await act(async () => {
        finish({ status: "ready" });
      });
      expect(api.ready).toHaveBeenCalledTimes(2);
      expect(screen.getByText("All systems ready")).toBeInTheDocument();
    });

    it("handles health failures and retains manual Retry", async () => {
      vi.mocked(api.health).mockRejectedValue(new ApiError("Health offline"));
      render(<ApiStatus attempts={1} />);
      await advance();
      expect(screen.getByText("API currently unavailable")).toBeInTheDocument();
      vi.mocked(api.health).mockResolvedValue({ status: "ok" });
      fireEvent.click(screen.getByRole("button", { name: "Retry" }));
      await advance();
      expect(screen.getByText("All systems ready")).toBeInTheDocument();
      expect(api.health).toHaveBeenCalledTimes(2);
    });

    it("times out hung requests and resumes periodic recovery", async () => {
      vi.mocked(api.ready).mockImplementationOnce(
        (signal) =>
          new Promise((_, reject) => {
            signal?.addEventListener(
              "abort",
              () => reject(new ApiError("Timed out")),
              { once: true },
            );
          }),
      );
      render(<ApiStatus attempts={1} timeoutMs={1000} />);
      await advance(1000);
      expect(screen.getByText("API currently unavailable")).toBeInTheDocument();
      await advance(30000);
      expect(screen.getByText("All systems ready")).toBeInTheDocument();
    });
  });
});

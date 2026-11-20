"use client";
import { useEffect, useRef, useState } from "react";
import { Activity, ArrowRight, RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export type ServiceState = "checking" | "waking" | "ready" | "unavailable";
const titles: Record<ServiceState, string> = {
  checking: "Checking API status",
  waking: "Waking the API",
  ready: "All systems ready",
  unavailable: "API currently unavailable",
};
export function ApiStatus({
  attempts = 4,
  retryMs = 5000,
  timeoutMs = 15000,
}: {
  attempts?: number;
  retryMs?: number;
  timeoutMs?: number;
}) {
  const [state, setState] = useState<ServiceState>("checking");
  const [error, setError] = useState<ApiError>();
  const recheck = useRef(() => {});
  useEffect(() => {
    let disposed = false;
    let attempt = 0;
    let revision = 0;
    let inFlight = false;
    let resumeWhenSettled = false;
    let active: AbortController | undefined;
    let scheduled: ReturnType<typeof setTimeout> | undefined;
    let timeout: ReturnType<typeof setTimeout> | undefined;

    function schedule(delay: number) {
      clearTimeout(scheduled);
      if (!disposed && !document.hidden)
        scheduled = setTimeout(() => void probe(), delay);
    }

    async function probe() {
      if (disposed || document.hidden || inFlight) return;
      inFlight = true;
      const startedRevision = revision;
      const controller = new AbortController();
      active = controller;
      timeout = setTimeout(() => controller.abort(), timeoutMs);
      const results = await Promise.allSettled([
        api.health(controller.signal),
        api.ready(controller.signal),
      ]);
      clearTimeout(timeout);
      controller.abort();
      active = undefined;
      inFlight = false;
      if (disposed) return;
      if (startedRevision !== revision) {
        if (resumeWhenSettled && !document.hidden) {
          resumeWhenSettled = false;
          void probe();
        }
        return;
      }
      const failure = results.find((result) => result.status === "rejected");
      if (!failure) {
        setState("ready");
        setError(undefined);
        attempt = 0;
        schedule(30000);
      } else {
        const cause: unknown = failure.reason;
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError("Cannot reach the API."),
        );
        attempt++;
        const exhausted = attempt >= attempts;
        setState(exhausted ? "unavailable" : "waking");
        if (exhausted) attempt = 0;
        schedule(exhausted ? 30000 : retryMs);
      }
    }

    function checkNow() {
      if (document.hidden || disposed) return;
      if (inFlight) {
        if (active?.signal.aborted) resumeWhenSettled = true;
        return;
      }
      clearTimeout(scheduled);
      attempt = 0;
      void probe();
    }

    function visibilityChanged() {
      if (document.hidden) {
        revision++;
        attempt = 0;
        resumeWhenSettled = false;
        clearTimeout(scheduled);
        clearTimeout(timeout);
        active?.abort();
      } else checkNow();
    }

    recheck.current = () => {
      if (document.hidden || inFlight) return;
      setState("checking");
      setError(undefined);
      checkNow();
    };
    document.addEventListener("visibilitychange", visibilityChanged);
    window.addEventListener("focus", checkNow);
    checkNow();
    return () => {
      disposed = true;
      clearTimeout(scheduled);
      clearTimeout(timeout);
      active?.abort();
      document.removeEventListener("visibilitychange", visibilityChanged);
      window.removeEventListener("focus", checkNow);
    };
  }, [attempts, retryMs, timeoutMs]);
  return (
    <section className="status-panel" aria-label="API status">
      <div className="flex items-center gap-3">
        <span className={`status-icon ${state === "ready" ? "ready" : ""}`}>
          <Activity size={20} />
        </span>
        <div aria-live="polite">
          <h2 className="font-semibold text-sm">{titles[state]}</h2>
          <p className="text-sm text-slate-500">
            {state === "ready"
              ? "API responding · Database connected"
              : state === "unavailable"
                ? "Will re-check automatically while this page is visible. Your work has not been changed."
                : "Free tier can take ~1 min. Retrying automatically with a fixed limit."}
          </p>
          {state === "unavailable" && error && (
            <p className="text-sm text-red-700">
              {error.message}
              {error.correlationId && (
                <> · Correlation ID: {error.correlationId}</>
              )}
            </p>
          )}
        </div>
      </div>
      {state === "unavailable" ? (
        <Button variant="outline" size="sm" onClick={() => recheck.current()}>
          <RefreshCw size={14} />
          Retry
        </Button>
      ) : (
        <span className="status-pill">
          {state === "ready" ? "Operational" : "Connecting"}
          <ArrowRight size={12} />
        </span>
      )}
    </section>
  );
}

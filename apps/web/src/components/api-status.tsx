"use client";
import { useEffect, useState } from "react";
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
  const [round, setRound] = useState(0);
  useEffect(() => {
    let disposed = false;
    const lifecycle = new AbortController();
    const active = new Set<AbortController>();
    async function run() {
      for (let attempt = 0; attempt < attempts; attempt++) {
        const controller = new AbortController();
        active.add(controller);
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
          await Promise.all([
            api.health(controller.signal),
            api.ready(controller.signal),
          ]);
          if (!disposed) {
            setState("ready");
            setError(undefined);
          }
          return;
        } catch (cause) {
          if (disposed) return;
          setError(
            cause instanceof ApiError
              ? cause
              : new ApiError("Cannot reach the API."),
          );
          setState(attempt === attempts - 1 ? "unavailable" : "waking");
        } finally {
          clearTimeout(timer);
          controller.abort();
          active.delete(controller);
        }
        if (attempt < attempts - 1)
          await new Promise<void>((resolve) => {
            const pause = setTimeout(resolve, retryMs);
            lifecycle.signal.addEventListener(
              "abort",
              () => {
                clearTimeout(pause);
                resolve();
              },
              { once: true },
            );
          });
        if (disposed) return;
      }
    }
    void run();
    return () => {
      disposed = true;
      lifecycle.abort();
      active.forEach((controller) => controller.abort());
    };
  }, [attempts, retryMs, timeoutMs, round]);
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
                ? "Automatic retries stopped. Your work has not been changed."
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
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setState("checking");
            setError(undefined);
            setRound((value) => value + 1);
          }}
        >
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

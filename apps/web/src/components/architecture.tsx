"use client";
import { useEffect, useState } from "react";
import {
  api,
  type ApiError,
  type RecommendationResult,
  type RecommendationInputs,
  type RecommendationOverrides,
} from "@/lib/api";
import { getProjectToken, readProjectToken } from "@/lib/token";
import { Button } from "@/components/ui/button";
import { ErrorBox, toApiError } from "@/components/form-error";
import {
  CATEGORY_LABELS,
  ScoredTechnology,
  SignalEvidence,
} from "@/components/technology";

const OPTIONS = {
  budget: ["zero", "low", "flexible"],
  scale: ["small", "medium", "large"],
  data_shape: ["relational", "document", "mixed"],
  background_jobs: ["yes", "no"],
  realtime: ["yes", "no"],
  auth_needs: ["none", "basic", "enterprise_sso"],
  ops_capability: ["low", "medium", "high"],
  ai_layer: ["not_needed", "required"],
} as const;
const INTEGRATIONS = [
  "payments",
  "email",
  "sms",
  "calendar",
  "maps",
  "generic_api",
] as const;

export function Architecture({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const [result, setResult] = useState<RecommendationResult>();
  const [inputs, setInputs] = useState<RecommendationInputs>();
  const [draft, setDraft] = useState<RecommendationOverrides>({});
  const [error, setError] = useState<ApiError>();
  const [attempt, setAttempt] = useState(0);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let disposed = false;
    async function load() {
      try {
        const token = readProjectToken();
        const [recommendations, values] = await Promise.all([
          api.recommendations(token, projectId),
          api.recommendationInputs(token, projectId),
        ]);
        if (!disposed) {
          setResult(recommendations);
          setInputs(values);
          setDraft(values.overrides as RecommendationOverrides);
          setError(undefined);
        }
      } catch (cause) {
        if (!disposed) setError(toApiError(cause));
      }
    }
    void load();
    return () => {
      disposed = true;
    };
  }, [projectId, attempt]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(undefined);
    setNotice("");
    try {
      const token = getProjectToken();
      const saved = await api.saveRecommendationInputs(token, projectId, draft);
      const recommendations = await api.recommendations(token, projectId);
      setInputs(saved);
      setResult(recommendations);
      setNotice("Inputs saved. Recommendations updated.");
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setSaving(false);
    }
  }
  function select(key: keyof RecommendationOverrides, value: string) {
    setNotice("");
    setDraft((previous) => {
      const next = { ...previous };
      if (value === "auto") delete next[key];
      else Object.assign(next, { [key]: value });
      return next;
    });
  }
  return (
    <div className="technology-page">
      <ErrorBox
        error={error}
        action="Retry"
        onAction={() => setAttempt((v) => v + 1)}
      />
      {!result || !inputs ? (
        !error && <p role="status">Loading architecture…</p>
      ) : (
        <>
          <section
            className="panel tech-panel"
            aria-labelledby="architecture-heading"
          >
            <div className="eyebrow">DETERMINISTIC DECISION SUPPORT</div>
            <h2 id="architecture-heading">Technology recommendations</h2>
            <div className="tech-badges">
              <span className="tech-badge">
                Catalogue {result.catalogue_version}
              </span>
              <span className="tech-badge">Rules {result.rules_version}</span>
            </div>
            <p className="fingerprint">
              <strong>Input fingerprint</strong>
              <code>{result.input_fingerprint}</code>
            </p>
            <p className="tech-disclaimer">{result.disclaimer}</p>
            {result.notes.length > 0 && (
              <div>
                <h3>Notes</h3>
                <ul className="plain-list">
                  {result.notes.map((note, i) => (
                    <li key={i}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
          <section
            className="panel tech-panel"
            aria-labelledby="inputs-heading"
          >
            <h2 id="inputs-heading">Inputs used</h2>
            <p>
              Auto uses discovery and requirements, then documented defaults.
              Only an explicit AI requirement enables optional AI candidates.
            </p>
            {readOnly && (
              <p className="tech-muted">Sample inputs are read-only.</p>
            )}
            <form onSubmit={save}>
              <fieldset disabled={saving} className="input-grid">
                <legend className="sr-only">Recommendation inputs</legend>
                {inputs.signals.map((signal) => (
                  <div className="input-signal" key={signal.id}>
                    <SignalEvidence signal={signal} />
                    {!readOnly &&
                      (signal.id === "integrations" ? (
                        <>
                          <label htmlFor="override-integrations">
                            Integrations override
                          </label>
                          <select
                            id="override-integrations"
                            value={
                              draft.integrations == null ? "auto" : "explicit"
                            }
                            onChange={(e) => {
                              setNotice("");
                              setDraft((previous) => {
                                const next = { ...previous };
                                if (e.target.value === "auto")
                                  delete next.integrations;
                                else next.integrations = [];
                                return next;
                              });
                            }}
                          >
                            <option value="auto">Auto</option>
                            <option value="explicit">
                              Choose integrations
                            </option>
                          </select>
                          {draft.integrations != null && (
                            <fieldset className="integration-options">
                              <legend>
                                Integration kinds (none is allowed)
                              </legend>
                              {INTEGRATIONS.map((kind) => (
                                <label key={kind}>
                                  <input
                                    type="checkbox"
                                    checked={
                                      draft.integrations?.includes(kind) ??
                                      false
                                    }
                                    onChange={(e) => {
                                      const checked = e.target.checked;
                                      setNotice("");
                                      setDraft((previous) => ({
                                        ...previous,
                                        integrations: checked
                                          ? [
                                              ...(previous.integrations ?? []),
                                              kind,
                                            ]
                                          : previous.integrations?.filter(
                                              (item) => item !== kind,
                                            ),
                                      }));
                                    }}
                                  />{" "}
                                  {kind}
                                </label>
                              ))}
                            </fieldset>
                          )}
                        </>
                      ) : (
                        <>
                          <label htmlFor={`override-${signal.id}`}>
                            {signal.label} override
                          </label>
                          <select
                            id={`override-${signal.id}`}
                            value={String(
                              draft[
                                signal.id as keyof RecommendationOverrides
                              ] ?? "auto",
                            )}
                            onChange={(e) =>
                              select(
                                signal.id as keyof RecommendationOverrides,
                                e.target.value,
                              )
                            }
                          >
                            <option value="auto">Auto</option>
                            {OPTIONS[signal.id as keyof typeof OPTIONS]?.map(
                              (value) => (
                                <option key={value} value={value}>
                                  {value}
                                </option>
                              ),
                            )}
                          </select>
                        </>
                      ))}
                  </div>
                ))}
              </fieldset>
              {!readOnly && (
                <Button type="submit" disabled={saving}>
                  {saving ? "Saving…" : "Save inputs"}
                </Button>
              )}
              <p role="status" className="save-notice">
                {notice}
              </p>
            </form>
          </section>
          {result.recommendations.length === 0 && (
            <p>No recommendations available for these inputs.</p>
          )}
          {result.recommendations.map((category) => (
            <section
              className="panel tech-panel"
              key={category.category}
              aria-labelledby={`category-${category.category}`}
            >
              <div className="eyebrow">
                {CATEGORY_LABELS[category.category]}
              </div>
              <h2 id={`category-${category.category}`}>
                {CATEGORY_LABELS[category.category]} recommendation
              </h2>
              <p>{category.explanation}</p>
              {category.status === "not_recommended" && (
                <p className="tech-disclaimer">
                  <strong>Not recommended · Optional, may incur cost</strong>
                </p>
              )}
              {category.recommendation && (
                <ScoredTechnology entry={category.recommendation} />
              )}
              {(category.alternatives.length > 0 ||
                category.candidates.length > 0) && (
                <details className="alternatives">
                  <summary>
                    {category.status === "not_recommended"
                      ? "Explore optional candidates"
                      : `Alternatives (${category.alternatives.length})`}
                  </summary>
                  {[...category.alternatives, ...category.candidates].map(
                    (entry) => (
                      <div className="alternative" key={entry.id}>
                        <ScoredTechnology entry={entry} />
                      </div>
                    ),
                  )}
                </details>
              )}
            </section>
          ))}
        </>
      )}
    </div>
  );
}

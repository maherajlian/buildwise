"use client";
import { useEffect, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Save } from "lucide-react";
import {
  api,
  ApiError,
  type Discovery,
  type DiscoveryAnswers,
  type DiscoveryWrite,
} from "@/lib/api";
import { getProjectToken, readProjectToken } from "@/lib/token";
import { Button } from "@/components/ui/button";
import { ErrorBox, lines, toApiError } from "@/components/form-error";

type Field = keyof DiscoveryAnswers;
type StepId = DiscoveryWrite["current_step"];
const FIELDS: Record<
  Field,
  { label: string; hint: string; required?: boolean }
> = {
  problem_statement: {
    label: "Problem statement",
    hint: "What problem are you solving, and for whom?",
    required: true,
  },
  target_users: {
    label: "Target users",
    hint: "One user group per line.",
    required: true,
  },
  user_needs: { label: "User needs", hint: "One need per line." },
  goals: { label: "Goals", hint: "One goal per line.", required: true },
  success_metrics: {
    label: "Success metrics",
    hint: "Measurable outcomes, one per line.",
  },
  in_scope: { label: "In scope", hint: "One item per line." },
  out_of_scope: { label: "Out of scope", hint: "One item per line." },
  constraints: {
    label: "Constraints",
    hint: "Budget, team, deadline, compliance, one per line.",
    required: true,
  },
  integrations: {
    label: "Integrations",
    hint: "External systems, one per line.",
  },
  assumptions: { label: "Assumptions", hint: "One assumption per line." },
  risks: { label: "Risks", hint: "One risk per line." },
  open_questions: {
    label: "Open questions",
    hint: "Things you still need to find out, one per line.",
  },
};
type Draft = Record<Field, string>;

function toDraft(answers: DiscoveryAnswers): Draft {
  return Object.fromEntries(
    (Object.keys(FIELDS) as Field[]).map((field) => {
      const value = answers[field];
      return [field, Array.isArray(value) ? value.join("\n") : value || ""];
    }),
  ) as Draft;
}
function toAnswers(draft: Draft): DiscoveryAnswers {
  return Object.fromEntries(
    (Object.keys(FIELDS) as Field[]).map((field) => [
      field,
      field === "problem_statement" ? draft[field].trim() : lines(draft[field]),
    ]),
  ) as unknown as DiscoveryAnswers;
}

export function DiscoveryWizard({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const [discovery, setDiscovery] = useState<Discovery>();
  const [draft, setDraft] = useState<Draft>();
  const [step, setStep] = useState<StepId>("problem");
  const [error, setError] = useState<ApiError>();
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");

  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let disposed = false;
    async function load() {
      try {
        const value = await api.discovery(readProjectToken(), projectId);
        if (disposed) return;
        setDiscovery(value);
        setDraft(toDraft(value.answers));
        setStep(value.current_step);
        setError(undefined);
      } catch (cause) {
        if (!disposed) setError(toApiError(cause));
      }
    }
    void load();
    return () => {
      disposed = true;
    };
  }, [projectId, attempt]);

  if (!discovery || !draft)
    return error ? (
      <ErrorBox
        error={error}
        action="Retry"
        onAction={() => setAttempt((value) => value + 1)}
      />
    ) : (
      <p role="status" className="text-sm text-slate-500">
        Loading discovery…
      </p>
    );

  const steps = [
    ...discovery.steps,
    { id: "review", title: "Review", fields: [] as string[] },
  ];
  const index = Math.max(
    0,
    steps.findIndex((item) => item.id === step),
  );
  const current = steps[index];

  async function save(next: StepId) {
    if (!draft) return;
    if (readOnly) {
      setStep(next);
      return;
    }
    setSaving(true);
    setError(undefined);
    setNotice("");
    try {
      const saved = await api.saveDiscovery(getProjectToken(), projectId, {
        answers: toAnswers(draft),
        current_step: next,
      });
      setDiscovery(saved);
      setStep(next);
      setNotice("Progress saved.");
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="discovery-grid">
      <nav aria-label="Discovery steps" className="panel step-nav">
        <ol>
          {steps.map((item, position) => {
            const done = discovery.completed_steps.includes(item.id);
            return (
              <li key={item.id}>
                <button
                  type="button"
                  aria-current={item.id === step ? "step" : undefined}
                  onClick={() => void save(item.id as StepId)}
                  disabled={saving}
                >
                  <span className="step-index" data-done={done}>
                    {done ? (
                      <Check size={14} aria-label="Complete" />
                    ) : (
                      position + 1
                    )}
                  </span>
                  {item.title}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
      <section className="panel">
        <div className="panel-heading">
          <h2>
            Step {index + 1} of {steps.length}: {current.title}
          </h2>
        </div>
        <form
          className="project-form"
          onSubmit={(event) => {
            event.preventDefault();
            void save((steps[index + 1]?.id || "review") as StepId);
          }}
        >
          <ErrorBox error={error} />
          {current.id === "review" ? (
            <>
              <h3 className="mb-3 font-semibold">Project brief</h3>
              <Review answers={toAnswers(draft)} />
            </>
          ) : (
            current.fields.map((name) => {
              const field = name as Field;
              const meta = FIELDS[field];
              return (
                <div key={field} className="flex flex-col gap-2">
                  <label htmlFor={`discovery-${field}`}>
                    {meta.label}{" "}
                    {meta.required && (
                      <span className="text-slate-500">
                        (needed to complete step)
                      </span>
                    )}
                  </label>
                  <p
                    id={`discovery-${field}-hint`}
                    className="text-xs text-slate-500"
                  >
                    {meta.hint}
                  </p>
                  <textarea
                    id={`discovery-${field}`}
                    rows={field === "problem_statement" ? 5 : 4}
                    value={draft[field]}
                    readOnly={readOnly}
                    aria-describedby={`discovery-${field}-hint`}
                    onChange={(event) =>
                      setDraft({ ...draft, [field]: event.target.value })
                    }
                  />
                </div>
              );
            })
          )}
          <div className="flex flex-wrap gap-3">
            {index > 0 && (
              <Button
                type="button"
                variant="outline"
                disabled={saving}
                onClick={() => void save(steps[index - 1].id as StepId)}
              >
                <ChevronLeft size={16} /> Back
              </Button>
            )}
            {!readOnly && (
              <Button
                type="button"
                variant="outline"
                disabled={saving}
                onClick={() => void save(current.id as StepId)}
              >
                <Save size={16} /> Save draft
              </Button>
            )}
            {index < steps.length - 1 && (
              <Button type="submit" disabled={saving}>
                {readOnly ? "Next" : saving ? "Saving…" : "Save and continue"}
                <ChevronRight size={16} />
              </Button>
            )}
          </div>
          <p role="status" className="text-sm text-emerald-800">
            {notice}
            {discovery.updated_at &&
              !readOnly &&
              ` Last saved ${new Date(discovery.updated_at).toLocaleString()}.`}
          </p>
        </form>
      </section>
    </div>
  );
}

function Review({ answers }: { answers: DiscoveryAnswers }) {
  return (
    <dl className="review-list">
      {(Object.keys(FIELDS) as Field[]).map((field) => {
        const value = answers[field];
        const empty = Array.isArray(value) ? !value.length : !value;
        return (
          <div key={field}>
            <dt>{FIELDS[field].label}</dt>
            <dd>
              {empty ? (
                <span className="text-slate-500">Not answered yet</span>
              ) : Array.isArray(value) ? (
                <ul>
                  {value.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                value
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

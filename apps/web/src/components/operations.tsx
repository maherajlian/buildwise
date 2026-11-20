"use client";
import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  type ApiError,
  type Operations,
  type TestCase,
  type TestCreate,
  type Risk,
  type RiskCreate,
  type SLO,
  type SLOCreate,
} from "@/lib/api";
import { getProjectToken } from "@/lib/token";
import { downloadCsv, downloadMarkdown } from "@/lib/download";
import { Button } from "@/components/ui/button";
import { ErrorBox, toApiError } from "@/components/form-error";

export const TEST_CATEGORIES: Record<TestCase["category"], string> = {
  unit: "Unit",
  integration: "Integration",
  api_contract: "API contract",
  e2e: "End-to-end",
  accessibility: "Accessibility",
  security: "Security",
  performance: "Performance/load",
  manual_acceptance: "Manual acceptance",
  model_evaluation: "Model evaluation",
  prompt_regression: "Prompt regression",
  tool_use_evaluation: "Tool-use evaluation",
};
const TEST_STATUSES: Record<NonNullable<TestCase["status"]>, string> = {
  proposed: "Proposed (not run)",
  planned: "Planned",
  passed: "Executed: Passed",
  failed: "Executed: Failed",
  blocked: "Blocked",
};

export function OperationsPanel({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const [data, setData] = useState<Operations>();
  const [error, setError] = useState<ApiError>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [token, setToken] = useState<string>();
  const locked = readOnly || !token;
  useEffect(() => {
    let disposed = false;
    let stored: string | undefined;
    try {
      stored = readOnly
        ? undefined
        : window.localStorage.getItem("buildwise.project-token") || undefined;
    } catch {
      stored = undefined;
    }
    api
      .operations(stored, projectId)
      .then((value) => {
        if (!disposed) {
          setToken(stored);
          setData(value);
          setError(undefined);
        }
      })
      .catch((cause) => {
        if (!disposed) setError(toApiError(cause));
      });
    return () => {
      disposed = true;
    };
  }, [projectId, readOnly, attempt]);
  async function action(work: () => Promise<void>) {
    setBusy(true);
    setError(undefined);
    setNotice("");
    try {
      await work();
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setBusy(false);
    }
  }
  async function refresh(message: string) {
    setData(await api.operations(token, projectId));
    setNotice(message);
  }
  function generate(replace = false) {
    if (
      replace &&
      !window.confirm(
        "Replace edited generated rows? Saved edits and recorded results on generated cases will be lost. User-created rows are kept.",
      )
    )
      return;
    void action(async () => {
      setData(
        await api.generateOperations(getProjectToken(), projectId, replace),
      );
      setNotice("Plans generated. No tests have been run by BuildWise.");
    });
  }
  function download(
    kind: "operations" | "test-cases" | "risks" | "slos",
    format: "markdown" | "csv" = "markdown",
  ) {
    void action(async () => {
      const text = await api.operationsExport(token, projectId, kind, format);
      if (format === "csv") downloadCsv(text, "test-plan.csv");
      else downloadMarkdown(text, `${kind}.md`);
    });
  }
  function remove(kind: "test" | "risk" | "slo", id: string) {
    if (!window.confirm(`Delete this ${kind}?`)) return;
    void action(async () => {
      if (kind === "test")
        await api.deleteTest(getProjectToken(), projectId, id);
      else if (kind === "risk")
        await api.deleteRisk(getProjectToken(), projectId, id);
      else await api.deleteSLO(getProjectToken(), projectId, id);
      await refresh("Item deleted.");
    });
  }
  return (
    <div className="technology-page operations-page">
      <header className="tech-title">
        <div>
          <div className="eyebrow">VALIDATE · RELEASE · OPERATE</div>
          <h2>Validate &amp; Operate</h2>
          <p className="tech-muted">
            Plans are generated deterministically from this project&apos;s
            requirements. Tests listed as proposed have not been run.
          </p>
        </div>
        <div className="tech-badges">
          {!locked && (
            <>
              <Button disabled={busy || !data} onClick={() => generate()}>
                {data &&
                (data.test_cases.length ||
                  data.risks.length ||
                  data.slos.length)
                  ? "Regenerate"
                  : "Generate from requirements"}
              </Button>
              {!!data &&
                [...data.test_cases, ...data.risks, ...data.slos].some(
                  (item) => item.source === "generated" && item.edited,
                ) && (
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() => generate(true)}
                  >
                    Replace edited rows…
                  </Button>
                )}
            </>
          )}
          <Button
            variant="outline"
            disabled={busy || !data}
            onClick={() => download("operations")}
          >
            Export operations pack (Markdown)
          </Button>
        </div>
      </header>
      {locked && (
        <p className="sample-banner">
          Read-only. Create or open a project in its owning browser to edit
          these plans.
        </p>
      )}
      <ErrorBox
        error={error}
        action="Retry loading"
        onAction={() => setAttempt((value) => value + 1)}
      />
      {notice && (
        <p role="status" className="save-notice">
          {notice}
        </p>
      )}
      {!data && !error && (
        <p role="status">Loading validation and operations plans…</p>
      )}
      {data && (
        <>
          <section
            aria-labelledby="test-plan-heading"
            className="operations-section"
          >
            <div className="tech-title">
              <div>
                <h2 id="test-plan-heading">Test plan</h2>
                <p className="tech-muted">
                  Recommendations, not execution claims. Record evidence after
                  running a test.
                </p>
              </div>
              <div className="tech-badges">
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => download("test-cases")}
                >
                  Export test plan Markdown
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => download("test-cases", "csv")}
                >
                  Export test plan CSV
                </Button>
              </div>
            </div>
            <dl className="operations-summary">
              {Object.entries(TEST_STATUSES).map(([status, label]) => (
                <div
                  key={status}
                  className={
                    status === "passed" || status === "failed"
                      ? "execution-summary"
                      : ""
                  }
                >
                  <dt>{label}</dt>
                  <dd>
                    {
                      data.test_cases.filter(
                        (item) =>
                          item.status === status &&
                          ((status !== "passed" && status !== "failed") ||
                            item.executed),
                      ).length
                    }
                  </dd>
                </div>
              ))}
            </dl>
            {!data.test_cases.length && (
              <p className="panel tech-panel">
                No test cases yet. Generate from requirements or add a case.
              </p>
            )}
            {Object.entries(TEST_CATEGORIES).map(([category, label]) => {
              const cases = data.test_cases.filter(
                (item) => item.category === category,
              );
              return cases.length ? (
                <section
                  key={category}
                  aria-label={`${label} tests`}
                  className="test-category"
                >
                  <h3>
                    {label} <span className="tech-muted">({cases.length})</span>
                  </h3>
                  <div className="operations-cases">
                    {cases.map((item) => (
                      <article
                        key={item.id + item.updated_at}
                        aria-label={item.title}
                        className="panel tech-panel operation-case"
                      >
                        <div className="tech-title">
                          <h4>{item.title}</h4>
                          <span
                            className={`operation-status ${item.executed ? "is-executed" : "is-proposed"}`}
                          >
                            {item.executed
                              ? TEST_STATUSES[item.status || "proposed"]
                              : item.status === "passed" ||
                                  item.status === "failed"
                                ? "Proposed (not run)"
                                : TEST_STATUSES[item.status || "proposed"]}
                          </span>
                        </div>
                        <p>{item.description}</p>
                        <p className="operation-source">
                          <strong>Source:</strong>{" "}
                          {item.rationale || "User-created case"}
                        </p>
                        {item.executed && (
                          <div className="operation-result">
                            <strong>Recorded result</strong>
                            <p>{item.result_notes}</p>
                            <p>
                              {item.executed_by || "Recorder not specified"} ·{" "}
                              {item.executed_at
                                ? new Date(item.executed_at).toLocaleString()
                                : "Date not recorded"}
                            </p>
                          </div>
                        )}
                        {!locked && (
                          <details>
                            <summary>Edit case / record result</summary>
                            <TestForm
                              item={item}
                              busy={busy}
                              onSave={(body) =>
                                void action(async () => {
                                  await api.updateTest(
                                    getProjectToken(),
                                    projectId,
                                    item.id,
                                    body,
                                  );
                                  await refresh("Test case saved.");
                                })
                              }
                            />
                            <Button
                              variant="outline"
                              disabled={busy}
                              onClick={() => remove("test", item.id)}
                            >
                              Delete case
                            </Button>
                          </details>
                        )}
                      </article>
                    ))}
                  </div>
                </section>
              ) : null;
            })}
            {!locked && (
              <details className="panel tech-panel">
                <summary>Add test case</summary>
                <TestForm
                  key={`new-${data.test_cases.length}`}
                  busy={busy}
                  onSave={(body) =>
                    void action(async () => {
                      await api.createTest(getProjectToken(), projectId, body);
                      await refresh("Test case added.");
                    })
                  }
                />
              </details>
            )}
          </section>
          <section
            aria-labelledby="risks-heading"
            className="operations-section"
            id="operations-risks"
          >
            <div className="tech-title">
              <div>
                <h2 id="risks-heading">Risk register</h2>
                <p className="tech-muted">
                  Score = likelihood × impact. Review ownership and mitigation
                  before release.
                </p>
              </div>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => download("risks")}
              >
                Export risks Markdown
              </Button>
            </div>
            {!data.risks.length ? (
              <p className="panel tech-panel">No risks recorded yet.</p>
            ) : (
              <div
                className="operations-table-wrap"
                role="region"
                aria-label="Risk register table"
                tabIndex={0}
              >
                <table className="operations-table">
                  <caption className="sr-only">Project risk register</caption>
                  <thead>
                    <tr>
                      {[
                        "Title",
                        "Category",
                        "Likelihood",
                        "Impact",
                        "Score",
                        "Status",
                        "Owner",
                        "Mitigation",
                        ...(!locked ? ["Actions"] : []),
                      ].map((name) => (
                        <th key={name} scope="col">
                          {name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.risks.map((item) => (
                      <tr key={item.id + item.updated_at}>
                        <th scope="row">
                          {item.title}
                          <p className="operation-source">{item.rationale}</p>
                        </th>
                        <td>{item.category}</td>
                        <td>{item.likelihood}</td>
                        <td>{item.impact}</td>
                        <td>
                          <strong className="risk-score">{item.score}</strong>
                        </td>
                        <td>{item.status}</td>
                        <td>{item.owner || "Unassigned"}</td>
                        <td>{item.mitigation}</td>
                        {!locked && (
                          <td>
                            <details>
                              <summary>Edit risk</summary>
                              <RiskForm
                                item={item}
                                busy={busy}
                                onSave={(body) =>
                                  void action(async () => {
                                    await api.updateRisk(
                                      getProjectToken(),
                                      projectId,
                                      item.id,
                                      body,
                                    );
                                    await refresh("Risk saved.");
                                  })
                                }
                              />
                              <Button
                                variant="outline"
                                disabled={busy}
                                onClick={() => remove("risk", item.id)}
                              >
                                Delete risk
                              </Button>
                            </details>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {!locked && (
              <details className="panel tech-panel">
                <summary>Add risk</summary>
                <RiskForm
                  key={`new-${data.risks.length}`}
                  busy={busy}
                  onSave={(body) =>
                    void action(async () => {
                      await api.createRisk(getProjectToken(), projectId, body);
                      await refresh("Risk added.");
                    })
                  }
                />
              </details>
            )}
          </section>
          <section
            aria-labelledby="slos-heading"
            className="operations-section"
            id="operations-slos"
          >
            <div className="tech-title">
              <div>
                <h2 id="slos-heading">SLO suggestions</h2>
                <p className="tech-muted">
                  Suggested objectives, not measured guarantees. Adopt targets
                  after review.
                </p>
              </div>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => download("slos")}
              >
                Export SLOs Markdown
              </Button>
            </div>
            {!data.slos.length && (
              <p className="panel tech-panel">No SLO suggestions yet.</p>
            )}
            <div className="operations-slos">
              {data.slos.map((item) => (
                <article
                  key={item.id + item.updated_at}
                  className="panel tech-panel"
                  aria-label={item.name}
                >
                  <div className="tech-title">
                    <h3>{item.name}</h3>
                    <span className="operation-status">{item.status}</span>
                  </div>
                  <p className="slo-target">
                    {item.target} <span>/ {item.window}</span>
                  </p>
                  <dl className="operation-definition">
                    <dt>SLI · how measured</dt>
                    <dd>{item.sli}</dd>
                    <dt>Alert recommendation</dt>
                    <dd>{item.alert}</dd>
                    <dt>Source</dt>
                    <dd>{item.rationale || "User-created objective"}</dd>
                  </dl>
                  {!locked && (
                    <details>
                      <summary>Edit SLO</summary>
                      <SLOForm
                        item={item}
                        busy={busy}
                        onSave={(body) =>
                          void action(async () => {
                            await api.updateSLO(
                              getProjectToken(),
                              projectId,
                              item.id,
                              body,
                            );
                            await refresh("SLO saved.");
                          })
                        }
                      />
                      <Button
                        variant="outline"
                        disabled={busy}
                        onClick={() => remove("slo", item.id)}
                      >
                        Delete SLO
                      </Button>
                    </details>
                  )}
                </article>
              ))}
            </div>
            {!locked && (
              <details className="panel tech-panel">
                <summary>Add SLO</summary>
                <SLOForm
                  key={`new-${data.slos.length}`}
                  busy={busy}
                  onSave={(body) =>
                    void action(async () => {
                      await api.createSLO(getProjectToken(), projectId, body);
                      await refresh("SLO added.");
                    })
                  }
                />
              </details>
            )}
          </section>
        </>
      )}
      <section
        className="panel tech-panel operations-section"
        aria-labelledby="release-plans"
      >
        <h2 id="release-plans">Deployment &amp; observability plans</h2>
        <p>
          Review and edit these artefacts in Specs. Generate specifications
          there if a plan does not exist yet.
        </p>
        <div className="tech-badges">
          <a
            className="tech-link"
            href={`/projects/view/?id=${encodeURIComponent(projectId)}&tab=specs&artefact=deployment`}
          >
            Open deployment plan in Specs →
          </a>
          <a
            className="tech-link"
            href={`/projects/view/?id=${encodeURIComponent(projectId)}&tab=specs&artefact=observability`}
          >
            Open observability plan in Specs →
          </a>
        </div>
      </section>
    </div>
  );
}

function TestForm({
  item,
  busy,
  onSave,
}: {
  item?: TestCase;
  busy: boolean;
  onSave: (body: TestCreate) => void;
}) {
  const [status, setStatus] = useState<TestCase["status"]>(
    item?.status || "proposed",
  );
  const [notes, setNotes] = useState(item?.result_notes || "");
  const record = status === "passed" || status === "failed";
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const date = String(form.get("executed_at") || "");
    onSave({
      title: String(form.get("title")).trim(),
      description: String(form.get("description")),
      category: (form.get("category") ||
        item?.category ||
        "unit") as TestCase["category"],
      status,
      ...(record
        ? {
            result_notes: notes.trim(),
            executed_by: String(form.get("executed_by") || "").trim() || null,
            ...(date ? { executed_at: new Date(date).toISOString() } : {}),
          }
        : {}),
    });
  }
  return (
    <form className="project-form operation-form" onSubmit={submit}>
      <label>
        Case title
        <input
          name="title"
          required
          maxLength={200}
          defaultValue={item?.title || ""}
        />
      </label>
      {!item && (
        <label>
          Category
          <select name="category">
            {Object.entries(TEST_CATEGORIES).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}
      <label>
        Description
        <textarea
          name="description"
          rows={3}
          defaultValue={item?.description || ""}
        />
      </label>
      <label>
        Test status
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as TestCase["status"])}
        >
          {Object.entries(TEST_STATUSES).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {record && (
        <fieldset className="operation-result">
          <legend>Record result</legend>
          <p>
            Only record a result after actually running this test. Include
            evidence or a result reference.
          </p>
          <label>
            Result notes (required)
            <textarea
              name="result_notes"
              required
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
          <label>
            Executed by (optional)
            <input
              name="executed_by"
              maxLength={200}
              defaultValue={item?.executed_by || ""}
            />
          </label>
          <label>
            Execution date (optional)
            <input name="executed_at" type="datetime-local" />
          </label>
          <p className="tech-muted">
            Leave the date empty to record the current time.
          </p>
        </fieldset>
      )}
      <Button disabled={busy || (record && !notes.trim())}>
        {item ? (record ? "Record result" : "Save case") : "Add case"}
      </Button>
    </form>
  );
}

type Field = {
  name: string;
  label: string;
  type?: "number" | "textarea";
  options?: string[];
  required?: boolean;
};
function Fields({ fields, item }: { fields: Field[]; item?: object }) {
  return fields.map((field) => {
    const value = String(
      (item as Record<string, unknown> | undefined)?.[field.name] ??
        (field.type === "number" ? 3 : ""),
    );
    return (
      <label key={field.name}>
        {field.label}
        {field.options ? (
          <select name={field.name} defaultValue={value || field.options[0]}>
            {field.options.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        ) : field.type === "textarea" ? (
          <textarea name={field.name} rows={3} defaultValue={value} />
        ) : (
          <input
            name={field.name}
            type={field.type || "text"}
            required={field.required}
            min={field.type === "number" ? 1 : undefined}
            max={field.type === "number" ? 5 : undefined}
            maxLength={field.type !== "number" ? 200 : undefined}
            defaultValue={value}
          />
        )}
      </label>
    );
  });
}
function values(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  return Object.fromEntries(
    new FormData(event.currentTarget).entries(),
  ) as Record<string, string>;
}
function RiskForm({
  item,
  busy,
  onSave,
}: {
  item?: Risk;
  busy: boolean;
  onSave: (body: RiskCreate) => void;
}) {
  return (
    <form
      className="project-form operation-form"
      onSubmit={(event) => {
        const v = values(event);
        onSave({
          title: v.title.trim(),
          description: v.description,
          category: v.category as Risk["category"],
          likelihood: Number(v.likelihood),
          impact: Number(v.impact),
          mitigation: v.mitigation,
          owner: v.owner,
          status: v.status as Risk["status"],
          rationale: v.rationale,
        });
      }}
    >
      <Fields
        item={item}
        fields={[
          { name: "title", label: "Risk title", required: true },
          { name: "description", label: "Risk description", type: "textarea" },
          {
            name: "category",
            label: "Risk category",
            options: [
              "technical",
              "security",
              "operational",
              "delivery",
              "compliance",
              "cost",
            ],
          },
          {
            name: "likelihood",
            label: "Likelihood (1–5)",
            type: "number",
            required: true,
          },
          {
            name: "impact",
            label: "Impact (1–5)",
            type: "number",
            required: true,
          },
          {
            name: "status",
            label: "Risk status",
            options: ["open", "mitigating", "accepted", "closed"],
          },
          { name: "owner", label: "Risk owner" },
          { name: "mitigation", label: "Mitigation", type: "textarea" },
          { name: "rationale", label: "Risk rationale", type: "textarea" },
        ]}
      />
      <Button disabled={busy}>{item ? "Save risk" : "Add risk"}</Button>
    </form>
  );
}
function SLOForm({
  item,
  busy,
  onSave,
}: {
  item?: SLO;
  busy: boolean;
  onSave: (body: SLOCreate) => void;
}) {
  return (
    <form
      className="project-form operation-form"
      onSubmit={(event) => {
        const v = values(event);
        onSave({
          name: v.name.trim(),
          sli: v.sli,
          target: v.target,
          window: v.window,
          alert: v.alert,
          rationale: v.rationale,
          status: v.status as SLO["status"],
        });
      }}
    >
      <Fields
        item={item || { window: "28 days" }}
        fields={[
          { name: "name", label: "SLO name", required: true },
          { name: "sli", label: "SLI (how measured)", type: "textarea" },
          { name: "target", label: "Target", required: true },
          { name: "window", label: "Window", required: true },
          { name: "alert", label: "Alert recommendation", type: "textarea" },
          { name: "rationale", label: "SLO rationale", type: "textarea" },
          {
            name: "status",
            label: "SLO status",
            options: ["suggested", "adopted", "rejected"],
          },
        ]}
      />
      <Button disabled={busy}>{item ? "Save SLO" : "Add SLO"}</Button>
    </form>
  );
}

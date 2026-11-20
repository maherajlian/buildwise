"use client";
import { useEffect, useState } from "react";
import {
  api,
  type ApiError,
  type Plan,
  type PlanTask,
  type TaskCreate,
} from "@/lib/api";
import { getProjectToken, readProjectToken } from "@/lib/token";
import { downloadMarkdown } from "@/lib/download";
import { ErrorBox, lines, toApiError } from "@/components/form-error";
import { Button } from "@/components/ui/button";
import { MarkdownPreview } from "@/components/markdown-preview";

const STATUSES: Record<NonNullable<PlanTask["status"]>, string> = {
  backlog: "Backlog",
  ready: "Ready",
  in_progress: "In progress",
  review: "Review",
  done: "Done",
};

export function BuildPlan({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const [plan, setPlan] = useState<Plan>();
  const [error, setError] = useState<ApiError>();
  const [taskError, setTaskError] = useState<{ id: string; error: ApiError }>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState<string>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let disposed = false;
    api
      .plan(readOnly ? undefined : readProjectToken(), projectId)
      .then((value) => {
        if (!disposed) {
          setPlan(value);
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
  async function action(work: () => Promise<void>, taskId?: string) {
    setBusy(true);
    setError(undefined);
    setTaskError(undefined);
    setNotice("");
    try {
      await work();
    } catch (cause) {
      if (taskId) setTaskError({ id: taskId, error: toApiError(cause) });
      else setError(toApiError(cause));
    } finally {
      setBusy(false);
    }
  }
  async function refresh(message: string) {
    setPlan(
      await api.plan(readOnly ? undefined : readProjectToken(), projectId),
    );
    setNotice(message);
  }
  return (
    <div className="technology-page phase4-page">
      <div className="tech-title">
        <div>
          <h2>Build plan</h2>
          <p className="tech-muted">
            A human-reviewed path from design to delivery. Dependencies gate
            active work.
          </p>
        </div>
        <div className="tech-badges">
          {!readOnly && (
            <>
              <Button
                disabled={busy}
                onClick={() =>
                  void action(async () => {
                    setPlan(
                      await api.generatePlan(getProjectToken(), projectId),
                    );
                    setNotice("Plan generated. Existing plans are preserved.");
                  })
                }
              >
                Generate plan
              </Button>
              <Button
                variant="outline"
                disabled={busy || !plan}
                onClick={() => setEditing("new")}
              >
                Add task
              </Button>
            </>
          )}
          <Button
            variant="outline"
            disabled={busy || !plan?.tasks.length}
            onClick={() =>
              void action(async () =>
                downloadMarkdown(
                  await api.planMarkdown(
                    readOnly ? undefined : readProjectToken(),
                    projectId,
                  ),
                  "build-plan.md",
                ),
              )
            }
          >
            Export plan Markdown
          </Button>
        </div>
      </div>
      <ErrorBox
        error={error}
        action="Retry loading"
        onAction={() => setAttempt((a) => a + 1)}
      />
      {notice && (
        <p role="status" className="save-notice">
          {notice}
        </p>
      )}
      {!plan && !error && <p role="status">Loading plan…</p>}
      {plan && (
        <>
          <div className="panel tech-panel" aria-label="Plan validation">
            <h3>Dependency validation</h3>
            <p>
              {plan.validation.valid
                ? "Valid — no dependency issues."
                : "Dependency issues need attention."}
            </p>
            {!!plan.validation.errors.length && (
              <ul className="plain-list">
                {plan.validation.errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            )}
          </div>
          {!plan.tasks.length && (
            <p>No tasks yet. Generate a plan or add a task to begin.</p>
          )}
          {!readOnly && editing === "new" && (
            <TaskForm
              plan={plan}
              busy={busy}
              error={taskError?.id === "new" ? taskError.error : undefined}
              onCancel={() => setEditing(undefined)}
              onSave={(body) =>
                void action(async () => {
                  await api.createTask(getProjectToken(), projectId, body);
                  await refresh("Task added.");
                  setEditing(undefined);
                }, "new")
              }
            />
          )}
          {[
            ...plan.epics,
            {
              id: "ungrouped",
              title: "Ungrouped tasks",
              description: "Tasks without an epic",
            },
          ].map((epic) => {
            const tasks = plan.tasks.filter(
              (t) => (t.epic_id || "ungrouped") === epic.id,
            );
            if (epic.id === "ungrouped" && !tasks.length) return null;
            return (
              <section
                key={epic.id}
                className="panel tech-panel"
                aria-label={`${epic.title} epic`}
              >
                <h3>{epic.title}</h3>
                <p>{epic.description}</p>
                {!tasks.length && (
                  <p className="tech-muted">No tasks in this epic.</p>
                )}
                {tasks.map((task) => (
                  <article
                    key={task.id}
                    className="plan-task"
                    aria-label={`${task.key}: ${task.title}`}
                  >
                    <div className="tech-title">
                      <h4>
                        {task.key}: {task.title}
                      </h4>
                      <span className="tech-badge">{task.priority}</span>
                    </div>
                    <p>{task.description}</p>
                    {readOnly ? (
                      <p>Status: {STATUSES[task.status || "backlog"]}</p>
                    ) : (
                      <label className="task-status">
                        Status for {task.key}
                        <select
                          aria-label={`Status for ${task.key}`}
                          disabled={busy}
                          value={task.status}
                          onChange={(e) => {
                            const status = e.target.value as PlanTask["status"];
                            void action(async () => {
                              await api.updateTask(
                                getProjectToken(),
                                projectId,
                                task.id,
                                { status },
                              );
                              await refresh(`${task.key} status updated.`);
                            }, task.id);
                          }}
                        >
                          {Object.entries(STATUSES).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    {editing !== task.id && (
                      <ErrorBox
                        error={
                          taskError?.id === task.id
                            ? taskError.error
                            : undefined
                        }
                      />
                    )}
                    <dl className="task-details">
                      <div>
                        <dt>Skill / tool</dt>
                        <dd>{task.skill || "TODO: assign a skill or tool"}</dd>
                      </div>
                      <div>
                        <dt>Suggested workflow</dt>
                        <dd>{task.workflow || "TODO: agree workflow"}</dd>
                      </div>
                      <div>
                        <dt>Dependencies</dt>
                        <dd>
                          {task.depends_on?.length
                            ? task.depends_on
                                .map(
                                  (id) =>
                                    plan.tasks.find((t) => t.id === id)?.key ||
                                    id,
                                )
                                .join(", ")
                            : "None"}
                        </dd>
                      </div>
                    </dl>
                    <h5>Acceptance criteria</h5>
                    <ul className="plain-list">
                      {task.acceptance_criteria.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                    <details>
                      <summary>Implementation notes for {task.key}</summary>
                      <MarkdownPreview
                        text={task.implementation_notes || "No notes yet."}
                      />
                    </details>
                    {!readOnly &&
                      (editing === task.id ? (
                        <TaskForm
                          key={task.id}
                          task={task}
                          plan={plan}
                          busy={busy}
                          error={
                            taskError?.id === task.id
                              ? taskError.error
                              : undefined
                          }
                          onCancel={() => setEditing(undefined)}
                          onSave={(body) =>
                            void action(async () => {
                              await api.updateTask(
                                getProjectToken(),
                                projectId,
                                task.id,
                                body,
                              );
                              await refresh("Task saved.");
                              setEditing(undefined);
                            }, task.id)
                          }
                        />
                      ) : (
                        <div className="tech-badges">
                          <Button
                            variant="outline"
                            disabled={busy}
                            onClick={() => setEditing(task.id)}
                          >
                            Edit {task.key}
                          </Button>
                          <Button
                            variant="outline"
                            disabled={busy}
                            onClick={() => {
                              if (
                                window.confirm(
                                  `Delete ${task.key}? Dependencies on it will be removed.`,
                                )
                              )
                                void action(async () => {
                                  await api.deleteTask(
                                    getProjectToken(),
                                    projectId,
                                    task.id,
                                  );
                                  await refresh("Task deleted.");
                                }, task.id);
                            }}
                          >
                            Delete {task.key}
                          </Button>
                        </div>
                      ))}
                  </article>
                ))}
              </section>
            );
          })}
        </>
      )}
    </div>
  );
}

function TaskForm({
  task,
  plan,
  busy,
  error,
  onSave,
  onCancel,
}: {
  task?: PlanTask;
  plan: Plan;
  busy: boolean;
  error?: ApiError;
  onSave: (body: TaskCreate) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(task?.title || "");
  const [priority, setPriority] = useState<PlanTask["priority"]>(
    task?.priority || "P1",
  );
  const [deps, setDeps] = useState(task?.depends_on || []);
  const [notes, setNotes] = useState(task?.implementation_notes || "");
  const [criteria, setCriteria] = useState(
    task?.acceptance_criteria.join("\n") || "",
  );
  const [epic, setEpic] = useState(task?.epic_id || "");
  const prefix = `task-${task?.id || "new"}`;
  return (
    <form
      className="project-form phase4-form"
      aria-label={task ? `Edit ${task.key}` : "New task"}
      onSubmit={(e) => {
        e.preventDefault();
        onSave({
          title: title.trim(),
          priority,
          depends_on: deps,
          implementation_notes: notes,
          acceptance_criteria: lines(criteria),
          epic_id: epic || null,
        });
      }}
    >
      <h4>{task ? `Edit ${task.key}` : "New task"}</h4>
      <ErrorBox error={error} />
      <label htmlFor={`${prefix}-title`}>Task title</label>
      <input
        id={`${prefix}-title`}
        required
        maxLength={200}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <div className="form-row">
        <div>
          <label htmlFor={`${prefix}-priority`}>Priority</label>
          <select
            id={`${prefix}-priority`}
            value={priority}
            onChange={(e) =>
              setPriority(e.target.value as PlanTask["priority"])
            }
          >
            {["P0", "P1", "P2"].map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${prefix}-epic`}>Epic</label>
          <select
            id={`${prefix}-epic`}
            value={epic}
            onChange={(e) => setEpic(e.target.value)}
          >
            <option value="">Ungrouped</option>
            {plan.epics.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </select>
        </div>
      </div>
      <label htmlFor={`${prefix}-deps`}>Dependencies (select multiple)</label>
      <p id={`${prefix}-deps-help`} className="tech-muted">
        Use Ctrl / Command or Shift to select multiple tasks. Dependencies must
        be done before active work.
      </p>
      <select
        id={`${prefix}-deps`}
        multiple
        size={Math.min(6, Math.max(2, plan.tasks.length))}
        aria-describedby={`${prefix}-deps-help`}
        value={deps}
        onChange={(e) =>
          setDeps(Array.from(e.target.selectedOptions, (o) => o.value))
        }
      >
        {plan.tasks
          .filter((t) => t.id !== task?.id)
          .map((t) => (
            <option key={t.id} value={t.id}>
              {t.key}: {t.title}
            </option>
          ))}
      </select>
      <label htmlFor={`${prefix}-notes`}>Implementation notes</label>
      <textarea
        id={`${prefix}-notes`}
        rows={5}
        maxLength={20000}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <label htmlFor={`${prefix}-criteria`}>
        Acceptance criteria (one per line)
      </label>
      <textarea
        id={`${prefix}-criteria`}
        rows={4}
        value={criteria}
        onChange={(e) => setCriteria(e.target.value)}
      />
      <div className="tech-badges">
        <Button disabled={busy || !title.trim()}>
          {task ? "Save task" : "Create task"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          onClick={onCancel}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}

"use client";
import { useEffect, useState } from "react";
import { ListChecks, Pencil, Plus, Trash2 } from "lucide-react";
import {
  api,
  ApiError,
  type Requirement,
  type RequirementCreate,
} from "@/lib/api";
import { getProjectToken, readProjectToken } from "@/lib/token";
import { Button } from "@/components/ui/button";
import {
  ErrorBox,
  FieldError,
  lines,
  requiredError,
  toApiError,
} from "@/components/form-error";

type Form = Required<Omit<RequirementCreate, "acceptance_criteria">> & {
  acceptance_criteria: string;
};
const EMPTY: Form = {
  type: "functional",
  title: "",
  description: "",
  priority: "P1",
  status: "proposed",
  acceptance_criteria: "",
};
const TYPE_LABELS = {
  functional: "Functional",
  non_functional: "Non-functional",
};

export function Requirements({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const [items, setItems] = useState<Requirement[]>();
  const [error, setError] = useState<ApiError>();
  const [formError, setFormError] = useState<ApiError>();
  const [form, setForm] = useState<Form>(EMPTY);
  const [editing, setEditing] = useState<string>();
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState<"all" | Requirement["type"]>("all");

  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let disposed = false;
    async function load() {
      try {
        const value = await api.requirements(readProjectToken(), projectId);
        if (!disposed) {
          setItems(value);
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

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    if (!form.title.trim()) {
      setFormError(requiredError("title", "Title"));
      document.getElementById("requirement-title")?.focus();
      return;
    }
    setSaving(true);
    setFormError(undefined);
    const body = {
      ...form,
      title: form.title.trim(),
      acceptance_criteria: lines(form.acceptance_criteria),
    };
    try {
      const token = getProjectToken();
      const saved = editing
        ? await api.updateRequirement(token, projectId, editing, body)
        : await api.createRequirement(token, projectId, body);
      setItems((previous = []) =>
        editing
          ? previous.map((item) => (item.id === saved.id ? saved : item))
          : [...previous, saved],
      );
      setNotice(
        editing ? `Updated “${saved.title}”.` : `Added “${saved.title}”.`,
      );
      setForm(EMPTY);
      setEditing(undefined);
    } catch (cause) {
      setFormError(toApiError(cause));
    } finally {
      setSaving(false);
    }
  }
  async function remove(item: Requirement) {
    setError(undefined);
    try {
      await api.deleteRequirement(getProjectToken(), projectId, item.id);
      setItems((previous = []) => previous.filter((row) => row.id !== item.id));
      setNotice(`Deleted “${item.title}”.`);
      if (editing === item.id) {
        setEditing(undefined);
        setForm(EMPTY);
      }
    } catch (cause) {
      setError(toApiError(cause));
    }
  }
  function edit(item: Requirement) {
    setEditing(item.id);
    setFormError(undefined);
    setForm({
      type: item.type,
      title: item.title,
      description: item.description,
      priority: item.priority,
      status: item.status,
      acceptance_criteria: item.acceptance_criteria.join("\n"),
    });
    document.getElementById("requirement-title")?.focus();
  }
  const visible = (items || []).filter(
    (item) => filter === "all" || item.type === filter,
  );
  return (
    <div className="projects-grid">
      <section className="panel">
        <div className="panel-heading">
          <h2>Requirements</h2>
          <span className="count-tag">{items?.length ?? 0}</span>
        </div>
        <div className="filter-row">
          <label htmlFor="requirement-filter">Show</label>
          <select
            id="requirement-filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value as typeof filter)}
          >
            <option value="all">All</option>
            <option value="functional">Functional</option>
            <option value="non_functional">Non-functional</option>
          </select>
        </div>
        <ErrorBox
          error={error}
          action="Retry"
          onAction={() => setAttempt((value) => value + 1)}
        />
        {!items && !error && (
          <p role="status" className="p-6 text-sm text-slate-500">
            Loading requirements…
          </p>
        )}
        {items && !visible.length && (
          <div className="empty-state">
            <span className="empty-icon">
              <ListChecks size={28} />
            </span>
            {items.length ? (
              <>
                <h3>No matching requirements</h3>
                <p>Change the filter to see your other requirements.</p>
              </>
            ) : (
              <>
                <h3>No requirements yet</h3>
                <p>
                  Capture what the system must do and how well it must do it.
                </p>
              </>
            )}
          </div>
        )}
        <ul className="requirement-list">
          {visible.map((item) => (
            <li key={item.id}>
              <div className="requirement-meta">
                <span className="project-status">{item.priority}</span>
                <span className="project-status">{TYPE_LABELS[item.type]}</span>
                <span className="project-status">{item.status}</span>
              </div>
              <h3 className="font-semibold break-words">{item.title}</h3>
              {item.description && (
                <p className="text-sm text-slate-600 break-words">
                  {item.description}
                </p>
              )}
              {item.acceptance_criteria.length > 0 && (
                <ul className="criteria">
                  {item.acceptance_criteria.map((criterion) => (
                    <li key={criterion}>{criterion}</li>
                  ))}
                </ul>
              )}
              {!readOnly && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => edit(item)}
                    aria-label={`Edit ${item.title}`}
                  >
                    <Pencil size={14} /> Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void remove(item)}
                    aria-label={`Delete ${item.title}`}
                  >
                    <Trash2 size={14} /> Delete
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
        <p role="status" className="px-6 pb-4 text-sm text-emerald-800">
          {notice}
        </p>
      </section>
      {!readOnly && (
        <section className="panel">
          <div className="panel-heading">
            <h2>{editing ? "Edit requirement" : "Add a requirement"}</h2>
            <Plus size={18} className="text-slate-400" />
          </div>
          <form className="project-form" onSubmit={submit} noValidate>
            <ErrorBox error={formError} />
            <label htmlFor="requirement-type">Type</label>
            <select
              id="requirement-type"
              value={form.type}
              onChange={(event) =>
                setForm({ ...form, type: event.target.value as Form["type"] })
              }
            >
              <option value="functional">Functional</option>
              <option value="non_functional">Non-functional</option>
            </select>
            <label htmlFor="requirement-title">
              Title <span className="text-slate-500">(required)</span>
            </label>
            <input
              id="requirement-title"
              value={form.title}
              maxLength={200}
              required
              aria-describedby="requirement-title-error"
              aria-invalid={Boolean(
                formError?.fields.some((f) => f.field === "title"),
              )}
              onChange={(event) =>
                setForm({ ...form, title: event.target.value })
              }
            />
            <FieldError
              error={formError}
              field="title"
              id="requirement-title-error"
            />
            <label htmlFor="requirement-description">Description</label>
            <textarea
              id="requirement-description"
              rows={3}
              maxLength={5000}
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
            />
            <div className="form-row">
              <div className="flex flex-col gap-2">
                <label htmlFor="requirement-priority">Priority</label>
                <select
                  id="requirement-priority"
                  value={form.priority}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      priority: event.target.value as Form["priority"],
                    })
                  }
                >
                  <option value="P0">P0 must have</option>
                  <option value="P1">P1 should have</option>
                  <option value="P2">P2 could have</option>
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label htmlFor="requirement-status">Status</label>
                <select
                  id="requirement-status"
                  value={form.status}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      status: event.target.value as Form["status"],
                    })
                  }
                >
                  <option value="proposed">Proposed</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="deferred">Deferred</option>
                </select>
              </div>
            </div>
            <label htmlFor="requirement-criteria">Acceptance criteria</label>
            <p
              id="requirement-criteria-hint"
              className="text-xs text-slate-500"
            >
              One criterion per line, e.g. Given… when… then…
            </p>
            <textarea
              id="requirement-criteria"
              rows={4}
              value={form.acceptance_criteria}
              aria-describedby="requirement-criteria-hint"
              onChange={(event) =>
                setForm({ ...form, acceptance_criteria: event.target.value })
              }
            />
            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={saving}>
                {saving
                  ? "Saving…"
                  : editing
                    ? "Save requirement"
                    : "Add requirement"}
              </Button>
              {editing && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setEditing(undefined);
                    setForm(EMPTY);
                    setFormError(undefined);
                  }}
                >
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </section>
      )}
    </div>
  );
}

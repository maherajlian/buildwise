"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Eye, Save, Trash2 } from "lucide-react";
import {
  api,
  ApiError,
  type Project,
  type ProjectOverview,
  type ProjectUpdate,
} from "@/lib/api";
import { getProjectToken, readProjectToken } from "@/lib/token";
import { Button } from "@/components/ui/button";
import {
  ErrorBox,
  FieldError,
  requiredError,
  toApiError,
} from "@/components/form-error";
import { DiscoveryWizard } from "@/components/discovery";
import { Requirements } from "@/components/requirements";

const TABS = ["overview", "discovery", "requirements"] as const;
type Tab = (typeof TABS)[number];
const TAB_LABELS: Record<Tab, string> = {
  overview: "Overview",
  discovery: "Discovery",
  requirements: "Requirements",
};
const STEP_LABELS: Record<string, string> = {
  problem: "Problem",
  users: "Users",
  goals: "Goals and success",
  scope: "Scope and constraints",
  context: "Integrations and risks",
  questions: "Open questions",
};

export function Workspace() {
  const params = useSearchParams();
  const router = useRouter();
  const requested = params.get("id") || "";
  const initialTab = params.get("tab") as Tab | null;
  const [tab, setTab] = useState<Tab>(
    initialTab && TABS.includes(initialTab) ? initialTab : "overview",
  );
  const [project, setProject] = useState<Project>();
  const [error, setError] = useState<ApiError>();
  const [loading, setLoading] = useState(Boolean(requested));

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!requested) return;
    let disposed = false;
    async function load() {
      try {
        const value =
          requested === "sample"
            ? await api.sample()
            : await api.project(readProjectToken(), requested);
        if (!disposed) {
          setProject(value);
          setError(undefined);
        }
      } catch (cause) {
        if (!disposed) setError(toApiError(cause));
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void load();
    return () => {
      disposed = true;
    };
  }, [requested, attempt]);

  function select(next: Tab) {
    setTab(next);
    const query = new URLSearchParams(params.toString());
    query.set("tab", next);
    router.replace(`/projects/view/?${query.toString()}`, { scroll: false });
  }

  if (!requested)
    return <ErrorBox error={new ApiError("No project selected.")} />;
  if (loading && !project)
    return (
      <p role="status" className="text-sm text-slate-500">
        Loading project…
      </p>
    );
  if (!project)
    return (
      <>
        <BackLink />
        <ErrorBox
          error={
            error?.status === 404
              ? new ApiError(
                  "Project not found. It may have been deleted, expired after 30 days without changes, or belong to another browser.",
                  error.correlationId,
                )
              : error
          }
          action="Retry"
          onAction={() => {
            setLoading(true);
            setAttempt((value) => value + 1);
          }}
        />
      </>
    );
  const readOnly = project.is_sample;
  return (
    <>
      <BackLink />
      <div className="eyebrow">
        {readOnly ? "ILLUSTRATIVE SAMPLE" : "PROJECT WORKSPACE"}
      </div>
      <div className="page-heading">
        <div className="min-w-0">
          <h1 className="break-words">{project.name}</h1>
          <p className="break-words">
            {project.description || "No description yet"}
          </p>
        </div>
        <span className="project-status">{project.status}</span>
      </div>
      {readOnly && (
        <div className="sample-banner" role="note">
          <Eye size={18} aria-hidden />
          <p>
            Illustrative sample, read-only. It shows a completed discovery for a
            fictional product.{" "}
            <Link href="/projects/">Create your own project</Link> to edit.
          </p>
        </div>
      )}
      <div role="tablist" aria-label="Project sections" className="tab-list">
        {TABS.map((item) => (
          <button
            key={item}
            role="tab"
            id={`tab-${item}`}
            aria-selected={tab === item}
            aria-controls={`panel-${item}`}
            className="tab"
            onClick={() => select(item)}
            onKeyDown={(event) => {
              const offset =
                event.key === "ArrowRight"
                  ? 1
                  : event.key === "ArrowLeft"
                    ? -1
                    : 0;
              if (!offset) return;
              const next =
                TABS[(TABS.indexOf(item) + offset + TABS.length) % TABS.length];
              select(next);
              document.getElementById(`tab-${next}`)?.focus();
            }}
            tabIndex={tab === item ? 0 : -1}
          >
            {TAB_LABELS[item]}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "overview" && (
          <Overview
            project={project}
            onChange={setProject}
            onDeleted={() => router.push("/projects/")}
            onNavigate={select}
          />
        )}
        {tab === "discovery" && (
          <DiscoveryWizard projectId={project.id} readOnly={readOnly} />
        )}
        {tab === "requirements" && (
          <Requirements projectId={project.id} readOnly={readOnly} />
        )}
      </div>
    </>
  );
}

function BackLink() {
  return (
    <Link href="/projects/" className="back-link">
      <ArrowLeft size={16} aria-hidden /> All projects
    </Link>
  );
}

function Overview({
  project,
  onChange,
  onDeleted,
  onNavigate,
}: {
  project: Project;
  onChange: (project: Project) => void;
  onDeleted: () => void;
  onNavigate: (tab: Tab) => void;
}) {
  const [overview, setOverview] = useState<ProjectOverview>();
  const [error, setError] = useState<ApiError>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let disposed = false;
    async function load() {
      try {
        const value = await api.overview(readProjectToken(), project.id);
        if (!disposed) {
          setOverview(value);
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
  }, [project.id, project.updated_at, attempt]);
  return (
    <div className="projects-grid">
      <section className="panel">
        <div className="panel-heading">
          <h2>Overview</h2>
        </div>
        <ErrorBox
          error={error}
          action="Retry"
          onAction={() => setAttempt((value) => value + 1)}
        />
        {!overview && !error && (
          <p role="status" className="p-6 text-sm text-slate-500">
            Loading overview…
          </p>
        )}
        {overview && (
          <div className="overview-body">
            <dl className="stat-grid">
              <div>
                <dt>Discovery</dt>
                <dd>
                  {overview.discovery_completed.length}/
                  {overview.discovery_steps.length} steps
                </dd>
              </div>
              <div>
                <dt>Requirements</dt>
                <dd>{overview.requirements.total}</dd>
              </div>
              <div>
                <dt>Confirmed</dt>
                <dd>{overview.requirements.confirmed}</dd>
              </div>
              <div>
                <dt>P0</dt>
                <dd>{overview.requirements.p0}</dd>
              </div>
            </dl>
            <h3>Discovery progress</h3>
            <ul className="step-progress">
              {overview.discovery_steps.map((step) => (
                <li
                  key={step}
                  data-done={overview.discovery_completed.includes(step)}
                >
                  {overview.discovery_completed.includes(step) ? "✓ " : "○ "}
                  {STEP_LABELS[step] || step}
                </li>
              ))}
            </ul>
            {overview.missing.length > 0 && (
              <>
                <h3>Still missing</h3>
                <ul className="plain-list">
                  {overview.missing.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            )}
            {overview.open_questions.length > 0 && (
              <>
                <h3>Open questions</h3>
                <ul className="plain-list">
                  {overview.open_questions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            )}
            {overview.assumptions.length > 0 && (
              <>
                <h3>Assumptions</h3>
                <ul className="plain-list">
                  {overview.assumptions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            )}
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" onClick={() => onNavigate("discovery")}>
                {project.is_sample ? "View discovery" : "Continue discovery"}
              </Button>
              <Button
                variant="outline"
                onClick={() => onNavigate("requirements")}
              >
                {project.is_sample
                  ? "View requirements"
                  : "Manage requirements"}
              </Button>
            </div>
          </div>
        )}
      </section>
      {!project.is_sample && (
        <EditProject
          project={project}
          onChange={onChange}
          onDeleted={onDeleted}
        />
      )}
    </div>
  );
}

function EditProject({
  project,
  onChange,
  onDeleted,
}: {
  project: Project;
  onChange: (project: Project) => void;
  onDeleted: () => void;
}) {
  const [form, setForm] = useState<Required<ProjectUpdate>>({
    name: project.name,
    description: project.description,
    status: project.status,
  });
  const [error, setError] = useState<ApiError>();
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [confirming, setConfirming] = useState(false);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    if (!form.name?.trim()) {
      setError(requiredError("name", "Project name"));
      document.getElementById("edit-name")?.focus();
      return;
    }
    setSaving(true);
    setError(undefined);
    try {
      const updated = await api.updateProject(getProjectToken(), project.id, {
        ...form,
        name: form.name?.trim(),
      });
      onChange(updated);
      setNotice("Project saved.");
    } catch (cause) {
      setError(toApiError(cause));
    } finally {
      setSaving(false);
    }
  }
  async function remove() {
    setSaving(true);
    setError(undefined);
    try {
      await api.deleteProject(getProjectToken(), project.id);
      onDeleted();
    } catch (cause) {
      setError(toApiError(cause));
      setSaving(false);
    }
  }
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Edit project</h2>
      </div>
      <form className="project-form" onSubmit={save} noValidate>
        <ErrorBox error={error} />
        <label htmlFor="edit-name">
          Project name <span className="text-slate-500">(required)</span>
        </label>
        <input
          id="edit-name"
          value={form.name || ""}
          maxLength={200}
          required
          aria-invalid={Boolean(error?.fields.some((f) => f.field === "name"))}
          aria-describedby="edit-name-error"
          onChange={(event) => setForm({ ...form, name: event.target.value })}
        />
        <FieldError error={error} field="name" id="edit-name-error" />
        <label htmlFor="edit-description">Description</label>
        <textarea
          id="edit-description"
          rows={4}
          maxLength={10000}
          value={form.description || ""}
          aria-describedby="edit-description-error"
          onChange={(event) =>
            setForm({ ...form, description: event.target.value })
          }
        />
        <FieldError
          error={error}
          field="description"
          id="edit-description-error"
        />
        <label htmlFor="edit-status">Status</label>
        <select
          id="edit-status"
          value={form.status || "draft"}
          onChange={(event) =>
            setForm({
              ...form,
              status: event.target.value as Project["status"],
            })
          }
        >
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
        <Button type="submit" disabled={saving}>
          <Save size={16} />
          {saving ? "Saving…" : "Save changes"}
        </Button>
        <p role="status" className="text-sm text-emerald-800">
          {notice}
        </p>
        <div className="danger-zone">
          {!confirming ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirming(true)}
            >
              <Trash2 size={16} /> Delete project
            </Button>
          ) : (
            <>
              <p>
                Delete “{project.name}” and its discovery and requirements? This
                cannot be undone.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  onClick={() => void remove()}
                  disabled={saving}
                >
                  Confirm delete
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setConfirming(false)}
                >
                  Cancel
                </Button>
              </div>
            </>
          )}
        </div>
      </form>
    </section>
  );
}

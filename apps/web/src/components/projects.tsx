"use client";
import { useEffect, useState } from "react";
import { FolderKanban, Plus, ArrowDown } from "lucide-react";
import { api, ApiError, type Project } from "@/lib/api";
import { getProjectToken } from "@/lib/token";
import { Button } from "@/components/ui/button";

export function Projects() {
  const [items, setItems] = useState<Project[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ApiError>();
  const [notice, setNotice] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  function failure(cause: unknown) {
    setError(
      cause instanceof ApiError
        ? cause
        : new ApiError(
            "Browser storage is unavailable. Enable local storage to keep your private project token.",
          ),
    );
  }
  useEffect(() => {
    let disposed = false;
    async function load() {
      try {
        const result = await api.projects(getProjectToken());
        if (!disposed) {
          setItems(result.items);
          setCursor(result.next_cursor);
        }
      } catch (cause) {
        if (!disposed) failure(cause);
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void load();
    return () => {
      disposed = true;
    };
  }, []);
  async function loadMore() {
    setLoading(true);
    setError(undefined);
    try {
      const result = await api.projects(getProjectToken(), cursor || undefined);
      setItems((previous) =>
        cursor
          ? [
              ...new Map(
                [...previous, ...result.items].map((item) => [item.id, item]),
              ).values(),
            ]
          : result.items,
      );
      setCursor(result.next_cursor);
    } catch (cause) {
      failure(cause);
    } finally {
      setLoading(false);
    }
  }
  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(undefined);
    setNotice("");
    try {
      const project = await api.createProject(getProjectToken(), {
        name: name.trim(),
        description,
      });
      setItems((previous) => [
        project,
        ...previous.filter((item) => item.id !== project.id),
      ]);
      setName("");
      setDescription("");
      setNotice(`Created “${project.name}”.`);
    } catch (cause) {
      failure(cause);
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      {error && (
        <div className="error-box" role="alert">
          <strong>Something needs attention</strong>
          <p>{error.message}</p>
          {error.correlationId && (
            <p className="break-all">Correlation ID: {error.correlationId}</p>
          )}
          <Button variant="outline" size="sm" onClick={() => void loadMore()}>
            Retry loading projects
          </Button>
        </div>
      )}
      <div className="projects-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Your projects</h2>
            <span className="count-tag">{items.length}</span>
          </div>
          <p className="section-description">
            Only projects belonging to this browser are shown.
          </p>
          {loading && (
            <p role="status" className="p-6 text-sm text-slate-500">
              Loading projects…
            </p>
          )}
          {!loading && !items.length && !error && (
            <div className="empty-state">
              <span className="empty-icon">
                <FolderKanban size={28} />
              </span>
              <h3>No projects yet</h3>
              <p>
                Every well-built system starts with a question.
                <br />
                Create your first project to get started.
              </p>
            </div>
          )}
          <ul className="project-list">
            {items.map((item) => (
              <li key={item.id}>
                <span className="project-icon">
                  <FolderKanban size={20} />
                </span>
                <div className="min-w-0">
                  <h3 className="font-semibold break-words">{item.name}</h3>
                  <p className="text-sm text-slate-500 break-words">
                    {item.description || "No description yet"}
                  </p>
                </div>
                <span className="project-status">{item.status}</span>
              </li>
            ))}
          </ul>
          {cursor && (
            <div className="p-5">
              <Button
                variant="outline"
                onClick={() => void loadMore()}
                disabled={loading}
              >
                <ArrowDown size={16} />
                Load more
              </Button>
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Create a project</h2>
            <Plus size={18} className="text-slate-400" />
          </div>
          <form className="project-form" onSubmit={create}>
            <label htmlFor="name">
              Project name <span className="text-slate-500">(required)</span>
            </label>
            <input
              id="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={200}
              required
              placeholder="e.g. Restaurant booking platform"
            />
            <label htmlFor="description">
              Description <span className="text-slate-500">(optional)</span>
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={10000}
              rows={4}
              placeholder="What problem do you want to solve?"
            />
            <p className="text-xs leading-5 text-slate-500">
              Saved to your browser’s private workspace. Clearing browser
              storage loses access. Don’t include sensitive information.
            </p>
            <Button type="submit" disabled={saving || !name.trim()}>
              <Plus size={16} />
              {saving ? "Creating…" : "Create project"}
            </Button>
            <p role="status" className="text-sm text-emerald-800">
              {notice}
            </p>
          </form>
        </section>
      </div>
    </>
  );
}

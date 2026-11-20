"use client";
import { useEffect, useState } from "react";
import { api, type Artefact, type ApiError } from "@/lib/api";
import { getProjectToken, readProjectToken } from "@/lib/token";
import { downloadMarkdown } from "@/lib/download";
import { Button } from "@/components/ui/button";
import { ErrorBox, toApiError } from "@/components/form-error";
import { MarkdownPreview } from "@/components/markdown-preview";

export const ARTEFACT_KINDS: Record<Artefact["kind"], string> = {
  prd: "Product requirements",
  technical_design: "Technical design",
  architecture: "Architecture overview",
  adr: "Architecture decisions",
  data_model: "Data model",
  api_contract: "API contract",
  user_stories: "User stories",
  acceptance_criteria: "Acceptance criteria",
  non_functional_requirements: "Non-functional requirements",
  security: "Security considerations",
  test_strategy: "Test strategy",
  deployment: "Deployment plan",
  observability: "Observability plan",
};

export function Specifications({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const [items, setItems] = useState<Artefact[]>();
  const [selected, setSelected] = useState<string>();
  const [error, setError] = useState<ApiError>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [adrTitle, setAdrTitle] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let disposed = false;
    api
      .artefacts(readOnly ? undefined : readProjectToken(), projectId)
      .then((value) => {
        if (!disposed) {
          setItems(value);
          setSelected(value[0]?.id);
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
  const current = items?.find((a) => a.id === selected);
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
  async function generate(overwrite: boolean) {
    if (
      overwrite &&
      !window.confirm(
        "Overwrite edited artefacts? Your saved edits will be replaced by generated templates.",
      )
    )
      return;
    await action(async () => {
      const value = await api.generateArtefacts(
        getProjectToken(),
        projectId,
        overwrite,
      );
      setItems(value);
      setSelected(
        value.some((a) => a.id === selected) ? selected : value[0]?.id,
      );
      setNotice(
        "Specifications generated. Review TODOs and decisions before implementation.",
      );
    });
  }
  return (
    <div className="technology-page phase4-page">
      <div className="tech-title">
        <div>
          <h2>Specifications</h2>
          <p className="tech-muted">
            Deterministic templates, not AI inference. Review, refine and export
            your design.
          </p>
        </div>
        <div className="tech-badges">
          {!readOnly && (
            <>
              <Button disabled={busy} onClick={() => void generate(false)}>
                {items?.length
                  ? "Regenerate specifications"
                  : "Generate specifications"}
              </Button>
              {!!items?.length && (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => void generate(true)}
                >
                  Overwrite edited artefacts…
                </Button>
              )}
            </>
          )}
          <Button
            variant="outline"
            disabled={busy || !items?.length}
            onClick={() =>
              void action(async () =>
                downloadMarkdown(
                  await api.allArtefactsMarkdown(
                    readOnly ? undefined : readProjectToken(),
                    projectId,
                  ),
                  "specifications.md",
                ),
              )
            }
          >
            Download all artefacts .md
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
      {!items && !error && <p role="status">Loading specifications…</p>}
      {items?.length === 0 && (
        <p className="panel tech-panel">
          No specifications yet. Generate a starting point from your project
          context.
        </p>
      )}
      {!readOnly && (
        <form
          className="panel project-form phase4-form"
          onSubmit={(event) => {
            event.preventDefault();
            void action(async () => {
              const item = await api.createADR(
                getProjectToken(),
                projectId,
                adrTitle.trim(),
              );
              setItems((old) => [...(old || []), item]);
              setSelected(item.id);
              setAdrTitle("");
              setNotice("ADR added.");
            });
          }}
        >
          <label htmlFor="adr-title">New ADR title</label>
          <input
            id="adr-title"
            required
            maxLength={200}
            value={adrTitle}
            onChange={(e) => setAdrTitle(e.target.value)}
          />
          <Button variant="outline" disabled={busy || !adrTitle.trim()}>
            Add ADR
          </Button>
        </form>
      )}
      {!!items?.length && (
        <div className="specs-grid">
          <nav
            aria-label="Artefacts by kind"
            className="panel tech-panel artefact-nav"
          >
            {Object.entries(ARTEFACT_KINDS).map(([kind, label]) => {
              const group = items.filter((a) => a.kind === kind);
              return group.length ? (
                <div key={kind}>
                  <h3>{label}</h3>
                  {group.map((item) => (
                    <button
                      key={item.id}
                      aria-current={selected === item.id ? "true" : undefined}
                      disabled={busy}
                      onClick={() => setSelected(item.id)}
                    >
                      {item.title}{" "}
                      {item.edited && (
                        <span className="tech-badge">Edited</span>
                      )}
                    </button>
                  ))}
                </div>
              ) : null;
            })}
          </nav>
          {current && (
            <ArtefactEditor
              key={current.id + current.updated_at}
              item={current}
              readOnly={readOnly}
              busy={busy}
              onSave={(title, sections) =>
                void action(async () => {
                  const saved = await api.updateArtefact(
                    getProjectToken(),
                    projectId,
                    current.id,
                    { title, sections },
                  );
                  setItems((old) =>
                    old?.map((a) => (a.id === saved.id ? saved : a)),
                  );
                  setNotice("Artefact saved.");
                })
              }
              onDelete={() => {
                if (window.confirm("Delete this ADR?"))
                  void action(async () => {
                    await api.deleteArtefact(
                      getProjectToken(),
                      projectId,
                      current.id,
                    );
                    const remaining = items.filter((a) => a.id !== current.id);
                    setItems(remaining);
                    setSelected(remaining[0]?.id);
                    setNotice("ADR deleted.");
                  });
              }}
              onDownload={() =>
                void action(async () =>
                  downloadMarkdown(
                    await api.artefactMarkdown(
                      readOnly ? undefined : readProjectToken(),
                      projectId,
                      current.id,
                    ),
                    `${current.kind}-${current.id}.md`,
                  ),
                )
              }
            />
          )}
        </div>
      )}
    </div>
  );
}

function ArtefactEditor({
  item,
  readOnly,
  busy,
  onSave,
  onDelete,
  onDownload,
}: {
  item: Artefact;
  readOnly: boolean;
  busy: boolean;
  onSave: (title: string, sections: Artefact["sections"]) => void;
  onDelete: () => void;
  onDownload: () => void;
}) {
  const [title, setTitle] = useState(item.title);
  const [sections, setSections] = useState(item.sections);
  const dirty =
    title !== item.title ||
    sections.some(
      (section, index) => section.body !== item.sections[index]?.body,
    );
  const context = item.context as {
    name?: string;
    description?: string;
    requirements?: unknown[];
    technologies?: Record<string, string>;
    discovery?: Record<string, unknown>;
  };
  return (
    <section className="panel tech-panel" aria-label="Selected artefact">
      <div className="tech-title">
        <h3>{item.title}</h3>
        {item.edited && <span className="tech-badge">Edited</span>}
      </div>
      <details>
        <summary>Generated project context</summary>
        <p>
          {context.name} —{" "}
          {(context.description || "No description").slice(0, 240)}
        </p>
        <p>
          {String(
            context.discovery?.problem_statement || "TODO: define the problem",
          ).slice(0, 300)}
        </p>
        <p>
          Requirements: {context.requirements?.length || 0}. Technologies:{" "}
          {Object.values(context.technologies || {}).join(", ") || "TODO"}.
        </p>
      </details>
      {!readOnly && (
        <form
          className="project-form phase4-form"
          onSubmit={(e) => {
            e.preventDefault();
            onSave(title.trim(), sections);
          }}
        >
          <label htmlFor="artefact-title">Artefact title</label>
          <input
            id="artefact-title"
            required
            maxLength={200}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          {sections.map((s, i) => (
            <div key={s.key}>
              <label htmlFor={`section-${s.key}`}>{s.heading}</label>
              <textarea
                id={`section-${s.key}`}
                rows={6}
                value={s.body}
                onChange={(e) =>
                  setSections((old) =>
                    old.map((section, j) =>
                      i === j ? { ...section, body: e.target.value } : section,
                    ),
                  )
                }
              />
            </div>
          ))}
          <div className="tech-badges">
            <Button disabled={busy || !title.trim()}>Save artefact</Button>
            {item.kind === "adr" && (
              <Button
                type="button"
                variant="outline"
                disabled={busy}
                onClick={onDelete}
              >
                Delete ADR
              </Button>
            )}
          </div>
        </form>
      )}
      <Button variant="outline" disabled={busy} onClick={onDownload}>
        Download this artefact .md
      </Button>
      <section aria-label="Markdown preview" className="spec-preview">
        <h3>Markdown preview{dirty ? " · unsaved draft" : ""}</h3>
        <h4>{title}</h4>
        {sections.map((s) => (
          <section key={s.key}>
            <h4>{s.heading}</h4>
            <MarkdownPreview text={s.body} />
          </section>
        ))}
      </section>
    </section>
  );
}

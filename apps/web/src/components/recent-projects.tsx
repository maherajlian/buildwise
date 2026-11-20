"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ErrorBox, toApiError } from "@/components/form-error";
import { api, type ApiError, type RecentProject } from "@/lib/api";
import { readProjectToken } from "@/lib/token";

export function RecentProjects() {
  const [projects, setProjects] = useState<RecentProject[]>();
  const [error, setError] = useState<ApiError>();
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    const token = readProjectToken();
    void (token ? api.dashboard(token) : Promise.resolve([]))
      .then((items) => {
        if (active) setProjects(items);
      })
      .catch((cause) => {
        if (active) setError(toApiError(cause));
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  return (
    <section className="panel tech-panel mb-6" aria-labelledby="recent-projects">
      <div className="tech-title">
        <h2 id="recent-projects" className="font-semibold">
          Recent projects
        </h2>
        <Link className="tech-link" href="/projects/">
          All projects →
        </Link>
      </div>
      <ErrorBox
        error={error}
        action="Retry loading projects"
        onAction={() => {
          setError(undefined);
          setAttempt((value) => value + 1);
        }}
      />
      {!projects && !error && <p role="status">Loading recent projects…</p>}
      {projects?.length === 0 && (
        <p className="text-sm text-slate-600">
          No projects in this browser yet. Start one or explore the public sample above.
        </p>
      )}
      {!!projects?.length && (
        <ul className="grid gap-3 md:grid-cols-3">
          {projects.map((project) => (
            <li key={project.id} className="rounded-lg border p-4 text-sm">
              <h3 className="break-words font-semibold">
                <Link className="tech-link" href={`/projects/view/?id=${project.id}`}>
                  {project.name}
                </Link>
              </h3>
              <dl className="mt-2 space-y-1">
                <div><dt className="inline font-medium">Stage: </dt><dd className="inline">{project.stage}</dd></div>
                <div><dt className="inline font-medium">Requirements to review: </dt><dd className="inline">{project.outstanding_requirements}</dd></div>
                <div><dt className="inline font-medium">Open tasks: </dt><dd className="inline">{project.open_tasks}</dd></div>
                <div>
                  <dt className="font-medium">Recent artefacts</dt>
                  <dd className="break-words">
                    {project.recent_artefacts.join(" · ") || "None yet"}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

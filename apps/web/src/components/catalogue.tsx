"use client";
import { useEffect, useState } from "react";
import { api, type ApiError, type Catalogue } from "@/lib/api";
import { ErrorBox, toApiError } from "@/components/form-error";
import { CATEGORY_LABELS, TechnologyDetails } from "@/components/technology";

export function TechnologyCatalogue() {
  const [catalogue, setCatalogue] = useState<Catalogue>();
  const [error, setError] = useState<ApiError>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let disposed = false;
    api
      .catalogue()
      .then((value) => {
        if (!disposed) {
          setCatalogue(value);
          setError(undefined);
        }
      })
      .catch((cause) => {
        if (!disposed) setError(toApiError(cause));
      });
    return () => {
      disposed = true;
    };
  }, [attempt]);
  return (
    <div className="technology-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">CURATED ENGINEERING OPTIONS</div>
          <h1>Technology catalogue</h1>
          <p>
            The same versioned catalogue used by the recommendation engine. A
            starting point for decisions, not an objective benchmark.
          </p>
        </div>
      </div>
      <ErrorBox
        error={error}
        action="Retry"
        onAction={() => setAttempt((v) => v + 1)}
      />
      {!catalogue && !error && <p role="status">Loading catalogue…</p>}
      {catalogue && (
        <>
          <div className="panel tech-panel">
            <div className="tech-badges">
              <span className="tech-badge">
                Catalogue {catalogue.catalogue_version}
              </span>
              <span className="tech-badge">
                Rules {catalogue.rules_version}
              </span>
              <span className="tech-badge">
                {catalogue.entries.length} technologies
              </span>
            </div>
            <p>
              Pricing/free-tier claims require verification. Review current
              provider terms, licensing, limits and regional availability before
              choosing.
            </p>
          </div>
          {catalogue.entries.length === 0 && (
            <p>No technologies available yet.</p>
          )}
          <nav aria-label="Catalogue categories" className="tech-badges">
            {catalogue.categories?.map((category) => (
              <a
                className="tech-badge"
                key={category}
                href={`#catalogue-${category}`}
              >
                {CATEGORY_LABELS[category]}
              </a>
            ))}
          </nav>
          {catalogue.categories?.map((category) => (
            <section
              key={category}
              aria-labelledby={`catalogue-${category}`}
              className="catalogue-category"
            >
              <h2 id={`catalogue-${category}`}>{CATEGORY_LABELS[category]}</h2>
              {category === "ai_layer" && (
                <p className="tech-disclaimer">
                  Optional, may incur cost. AI candidates are never enabled by
                  default or by a detected keyword.
                </p>
              )}
              <div className="catalogue-grid">
                {catalogue.entries
                  .filter((entry) => entry.category === category)
                  .map((entry) => (
                    <article key={entry.id} className="panel tech-panel">
                      <h3>{entry.name}</h3>
                      <TechnologyDetails entry={entry} />
                      <p className="tech-muted">
                        Last reviewed:{" "}
                        <time dateTime={entry.last_reviewed}>
                          {entry.last_reviewed}
                        </time>
                      </p>
                      {!!entry.links?.length && (
                        <ul className="plain-list">
                          {entry.links.map((link, i) => (
                            <li key={link}>
                              <a href={link} className="tech-link">
                                {entry.name} documentation
                                {entry.links!.length > 1 ? ` ${i + 1}` : ""}
                              </a>
                            </li>
                          ))}
                        </ul>
                      )}
                    </article>
                  ))}
              </div>
            </section>
          ))}
        </>
      )}
    </div>
  );
}

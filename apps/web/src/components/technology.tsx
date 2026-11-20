import type { CatalogueEntry, ScoredEntry, Signal } from "@/lib/api";

export const CATEGORY_LABELS: Record<CatalogueEntry["category"], string> = {
  frontend: "Frontend",
  backend: "Backend",
  database: "Database",
  cache_queue: "Cache / queue",
  auth: "Authentication",
  hosting: "Hosting",
  ci_cd: "CI/CD",
  observability: "Observability",
  integrations: "Integrations",
  ai_layer: "AI layer",
};

export function SignalEvidence({ signal }: { signal: Signal }) {
  return (
    <div className="signal-evidence">
      <p>
        <strong>{signal.label}:</strong>{" "}
        {Array.isArray(signal.value)
          ? signal.value.join(", ") || "None"
          : signal.value}{" "}
        <span className="tech-badge">{signal.source}</span>
      </p>
      {!!signal.evidence?.length ? (
        <ul className="evidence-list">
          {signal.evidence?.map((item, i) => (
            <li key={`${item.field}-${i}`}>
              <code>{item.field}</code>
              <blockquote>“{item.excerpt}”</blockquote>
            </li>
          ))}
        </ul>
      ) : (
        <p className="tech-muted">No matching evidence; default assumption.</p>
      )}
    </div>
  );
}

export function TextList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="tech-list">
      <h4>{title}</h4>
      <ul className="plain-list">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function TechnologyDetails({ entry }: { entry: CatalogueEntry }) {
  return (
    <>
      <p>{entry.summary}</p>
      <div className="tech-badges">
        <span className="tech-badge">
          {entry.cost_category} · verify pricing
        </span>
        <span className="tech-badge">
          Complexity: {entry.operational_complexity}
        </span>
        {entry.optional && (
          <span className="tech-badge">Optional, may incur cost</span>
        )}
      </div>
      <p className="tech-muted">{entry.cost_note}</p>
      <p>
        <strong>Operational burden:</strong> {entry.operational_burden}
      </p>
      <TextList title="Strengths" items={entry.strengths} />
      <TextList title="Constraints" items={entry.constraints} />
      <TextList title="Trade-offs" items={entry.trade_offs} />
      <TextList title="Assumptions" items={entry.assumptions} />
      <TextList title="Change conditions" items={entry.change_conditions} />
    </>
  );
}

export function ScoredTechnology({ entry }: { entry: ScoredEntry }) {
  return (
    <div className="scored-technology">
      <div className="tech-title">
        <h3>{entry.name}</h3>
        <span className="tech-badge">Score {entry.score}</span>
      </div>
      <TechnologyDetails entry={entry} />
      <div className="rule-explanations">
        <h4>Why this appears</h4>
        <p>{entry.reason}</p>
        {(
          [
            ["Positive matches", entry.positive_matches],
            ["Negative matches", entry.negative_matches],
          ] as const
        ).map(([label, matches]) => (
          <div key={label} className="rule-group">
            <h5>{label}</h5>
            {matches.length ? (
              <ul>
                {matches.map((match) => (
                  <li key={match.rule_id} className="rule-match">
                    <p>
                      <strong>{match.rule_id}</strong> ·{" "}
                      {match.weight > 0 ? "+" : ""}
                      {match.weight}
                    </p>
                    <p>{match.reason}</p>
                    {match.signals.map((signal) => (
                      <SignalEvidence key={signal.id} signal={signal} />
                    ))}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="tech-muted">No {label.toLowerCase()}.</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

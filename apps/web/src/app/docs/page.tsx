import Link from "next/link";

const repository = "https://github.com/maherajlian/buildwise";
const references = [
  { title: "Source and local setup", href: repository, detail: "Run the browser, API and database from a clean checkout." },
  { title: "Architecture and decisions", href: `${repository}/tree/main/docs/architecture`, detail: "See the deployed system boundaries, request flow and ADRs." },
  { title: "Free-tier assessment", href: `${repository}/blob/main/docs/hosting/free-tier-assessment.md`, detail: "Check provider quotas, cost controls and fallback options." },
  { title: "Observability runbook", href: `${repository}/blob/main/docs/operations/observability.md`, detail: "Run the local telemetry stack and diagnose a controlled fault." },
];

export default function Page() {
  return (
    <>
      <div className="eyebrow">BUILDWISE REFERENCE</div>
      <div className="page-heading">
        <div>
          <h1>Documentation</h1>
          <p>How to use BuildWise and how the public demo is built.</p>
        </div>
      </div>
      <div className="technology-page">
        <section className="panel tech-panel">
          <h2>Using the demo</h2>
          <p>
            <Link href="/guides/#walkthrough" className="tech-link">
              Follow the demo walkthrough
            </Link>{" "}
            or explore the <Link href="/catalogue/" className="tech-link">versioned technology catalogue</Link>.
          </p>
          <h3>Known limitations</h3>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-600">
            <li>Use synthetic data only. There are no accounts, shared workspaces or token recovery.</li>
            <li>Projects inactive for 30 days are eligible for deletion. Export work you want to keep.</li>
            <li>Specifications and tests are suggestions. BuildWise does not ship your code, run your tests or invoke AI services.</li>
            <li>Free hosting may sleep or hit quotas. The demo has no uptime guarantee.</li>
          </ul>
        </section>
        <section className="panel tech-panel">
          <h2>Developer reference</h2>
          <ul className="grid gap-4 md:grid-cols-2">
            {references.map((reference) => (
              <li key={reference.href}>
                <a className="tech-link font-semibold" href={reference.href}>
                  {reference.title} ↗
                </a>
                <p className="text-sm text-slate-600">{reference.detail}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}

import Link from "next/link";

const stages = [
  {
    title: "Start with the problem",
    tab: "discovery",
    link: "Read the project brief",
    detail: "See why the fictional restaurants lose bookings, who uses the product, and how the team would measure success. The final discovery step turns the answers into a structured brief.",
  },
  {
    title: "Define what success looks like",
    tab: "requirements",
    link: "Review the sample requirements",
    detail: "Compare the booking and reminder requirements. Write criteria someone can test, such as what happens when a diner selects an available slot.",
  },
  {
    title: "Compare technologies",
    tab: "architecture",
    link: "Inspect recommendations and alternatives",
    detail: "Open a recommendation to see matched rules, costs, trade-offs and alternatives. Review provider terms before adopting any suggestion.",
  },
  {
    title: "Make the work buildable",
    tab: "specs",
    link: "Read the PRD and technical design",
    detail: "Use specs to review the PRD, technical design, stories and acceptance criteria. In the Plan tab, open a task to see implementation notes and dependencies.",
  },
  {
    title: "Plan validation and operations",
    tab: "testing",
    link: "Review proposed tests",
    detail: "Review the suggested test cases. Under Operations, find the risk register, SLOs, and links to deployment and observability plans. Proposed tests have not been run.",
  },
  {
    title: "Take the work with you",
    tab: "overview",
    link: "Open Overview to export the pack",
    detail: "Select Export project pack (Markdown) to download the brief, recommendations, current specifications, build tasks and operating plans in one file.",
  },
];

export default function Page() {
  return (
    <>
      <div className="eyebrow">LEARN BY EXAMPLE</div>
      <div className="page-heading">
        <div>
          <h1>Engineering guides</h1>
          <p>Follow a worked example, then use the same steps on your own project.</p>
        </div>
      </div>
      <section id="walkthrough" className="technology-page">
        <h2>Public demo walkthrough</h2>
        <p className="text-sm text-slate-600">
          The restaurant booking sample is fictional and read-only. You do not
          need an account and nothing you do changes the shared example.
        </p>
        <ol className="grid list-decimal gap-4 pl-6 md:grid-cols-2">
          {stages.map((stage) => (
            <li key={stage.tab} className="panel p-5">
              <h3>{stage.title}</h3>
              <p className="my-2 text-sm text-slate-600">{stage.detail}</p>
              <Link
                className="tech-link text-sm"
                href={`/projects/view/?id=sample&tab=${stage.tab}`}
              >
                {stage.link} →
              </Link>
            </li>
          ))}
        </ol>
        <section className="panel tech-panel">
          <h2>Try the workflow on your own project</h2>
          <p>
            <Link href="/projects/" className="tech-link">Create a project</Link>{" "}
            using synthetic data. Fill in discovery, add a P0 requirement with a
            testable criterion, then generate specifications before generating
            the build plan. Edit the drafts and export the pack when ready.
          </p>
        </section>
      </section>
    </>
  );
}

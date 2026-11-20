import Link from "next/link";
import {
  ArrowRight,
  Plus,
  Compass,
  Layers3,
  ListChecks,
  ArrowUpRight,
  FolderKanban,
  GitBranch,
  CheckCheck,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiStatus } from "@/components/api-status";
export default function Dashboard() {
  return (
    <>
      <div className="eyebrow">YOUR ENGINEERING WORKBENCH</div>
      <div className="page-heading">
        <div>
          <h1>Build with a clearer picture.</h1>
          <p>
            Turn your next idea into a plan you can explain, build and operate.
          </p>
        </div>
        <Button asChild>
          <Link href="/projects/">
            <Plus size={16} />
            New project
          </Link>
        </Button>
      </div>
      <ApiStatus />
      <section className="hero-card">
        <div className="hero-copy">
          <span className="hero-label">
            <span className="dot" />A BETTER STARTING POINT
          </span>
          <h2>
            Good software starts
            <br />
            before the first line of code.
          </h2>
          <p>
            Clarify the problem. Explore the trade-offs.
            <br />
            Build a practical path from idea to deployment.
          </p>
          <Button asChild>
            <Link href="/projects/">
              Start a project
              <ArrowRight size={16} />
            </Link>
          </Button>
          <span className="hero-footnote">
            No prompts. No black boxes. Just a thoughtful process.
          </span>
        </div>
        <div className="blueprint-art" aria-hidden="true">
          <span className="diagram-kicker">THE BUILDWISE PATH</span>
          {[
            "Understand the problem",
            "Make informed decisions",
            "Build with confidence",
          ].map((text, index) => (
            <div key={text} className="diagram-step">
              <span>0{index + 1}</span>
              <div>
                {text}
                <small>
                  {
                    [
                      "Discovery & requirements",
                      "Architecture & specifications",
                      "Delivery & observability",
                    ][index]
                  }
                </small>
              </div>
              <CheckCheck size={18} />
            </div>
          ))}
          <div className="diagram-bottom">
            <span className="dot" />
            Explainable by design
          </div>
        </div>
      </section>
      <section aria-label="Workspace summary" className="summary-grid">
        {[
          {
            icon: FolderKanban,
            label: "Projects",
            text: "Your ideas, organized",
            href: "/projects/",
          },
          {
            icon: GitBranch,
            label: "Architecture",
            text: "Decisions with context",
            href: "/catalogue/",
          },
          {
            icon: ListChecks,
            label: "Delivery plans",
            text: "A practical next step",
            href: "/guides/",
          },
          {
            icon: FileText,
            label: "Specifications",
            text: "Clarity you can share",
            href: "/docs/",
          },
        ].map(({ icon: Icon, ...item }) => (
          <Link key={item.label} href={item.href} className="summary-card">
            <Icon size={19} />
            <ArrowUpRight size={15} className="ml-auto text-slate-400" />
            <h2>{item.label}</h2>
            <p>{item.text}</p>
          </Link>
        ))}
      </section>
      <div className="section-title">
        <div>
          <h2>A little structure. A lot more clarity.</h2>
          <p>
            A connected workflow, from the first question to the live system.
          </p>
        </div>
        <span className="tiny-label text-slate-500">HOW IT WORKS</span>
      </div>
      <section className="steps-grid" aria-label="How BuildWise works">
        {[
          {
            icon: Compass,
            title: "Discover what matters",
            text: "Define the problem, the people and the constraints before choosing a solution.",
          },
          {
            icon: Layers3,
            title: "Design with intention",
            text: "Compare technologies and understand the reasoning behind every trade-off.",
          },
          {
            icon: ListChecks,
            title: "Make the work buildable",
            text: "Turn decisions into specifications, testable tasks and an operations plan.",
          },
        ].map(({ icon: Icon, title, text }, i) => (
          <article className="step-card" key={title}>
            <div className="flex justify-between">
              <Icon size={22} />
              <span className="step-number">0{i + 1}</span>
            </div>
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </section>
      <div className="foundation-note">
        <span className="dot" />
        <p>
          <strong>A foundation, not a finished product.</strong> Project storage
          is live. Discovery, recommendations and planning are coming in later
          phases.
        </p>
      </div>
    </>
  );
}

import Link from "next/link";
import { ArrowLeft, Construction } from "lucide-react";
import { Button } from "@/components/ui/button";
export function Placeholder({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <>
      <div className="eyebrow">THE WORKSPACE IS GROWING</div>
      <div className="page-heading">
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </div>
      <section className="placeholder-panel">
        <span className="empty-icon">
          <Construction size={30} />
        </span>
        <span className="phase-label">PLANNED · NOT AVAILABLE YET</span>
        <h2>A thoughtful next step.</h2>
        <p>
          This part of BuildWise is planned for a later phase.
          <br />
          For now, create a project and explore the foundation.
        </p>
        <Button asChild variant="outline">
          <Link href="/projects/">
            <ArrowLeft size={16} />
            Go to projects
          </Link>
        </Button>
      </section>
    </>
  );
}

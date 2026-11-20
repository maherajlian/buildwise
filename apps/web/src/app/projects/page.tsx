import { Projects } from "@/components/projects";
export default function ProjectsPage() {
  return (
    <>
      <div className="eyebrow">YOUR WORK, TAKING SHAPE</div>
      <div className="page-heading">
        <div>
          <h1>Projects</h1>
          <p>
            A dedicated space for each idea, from the first question onward.
          </p>
        </div>
      </div>
      <Projects />
    </>
  );
}

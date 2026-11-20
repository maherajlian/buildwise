import type { Artefact, Plan } from "@/lib/api";

export const artefact: Artefact = {
  id: "a1",
  project_id: "p1",
  kind: "prd",
  title: "Product requirements document",
  edited: false,
  sections: [
    { key: "problem", heading: "Problem", body: "Launches collide" },
    { key: "goals", heading: "Goals", body: "- Reliable launches" },
  ],
  context: {
    name: "Orbit",
    description: "Coordinate launches",
    requirements: [],
    technologies: { backend: "FastAPI" },
  },
  created_at: "2026-11-20T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
};
export const plan: Plan = {
  epics: [
    {
      id: "e1",
      project_id: "p1",
      title: "Foundation",
      description: "Set up Orbit",
      position: 0,
    },
  ],
  tasks: [
    {
      id: "t1",
      project_id: "p1",
      epic_id: "e1",
      key: "T-001",
      title: "Setup",
      description: "Repository setup",
      priority: "P0",
      status: "ready",
      implementation_notes: "Use FastAPI",
      acceptance_criteria: ["Checks pass"],
      skill: "Architecture",
      workflow: "pair: review changes",
      depends_on: [],
      requirement_id: null,
    },
    {
      id: "t2",
      project_id: "p1",
      epic_id: "e1",
      key: "T-002",
      title: "Implement",
      description: "Implement feature",
      priority: "P1",
      status: "backlog",
      implementation_notes: "Review design",
      acceptance_criteria: ["Feature works"],
      skill: "Engineering",
      workflow: "human: approve",
      depends_on: ["t1"],
      requirement_id: null,
    },
  ],
  validation: { valid: true, errors: [] },
};

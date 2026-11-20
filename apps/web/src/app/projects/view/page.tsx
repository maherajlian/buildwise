import { Suspense } from "react";
import { Workspace } from "@/components/workspace";

export default function ProjectWorkspacePage() {
  return (
    <Suspense
      fallback={
        <p role="status" className="text-sm text-slate-500">
          Loading project…
        </p>
      }
    >
      <Workspace />
    </Suspense>
  );
}

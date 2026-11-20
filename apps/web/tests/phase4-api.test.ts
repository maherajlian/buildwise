import { expect, it, vi } from "vitest";
import { createApi } from "@/lib/api";

it("fetches Markdown as text with owner headers, and public exports without a token", async () => {
  const fetcher = vi.fn<typeof fetch>().mockImplementation(
    async () =>
      new Response("# Orbit\n\nComplete", {
        headers: { "Content-Type": "text/markdown" },
      }),
  );
  const client = createApi("http://localhost:8000", fetcher);
  expect(await client.artefactMarkdown("owner", "p1", "a1")).toBe(
    "# Orbit\n\nComplete",
  );
  expect(await client.allArtefactsMarkdown("owner", "p1")).toContain("Orbit");
  expect(await client.planMarkdown(undefined, "sample")).toContain("Orbit");
  const requests = fetcher.mock.calls.map(([request]) => request as Request);
  expect(requests[0].url).toBe(
    "http://localhost:8000/api/v1/projects/p1/artefacts/a1/markdown",
  );
  expect(requests[0].headers.get("X-Project-Token")).toBe("owner");
  expect(requests[1].url).toBe(
    "http://localhost:8000/api/v1/projects/p1/artefacts/export/markdown",
  );
  expect(requests[2].headers.has("X-Project-Token")).toBe(false);
});

it("sends typed generation and task updates and preserves dependency errors", async () => {
  const fetcher = vi
    .fn<typeof fetch>()
    .mockImplementation(
      async () =>
        new Response("{}", { headers: { "Content-Type": "application/json" } }),
    );
  const client = createApi("http://localhost:8000", fetcher);
  await client.generateArtefacts("owner", "p1", true);
  await client.generatePlan("owner", "p1");
  await client.updateTask("owner", "p1", "t1", { status: "done" });
  const requests = fetcher.mock.calls.map(([request]) => request as Request);
  expect(await requests[0].json()).toEqual({ overwrite_edited: true });
  expect(await requests[2].json()).toEqual({ status: "done" });
  fetcher.mockResolvedValueOnce(
    new Response(
      JSON.stringify({
        error: {
          message: "Dependency cycle detected",
          correlation_id: "cycle-id",
        },
      }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    ),
  );
  await expect(
    client.updateTask("owner", "p1", "t1", { depends_on: ["t2"] }),
  ).rejects.toMatchObject({
    message: "Dependency cycle detected",
    status: 422,
    correlationId: "cycle-id",
  });
});

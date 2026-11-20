import { expect, it, vi } from "vitest";
import { createApi } from "@/lib/api";

it("combines operation lists and uses typed owner-authenticated CRUD and generation", async () => {
  const fetcher = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const request = input as Request;
    if (request.method === "DELETE") return new Response(null, { status: 204 });
    return new Response(request.method === "GET" ? "[]" : "{}", {
      headers: { "Content-Type": "application/json" },
    });
  });
  const client = createApi("http://localhost:8000", fetcher);
  expect(await client.operations(undefined, "sample")).toEqual({
    test_cases: [],
    risks: [],
    slos: [],
  });
  await client.generateOperations("owner", "p1", true);
  await client.createTest("owner", "p1", {
    category: "unit",
    title: "Validate input",
  });
  await client.updateTest("owner", "p1", "t1", {
    status: "passed",
    result_notes: "Run 42 passed",
  });
  await client.deleteTest("owner", "p1", "t1");
  await client.createRisk("owner", "p1", { title: "Outage" });
  await client.updateRisk("owner", "p1", "r1", { owner: "Team" });
  await client.deleteRisk("owner", "p1", "r1");
  await client.createSLO("owner", "p1", {
    name: "Availability",
    sli: "Successful requests",
    target: "99.5%",
  });
  await client.updateSLO("owner", "p1", "s1", { status: "adopted" });
  await client.deleteSLO("owner", "p1", "s1");
  const requests = fetcher.mock.calls.map(([request]) => request as Request);
  expect(
    requests.slice(0, 3).map((request) => new URL(request.url).pathname),
  ).toEqual([
    "/api/v1/projects/sample/test-cases",
    "/api/v1/projects/sample/risks",
    "/api/v1/projects/sample/slos",
  ]);
  expect(
    requests
      .slice(0, 3)
      .every((request) => !request.headers.has("X-Project-Token")),
  ).toBe(true);
  expect(
    requests
      .slice(3)
      .every((request) => request.headers.get("X-Project-Token") === "owner"),
  ).toBe(true);
  expect(await requests[3].json()).toEqual({ replace_edited: true });
  expect(await requests[5].json()).toEqual({
    status: "passed",
    result_notes: "Run 42 passed",
  });
  expect(requests.slice(4).map((request) => request.method)).toEqual([
    "POST",
    "PATCH",
    "DELETE",
    "POST",
    "PATCH",
    "DELETE",
    "POST",
    "PATCH",
    "DELETE",
  ]);
  expect(requests[5].url).toContain("/test-cases/t1");
  expect(requests[8].url).toContain("/risks/r1");
  expect(requests[11].url).toContain("/slos/s1");
});

it("exports operations Markdown/CSV as text and preserves API 422 evidence errors", async () => {
  const fetcher = vi
    .fn<typeof fetch>()
    .mockImplementation(async () => new Response("Plan text"));
  const client = createApi("http://localhost:8000", fetcher);
  for (const kind of ["operations", "test-cases", "risks", "slos"] as const) {
    expect(await client.operationsExport(undefined, "sample", kind)).toBe(
      "Plan text",
    );
  }
  expect(
    await client.operationsExport("owner", "p1", "test-cases", "csv"),
  ).toBe("Plan text");
  const requests = fetcher.mock.calls.map(([request]) => request as Request);
  expect(requests.map((request) => new URL(request.url).pathname)).toEqual([
    "/api/v1/projects/sample/operations/export/markdown",
    "/api/v1/projects/sample/test-cases/export/markdown",
    "/api/v1/projects/sample/risks/export/markdown",
    "/api/v1/projects/sample/slos/export/markdown",
    "/api/v1/projects/p1/test-cases/export/csv",
  ]);
  fetcher.mockResolvedValueOnce(
    new Response(
      JSON.stringify({
        error: {
          message: "Result notes are required",
          correlation_id: "result-id",
        },
      }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    ),
  );
  await expect(
    client.updateTest("owner", "p1", "t1", { status: "failed" }),
  ).rejects.toMatchObject({
    status: 422,
    message: "Result notes are required",
    correlationId: "result-id",
  });
});

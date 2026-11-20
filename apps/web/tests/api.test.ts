import { describe, it, expect, vi } from "vitest";
import { ApiError, createApi } from "@/lib/api";
describe("typed API client", () => {
  it("reads public catalogue and recommendation endpoints and puts owner overrides", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockImplementation(
        async () =>
          new Response("{}", {
            headers: { "Content-Type": "application/json" },
          }),
      );
    const client = createApi("http://localhost:8000", fetcher);
    await client.catalogue();
    await client.recommendations(undefined, "sample");
    await client.recommendationInputs("owner", "p1");
    await client.saveRecommendationInputs("owner", "p1", { budget: "zero" });
    const requests = fetcher.mock.calls.map(([request]) => request as Request);
    expect(requests[0].url).toBe("http://localhost:8000/api/v1/catalogue");
    expect(requests[1].headers.has("X-Project-Token")).toBe(false);
    expect(requests[2].headers.get("X-Project-Token")).toBe("owner");
    expect(requests[3].method).toBe("PUT");
    expect(await requests[3].json()).toEqual({ overrides: { budget: "zero" } });
  });
  it("sends project owner token and parses the page", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ items: [], next_cursor: null }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createApi("http://localhost:8000", fetcher);
    expect(await client.projects("a".repeat(43))).toEqual({
      items: [],
      next_cursor: null,
    });
    const request = fetcher.mock.calls[0][0] as Request;
    expect(request.headers.get("X-Project-Token")).toBe("a".repeat(43));
    expect(request.url).toContain("limit=20");
  });
  it("preserves standard error correlation IDs", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "database_unavailable",
            message: "Service unavailable",
            correlation_id: "test-id",
          },
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    );
    await expect(
      createApi("http://localhost", fetcher).ready(),
    ).rejects.toMatchObject({
      message: "Service unavailable",
      correlationId: "test-id",
    });
  });
  it("handles network errors and invalid JSON without exposing raw data", async () => {
    for (const fetcher of [
      vi.fn<typeof fetch>().mockRejectedValue(new Error("secret")),
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response("not-json", { status: 502 })),
    ]) {
      await expect(
        createApi("http://localhost", fetcher).health(),
      ).rejects.toThrow(ApiError);
      await expect(
        createApi("http://localhost", fetcher).health(),
      ).rejects.not.toThrow("secret");
    }
  });
  it("posts the project body and owner header", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response('{"id":"one"}', {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await createApi("http://localhost", fetcher).createProject("owner", {
      name: "New project",
    });
    const request = fetcher.mock.calls[0][0] as Request;
    expect(request.method).toBe("POST");
    expect(request.headers.get("X-Project-Token")).toBe("owner");
    expect(await request.json()).toEqual({ name: "New project" });
  });
  it("accepts empty 204 responses for deletes", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 204 }));
    const client = createApi("http://localhost", fetcher);
    await expect(client.deleteProject("t", "p")).resolves.toBeUndefined();
    await expect(
      client.deleteRequirement("t", "p", "r"),
    ).resolves.toBeUndefined();
  });
  it("rejects an empty success response", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 204 }));
    await expect(
      createApi("http://localhost", fetcher).health(),
    ).rejects.toThrow("empty response");
  });
  it("uses the response correlation header for nonstandard errors", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("{}", {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "X-Correlation-ID": "header-id",
        },
      }),
    );
    await expect(
      createApi("http://localhost", fetcher).health(),
    ).rejects.toMatchObject({
      message: "API request failed (500)",
      correlationId: "header-id",
    });
  });
});

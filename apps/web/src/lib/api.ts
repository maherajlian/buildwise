import createClient from "openapi-fetch";
import type { paths, components } from "../../../../packages/shared-types/api";

export type Project = components["schemas"]["ProjectRead"];
export type ProjectPage = components["schemas"]["ProjectPage"];
export class ApiError extends Error {
  constructor(
    message: string,
    public correlationId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export function createApi(
  baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  fetcher: typeof fetch = fetch,
) {
  const client = createClient<paths>({ baseUrl, fetch: fetcher });
  async function checked<T>(
    operation: () => Promise<{ data?: T; error?: unknown; response: Response }>,
  ): Promise<T> {
    try {
      const { data, error, response } = await operation();
      if (error || !response.ok) {
        const detail = error as
          components["schemas"]["ErrorResponse"] | undefined;
        throw new ApiError(
          detail?.error?.message || `API request failed (${response.status})`,
          detail?.error?.correlation_id ||
            response.headers.get("X-Correlation-ID") ||
            undefined,
        );
      }
      if (data === undefined)
        throw new ApiError("The API returned an empty response.");
      return data;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError("Cannot reach the API. Please try again shortly.");
    }
  }
  return {
    health: (signal?: AbortSignal) =>
      checked(() => client.GET("/health", { signal })),
    ready: (signal?: AbortSignal) =>
      checked(() => client.GET("/ready", { signal })),
    projects: (token: string, cursor?: string) =>
      checked<ProjectPage>(() =>
        client.GET("/api/v1/projects", {
          params: {
            header: { "X-Project-Token": token },
            query: { limit: 20, ...(cursor ? { cursor } : {}) },
          },
        }),
      ),
    createProject: (
      token: string,
      body: components["schemas"]["ProjectCreate"],
    ) =>
      checked<Project>(() =>
        client.POST("/api/v1/projects", {
          params: { header: { "X-Project-Token": token } },
          body,
        }),
      ),
  };
}
export const api = createApi();

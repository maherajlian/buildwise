import createClient from "openapi-fetch";
import type { paths, components } from "../../../../packages/shared-types/api";

export type Project = components["schemas"]["ProjectRead"];
export type ProjectPage = components["schemas"]["ProjectPage"];
export type ProjectUpdate = components["schemas"]["ProjectUpdate"];
export type ProjectOverview = components["schemas"]["ProjectOverview"];
export type Discovery = components["schemas"]["DiscoveryRead"];
export type DiscoveryAnswers = components["schemas"]["DiscoveryAnswers"];
export type DiscoveryWrite = components["schemas"]["DiscoveryWrite"];
export type Requirement = components["schemas"]["RequirementRead"];
export type RequirementCreate = components["schemas"]["RequirementCreate"];
export type RequirementUpdate = components["schemas"]["RequirementUpdate"];
export type FieldError = components["schemas"]["FieldError"];
export class ApiError extends Error {
  constructor(
    message: string,
    public correlationId?: string,
    public fields: FieldError[] = [],
    public status?: number,
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
    allowEmpty = false,
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
          detail?.error?.fields || [],
          response.status,
        );
      }
      if (allowEmpty && response.status === 204) return undefined as T;
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
    sample: () => checked<Project>(() => client.GET("/api/v1/projects/sample")),
    project: (token: string, id: string) =>
      checked<Project>(() =>
        client.GET("/api/v1/projects/{project_id}", {
          params: { path: { project_id: id }, header: auth(token) },
        }),
      ),
    updateProject: (token: string, id: string, body: ProjectUpdate) =>
      checked<Project>(() =>
        client.PATCH("/api/v1/projects/{project_id}", {
          params: { path: { project_id: id }, header: auth(token) },
          body,
        }),
      ),
    deleteProject: (token: string, id: string) =>
      checked<void>(
        () =>
          client.DELETE("/api/v1/projects/{project_id}", {
            params: { path: { project_id: id }, header: auth(token) },
          }),
        true,
      ),
    overview: (token: string, id: string) =>
      checked<ProjectOverview>(() =>
        client.GET("/api/v1/projects/{project_id}/overview", {
          params: { path: { project_id: id }, header: auth(token) },
        }),
      ),
    discovery: (token: string, id: string) =>
      checked<Discovery>(() =>
        client.GET("/api/v1/projects/{project_id}/discovery", {
          params: { path: { project_id: id }, header: auth(token) },
        }),
      ),
    saveDiscovery: (token: string, id: string, body: DiscoveryWrite) =>
      checked<Discovery>(() =>
        client.PUT("/api/v1/projects/{project_id}/discovery", {
          params: { path: { project_id: id }, header: auth(token) },
          body,
        }),
      ),
    requirements: (token: string, id: string) =>
      checked<Requirement[]>(() =>
        client.GET("/api/v1/projects/{project_id}/requirements", {
          params: { path: { project_id: id }, header: auth(token) },
        }),
      ),
    createRequirement: (token: string, id: string, body: RequirementCreate) =>
      checked<Requirement>(() =>
        client.POST("/api/v1/projects/{project_id}/requirements", {
          params: { path: { project_id: id }, header: auth(token) },
          body,
        }),
      ),
    updateRequirement: (
      token: string,
      id: string,
      requirementId: string,
      body: RequirementUpdate,
    ) =>
      checked<Requirement>(() =>
        client.PATCH(
          "/api/v1/projects/{project_id}/requirements/{requirement_id}",
          {
            params: {
              path: { project_id: id, requirement_id: requirementId },
              header: auth(token),
            },
            body,
          },
        ),
      ),
    deleteRequirement: (token: string, id: string, requirementId: string) =>
      checked<void>(() =>
        client.DELETE(
          "/api/v1/projects/{project_id}/requirements/{requirement_id}",
          {
            params: {
              path: { project_id: id, requirement_id: requirementId },
              header: auth(token),
            },
          },
        ),
      ),
  };
}
function auth(token: string) {
  return { "X-Project-Token": token };
}
export function fieldMessage(error: ApiError | undefined, field: string) {
  return error?.fields.find((item) => item.field === field)?.message;
}
export const api = createApi();

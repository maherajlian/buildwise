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
export type Catalogue = components["schemas"]["Catalogue"];
export type CatalogueEntry = components["schemas"]["Entry"];
export type RecommendationResult = components["schemas"]["Result"];
export type ScoredEntry = components["schemas"]["ScoredEntry"];
export type Signal = components["schemas"]["Signal"];
export type RecommendationInputs = components["schemas"]["InputRead"];
export type RecommendationOverrides = components["schemas"]["Overrides"];
export type FieldError = components["schemas"]["FieldError"];
export type Artefact = components["schemas"]["Read"];
export type ArtefactEdit = components["schemas"]["Edit"];
export type Plan = components["schemas"]["PlanRead"];
export type PlanTask = components["schemas"]["TaskRead"];
export type TaskCreate = components["schemas"]["TaskCreate"];
export type TaskEdit = components["schemas"]["TaskEdit"];
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
    artefacts: (token: string | undefined, id: string) =>
      checked<Artefact[]>(() =>
        client.GET("/api/v1/projects/{project_id}/artefacts", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
        }),
      ),
    generateArtefacts: (token: string, id: string, overwrite = false) =>
      checked<Artefact[]>(() =>
        client.POST("/api/v1/projects/{project_id}/artefacts/generate", {
          params: { path: { project_id: id }, header: auth(token) },
          body: { overwrite_edited: overwrite },
        }),
      ),
    updateArtefact: (
      token: string,
      id: string,
      aid: string,
      body: ArtefactEdit,
    ) =>
      checked<Artefact>(() =>
        client.PATCH("/api/v1/projects/{project_id}/artefacts/{aid}", {
          params: { path: { project_id: id, aid }, header: auth(token) },
          body,
        }),
      ),
    createADR: (token: string, id: string, title: string) =>
      checked<Artefact>(() =>
        client.POST("/api/v1/projects/{project_id}/artefacts", {
          params: { path: { project_id: id }, header: auth(token) },
          body: { kind: "adr", title },
        }),
      ),
    deleteArtefact: (token: string, id: string, aid: string) =>
      checked<void>(
        () =>
          client.DELETE("/api/v1/projects/{project_id}/artefacts/{aid}", {
            params: { path: { project_id: id, aid }, header: auth(token) },
          }),
        true,
      ),
    artefactMarkdown: (token: string | undefined, id: string, aid: string) =>
      checked<string>(() =>
        client.GET("/api/v1/projects/{project_id}/artefacts/{aid}/markdown", {
          params: {
            path: { project_id: id, aid },
            header: optionalAuth(token),
          },
          parseAs: "text",
        }),
      ),
    allArtefactsMarkdown: (token: string | undefined, id: string) =>
      checked<string>(() =>
        client.GET("/api/v1/projects/{project_id}/artefacts/export/markdown", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
          parseAs: "text",
        }),
      ),
    plan: (token: string | undefined, id: string) =>
      checked<Plan>(() =>
        client.GET("/api/v1/projects/{project_id}/plan", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
        }),
      ),
    generatePlan: (token: string, id: string) =>
      checked<Plan>(() =>
        client.POST("/api/v1/projects/{project_id}/plan/generate", {
          params: { path: { project_id: id }, header: auth(token) },
          body: {},
        }),
      ),
    createTask: (token: string, id: string, body: TaskCreate) =>
      checked<PlanTask>(() =>
        client.POST("/api/v1/projects/{project_id}/plan/tasks", {
          params: { path: { project_id: id }, header: auth(token) },
          body,
        }),
      ),
    updateTask: (token: string, id: string, tid: string, body: TaskEdit) =>
      checked<PlanTask>(() =>
        client.PATCH("/api/v1/projects/{project_id}/plan/tasks/{tid}", {
          params: { path: { project_id: id, tid }, header: auth(token) },
          body,
        }),
      ),
    deleteTask: (token: string, id: string, tid: string) =>
      checked<void>(
        () =>
          client.DELETE("/api/v1/projects/{project_id}/plan/tasks/{tid}", {
            params: { path: { project_id: id, tid }, header: auth(token) },
          }),
        true,
      ),
    planMarkdown: (token: string | undefined, id: string) =>
      checked<string>(() =>
        client.GET("/api/v1/projects/{project_id}/plan/export/markdown", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
          parseAs: "text",
        }),
      ),
    catalogue: () => checked<Catalogue>(() => client.GET("/api/v1/catalogue")),
    recommendations: (token: string | undefined, id: string) =>
      checked<RecommendationResult>(() =>
        client.GET("/api/v1/projects/{project_id}/recommendations", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
        }),
      ),
    recommendationInputs: (token: string | undefined, id: string) =>
      checked<RecommendationInputs>(() =>
        client.GET("/api/v1/projects/{project_id}/recommendation-inputs", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
        }),
      ),
    saveRecommendationInputs: (
      token: string,
      id: string,
      overrides: RecommendationOverrides,
    ) =>
      checked<RecommendationInputs>(() =>
        client.PUT("/api/v1/projects/{project_id}/recommendation-inputs", {
          params: { path: { project_id: id }, header: auth(token) },
          body: { overrides },
        }),
      ),
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
    project: (token: string | undefined, id: string) =>
      checked<Project>(() =>
        client.GET("/api/v1/projects/{project_id}", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
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
    overview: (token: string | undefined, id: string) =>
      checked<ProjectOverview>(() =>
        client.GET("/api/v1/projects/{project_id}/overview", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
        }),
      ),
    discovery: (token: string | undefined, id: string) =>
      checked<Discovery>(() =>
        client.GET("/api/v1/projects/{project_id}/discovery", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
        }),
      ),
    saveDiscovery: (token: string, id: string, body: DiscoveryWrite) =>
      checked<Discovery>(() =>
        client.PUT("/api/v1/projects/{project_id}/discovery", {
          params: { path: { project_id: id }, header: auth(token) },
          body,
        }),
      ),
    requirements: (token: string | undefined, id: string) =>
      checked<Requirement[]>(() =>
        client.GET("/api/v1/projects/{project_id}/requirements", {
          params: { path: { project_id: id }, header: optionalAuth(token) },
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
      checked<void>(
        () =>
          client.DELETE(
            "/api/v1/projects/{project_id}/requirements/{requirement_id}",
            {
              params: {
                path: { project_id: id, requirement_id: requirementId },
                header: auth(token),
              },
            },
          ),
        true,
      ),
  };
}
function auth(token: string) {
  return { "X-Project-Token": token };
}
function optionalAuth(token: string | undefined) {
  return token ? auth(token) : {};
}
export function fieldMessage(error: ApiError | undefined, field: string) {
  return error?.fields.find((item) => item.field === field)?.message;
}
export const api = createApi();

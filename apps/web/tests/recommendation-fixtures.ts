import catalogueData from "../../../services/api/app/modules/recommendations/catalogue/catalogue.json";
import type {
  Catalogue,
  RecommendationResult,
  RecommendationInputs,
  ScoredEntry,
  Signal,
} from "@/lib/api";

export const catalogue = catalogueData as unknown as Catalogue;
catalogue.categories = ["database", "hosting", "ai_layer"];
export const signal: Signal = {
  id: "budget",
  label: "Budget",
  value: "low",
  source: "detected",
  evidence: [
    { field: "discovery.constraints[0]", excerpt: "A low budget for launch" },
  ],
};
export const defaultSignal: Signal = {
  id: "scale",
  label: "Scale",
  value: "small",
  source: "default",
  evidence: [],
};
export const explicitSignal: Signal = {
  id: "ops_capability",
  label: "Ops capability",
  value: "high",
  source: "explicit",
  evidence: [{ field: "overrides.ops_capability", excerpt: "high" }],
};
export const inputs: RecommendationInputs = {
  overrides: {},
  signals: [
    signal,
    defaultSignal,
    explicitSignal,
    {
      id: "integrations",
      label: "Integrations",
      value: [],
      source: "default",
      evidence: [],
    },
  ],
};
const entry = catalogue.entries.find((e) => e.id === "postgresql")!;
const positive = {
  rule_id: "small",
  weight: 20,
  reason: "Small deployments are simpler.",
  signals: [defaultSignal],
};
const negative = {
  rule_id: "budget-limit",
  weight: -5,
  reason: "Budget limits managed capacity.",
  signals: [signal, explicitSignal],
};
const selected: ScoredEntry = {
  ...entry,
  score: 15,
  reason: "A relational database fits this project.",
  matched_rules: [positive, negative],
  positive_matches: [positive],
  negative_matches: [negative],
};
export const recommendations: RecommendationResult = {
  project_id: "p1",
  catalogue_version: "2026.11.2",
  rules_version: "1",
  input_fingerprint: "a".repeat(64),
  signals: inputs.signals,
  notes: ["AI mention detected; set it explicitly if needed."],
  disclaimer:
    "Scores are a decision aid, not an objective benchmark; pricing requires verification.",
  recommendations: [
    {
      category: "database",
      status: "recommended",
      explanation: "Ranked by input rules.",
      recommendation: selected,
      reason: selected.reason,
      alternatives: [
        {
          ...selected,
          id: "mongodb",
          name: "MongoDB",
          score: 0,
          reason: "Ranked below postgresql: score 0 versus 15.",
          trade_offs: ["Document relationships require care."],
        },
      ],
      candidates: [],
      trade_offs: selected.trade_offs,
      operational_complexity: selected.operational_complexity,
      operational_burden: selected.operational_burden,
      cost_category: selected.cost_category,
      assumptions: selected.assumptions,
      change_conditions: selected.change_conditions,
    },
    {
      category: "ai_layer",
      status: "not_recommended",
      explanation: "Explicit required input is absent.",
      recommendation: null,
      alternatives: [],
      candidates: [
        {
          ...selected,
          id: "hosted-model-api",
          name: "Hosted model API",
          category: "ai_layer",
          optional: true,
        },
      ],
      reason: "No explicit requirement",
      trade_offs: [],
      operational_complexity: null,
      operational_burden: "None",
      cost_category: null,
      assumptions: [],
      change_conditions: [],
    },
  ],
};

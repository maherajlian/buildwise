import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
vi.mock("next/navigation", async () => {
  const { navigation } = await import("./navigation");
  return {
    useRouter: () => ({ push: navigation.push, replace: navigation.replace }),
    useSearchParams: () => navigation.params,
  };
});

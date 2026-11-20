import { afterEach, describe, it, expect } from "vitest";
import { getProjectToken } from "@/lib/token";
afterEach(() => localStorage.clear());
describe("browser project token", () => {
  it("generates and persists 32 random bytes as base64url", () => {
    const first = getProjectToken();
    expect(first).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(getProjectToken()).toBe(first);
    localStorage.clear();
    expect(getProjectToken()).not.toBe(first);
  });
  it("replaces invalid saved tokens", () => {
    localStorage.setItem("buildwise.project-token", "short");
    expect(getProjectToken()).toHaveLength(43);
  });
  it("does not silently create an inaccessible project when storage fails", () => {
    expect(() =>
      getProjectToken({
        getItem: () => {
          throw new Error("denied");
        },
      } as unknown as Storage),
    ).toThrow("denied");
  });
});

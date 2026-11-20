import { vi } from "vitest";

export const navigation = {
  push: vi.fn(),
  replace: vi.fn(),
  params: new URLSearchParams(),
};

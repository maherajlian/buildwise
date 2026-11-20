import { expect, it, vi } from "vitest";
import { downloadMarkdown } from "@/lib/download";

it("downloads Markdown using a Blob and revokes the object URL", () => {
  vi.useFakeTimers();
  const create = vi.fn(() => "blob:markdown");
  const revoke = vi.fn();
  vi.stubGlobal(
    "URL",
    Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke }),
  );
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe("orbit.md");
      expect(this.href).toBe("blob:markdown");
    });
  downloadMarkdown("# Orbit", "orbit.md");
  expect(create).toHaveBeenCalledWith(expect.any(Blob));
  expect(click).toHaveBeenCalledOnce();
  vi.runAllTimers();
  expect(revoke).toHaveBeenCalledWith("blob:markdown");
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

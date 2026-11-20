const KEY = "buildwise.project-token";
export function getProjectToken(
  storage: Storage = window.localStorage,
): string {
  const saved = storage.getItem(KEY);
  if (saved && /^[A-Za-z0-9_-]{43,128}$/.test(saved)) return saved;
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  const token = btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  storage.setItem(KEY, token);
  return token;
}
export function readProjectToken(): string | undefined {
  try {
    return getProjectToken();
  } catch {
    return undefined;
  }
}

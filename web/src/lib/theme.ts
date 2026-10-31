export type ThemePreference = "auto" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "fqa-theme";

export function resolveTheme(
  preference: ThemePreference,
  prefersDark: boolean,
): ResolvedTheme {
  if (preference === "auto") {
    return prefersDark ? "dark" : "light";
  }
  return preference;
}

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "auto" || value === "light" || value === "dark";
}

export function readThemePreference(storage: Pick<Storage, "getItem"> | undefined): ThemePreference {
  if (!storage) {
    return "auto";
  }
  try {
    const stored = storage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(stored) ? stored : "auto";
  } catch {
    return "auto";
  }
}

export function writeThemePreference(
  storage: Pick<Storage, "setItem"> | undefined,
  preference: ThemePreference,
): void {
  if (!storage) {
    return;
  }
  try {
    storage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // Private browsing can refuse storage; the in-memory preference still works.
  }
}

/** Apply an explicit theme to the document, or clear it so the OS preference wins. */
export function applyTheme(preference: ThemePreference, root: HTMLElement): void {
  if (preference === "auto") {
    delete root.dataset.theme;
    return;
  }
  root.dataset.theme = preference;
}

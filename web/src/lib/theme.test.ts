import { describe, expect, it } from "vitest";

import { readThemePreference, resolveTheme, THEME_STORAGE_KEY } from "./theme";

function storageWith(value: string | null): Pick<Storage, "getItem"> {
  return {
    getItem: (key: string) => (key === THEME_STORAGE_KEY ? value : null),
  };
}

describe("theme preference", () => {
  it("resolves auto from the system preference", () => {
    expect(resolveTheme("auto", true)).toBe("dark");
    expect(resolveTheme("auto", false)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
    expect(resolveTheme("light", true)).toBe("light");
  });

  it("reads only known preferences", () => {
    expect(readThemePreference(storageWith("dark"))).toBe("dark");
    expect(readThemePreference(storageWith("purple"))).toBe("auto");
    expect(readThemePreference(storageWith(null))).toBe("auto");
    expect(readThemePreference(undefined)).toBe("auto");
  });
});

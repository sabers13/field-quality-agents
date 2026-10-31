import { describe, expect, it } from "vitest";

import { fqaDarkTheme, fqaTheme, STATUS_SERIES, themeFor } from "./echartsTheme";

describe("ECharts theme", () => {
  it("has the documented series palette", () => {
    expect(fqaTheme.color).toHaveLength(6);
    expect(fqaDarkTheme.color).toHaveLength(6);
    expect(fqaTheme.color).not.toEqual(fqaDarkTheme.color);
  });

  it("keeps status colours semantic", () => {
    expect(Object.keys(STATUS_SERIES)).toEqual([
      "new",
      "in_agent",
      "needs_engineer",
      "decided",
      "issue",
    ]);
    expect(STATUS_SERIES.issue).toBe("#a32020");
  });

  it("selects the requested theme", () => {
    expect(themeFor("light")).toBe(fqaTheme);
    expect(themeFor("dark")).toBe(fqaDarkTheme);
  });
});

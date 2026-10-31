import { describe, expect, it } from "vitest";

import { parseRoute, routeHref, type Route } from "./router";

describe("hash router", () => {
  it("parses every page and detail route", () => {
    expect(parseRoute("")).toEqual({ page: "command" });
    expect(parseRoute("#/")).toEqual({ page: "command" });
    expect(parseRoute("#/cases")).toEqual({ page: "cases" });
    expect(parseRoute("#/cases/C-2025-0001")).toEqual({ page: "cases", caseId: "C-2025-0001" });
    expect(parseRoute("#/issues/I-2025-0001")).toEqual({ page: "issues", issueId: "I-2025-0001" });
    expect(parseRoute("#/compare")).toEqual({ page: "compare" });
    expect(parseRoute("#/replay")).toEqual({ page: "replay" });
    expect(parseRoute("#/report")).toEqual({ page: "report" });
  });

  it("falls back to the command centre on an unknown hash", () => {
    expect(parseRoute("#/nope")).toEqual({ page: "command" });
  });

  it("round-trips every route", () => {
    const routes: Route[] = [
      { page: "command" },
      { page: "cases" },
      { page: "cases", caseId: "C-1" },
      { page: "issues" },
      { page: "issues", issueId: "I-1" },
      { page: "compare" },
      { page: "replay" },
      { page: "report" },
    ];
    for (const route of routes) {
      expect(parseRoute(routeHref(route))).toEqual(route);
    }
  });

  it("encodes ids in links", () => {
    expect(routeHref({ page: "cases", caseId: "a b" })).toBe("#/cases/a%20b");
  });
});

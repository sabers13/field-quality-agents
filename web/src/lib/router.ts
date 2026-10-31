/** Tiny hash router: no dependency, works in the static export and dev server. */

export type Route =
  | { page: "command" }
  | { page: "cases"; caseId?: string }
  | { page: "issues"; issueId?: string }
  | { page: "compare" }
  | { page: "replay" }
  | { page: "report" };

export type PageId = Route["page"];

export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, "").replace(/^\/+/, "").replace(/\/+$/, "");
  if (path === "") {
    return { page: "command" };
  }
  const [head, ...rest] = path.split("/");
  const id = rest.join("/");
  switch (head) {
    case "cases":
      return id ? { page: "cases", caseId: decodeURIComponent(id) } : { page: "cases" };
    case "issues":
      return id ? { page: "issues", issueId: decodeURIComponent(id) } : { page: "issues" };
    case "compare":
      return { page: "compare" };
    case "replay":
      return { page: "replay" };
    case "report":
      return { page: "report" };
    default:
      return { page: "command" };
  }
}

export function routeHref(route: Route): string {
  switch (route.page) {
    case "command":
      return "#/";
    case "cases":
      return route.caseId ? `#/cases/${encodeURIComponent(route.caseId)}` : "#/cases";
    case "issues":
      return route.issueId ? `#/issues/${encodeURIComponent(route.issueId)}` : "#/issues";
    case "compare":
      return "#/compare";
    case "replay":
      return "#/replay";
    case "report":
      return "#/report";
  }
}

export const PAGE_TITLES: Record<PageId, string> = {
  command: "Command centre",
  cases: "Case board",
  issues: "Issue room",
  compare: "Before vs after",
  replay: "Replay",
  report: "Weekly report",
};

export const NAV_ITEMS: { page: PageId; label: string; short: string }[] = [
  { page: "command", label: "Command centre", short: "Command" },
  { page: "cases", label: "Case board", short: "Cases" },
  { page: "issues", label: "Issue room", short: "Issues" },
  { page: "compare", label: "Before vs after", short: "Compare" },
  { page: "replay", label: "Replay", short: "Replay" },
  { page: "report", label: "Weekly report", short: "Report" },
];

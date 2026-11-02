/** Tiny hash router: no dependency, works in the static export and dev server. */

export type Route =
  | { page: "overview" }
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
    return { page: "overview" };
  }
  const [head, ...rest] = path.split("/");
  const id = rest.join("/");
  switch (head) {
    case "overview":
      return { page: "overview" };
    case "dashboard":
    case "command":
      return { page: "command" };
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
      return { page: "overview" };
  }
}

export function routeHref(route: Route): string {
  switch (route.page) {
    case "overview":
      return "#/";
    case "command":
      return "#/dashboard";
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
  overview: "Field quality agents",
  command: "Command centre",
  cases: "Case board",
  issues: "Issue room",
  compare: "Before vs after",
  replay: "Replay",
  report: "Weekly report",
};

export const NAV_ITEMS: { page: PageId; label: string; short: string }[] = [
  { page: "overview", label: "Overview", short: "Overview" },
  { page: "cases", label: "Cases", short: "Cases" },
  { page: "issues", label: "Issues", short: "Issues" },
  { page: "compare", label: "Results", short: "Results" },
  { page: "command", label: "Dashboard", short: "Dashboard" },
  { page: "replay", label: "Replay", short: "Replay" },
  { page: "report", label: "Weekly report", short: "Report" },
];

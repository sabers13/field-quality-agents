import type {
  CaseDetail,
  CaseListItem,
  CommandCentreData,
  ComparisonData,
  IssueDetail,
  WeeklyReport,
  ReplayEvent,
  ReplayRun,
} from "../../types";

import commandCentreJson from "./command_centre.json";
import casesJson from "./cases.json";
import case1 from "./cases/C-2025-0001.json";
import case2 from "./cases/C-2025-0002.json";
import case3 from "./cases/C-2025-0003.json";
import case4 from "./cases/C-2025-0004.json";
import case5 from "./cases/C-2025-0005.json";
import case6 from "./cases/C-2025-0006.json";
import issuesJson from "./issues.json";
import comparisonJson from "./comparison.json";
import weeklyReportJson from "./weekly_report.json";
import replayJson from "./replay.json";

export interface ReplayBundle {
  runs: ReplayRun[];
  events: Record<string, ReplayEvent[]>;
}

export interface StaticBundle {
  commandCentre: CommandCentreData;
  cases: CaseListItem[];
  caseDetails: Record<string, CaseDetail>;
  issues: IssueDetail[];
  comparison: ComparisonData;
  weeklyReport: WeeklyReport;
  replay: ReplayBundle;
}

const caseDetails: Record<string, CaseDetail> = {
  "C-2025-0001": case1 as unknown as CaseDetail,
  "C-2025-0002": case2 as unknown as CaseDetail,
  "C-2025-0003": case3 as unknown as CaseDetail,
  "C-2025-0004": case4 as unknown as CaseDetail,
  "C-2025-0005": case5 as unknown as CaseDetail,
  "C-2025-0006": case6 as unknown as CaseDetail,
};

/**
 * Bundled fixture data for the static/portfolio mode. It is imported into the
 * JS bundle rather than fetched, so the static page makes no network request
 * and renders identically in tests, screenshots and the offline export.
 */
export const fixtureBundle: StaticBundle = {
  commandCentre: commandCentreJson as unknown as CommandCentreData,
  cases: casesJson as unknown as CaseListItem[],
  caseDetails,
  issues: issuesJson as unknown as IssueDetail[],
  comparison: comparisonJson as unknown as ComparisonData,
  weeklyReport: weeklyReportJson as unknown as WeeklyReport,
  replay: replayJson as unknown as ReplayBundle,
};

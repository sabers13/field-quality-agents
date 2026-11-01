import { describe, expect, it } from "vitest";

import { formatKpiValue } from "./KpiTile";

describe("KPI values", () => {
  it("formats the recorded run's KPI ids", () => {
    expect(formatKpiValue({ id: "cases_in", label: "", value: 600, context: "" })).toBe("600");
    expect(
      formatKpiValue({ id: "prepared_without_edits", label: "", value: 100, context: "" }),
    ).toBe("100.0%");
    expect(
      formatKpiValue({ id: "time_to_decision", label: "", value: 0, unit: "days", context: "" }),
    ).toBe("0.0");
    expect(
      formatKpiValue({ id: "cost_per_case", label: "", value: 0.0013, unit: "USD", context: "" }),
    ).toBe("$0.0013");
  });
});

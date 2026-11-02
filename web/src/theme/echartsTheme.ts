/**
 * ECharts themes matching DESIGN.md. A chart card supplies the background, so
 * both themes keep the canvas transparent.
 */

export interface FqaChartTheme {
  color: string[];
  backgroundColor: string;
  textStyle: {
    fontFamily: string;
    fontSize: number;
    color: string;
  };
  title: {
    textStyle: { color: string; fontSize: number; fontWeight: number };
    subtextStyle: { color: string; fontSize: number };
  };
  line: {
    symbolSize: number;
    lineStyle: { width: number };
  };
  categoryAxis: {
    axisLine: { lineStyle: { color: string } };
    axisTick: { show: boolean };
    axisLabel: { color: string; fontSize: number };
    splitLine: { show: boolean };
  };
  valueAxis: {
    axisLine: { show: boolean };
    axisLabel: { color: string; fontSize: number };
    splitLine: { lineStyle: { color: string; type: "dashed"; opacity: number } };
  };
  legend: {
    textStyle: { color: string; fontSize: number };
  };
  tooltip: {
    backgroundColor: string;
    borderColor: string;
    borderWidth: number;
    textStyle: { color: string; fontSize: number };
  };
}

const FONT = 'Inter, ui-sans-serif, system-ui, sans-serif';

const base = {
  backgroundColor: "transparent",
  textStyle: { fontFamily: FONT, fontSize: 12 },
  title: {
    textStyle: { fontSize: 14, fontWeight: 600 },
    subtextStyle: { fontSize: 11 },
  },
  line: { symbolSize: 5, lineStyle: { width: 2 } },
  categoryAxis: {
    axisLine: { lineStyle: { color: "" } },
    axisTick: { show: false },
    axisLabel: { fontSize: 12 },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisLabel: { fontSize: 12 },
    splitLine: { lineStyle: { color: "", type: "dashed" as const, opacity: 0.5 } },
  },
  legend: { textStyle: { fontSize: 12 } },
  tooltip: {
    borderWidth: 1,
    textStyle: { fontSize: 12 },
  },
};

export const fqaTheme: FqaChartTheme = {
  ...base,
  color: ["#2563eb", "#626b78", "#8a4b00", "#374151", "#17663a", "#a32020"],
  textStyle: { ...base.textStyle, color: "#374151" },
  title: {
    textStyle: { ...base.title.textStyle, color: "#111827" },
    subtextStyle: { ...base.title.subtextStyle, color: "#626b78" },
  },
  categoryAxis: {
    ...base.categoryAxis,
    axisLine: { lineStyle: { color: "#e5e7eb" } },
    axisLabel: { ...base.categoryAxis.axisLabel, color: "#626b78" },
  },
  valueAxis: {
    ...base.valueAxis,
    axisLabel: { ...base.valueAxis.axisLabel, color: "#626b78" },
    splitLine: {
      ...base.valueAxis.splitLine,
      lineStyle: { ...base.valueAxis.splitLine.lineStyle, color: "#e5e7eb" },
    },
  },
  legend: { textStyle: { ...base.legend.textStyle, color: "#374151" } },
  tooltip: {
    ...base.tooltip,
    backgroundColor: "#ffffff",
    borderColor: "#e5e7eb",
    textStyle: { ...base.tooltip.textStyle, color: "#111827" },
  },
};

export const fqaDarkTheme: FqaChartTheme = {
  ...base,
  color: ["#60a5fa", "#a6afbd", "#f0b45e", "#d1d5db", "#6fd39a", "#ff8d8d"],
  textStyle: { ...base.textStyle, color: "#d1d5db" },
  title: {
    textStyle: { ...base.title.textStyle, color: "#f9fafb" },
    subtextStyle: { ...base.title.subtextStyle, color: "#a6afbd" },
  },
  categoryAxis: {
    ...base.categoryAxis,
    axisLine: { lineStyle: { color: "#374151" } },
    axisLabel: { ...base.categoryAxis.axisLabel, color: "#a6afbd" },
  },
  valueAxis: {
    ...base.valueAxis,
    axisLabel: { ...base.valueAxis.axisLabel, color: "#a6afbd" },
    splitLine: {
      ...base.valueAxis.splitLine,
      lineStyle: { ...base.valueAxis.splitLine.lineStyle, color: "#374151" },
    },
  },
  legend: { textStyle: { ...base.legend.textStyle, color: "#d1d5db" } },
  tooltip: {
    ...base.tooltip,
    backgroundColor: "#1a2232",
    borderColor: "#374151",
    textStyle: { ...base.tooltip.textStyle, color: "#f9fafb" },
  },
};

export function themeFor(mode: "light" | "dark"): FqaChartTheme {
  return mode === "dark" ? fqaDarkTheme : fqaTheme;
}

/** Status palette is semantic; chart series order must not redefine it. */
export const STATUS_SERIES = {
  new: "#44515f",
  in_agent: "#1f5fbf",
  needs_engineer: "#8a4b00",
  decided: "#17663a",
  issue: "#a32020",
} as const;

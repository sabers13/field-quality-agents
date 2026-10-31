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

const FONT = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

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
    axisLabel: { fontSize: 11 },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisLabel: { fontSize: 11 },
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
  color: ["#1f5fbf", "#0f766e", "#b45309", "#6d4aff", "#17663a", "#a32020"],
  textStyle: { ...base.textStyle, color: "#4d5a68" },
  title: {
    textStyle: { ...base.title.textStyle, color: "#1b2430" },
    subtextStyle: { ...base.title.subtextStyle, color: "#6f7c8a" },
  },
  categoryAxis: {
    ...base.categoryAxis,
    axisLine: { lineStyle: { color: "#d8dee5" } },
    axisLabel: { ...base.categoryAxis.axisLabel, color: "#6f7c8a" },
  },
  valueAxis: {
    ...base.valueAxis,
    axisLabel: { ...base.valueAxis.axisLabel, color: "#6f7c8a" },
    splitLine: {
      ...base.valueAxis.splitLine,
      lineStyle: { ...base.valueAxis.splitLine.lineStyle, color: "#d8dee5" },
    },
  },
  legend: { textStyle: { ...base.legend.textStyle, color: "#4d5a68" } },
  tooltip: {
    ...base.tooltip,
    backgroundColor: "#ffffff",
    borderColor: "#d8dee5",
    textStyle: { ...base.tooltip.textStyle, color: "#1b2430" },
  },
};

export const fqaDarkTheme: FqaChartTheme = {
  ...base,
  color: ["#6ea8ff", "#4fd1c5", "#f0b45e", "#a78bfa", "#6fd39a", "#ff8d8d"],
  textStyle: { ...base.textStyle, color: "#b3bec9" },
  title: {
    textStyle: { ...base.title.textStyle, color: "#e8edf2" },
    subtextStyle: { ...base.title.subtextStyle, color: "#8794a1" },
  },
  categoryAxis: {
    ...base.categoryAxis,
    axisLine: { lineStyle: { color: "#2c3742" } },
    axisLabel: { ...base.categoryAxis.axisLabel, color: "#8794a1" },
  },
  valueAxis: {
    ...base.valueAxis,
    axisLabel: { ...base.valueAxis.axisLabel, color: "#8794a1" },
    splitLine: {
      ...base.valueAxis.splitLine,
      lineStyle: { ...base.valueAxis.splitLine.lineStyle, color: "#2c3742" },
    },
  },
  legend: { textStyle: { ...base.legend.textStyle, color: "#b3bec9" } },
  tooltip: {
    ...base.tooltip,
    backgroundColor: "#202a35",
    borderColor: "#2c3742",
    textStyle: { ...base.tooltip.textStyle, color: "#e8edf2" },
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

import { useEffect, useRef, type ReactNode } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";

import { useApp } from "../app/AppContext";
import { fqaDarkTheme, fqaTheme } from "../theme/echartsTheme";

echarts.use([LineChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

interface ChartProps {
  option: EChartsOption;
  height?: number;
  ariaLabel: string;
  summary?: ReactNode;
  className?: string;
}

/**
 * ECharts wrapper. The theme follows the resolved light/dark theme, the chart
 * re-sizes with its card, and animation is off so screenshots and reduced
 * motion both get the settled frame immediately.
 */
export function Chart({ option, height = 220, ariaLabel, summary, className }: ChartProps) {
  const { resolvedTheme } = useApp();
  const elementRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }
    const chart = echarts.init(
      element,
      resolvedTheme === "dark" ? fqaDarkTheme : fqaTheme,
      { renderer: "canvas" },
    );
    chart.setOption({ animation: false, ...option }, true);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [option, resolvedTheme]);

  return (
    <figure className={`chart${className ? ` ${className}` : ""}`}>
      <div
        ref={elementRef}
        className="chart-canvas"
        style={{ height }}
        role="img"
        aria-label={ariaLabel}
      />
      {summary ? <figcaption className="chart-caption">{summary}</figcaption> : null}
    </figure>
  );
}

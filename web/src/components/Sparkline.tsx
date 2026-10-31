/** A 32 px sparkline with no axes or labels; the KPI text carries the number. */
export function Sparkline({ series }: { series: readonly number[] }) {
  if (series.length < 2) {
    return null;
  }
  const width = 120;
  const height = 32;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  const points = series.map((value, index) => {
    const x = (index / (series.length - 1)) * (width - 4) + 2;
    const y = height - 3 - ((value - min) / span) * (height - 6);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <polyline points={points.join(" ")} fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

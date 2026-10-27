interface Props {
  values: number[];
  width?: number;
  height?: number;
  label: string;
}

/** A tiny line of recent values. The label carries the meaning for screen readers. */
export function Sparkline({ values, width = 84, height = 24, label }: Props) {
  if (values.length < 2) return <span className="text-muted">–</span>;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = (width - 4) / (values.length - 1);
  const points = values.map(
    (v, i) => `${(2 + i * step).toFixed(1)},${(height - 3 - ((v - min) / span) * (height - 6)).toFixed(1)}`,
  );
  const last = points[points.length - 1].split(",");
  return (
    <svg width={width} height={height} role="img" aria-label={label} className="text-brand">
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={last[0]} cy={last[1]} r="2.4" fill="currentColor" />
    </svg>
  );
}

export function trendLabel(name: string, values: number[]): string {
  if (values.length < 2) return `${name}: not enough data`;
  const first = values[0];
  const last = values[values.length - 1];
  const direction = last > first + 0.5 ? "up" : last < first - 0.5 ? "down" : "steady";
  return `${name} ${direction}, from ${first.toFixed(0)} to ${last.toFixed(0)}`;
}

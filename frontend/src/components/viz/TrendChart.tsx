import { useId } from "react";

interface TrendPoint {
  label: string;
  value: number;
}

interface TrendChartProps {
  title?: string;
  points: TrendPoint[];
  /** Positive values = growth (amber), negative = decline (coral) relative to first */
  mode?: "signed" | "absolute";
  height?: number;
  unit?: string;
}

/** Lightweight SVG area/line chart — no chart library required */
export function TrendChart({
  title,
  points,
  mode = "signed",
  height = 120,
  unit = "",
}: TrendChartProps) {
  const uid = useId().replace(/:/g, "");

  if (points.length < 2) {
    return (
      <div className="trend-chart empty">
        {title && <h4 className="viz-title">{title}</h4>}
        <p>Not enough points for a trend.</p>
      </div>
    );
  }

  const width = 320;
  const pad = { top: 12, right: 12, bottom: 28, left: 12 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const values = points.map((p) => p.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = max - min || 1;

  const coords = points.map((p, i) => {
    const x = pad.left + (i / (points.length - 1)) * innerW;
    const y = pad.top + innerH - ((p.value - min) / span) * innerH;
    return { x, y, ...p };
  });

  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const area = `${line} L${coords[coords.length - 1].x},${pad.top + innerH} L${coords[0].x},${pad.top + innerH} Z`;
  const last = points[points.length - 1].value;
  const first = points[0].value;
  const delta = last - first;
  const rising = delta >= 0;
  const stroke = mode === "absolute" ? "var(--accent-sky)" : rising ? "var(--accent-amber)" : "var(--accent-coral)";
  const fill =
    mode === "absolute" ? `url(#gradSky-${uid})` : rising ? `url(#gradAmber-${uid})` : `url(#gradCoral-${uid})`;

  return (
    <div className="trend-chart">
      <div className="trend-head">
        {title && <h4 className="viz-title">{title}</h4>}
        <span className={`trend-badge ${rising ? "up" : "down"}`}>
          {rising ? "▲ Growth" : "▼ Decline"} {delta > 0 ? "+" : ""}
          {delta.toFixed(2)}
          {unit}
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title ?? "Trend chart"}>
        <defs>
          <linearGradient id={`gradAmber-${uid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e8a838" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#e8a838" stopOpacity="0" />
          </linearGradient>
          <linearGradient id={`gradCoral-${uid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e85d4c" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#e85d4c" stopOpacity="0" />
          </linearGradient>
          <linearGradient id={`gradSky-${uid}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3db8d0" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#3db8d0" stopOpacity="0" />
          </linearGradient>
        </defs>
        {min < 0 && max > 0 && (
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={pad.top + innerH - ((0 - min) / span) * innerH}
            y2={pad.top + innerH - ((0 - min) / span) * innerH}
            stroke="var(--border)"
            strokeDasharray="3 3"
          />
        )}
        <path d={area} fill={fill} />
        <path d={line} fill="none" stroke={stroke} strokeWidth="2.5" strokeLinejoin="round" />
        {coords.map((c) => (
          <g key={`${c.label}-${c.x}`}>
            <circle cx={c.x} cy={c.y} r="4" fill={stroke} stroke="var(--surface)" strokeWidth="2" />
            <text x={c.x} y={height - 8} textAnchor="middle" className="chart-label">
              {c.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

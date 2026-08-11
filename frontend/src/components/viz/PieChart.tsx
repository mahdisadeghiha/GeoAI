interface PieSlice {
  label: string;
  value: number;
  color: string;
}

interface PieChartProps {
  title?: string;
  slices: PieSlice[];
  size?: number;
  unit?: string;
}

export function PieChart({ title, slices, size = 148, unit = "" }: PieChartProps) {
  const total = slices.reduce((sum, s) => sum + Math.max(0, s.value), 0) || 1;
  const r = size / 2;
  const ir = r * 0.58;
  let angle = -Math.PI / 2;

  const arcs = slices
    .filter((s) => s.value > 0)
    .map((slice) => {
      const portion = Math.max(0, slice.value) / total;
      const sweep = portion * Math.PI * 2;
      const start = angle;
      const end = angle + sweep;
      angle = end;
      const large = sweep > Math.PI ? 1 : 0;
      const x1 = r + r * Math.cos(start);
      const y1 = r + r * Math.sin(start);
      const x2 = r + r * Math.cos(end);
      const y2 = r + r * Math.sin(end);
      const ix1 = r + ir * Math.cos(end);
      const iy1 = r + ir * Math.sin(end);
      const ix2 = r + ir * Math.cos(start);
      const iy2 = r + ir * Math.sin(start);
      const d = [
        `M ${x1} ${y1}`,
        `A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`,
        `L ${ix1} ${iy1}`,
        `A ${ir} ${ir} 0 ${large} 0 ${ix2} ${iy2}`,
        "Z",
      ].join(" ");
      return { ...slice, d, pct: portion * 100 };
    });

  return (
    <div className="pie-chart">
      {title && <h4 className="viz-title">{title}</h4>}
      <div className="pie-body">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={title ?? "Pie chart"}>
          {arcs.length === 0 ? (
            <circle cx={r} cy={r} r={r - 2} fill="var(--surface-2)" />
          ) : (
            arcs.map((a) => <path key={a.label} d={a.d} fill={a.color} stroke="var(--bg-1)" strokeWidth="1.5" />)
          )}
          <circle cx={r} cy={r} r={ir - 2} fill="var(--bg-1)" />
          <text x={r} y={r - 2} textAnchor="middle" className="pie-center-value">
            {total.toFixed(total >= 10 ? 1 : 2)}
          </text>
          <text x={r} y={r + 14} textAnchor="middle" className="pie-center-unit">
            {unit || "total"}
          </text>
        </svg>
        <ul className="pie-legend">
          {slices.map((s) => (
            <li key={s.label}>
              <i style={{ background: s.color }} />
              <span>{s.label}</span>
              <strong>
                {s.value.toFixed(s.value >= 10 ? 1 : 2)}
                {unit ? ` ${unit}` : ""} · {((Math.max(0, s.value) / total) * 100).toFixed(0)}%
              </strong>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

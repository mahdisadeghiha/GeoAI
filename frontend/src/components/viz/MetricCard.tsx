interface MetricCardProps {
  icon: string;
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "teal" | "amber" | "coral" | "sky";
  bar?: number; // 0–100
  delta?: number;
  active?: boolean;
  onClick?: () => void;
}

export function MetricCard({
  icon,
  label,
  value,
  hint,
  tone = "neutral",
  bar,
  delta,
  active,
  onClick,
}: MetricCardProps) {
  const deltaClass =
    delta === undefined || Number.isNaN(delta)
      ? ""
      : delta > 0
        ? "up"
        : delta < 0
          ? "down"
          : "flat";

  return (
    <button
      type="button"
      className={`metric-card tone-${tone}${active ? " active" : ""}${onClick ? " clickable" : ""}`}
      onClick={onClick}
      disabled={!onClick}
    >
      <div className="metric-card-top">
        <span className="metric-icon" aria-hidden>
          {icon}
        </span>
        <span className="metric-label">{label}</span>
        {delta !== undefined && !Number.isNaN(delta) && (
          <span className={`metric-delta ${deltaClass}`}>
            {delta > 0 ? "▲" : delta < 0 ? "▼" : "●"} {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>
      <strong className="metric-value">{value}</strong>
      {hint && <span className="metric-hint">{hint}</span>}
      {bar !== undefined && (
        <div className="meter" aria-hidden>
          <div className="meter-fill" style={{ width: `${Math.max(0, Math.min(100, bar))}%` }} />
        </div>
      )}
    </button>
  );
}

import type { AnalysisResponse } from "../types";

interface StatsPanelProps {
  result: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
}

export function StatsPanel({ result, loading, error }: StatsPanelProps) {
  if (loading) return <div className="stats-panel">Running analysis...</div>;
  if (error) return <div className="stats-panel error">{error}</div>;
  if (!result) return <div className="stats-panel muted">Run analysis to view statistics.</div>;

  const rows = [
    ["Changed Area", `${result.changed_area_km2.toFixed(1)} km²`],
    ["Change Percentage", `${result.change_percentage.toFixed(1)}%`],
    ["Vegetation Change", `${result.vegetation_change_percentage.toFixed(1)}%`],
    ["Urban Growth", `${result.built_up_change_percentage >= 0 ? "+" : ""}${result.built_up_change_percentage.toFixed(1)}%`],
    ["Change Regions", String(result.num_change_regions)],
  ];

  return (
    <div className="stats-panel">
      <h2>Statistics</h2>
      {rows.map(([label, value]) => (
        <div className="stat-row" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

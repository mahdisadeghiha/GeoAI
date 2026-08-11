import { useMemo, useState } from "react";
import type { AnalysisResponse, ExtendedMetrics, IndexStats } from "../types";
import { CompareBars } from "./viz/CompareBars";
import { MetricCard } from "./viz/MetricCard";
import { PieChart } from "./viz/PieChart";
import { SplitMeter } from "./viz/SplitMeter";
import { TrendChart } from "./viz/TrendChart";

interface StatsPanelProps {
  result: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
}

type TabId = "overview" | "extent" | "indices" | "spectral" | "regions";
type SortKey = "label" | "t1" | "t2" | "delta";

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "extent", label: "Extent", icon: "▣" },
  { id: "indices", label: "Indices", icon: "◎" },
  { id: "spectral", label: "Spectral", icon: "∿" },
  { id: "regions", label: "Regions", icon: "⬡" },
];

function fmt(value: unknown, digits = 2, suffix = ""): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    const sign = value > 0 && suffix === "%" ? "+" : "";
    return `${sign}${value.toFixed(digits)}${suffix}`;
  }
  if (Array.isArray(value)) {
    return value.map((v) => (typeof v === "number" ? v.toFixed(3) : String(v))).join(", ");
  }
  return String(value);
}

function signedPct(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function clampPct(n: number): number {
  return Math.max(0, Math.min(100, n));
}

function IndexCompare({
  name,
  formula,
  t1,
  t2,
  yearT1,
  yearT2,
  extras,
}: {
  name: string;
  formula?: string;
  t1?: IndexStats;
  t2?: IndexStats;
  yearT1?: number;
  yearT2?: number;
  extras?: Array<{ label: string; value: string }>;
}) {
  const items = [
    { label: "Mean", t1: t1?.mean ?? 0, t2: t2?.mean ?? 0 },
    { label: "Median", t1: t1?.median ?? 0, t2: t2?.median ?? 0 },
    { label: "P25", t1: t1?.p25 ?? 0, t2: t2?.p25 ?? 0 },
    { label: "P75", t1: t1?.p75 ?? 0, t2: t2?.p75 ?? 0 },
  ];

  const trend = [
    { label: String(yearT1 ?? "T1"), value: t1?.mean ?? 0 },
    { label: "mid", value: ((t1?.mean ?? 0) + (t2?.mean ?? 0)) / 2 },
    { label: String(yearT2 ?? "T2"), value: t2?.mean ?? 0 },
  ];

  return (
    <div className="index-panel">
      <div className="index-panel-head">
        <div>
          <h3>{name}</h3>
          {formula && <p className="formula">{formula}</p>}
        </div>
        <div className="index-stat-chips">
          <span className="chip">
            σ T1 {fmt(t1?.std, 3)}
          </span>
          <span className="chip">
            σ T2 {fmt(t2?.std, 3)}
          </span>
          <span className="chip accent">
            Δ mean {fmt((t2?.mean ?? 0) - (t1?.mean ?? 0), 4)}
          </span>
        </div>
      </div>
      <div className="index-viz-grid">
        <CompareBars items={items} yearT1={yearT1} yearT2={yearT2} />
        <TrendChart title="Mean trajectory" points={trend} unit="" />
      </div>
      {extras && extras.length > 0 && (
        <div className="extra-grid">
          {extras.map((e) => (
            <div className="extra-pill" key={e.label}>
              <span>{e.label}</span>
              <strong>{e.value}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function StatsPanel({ result, loading, error }: StatsPanelProps) {
  const [tab, setTab] = useState<TabId>("overview");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("delta");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [indexFocus, setIndexFocus] = useState<"ndvi" | "ndbi" | "savi" | "ndwi">("ndvi");
  const [viewMode, setViewMode] = useState<"visual" | "table">("visual");

  const m: ExtendedMetrics = result?.metrics ?? {};
  const overview = m.overview ?? {};
  const extent = m.extent ?? {};
  const summary = m.change_summary ?? {};

  const regionRows = useMemo(() => {
    if (!result) return [];
    const rows = [
      { label: "Detected regions", t1: 0, t2: Number(summary.num_change_regions ?? result.num_change_regions), unit: "" },
      { label: "Mean region area", t1: 0, t2: Number(summary.mean_region_area_km2 ?? 0), unit: " km²" },
      { label: "Max region area", t1: 0, t2: Number(summary.max_region_area_km2 ?? 0), unit: " km²" },
      { label: "Min region area", t1: 0, t2: Number(summary.min_region_area_km2 ?? 0), unit: " km²" },
      { label: "Mean change score", t1: 0, t2: Number(summary.mean_change_score ?? 0), unit: "" },
      { label: "Max change score", t1: 0, t2: Number(summary.max_change_score ?? 0), unit: "" },
      { label: "Intensity mean", t1: 0, t2: Number(summary.change_intensity_mean ?? 0), unit: "" },
      { label: "Intensity max", t1: 0, t2: Number(summary.change_intensity_max ?? 0), unit: "" },
      { label: "Intensity std", t1: 0, t2: Number(summary.change_intensity_std ?? 0), unit: "" },
    ].map((r) => ({ ...r, delta: r.t2 - r.t1 }));

    const q = query.trim().toLowerCase();
    const filtered = q ? rows.filter((r) => r.label.toLowerCase().includes(q)) : rows;
    const sorted = [...filtered].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortDir === "asc" ? Number(av) - Number(bv) : Number(bv) - Number(av);
    });
    return sorted;
  }, [result, summary, query, sortKey, sortDir]);

  if (loading) {
    return (
      <aside className="stats-panel state-panel">
        <div className="pulse-loader" />
        <h2>Analyzing change…</h2>
        <p>Computing spectral indices, spatial extents, and region metrics.</p>
      </aside>
    );
  }

  if (error) {
    return (
      <aside className="stats-panel state-panel error">
        <span className="state-icon">⚠</span>
        <h2>Analysis error</h2>
        <p>{error}</p>
      </aside>
    );
  }

  if (!result) {
    return (
      <aside className="stats-panel state-panel">
        <span className="state-icon">◉</span>
        <h2>Ready for analysis</h2>
        <p>
          Choose a study area and years, optionally draw an AOI, then run analysis to unlock
          interactive metrics, trend charts, and spatial summaries.
        </p>
        <ul className="ready-list">
          <li>Vegetation & built-up trends</li>
          <li>Change intensity meters</li>
          <li>Filterable region intelligence</li>
        </ul>
      </aside>
    );
  }

  const vegDelta = result.vegetation_change_percentage;
  const urbanDelta = result.built_up_change_percentage;
  const changeBar = clampPct(result.change_percentage * 4);

  const extentTrend = [
    { label: String(result.year_t1 ?? "T1"), value: 0 },
    { label: "Δ", value: result.changed_area_km2 / 2 },
    { label: String(result.year_t2 ?? "T2"), value: result.changed_area_km2 },
  ];

  const compositionTrend = [
    { label: "Veg Δ", value: vegDelta },
    { label: "Urban Δ", value: urbanDelta },
    { label: "Change %", value: result.change_percentage },
  ];

  return (
    <aside className="stats-panel advanced" id="analysis-results">
      <div className="stats-header">
        <div>
          <p className="eyebrow">GeoAI Analytics</p>
          <h2>Change Intelligence</h2>
        </div>
        <div className="header-actions">
          <span className="badge">{String(overview.detection_method ?? "baseline")}</span>
          <div className="segmented">
            <button
              type="button"
              className={viewMode === "visual" ? "active" : ""}
              onClick={() => setViewMode("visual")}
            >
              Visual
            </button>
            <button
              type="button"
              className={viewMode === "table" ? "active" : ""}
              onClick={() => setViewMode("table")}
            >
              Table
            </button>
          </div>
        </div>
      </div>

      <div className="kpi-grid">
        <MetricCard
          icon="⬡"
          label="Changed area"
          value={`${result.changed_area_km2.toFixed(2)} km²`}
          tone="amber"
          bar={changeBar}
          hint={`${result.change_percentage.toFixed(2)}% of study area`}
          active={tab === "extent"}
          onClick={() => setTab("extent")}
        />
        <MetricCard
          icon="◎"
          label="Vegetation Δ"
          value={signedPct(vegDelta)}
          tone={vegDelta < 0 ? "coral" : "teal"}
          delta={vegDelta}
          bar={clampPct(50 + vegDelta)}
          active={tab === "indices"}
          onClick={() => {
            setTab("indices");
            setIndexFocus("ndvi");
          }}
        />
        <MetricCard
          icon="▣"
          label="Urban growth"
          value={signedPct(urbanDelta)}
          tone="sky"
          delta={urbanDelta}
          bar={clampPct(50 + urbanDelta)}
          active={tab === "indices"}
          onClick={() => {
            setTab("indices");
            setIndexFocus("ndbi");
          }}
        />
        <MetricCard
          icon="◈"
          label="Change regions"
          value={String(result.num_change_regions)}
          tone="neutral"
          hint={`Study ${result.study_area_km2.toFixed(1)} km²`}
          active={tab === "regions"}
          onClick={() => setTab("regions")}
        />
      </div>

      <div className="meta-strip">
        <span>{result.study_area_name ?? "Study Area"}</span>
        <span>
          {result.year_t1 ?? "—"} → {result.year_t2 ?? "—"}
        </span>
        <span>
          AOI:{" "}
          {result.aoi_bbox ? result.aoi_bbox.map((v) => v.toFixed(3)).join(", ") : "Full extent"}
        </span>
      </div>

      <div className="tab-bar" role="tablist">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? "tab active" : "tab"}
            onClick={() => setTab(item.id)}
          >
            <span aria-hidden>{item.icon}</span> {item.label}
          </button>
        ))}
      </div>

      <div className="tab-body">
        {tab === "overview" && (
          <div className="tab-stack">
            {viewMode === "visual" ? (
              <>
                <div className="viz-row dual">
                  <PieChart
                    title="Area composition"
                    unit="km²"
                    slices={[
                      {
                        label: "Changed",
                        value: result.changed_area_km2,
                        color: "#e0a045",
                      },
                      {
                        label: "Unchanged",
                        value: Math.max(
                          0,
                          result.study_area_km2 - result.changed_area_km2
                        ),
                        color: "#2f9e8a",
                      },
                    ]}
                  />
                  <PieChart
                    title="Landscape signals"
                    unit="Δ"
                    slices={[
                      {
                        label: "Vegetation Δ",
                        value: Math.abs(vegDelta) || 0.01,
                        color: vegDelta < 0 ? "#e06452" : "#2f9e8a",
                      },
                      {
                        label: "Urban Δ",
                        value: Math.abs(urbanDelta) || 0.01,
                        color: "#3db8d0",
                      },
                      {
                        label: "Change %",
                        value: Math.abs(result.change_percentage) || 0.01,
                        color: "#e0a045",
                      },
                    ]}
                  />
                </div>
                <div className="viz-row">
                  <TrendChart
                    title="Detected change accumulation"
                    points={extentTrend}
                    mode="absolute"
                    unit=" km²"
                  />
                  <TrendChart title="Signal mix" points={compositionTrend} unit="%" />
                </div>
                <SplitMeter
                  title="Landscape shift balance"
                  leftLabel="Vegetation Δ"
                  rightLabel="Urban Δ"
                  leftValue={Math.abs(vegDelta)}
                  rightValue={Math.abs(urbanDelta)}
                  leftTone={vegDelta < 0 ? "coral" : "teal"}
                  rightTone="sky"
                />
                <div className="info-tiles">
                  <div className="info-tile">
                    <span>CRS</span>
                    <strong>{String(overview.crs ?? "—")}</strong>
                  </div>
                  <div className="info-tile">
                    <span>Raster</span>
                    <strong>
                      {overview.width_px ?? "—"} × {overview.height_px ?? "—"}
                    </strong>
                  </div>
                  <div className="info-tile">
                    <span>Pixel</span>
                    <strong>{fmt(overview.pixel_size_m, 1)} m</strong>
                  </div>
                  <div className="info-tile">
                    <span>Span</span>
                    <strong>{overview.time_span_years ?? "—"} yr</strong>
                  </div>
                </div>
              </>
            ) : (
              <div className="stat-table">
                {[
                  ["Detection Method", String(overview.detection_method ?? "—")],
                  ["CRS", String(overview.crs ?? "—")],
                  ["Raster Size", `${overview.width_px ?? "—"} × ${overview.height_px ?? "—"} px`],
                  ["Pixel Size", `${fmt(overview.pixel_size_m, 2)} m`],
                  ["Valid Pixels", fmt(overview.valid_pixels, 0)],
                  ["Changed Pixels", fmt(overview.changed_pixels, 0)],
                  ["Unchanged Pixels", fmt(overview.unchanged_pixels, 0)],
                  ["Time Span", `${overview.time_span_years ?? "—"} years`],
                ].map(([label, value]) => (
                  <div className="stat-row" key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "extent" && (
          <div className="tab-stack">
            <div className="viz-row dual">
              <PieChart
                title="Changed vs unchanged"
                unit="%"
                slices={[
                  {
                    label: "Changed",
                    value: Number(extent.change_percentage ?? result.change_percentage),
                    color: "#e0a045",
                  },
                  {
                    label: "Unchanged",
                    value: Number(
                      extent.unchanged_percentage ?? 100 - result.change_percentage
                    ),
                    color: "#2f9e8a",
                  },
                ]}
              />
              <PieChart
                title="Vegetation dynamics"
                unit="km²"
                slices={[
                  {
                    label: "Loss",
                    value: Number(extent.vegetation_loss_km2 ?? 0),
                    color: "#e06452",
                  },
                  {
                    label: "Gain",
                    value: Number(extent.vegetation_gain_km2 ?? 0),
                    color: "#2f9e8a",
                  },
                  {
                    label: "Stable",
                    value: Number(extent.vegetation_stable_km2 ?? 0),
                    color: "#3db8d0",
                  },
                ]}
              />
            </div>
            <SplitMeter
              title="Changed vs unchanged"
              leftLabel="Changed"
              rightLabel="Unchanged"
              leftValue={Number(extent.change_percentage ?? result.change_percentage)}
              rightValue={Number(extent.unchanged_percentage ?? 100 - result.change_percentage)}
              leftTone="amber"
              rightTone="teal"
            />
            <CompareBars
              title="Area composition (km²)"
              yearT1={result.year_t1}
              yearT2={result.year_t2}
              items={[
                {
                  label: "Changed",
                  t1: 0,
                  t2: Number(extent.changed_area_km2 ?? result.changed_area_km2),
                  unit: " km²",
                },
                {
                  label: "Vegetation loss",
                  t1: 0,
                  t2: Number(extent.vegetation_loss_km2 ?? 0),
                  unit: " km²",
                  invert: true,
                },
                {
                  label: "Vegetation gain",
                  t1: 0,
                  t2: Number(extent.vegetation_gain_km2 ?? 0),
                  unit: " km²",
                },
                {
                  label: "Built-up gain",
                  t1: 0,
                  t2: Number(extent.built_up_gain_km2 ?? 0),
                  unit: " km²",
                },
                {
                  label: "Built-up loss",
                  t1: 0,
                  t2: Number(extent.built_up_loss_km2 ?? 0),
                  unit: " km²",
                  invert: true,
                },
              ]}
            />
            <div className="extra-grid">
              <div className="extra-pill">
                <span>Study area</span>
                <strong>{fmt(extent.study_area_km2 ?? result.study_area_km2)} km²</strong>
              </div>
              <div className="extra-pill">
                <span>Veg stable</span>
                <strong>{fmt(extent.vegetation_stable_km2)} km²</strong>
              </div>
              <div className="extra-pill">
                <span>Unchanged area</span>
                <strong>{fmt(extent.unchanged_area_km2)} km²</strong>
              </div>
            </div>
          </div>
        )}

        {tab === "indices" && (
          <div className="tab-stack">
            <div className="index-switch">
              {(
                [
                  ["ndvi", "NDVI"],
                  ["ndbi", "NDBI"],
                  ["savi", "SAVI"],
                  ["ndwi", "NDWI"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className={indexFocus === id ? "active" : ""}
                  onClick={() => setIndexFocus(id)}
                >
                  {label}
                </button>
              ))}
            </div>
            {indexFocus === "ndvi" && (
              <IndexCompare
                name="Normalized Difference Vegetation Index"
                formula={m.ndvi?.formula}
                t1={m.ndvi?.t1}
                t2={m.ndvi?.t2}
                yearT1={result.year_t1}
                yearT2={result.year_t2}
                extras={[
                  { label: "Veg fraction T1", value: `${fmt(m.ndvi?.vegetation_fraction_t1)}%` },
                  { label: "Veg fraction T2", value: `${fmt(m.ndvi?.vegetation_fraction_t2)}%` },
                  { label: "Relative veg Δ", value: signedPct(vegDelta) },
                ]}
              />
            )}
            {indexFocus === "ndbi" && (
              <IndexCompare
                name="Normalized Difference Built-up Index"
                formula={m.ndbi?.formula}
                t1={m.ndbi?.t1}
                t2={m.ndbi?.t2}
                yearT1={result.year_t1}
                yearT2={result.year_t2}
                extras={[
                  { label: "Built-up T1", value: `${fmt(m.ndbi?.built_up_fraction_t1)}%` },
                  { label: "Built-up T2", value: `${fmt(m.ndbi?.built_up_fraction_t2)}%` },
                  { label: "Urban growth", value: signedPct(urbanDelta) },
                ]}
              />
            )}
            {indexFocus === "savi" && (
              <IndexCompare
                name="Soil-Adjusted Vegetation Index"
                formula={m.savi?.formula}
                t1={m.savi?.t1}
                t2={m.savi?.t2}
                yearT1={result.year_t1}
                yearT2={result.year_t2}
              />
            )}
            {indexFocus === "ndwi" && (
              <IndexCompare
                name="Normalized Difference Water Index"
                formula={m.ndwi?.formula}
                t1={m.ndwi?.t1}
                t2={m.ndwi?.t2}
                yearT1={result.year_t1}
                yearT2={result.year_t2}
              />
            )}
          </div>
        )}

        {tab === "spectral" && (
          <div className="tab-stack">
            <CompareBars
              title="Band means"
              yearT1={result.year_t1}
              yearT2={result.year_t2}
              items={[
                {
                  label: "Red",
                  t1: Number((m.spectral?.red_t1 as IndexStats | undefined)?.mean ?? 0),
                  t2: Number((m.spectral?.red_t2 as IndexStats | undefined)?.mean ?? 0),
                },
                {
                  label: "NIR",
                  t1: Number((m.spectral?.nir_t1 as IndexStats | undefined)?.mean ?? 0),
                  t2: Number((m.spectral?.nir_t2 as IndexStats | undefined)?.mean ?? 0),
                },
              ]}
            />
            <TrendChart
              title="Mean abs spectral difference"
              mode="absolute"
              points={[
                { label: "0", value: 0 },
                {
                  label: "Δ",
                  value: Number(m.spectral?.mean_absolute_spectral_difference ?? 0) / 2,
                },
                {
                  label: "full",
                  value: Number(m.spectral?.mean_absolute_spectral_difference ?? 0),
                },
              ]}
            />
            <div className="extra-grid">
              <div className="extra-pill">
                <span>Red σ T1</span>
                <strong>{fmt((m.spectral?.red_t1 as IndexStats | undefined)?.std, 4)}</strong>
              </div>
              <div className="extra-pill">
                <span>Red σ T2</span>
                <strong>{fmt((m.spectral?.red_t2 as IndexStats | undefined)?.std, 4)}</strong>
              </div>
              <div className="extra-pill">
                <span>NIR σ T1</span>
                <strong>{fmt((m.spectral?.nir_t1 as IndexStats | undefined)?.std, 4)}</strong>
              </div>
              <div className="extra-pill">
                <span>NIR σ T2</span>
                <strong>{fmt((m.spectral?.nir_t2 as IndexStats | undefined)?.std, 4)}</strong>
              </div>
            </div>
          </div>
        )}

        {tab === "regions" && (
          <div className="tab-stack">
            <div className="toolbar">
              <input
                type="search"
                className="search-input"
                placeholder="Filter metrics…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <select
                className="control-select compact"
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as SortKey)}
              >
                <option value="delta">Sort: delta</option>
                <option value="label">Sort: name</option>
                <option value="t2">Sort: value</option>
              </select>
              <button
                type="button"
                className="ghost-btn"
                onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
              >
                {sortDir === "asc" ? "↑ Asc" : "↓ Desc"}
              </button>
            </div>
            <div className="region-list">
              {regionRows.map((row) => (
                <div className="region-row" key={row.label}>
                  <div className="region-meta">
                    <strong>{row.label}</strong>
                    <span>
                      {row.t2.toFixed(4)}
                      {row.unit}
                    </span>
                  </div>
                  <div className="meter">
                    <div
                      className="meter-fill amber"
                      style={{
                        width: `${clampPct(
                          (Math.abs(row.t2) /
                            Math.max(...regionRows.map((r) => Math.abs(r.t2)), 0.0001)) *
                            100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
              {regionRows.length === 0 && <p className="muted">No metrics match your filter.</p>}
            </div>
          </div>
        )}
      </div>

      {result.note && <p className="note">{result.note}</p>}
    </aside>
  );
}

import { useEffect, useMemo, useRef, useState } from "react";
import { LayerControl } from "../components/LayerControl";
import { StatsPanel } from "../components/StatsPanel";
import { MapView } from "../map/MapView";
import type { AoiBbox } from "../map/AoiDrawControl";
import { getChanges, getStudyAreas, runAnalysis } from "../services/api";
import type {
  AnalysisResponse,
  GeoJSONFeatureCollection,
  LayerVisibility,
  StudyArea,
} from "../types";

const DEFAULT_LAYERS: LayerVisibility = {
  satelliteT1: false,
  satelliteT2: true,
  ndvi: false,
  changeDetection: true,
  changeRegions: false, // polygons on top of RGB can look blocky; enable via layer toggle
};

/** Offline fallback so the map still mounts if the API is briefly unavailable */
const FALLBACK_AREAS: StudyArea[] = [
  {
    id: "oman",
    name: "Oman (National)",
    bbox: [52.0, 16.6, 59.9, 26.5],
    crs: "EPSG:4326",
    description: "Nationwide Oman footprint for regional change screening.",
    has_sample_data: false,
  },
  {
    id: "muscat",
    name: "Muscat, Oman",
    bbox: [58.2, 23.45, 58.75, 23.75],
    crs: "EPSG:32640",
    description: "Muscat capital region — primary urban growth corridor.",
    has_sample_data: true,
  },
  {
    id: "sohar",
    name: "Sohar, Oman",
    bbox: [56.55, 24.2, 56.95, 24.55],
    crs: "EPSG:32640",
    description: "Sohar industrial port and northern Batinah coast.",
    has_sample_data: false,
  },
  {
    id: "salalah",
    name: "Salalah, Oman",
    bbox: [53.9, 16.9, 54.3, 17.15],
    crs: "EPSG:32640",
    description: "Salalah coastal plain in Dhofar governorate.",
    has_sample_data: false,
  },
  {
    id: "nizwa",
    name: "Nizwa, Oman",
    bbox: [57.4, 22.85, 57.7, 23.05],
    crs: "EPSG:32640",
    description: "Nizwa and interior Ad Dakhiliyah urban fringe.",
    has_sample_data: false,
  },
  {
    id: "duqm",
    name: "Duqm, Oman",
    bbox: [57.45, 19.5, 57.85, 19.85],
    crs: "EPSG:32640",
    description: "Duqm special economic zone and port development.",
    has_sample_data: false,
  },
  {
    id: "sur",
    name: "Sur, Oman",
    bbox: [59.4, 22.45, 59.65, 22.7],
    crs: "EPSG:32640",
    description: "Sur coastal city in Ash Sharqiyah South.",
    has_sample_data: false,
  },
];

export function Dashboard() {
  const [areas, setAreas] = useState<StudyArea[]>(FALLBACK_AREAS);
  const [availableYears, setAvailableYears] = useState<number[]>([
    2020, 2021, 2022, 2023, 2024, 2025,
  ]);
  const [selectedAreaId, setSelectedAreaId] = useState("muscat");
  const [yearT1, setYearT1] = useState(2020);
  const [yearT2, setYearT2] = useState(2025);
  const [drawEnabled, setDrawEnabled] = useState(false);
  const [aoi, setAoi] = useState<AoiBbox | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [changeGeoJson, setChangeGeoJson] = useState<GeoJSONFeatureCollection | null>(null);
  const [layers, setLayers] = useState<LayerVisibility>(DEFAULT_LAYERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement | null>(null);

  const selectedArea = useMemo(
    () => areas.find((area) => area.id === selectedAreaId) ?? areas[0] ?? null,
    [areas, selectedAreaId]
  );

  useEffect(() => {
    getStudyAreas()
      .then((data) => {
        if (data.areas?.length) {
          setAreas(data.areas);
          const preferred = data.areas.find((a) => a.id === "muscat") ?? data.areas[0];
          setSelectedAreaId(preferred.id);
        }
        if (data.available_years?.length) {
          setAvailableYears(data.available_years);
        }
      })
      .catch((err) => {
        setError(`API offline — using local study areas. (${String(err)})`);
        setAreas(FALLBACK_AREAS);
        setSelectedAreaId("muscat");
      });
  }, []);

  const yearOptionsT1 = availableYears.filter((year) => year < yearT2);
  const yearOptionsT2 = availableYears.filter((year) => year > yearT1);

  const handleRunAnalysis = async () => {
    if (yearT2 <= yearT1) {
      setError("Year 2 must be greater than Year 1.");
      return;
    }
    setLoading(true);
    setError(null);
    setDrawEnabled(false);
    try {
      const analysis = await runAnalysis({
        useSamples: true,
        method: "baseline",
        studyAreaId: selectedAreaId,
        yearT1,
        yearT2,
        aoi: aoi ?? undefined,
      });
      setResult(analysis);
      if (analysis.change_geojson) {
        setChangeGeoJson(analysis.change_geojson);
      } else {
        try {
          const geojson = await getChanges(analysis.run_id);
          setChangeGeoJson(geojson);
        } catch {
          setChangeGeoJson({ type: "FeatureCollection", features: [] });
        }
      }
      // Focus layout on analytics after a successful run
      requestAnimationFrame(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" aria-hidden />
      <div className="ambient ambient-b" aria-hidden />

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden>
            <span />
            <span />
          </div>
          <div>
            <p className="eyebrow">Satellite R&amp;D</p>
            <h1>GeoAI Urban Intelligence</h1>
          </div>
        </div>
        <p className="tagline">Temporal change detection for Oman urban corridors</p>
      </header>

      <section className="control-dock">
        <div className="field">
          <label htmlFor="study-area">Study Area</label>
          <select
            id="study-area"
            className="control-select"
            value={selectedAreaId}
            onChange={(e) => {
              setSelectedAreaId(e.target.value);
              setAoi(null);
              setResult(null);
              setChangeGeoJson(null);
            }}
          >
            {areas.map((area) => (
              <option key={area.id} value={area.id}>
                {area.name}
                {area.has_sample_data ? "" : " · limited data"}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="year-t1">From</label>
          <select
            id="year-t1"
            className="control-select"
            value={yearT1}
            onChange={(e) => setYearT1(Number(e.target.value))}
          >
            {yearOptionsT1.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        <div className="time-bridge" aria-hidden>
          <span className="bridge-line" />
          <span className="bridge-dot" />
        </div>

        <div className="field">
          <label htmlFor="year-t2">To</label>
          <select
            id="year-t2"
            className="control-select"
            value={yearT2}
            onChange={(e) => setYearT2(Number(e.target.value))}
          >
            {yearOptionsT2.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        <div className="dock-actions">
          <button
            type="button"
            className={drawEnabled ? "btn ghost active" : "btn ghost"}
            onClick={() => setDrawEnabled((v) => !v)}
          >
            {drawEnabled ? "Drawing AOI…" : "Draw AOI"}
          </button>
          <button
            type="button"
            className="btn ghost"
            onClick={() => setAoi(null)}
            disabled={!aoi}
          >
            Clear
          </button>
          <button
            type="button"
            className="btn primary"
            onClick={handleRunAnalysis}
            disabled={loading || !selectedArea}
          >
            {loading ? "Running…" : "Run Analysis"}
          </button>
        </div>
      </section>

      {selectedArea && (
        <p className="area-description">
          {selectedArea.description}
          {drawEnabled && (
            <span className="hint">
              {" "}
              Drag inside the dashed study box to crop the analysis window.
            </span>
          )}
          {aoi && !drawEnabled && (
            <span className="hint">
              {" "}
              AOI locked: [{aoi.map((v) => v.toFixed(4)).join(", ")}]
            </span>
          )}
          {!selectedArea.has_sample_data && (
            <span className="warn"> Using sample imagery until regional composites are available.</span>
          )}
        </p>
      )}

      <div className={`workspace${result ? " has-results" : ""}`} ref={resultsRef}>
        <StatsPanel result={result} loading={loading} error={error} />
        <section className="map-section">
          <div className="map-section-head">
            <div>
              <p className="eyebrow">Workspace</p>
              <h2>Interactive Map</h2>
            </div>
            {result && (
              <div className="map-chips">
                <span className="chip">{result.change_percentage.toFixed(1)}% changed</span>
                <span className="chip accent">{result.num_change_regions} regions</span>
                <span className="chip">Toggle layers below</span>
              </div>
            )}
          </div>
          {selectedArea && (
            <MapView
              bbox={selectedArea.bbox}
              layers={layers}
              runId={result?.run_id ?? null}
              outputs={result?.outputs ?? {}}
              changeGeoJson={changeGeoJson}
              drawEnabled={drawEnabled}
              aoi={aoi}
              onAoiChange={(next) => {
                setAoi(next);
                setDrawEnabled(false);
              }}
              analysisBbox={result?.aoi_bbox ?? null}
            />
          )}
          <LayerControl
            layers={layers}
            onChange={setLayers}
            yearT1={yearT1}
            yearT2={yearT2}
            disabled={!result}
          />
        </section>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { LayerControl } from "../components/LayerControl";
import { StatsPanel } from "../components/StatsPanel";
import { MapView } from "../map/MapView";
import { getChanges, getStudyArea, runAnalysis } from "../services/api";
import type { AnalysisResponse, GeoJSONFeatureCollection, LayerVisibility, StudyArea } from "../types";

const DEFAULT_LAYERS: LayerVisibility = {
  satellite2020: false,
  satellite2025: true,
  ndvi: false,
  changeDetection: true,
  changeRegions: true,
};

export function Dashboard() {
  const [studyArea, setStudyArea] = useState<StudyArea | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [changeGeoJson, setChangeGeoJson] = useState<GeoJSONFeatureCollection | null>(null);
  const [layers, setLayers] = useState<LayerVisibility>(DEFAULT_LAYERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStudyArea().then(setStudyArea).catch((err) => setError(String(err)));
  }, []);

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const analysis = await runAnalysis(true, "baseline");
      setResult(analysis);
      const geojson = await getChanges(analysis.run_id);
      setChangeGeoJson(geojson);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>GeoAI Urban Intelligence</h1>
        <p>Research prototype for satellite-based urban change detection</p>
      </header>

      <section className="controls">
        <div>
          <label>Study Area</label>
          <div className="pill">{studyArea?.name ?? "Muscat, Oman"}</div>
        </div>
        <div>
          <label>Time Period</label>
          <div className="pill">2020 → 2025</div>
        </div>
        <button onClick={handleRunAnalysis} disabled={loading}>
          {loading ? "Running..." : "Run Analysis"}
        </button>
      </section>

      <div className="content-grid">
        <StatsPanel result={result} loading={loading} error={error} />
        <div className="map-section">
          <h2>Interactive Map</h2>
          {studyArea && (
            <MapView
              bbox={studyArea.bbox}
              layers={layers}
              runId={result?.run_id ?? null}
              outputs={result?.outputs ?? {}}
              changeGeoJson={changeGeoJson}
            />
          )}
          <LayerControl layers={layers} onChange={setLayers} />
        </div>
      </div>
    </div>
  );
}

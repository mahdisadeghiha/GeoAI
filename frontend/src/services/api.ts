import type { AnalysisResponse, GeoJSONFeatureCollection, StudyArea } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function getStudyArea(): Promise<StudyArea> {
  return fetchJson<StudyArea>("/api/study-area");
}

export function runAnalysis(useSamples = true, method = "baseline"): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append("use_samples", String(useSamples));
  form.append("method", method);
  return fetchJson<AnalysisResponse>("/api/analyze", { method: "POST", body: form });
}

export function getChanges(runId?: string): Promise<GeoJSONFeatureCollection> {
  const query = runId ? `?run_id=${runId}` : "";
  return fetchJson<GeoJSONFeatureCollection>(`/api/changes${query}`);
}

export function getStatistics(runId?: string): Promise<Record<string, number>> {
  const query = runId ? `?run_id=${runId}` : "";
  return fetchJson<Record<string, number>>(`/api/statistics${query}`);
}

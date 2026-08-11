import type { AnalysisResponse, GeoJSONFeatureCollection, StudyArea, StudyAreasResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const text = await response.text();
      if (text) {
        try {
          const parsed = JSON.parse(text) as { detail?: unknown };
          if (typeof parsed.detail === "string") {
            message = parsed.detail;
          } else if (parsed.detail !== undefined) {
            message = JSON.stringify(parsed.detail);
          } else {
            message = text;
          }
        } catch {
          message = text;
        }
      }
    } catch {
      // keep default message
    }
    throw new Error(message);
  }
  return response.json();
}

export function getStudyAreas(): Promise<StudyAreasResponse> {
  return fetchJson<StudyAreasResponse>("/api/study-areas");
}

export function getStudyArea(areaId = "muscat"): Promise<StudyArea> {
  return fetchJson<StudyArea>(`/api/study-area?area_id=${encodeURIComponent(areaId)}`);
}

export function runAnalysis(options: {
  useSamples?: boolean;
  method?: string;
  studyAreaId: string;
  yearT1: number;
  yearT2: number;
  aoi?: [number, number, number, number];
}): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append("use_samples", String(options.useSamples ?? true));
  form.append("method", options.method ?? "baseline");
  form.append("study_area_id", options.studyAreaId);
  form.append("year_t1", String(options.yearT1));
  form.append("year_t2", String(options.yearT2));
  if (options.aoi) {
    form.append("bbox_west", String(options.aoi[0]));
    form.append("bbox_south", String(options.aoi[1]));
    form.append("bbox_east", String(options.aoi[2]));
    form.append("bbox_north", String(options.aoi[3]));
  }
  return fetchJson<AnalysisResponse>("/api/analyze", { method: "POST", body: form });
}

export function getChanges(runId?: string): Promise<GeoJSONFeatureCollection> {
  const query = runId ? `?run_id=${runId}` : "";
  return fetchJson<GeoJSONFeatureCollection>(`/api/changes${query}`);
}

export function getStatistics(runId?: string): Promise<Record<string, number | string>> {
  const query = runId ? `?run_id=${runId}` : "";
  return fetchJson<Record<string, number | string>>(`/api/statistics${query}`);
}

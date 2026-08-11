export interface AnalysisStatistics {
  study_area_km2: number;
  changed_area_km2: number;
  change_percentage: number;
  vegetation_change_percentage: number;
  built_up_change_percentage: number;
  num_change_regions: number;
}

export interface AnalysisOutputs {
  change_mask?: string;
  change_intensity?: string;
  ndvi_t1?: string;
  ndvi_t2?: string;
  ndvi_diff?: string;
  rgb_t1?: string;
  rgb_t2?: string;
  change_geojson?: string;
}

export interface AnalysisResponse {
  run_id: string;
  status: string;
  study_area_km2: number;
  changed_area_km2: number;
  change_percentage: number;
  vegetation_change_percentage: number;
  built_up_change_percentage: number;
  num_change_regions: number;
  outputs: AnalysisOutputs;
}

export interface StudyArea {
  name: string;
  bbox: number[];
  crs: string;
  description: string;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: GeoJSON.Geometry;
    properties: Record<string, unknown>;
  }>;
}

export interface LayerVisibility {
  satellite2020: boolean;
  satellite2025: boolean;
  ndvi: boolean;
  changeDetection: boolean;
  changeRegions: boolean;
}

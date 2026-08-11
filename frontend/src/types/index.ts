export interface IndexStats {
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
  p25: number;
  p75: number;
}

export interface ExtendedMetrics {
  overview?: Record<string, string | number | number[] | null>;
  extent?: Record<string, number>;
  change_summary?: Record<string, number | string>;
  ndvi?: {
    formula?: string;
    t1?: IndexStats;
    t2?: IndexStats;
    diff?: IndexStats;
    vegetation_fraction_t1?: number;
    vegetation_fraction_t2?: number;
  };
  ndbi?: {
    formula?: string;
    t1?: IndexStats;
    t2?: IndexStats;
    diff?: IndexStats;
    built_up_fraction_t1?: number;
    built_up_fraction_t2?: number;
  };
  savi?: {
    formula?: string;
    t1?: IndexStats;
    t2?: IndexStats;
    diff?: IndexStats;
  };
  ndwi?: {
    formula?: string;
    t1?: IndexStats;
    t2?: IndexStats;
    diff?: IndexStats;
  };
  spectral?: Record<string, IndexStats | number>;
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
  study_area_id?: string;
  study_area_name?: string;
  year_t1?: number;
  year_t2?: number;
  aoi_bbox?: number[] | null;
  study_area_km2: number;
  changed_area_km2: number;
  change_percentage: number;
  vegetation_change_percentage: number;
  built_up_change_percentage: number;
  num_change_regions: number;
  outputs: AnalysisOutputs;
  metrics?: ExtendedMetrics | null;
  change_geojson?: GeoJSONFeatureCollection | null;
  note?: string;
}

export interface StudyArea {
  id: string;
  name: string;
  bbox: number[];
  crs: string;
  description: string;
  has_sample_data: boolean;
  imagery_bbox?: number[] | null;
}

export interface StudyAreasResponse {
  areas: StudyArea[];
  available_years: number[];
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
  satelliteT1: boolean;
  satelliteT2: boolean;
  ndvi: boolean;
  changeDetection: boolean;
  changeRegions: boolean;
}

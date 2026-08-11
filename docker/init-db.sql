CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS study_areas (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    bbox GEOMETRY(Polygon, 4326),
    crs TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID PRIMARY KEY,
    study_area_id UUID REFERENCES study_areas(id),
    image_t1_path TEXT,
    image_t2_path TEXT,
    status TEXT,
    statistics JSONB,
    outputs JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS change_regions (
    id UUID PRIMARY KEY,
    analysis_run_id UUID REFERENCES analysis_runs(id),
    geom GEOMETRY(MultiPolygon, 4326),
    area_km2 FLOAT,
    centroid GEOMETRY(Point, 4326),
    bbox GEOMETRY(Polygon, 4326),
    change_score FLOAT
);

CREATE INDEX IF NOT EXISTS idx_change_regions_geom ON change_regions USING GIST(geom);

# GeoAI Urban Satellite Change Detection

Research & Development prototype for detecting and analyzing urban land cover changes from multi-temporal satellite imagery over **Muscat, Oman**.

> **Disclaimer:** This is a research prototype. Results require expert validation before operational or decision-making use. Do not treat outputs as ground truth without field verification.

---

## 1. Project Overview

**GeoAI Urban Satellite Change Detection** compares two satellite images of the same urban area from different time periods, identifies changed regions, and quantifies urban growth and vegetation change.

The system ingests GeoTIFF rasters, runs a modular geospatial processing pipeline, and delivers statistics, vector change regions, and an interactive map via a REST API and React frontend.

---

## 2. Research Problem

**How can satellite imagery be used to detect and quantify urban changes over time?**

Urban areas expand, vegetation is replaced by built-up land, and land cover shifts in ways that are visible in multi-spectral satellite data. This project demonstrates a reproducible workflow to:

- Align multi-temporal imagery
- Compute spectral indices (NDVI, NDBI)
- Detect changes using classical remote sensing methods
- Vectorize and quantify change regions spatially

---

## 3. Features

- GeoTIFF ingestion with CRS, resolution, and bounds preservation
- 8-step modular preprocessing pipeline
- NDVI computation and vegetation change quantification
- Baseline spectral change detection + Change Vector Analysis (CVA)
- Built-up change proxy via NDBI
- Raster-to-polygon conversion with GeoJSON export
- PostGIS persistence for study areas, analysis runs, and change regions
- FastAPI REST API with file upload support
- React + Leaflet interactive map with layer control
- Docker Compose for full-stack deployment
- pytest test suite with synthetic sample data

---

## 4. Architecture

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram and component breakdown.

```
Frontend (React/Leaflet) → FastAPI → Processing Pipeline → PostGIS + GeoTIFF files
```

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn, pydantic-settings |
| GIS/Raster | rasterio, rioxarray, numpy, scipy, scikit-image |
| Vector | geopandas, shapely, pyproj |
| Database | PostgreSQL 16 + PostGIS 3.4, SQLAlchemy, GeoAlchemy2 |
| Frontend | React 18, TypeScript, Vite, Leaflet, react-leaflet |
| Testing | pytest, httpx |
| Containerization | Docker Compose |

---

## 6. Dataset

### Study Area
**Muscat, Oman** — urban core bounding box `[58.35, 23.50, 58.65, 23.65]` (WGS84)

### Source
[Microsoft Planetary Computer STAC](https://planetarycomputer.microsoft.com/api/stac/v1) — Sentinel-2 Level-2A (`sentinel-2-l2a`)

| Property | Value |
|---|---|
| Satellite | Sentinel-2A/2B (Copernicus/ESA) |
| Resolution | 10 m (B02, B03, B04, B08); 20 m (B11) |
| CRS | EPSG:32640 (UTM Zone 40N) |
| MGRS Tile | 40RGU |
| Time 1 | 2020 dry season (Oct–Feb median composite) |
| Time 2 | 2025 dry season (Oct–Feb median composite) |
| Bands | B02, B03, B04, B08, B11 |

### Why this dataset?
No pre-packaged Muscat 2020/2025 GeoTIFF bundle exists for free offline use. The project provides:
1. `scripts/download_sentinel2.py` — reproducible STAC download
2. `data/samples/` — synthetic test rasters for CI/offline dev
3. `data/metadata/dataset_metadata.json` — full provenance record

**Fallback:** [QuickMapTools](https://www.quickmaptools.com/download-satellite-imagery) for manual clipping of the same bbox/bands.

---

## 7. Data Processing Pipeline

See [docs/pipeline.md](docs/pipeline.md) for the detailed pipeline diagram.

1. Validation → 2. CRS check → 3. Reprojection → 4. Resampling → 5. Alignment → 6. Cropping → 7. Normalization → 8. NoData handling → NDVI → Change Detection → Spatial Analysis

---

## 8. Change Detection Method

### Baseline (default)
- Spectral difference on normalized NIR + Red bands
- NDVI difference with sigma-based thresholding
- Output: binary change mask + change intensity map

### Built-up proxy
- NDBI = (SWIR − NIR) / (SWIR + NIR)
- Relative change in mean NDBI between time periods

### Advanced: Change Vector Analysis (CVA)
- 2D feature space (NIR, Red)
- Mahalanobis distance threshold (χ² = 5.991, p = 0.05)
- Select via `method=cva` in API or CLI

---

## 9. NDVI Method

```
NDVI = (NIR - Red) / (NIR + Red)
NDVI_diff = NDVI_t2 - NDVI_t1
Vegetation Change % = relative change in mean NDVI over valid pixels
```

Outputs: NDVI rasters for both dates, difference raster, and summary statistic.

---

## 10. API Documentation

Interactive docs available at `http://localhost:8000/docs` when the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Service and database health |
| GET | `/api/study-area` | Muscat AOI metadata |
| GET | `/api/statistics?run_id=` | Analysis statistics |
| GET | `/api/changes?run_id=` | GeoJSON change regions |
| GET | `/api/ndvi?run_id=` | NDVI summary and raster URLs |
| POST | `/api/analyze` | Run full pipeline (upload or sample data) |
| GET | `/api/rasters/{run_id}/{filename}` | Download output GeoTIFF |

### Example: Run analysis with sample data

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -F "use_samples=true" \
  -F "method=baseline"
```

### Example response

```json
{
  "run_id": "uuid",
  "study_area_km2": 524.3,
  "changed_area_km2": 18.7,
  "change_percentage": 3.57,
  "vegetation_change_percentage": -12.4,
  "built_up_change_percentage": 8.2,
  "num_change_regions": 1
}
```

---

## 11. Installation

### Prerequisites
- Python 3.12+
- Node.js 20+ (for frontend)
- PostgreSQL 16 + PostGIS (optional; file-based fallback available)
- Docker & Docker Compose (recommended)

### Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Generate sample data

```bash
python scripts/generate_test_rasters.py
```

### Run backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## 12. Docker Setup

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/docs |
| PostGIS | localhost:5432 |

Environment variables are configured in `docker-compose.yml`. Copy `.env.example` to `.env` for local overrides.

---

## 13. Example Usage

### CLI

```bash
cd backend
python ../scripts/run_analysis_cli.py \
  --t1 ../data/samples/sample_t1.tif \
  --t2 ../data/samples/sample_t2.tif \
  --method baseline
```

### Download real Sentinel-2 data

```bash
python scripts/download_sentinel2.py --year 2020 --output data/raw/muscat_2020.tif
python scripts/download_sentinel2.py --year 2025 --output data/raw/muscat_2025.tif
```

### Run tests

```bash
cd backend
pytest tests -v
```

---

## 14. Results

After running analysis on sample data, the system produces:

- **Study area** — total valid analysis extent in km²
- **Changed area** — extent of detected change in km²
- **Change percentage** — proportion of study area changed
- **Vegetation change** — relative NDVI shift (%)
- **Urban growth** — relative NDBI shift (%)
- **Change regions** — vector polygons with area, centroid, and change score
- **Output rasters** — change mask, intensity, NDVI, RGB composites

All values are computed from actual raster data — nothing is hard-coded.

---

## 15. Limitations

- **Research prototype only** — not validated against ground truth
- **Cloud cover** — dry-season median composites mitigate but do not eliminate cloud effects
- **Built-up proxy** — NDBI is a spectral index proxy, not a formal land cover classification
- **Baseline methods** — classical thresholding/CVA; no deep learning change detection
- **Sample data** — synthetic rasters for CI; real Muscat results require STAC download
- **Resolution** — Sentinel-2 10 m limits detection of sub-pixel changes
- **PostGIS optional** — file-based fallback works without database for development

---

## 16. Future Work

- Integrate Sentinel-2 SCL cloud masking in download pipeline
- Add supervised land cover classification (e.g., Random Forest on spectral bands)
- Implement deep learning change detection (FC-Siam-diff, BIT)
- Time series analysis with >2 dates
- COG tile server for efficient map overlay rendering
- Automated accuracy assessment with reference data
- Export to standard formats (Shapefile, GeoPackage)
- CI/CD pipeline with GitHub Actions

---

## License

MIT License — see [LICENSE](LICENSE).

## Project Structure

```
├── backend/           # FastAPI application
├── frontend/          # React + Leaflet dashboard
├── data/              # Raw, processed, samples, metadata
├── scripts/           # Download, test data generation, CLI
├── docker/            # PostGIS init SQL
├── docs/              # Architecture and pipeline docs
├── notebooks/         # Exploratory analysis
├── docker-compose.yml
└── README.md
```

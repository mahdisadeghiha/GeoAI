"""Vectorization and spatial statistics for change regions."""

from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio.features
from pyproj import Geod
from scipy import ndimage
from shapely.geometry import box, mapping, shape

from app.core.config import Settings, get_settings
from app.utils.raster import RasterData, pixel_area_m2


@dataclass
class ChangeRegion:
    region_id: int
    geometry: Any
    area_km2: float
    centroid_lon: float
    centroid_lat: float
    bbox: tuple[float, float, float, float]
    change_score: float


@dataclass
class SpatialAnalysisResult:
    regions: list[ChangeRegion]
    geojson: dict[str, Any]
    num_regions: int


def _geodesic_area_km2(geom, crs: str) -> float:
    if crs.upper().endswith("4326") or "4326" in crs:
        geod = Geod(ellps="WGS84")
        area_m2, _ = geod.geometry_area_perimeter(geom)
        return abs(area_m2) / 1_000_000.0
    return geom.area / 1_000_000.0


def polygonize_changes(
    change_mask: RasterData,
    intensity: RasterData,
    valid_mask: np.ndarray,
    min_area_m2: float = 1000.0,
    settings: Settings | None = None,
) -> SpatialAnalysisResult:
    settings = settings or get_settings()
    mask = (change_mask.array.astype(bool)) & valid_mask
    labeled, num_features = ndimage.label(mask)

    pixel_area = pixel_area_m2(change_mask.transform)
    regions: list[ChangeRegion] = []
    features = []

    for region_id in range(1, num_features + 1):
        region_mask = labeled == region_id
        area_m2 = region_mask.sum() * pixel_area
        if area_m2 < min_area_m2:
            continue

        shapes = list(
            rasterio.features.shapes(
                region_mask.astype(np.uint8),
                mask=region_mask,
                transform=change_mask.transform,
            )
        )
        if not shapes:
            continue

        geom = shape(shapes[0][0])
        score_vals = intensity.array[region_mask]
        score = float(score_vals.mean()) if score_vals.size else 0.0

        gdf = gpd.GeoDataFrame(geometry=[geom], crs=change_mask.crs)
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        geom_wgs84 = gdf_wgs84.geometry.iloc[0]
        centroid = geom_wgs84.centroid
        bounds = geom_wgs84.bounds

        area_km2 = _geodesic_area_km2(geom_wgs84, "EPSG:4326")
        region = ChangeRegion(
            region_id=len(regions) + 1,
            geometry=geom_wgs84,
            area_km2=area_km2,
            centroid_lon=float(centroid.x),
            centroid_lat=float(centroid.y),
            bbox=bounds,
            change_score=score,
        )
        regions.append(region)
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom_wgs84),
                "properties": {
                    "region_id": region.region_id,
                    "area_km2": round(region.area_km2, 4),
                    "change_score": round(region.change_score, 4),
                    "centroid_lon": region.centroid_lon,
                    "centroid_lat": region.centroid_lat,
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    return SpatialAnalysisResult(regions=regions, geojson=geojson, num_regions=len(regions))

"""Download Sentinel-2 L2A composites for Oman (national + major urban AOIs).

National coverage uses coarser resolution to keep file sizes practical.
City AOIs use higher resolution for local change detection.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import planetary_computer
import rasterio
import stackstac
from pystac_client import Client
from rasterio.transform import from_bounds

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("download_oman")

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-2-l2a"
DEFAULT_BANDS = ["B02", "B03", "B04", "B08", "B11"]

# Practical AOIs for Oman GeoAI prototype
REGIONS: dict[str, dict] = {
    "oman": {
        "name": "Oman (National)",
        # Slightly padded national footprint
        "bbox": (52.0, 16.6, 59.9, 26.5),
        "epsg": 4326,
        # ~500 m in degrees — practical nationwide mosaic
        "resolution": 0.005,
        "resolution_m": 500,
        "max_items": 14,
    },
    "muscat": {
        "name": "Muscat, Oman",
        "bbox": (58.20, 23.45, 58.75, 23.75),
        "epsg": 32640,
        "resolution": 20,
        "resolution_m": 20,
        "max_items": 8,
    },
    "sohar": {
        "name": "Sohar, Oman",
        "bbox": (56.55, 24.20, 56.95, 24.55),
        "epsg": 32640,
        "resolution": 20,
        "resolution_m": 20,
        "max_items": 8,
    },
    "salalah": {
        "name": "Salalah, Oman",
        "bbox": (53.90, 16.90, 54.30, 17.15),
        "epsg": 32640,
        "resolution": 20,
        "resolution_m": 20,
        "max_items": 8,
    },
    "nizwa": {
        "name": "Nizwa, Oman",
        "bbox": (57.40, 22.85, 57.70, 23.05),
        "epsg": 32640,
        "resolution": 20,
        "resolution_m": 20,
        "max_items": 8,
    },
    "duqm": {
        "name": "Duqm, Oman",
        "bbox": (57.45, 19.50, 57.85, 19.85),
        "epsg": 32640,
        "resolution": 20,
        "resolution_m": 20,
        "max_items": 8,
    },
    "sur": {
        "name": "Sur, Oman",
        "bbox": (59.40, 22.45, 59.65, 22.70),
        "epsg": 32640,
        "resolution": 20,
        "resolution_m": 20,
        "max_items": 8,
    },
}


def dry_season_range(year: int) -> str:
    """Oct (year) through Feb (year+1) dry-season window."""
    return f"{year}-10-01/{year + 1}-02-28"


def search_scenes(
    bbox: tuple[float, float, float, float],
    date_range: str,
    max_cloud: int = 40,
    max_items: int = 40,
):
    catalog = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    search = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": max_cloud}},
        max_items=max(max_items * 4, 80),
    )
    items = list(search.items())
    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
    return _diversify_items(items, max_items)


def _item_centroid(item) -> tuple[float, float]:
    geom = item.geometry or {}
    coords = geom.get("coordinates")
    if geom.get("type") == "Polygon" and coords:
        ring = coords[0]
        lons = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        return (sum(lons) / len(lons), sum(lats) / len(lats))
    bbox = item.bbox or [0, 0, 0, 0]
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _diversify_items(items, max_items: int):
    """Keep low-cloud scenes while spreading coverage across a coarse lon/lat grid."""
    if len(items) <= max_items:
        return items
    selected = []
    used_cells: set[tuple[int, int]] = set()
    # First pass: one best scene per ~1° cell
    for item in items:
        lon, lat = _item_centroid(item)
        cell = (int(lon), int(lat))
        if cell in used_cells:
            continue
        selected.append(item)
        used_cells.add(cell)
        if len(selected) >= max_items:
            return selected
    # Fill remaining slots with next-best cloudy scenes
    selected_ids = {it.id for it in selected}
    for item in items:
        if item.id in selected_ids:
            continue
        selected.append(item)
        if len(selected) >= max_items:
            break
    return selected


def build_median_composite(
    items,
    bbox: tuple[float, float, float, float],
    bands: list[str],
    epsg: int,
    resolution: float,
) -> tuple[np.ndarray, object, str]:
    if not items:
        raise RuntimeError("No Sentinel-2 scenes found for the given parameters")

    logger.info("Stacking %d scenes @ epsg=%s resolution=%s", len(items), epsg, resolution)
    # bounds_latlon keeps AOI in WGS84; default float64+nan avoids fill_value dtype errors
    data = stackstac.stack(
        items,
        assets=bands,
        bounds_latlon=bbox,
        epsg=epsg,
        resolution=resolution,
        dtype=np.float64,
        fill_value=np.nan,
        rescale=False,
        chunksize=2048,
    )
    median = data.median(dim="time", skipna=True).compute()
    array = np.asarray(median.values, dtype=np.float32)
    array = np.nan_to_num(array, nan=0.0, posinf=0.0, neginf=0.0)
    height, width = array.shape[-2], array.shape[-1]
    x = np.asarray(median.x.values)
    y = np.asarray(median.y.values)
    res_x = float(abs(x[1] - x[0])) if len(x) > 1 else float(resolution)
    res_y = float(abs(y[1] - y[0])) if len(y) > 1 else float(resolution)
    west = float(min(x) - res_x / 2.0)
    east = float(max(x) + res_x / 2.0)
    south = float(min(y) - res_y / 2.0)
    north = float(max(y) + res_y / 2.0)
    transform = from_bounds(west, south, east, north, width, height)
    return array, transform, f"EPSG:{epsg}"


def save_composite(array: np.ndarray, transform, crs: str, path: Path, band_names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = array.shape[0]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[1],
        width=array.shape[2],
        count=count,
        dtype="float32",
        crs=crs,
        transform=transform,
        compress="deflate",
        tiled=True,
        blockxsize=256,
        blockysize=256,
    ) as dst:
        dst.write(array)
        for i, name in enumerate(band_names):
            dst.set_band_description(i + 1, name)


def download_region(
    region_id: str,
    year: int,
    output_dir: Path,
    max_cloud: int = 40,
    skip_existing: bool = True,
) -> Path:
    if region_id not in REGIONS:
        raise ValueError(f"Unknown region '{region_id}'. Choose from: {', '.join(REGIONS)}")

    region = REGIONS[region_id]
    bbox = tuple(region["bbox"])
    date_range = dry_season_range(year)
    output = output_dir / f"{region_id}_{year}.tif"

    if skip_existing and output.exists() and output.stat().st_size > 10_000:
        logger.info("Skipping existing %s (%.1f MB)", output, output.stat().st_size / 1e6)
        return output

    max_items = int(region.get("max_items", 30))
    logger.info("Searching %s %s (%s)", region["name"], year, date_range)
    items = search_scenes(bbox, date_range, max_cloud=max_cloud, max_items=max_items)
    if not items:
        # Fallback: widen cloud threshold
        logger.warning("No scenes with cloud<%d; retrying with cloud<80", max_cloud)
        items = search_scenes(bbox, date_range, max_cloud=80, max_items=max_items)
    if not items:
        raise RuntimeError(f"No scenes found for {region_id} {year}")

    logger.info("Found %d scenes for %s %s", len(items), region_id, year)
    array, transform, crs = build_median_composite(
        items,
        bbox,
        DEFAULT_BANDS,
        epsg=region["epsg"],
        resolution=region["resolution"],
    )
    save_composite(array, transform, crs, output, DEFAULT_BANDS)

    metadata = {
        "source": STAC_URL,
        "collection": COLLECTION,
        "region_id": region_id,
        "study_area": region["name"],
        "bbox_wgs84": list(bbox),
        "crs": crs,
        "resolution": region["resolution"],
        "resolution_m": region["resolution_m"],
        "bands": DEFAULT_BANDS,
        "year": year,
        "date_range": date_range,
        "scene_count": len(items),
        "shape": list(array.shape),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "output": str(output).replace("\\", "/"),
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Saved %s (%.1f MB)", output, output.stat().st_size / 1e6)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Oman Sentinel-2 composites")
    parser.add_argument(
        "--regions",
        nargs="+",
        default=["oman", "muscat", "sohar", "salalah", "nizwa", "duqm", "sur"],
        help="Region ids to download",
    )
    parser.add_argument("--years", nargs="+", type=int, default=[2020, 2025])
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--max-cloud", type=int, default=40)
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    parser.add_argument("--list-regions", action="store_true")
    args = parser.parse_args()

    if args.list_regions:
        for rid, meta in REGIONS.items():
            print(f"{rid:10s} {meta['name']:20s} bbox={meta['bbox']} res≈{meta['resolution_m']}m")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for region_id in args.regions:
        for year in args.years:
            try:
                path = download_region(
                    region_id,
                    year,
                    args.output_dir,
                    max_cloud=args.max_cloud,
                    skip_existing=not args.force,
                )
                summary.append({"region": region_id, "year": year, "path": str(path), "status": "ok"})
            except Exception as exc:
                logger.exception("Failed %s %s: %s", region_id, year, exc)
                summary.append({"region": region_id, "year": year, "status": "failed", "error": str(exc)})

    summary_path = args.output_dir / "download_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "results": summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Summary written to %s", summary_path)


if __name__ == "__main__":
    main()

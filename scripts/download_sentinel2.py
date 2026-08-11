"""Download Sentinel-2 L2A median composites for Muscat, Oman via Planetary Computer STAC."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import planetary_computer
import rasterio
import stackstac
from pystac_client import Client
from rasterio.transform import from_bounds

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-2-l2a"
DEFAULT_BBOX = (58.35, 23.50, 58.65, 23.65)
DEFAULT_BANDS = ["B02", "B03", "B04", "B08", "B11"]
TARGET_CRS = "EPSG:32640"


def search_scenes(bbox: tuple[float, float, float, float], date_range: str, max_cloud: int = 20):
    catalog = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    search = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": max_cloud}},
    )
    return list(search.items())


def build_median_composite(items, bbox, bands, epsg: int = 32640) -> tuple[np.ndarray, object, str]:
    if not items:
        raise RuntimeError("No Sentinel-2 scenes found for the given parameters")

    data = stackstac.stack(
        items,
        assets=bands,
        bounds=bbox,
        epsg=epsg,
        resolution=10,
        dtype=np.float32,
        rescale=False,
    )
    median = data.median(dim="time", skipna=True).compute()
    array = median.values
    transform = from_bounds(*bbox, array.shape[2], array.shape[1])
    return array, transform, f"EPSG:{epsg}"


def save_composite(array: np.ndarray, transform, crs: str, path: Path, band_names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[1],
        width=array.shape[2],
        count=array.shape[0],
        dtype=array.dtype,
        crs=crs,
        transform=transform,
        compress="deflate",
    ) as dst:
        dst.write(array)
        for i, name in enumerate(band_names):
            dst.set_band_description(i + 1, name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Sentinel-2 composites for Muscat")
    parser.add_argument("--year", type=int, required=True, help="Composite year (e.g. 2020)")
    parser.add_argument("--output", type=Path, required=True, help="Output GeoTIFF path")
    parser.add_argument("--bbox", type=float, nargs=4, default=DEFAULT_BBOX)
    parser.add_argument("--months", default="10-01/02-28", help="Dry season date range within year")
    args = parser.parse_args()

    year = args.year
    date_range = f"{year}-{args.months}"
    items = search_scenes(tuple(args.bbox), date_range)
    array, transform, crs = build_median_composite(items, tuple(args.bbox), DEFAULT_BANDS)
    save_composite(array, transform, crs, args.output, DEFAULT_BANDS)

    metadata = {
        "source": STAC_URL,
        "collection": COLLECTION,
        "study_area": "Muscat, Oman",
        "bbox_wgs84": list(args.bbox),
        "crs": crs,
        "resolution_m": 10,
        "bands": DEFAULT_BANDS,
        "year": year,
        "date_range": date_range,
        "scene_count": len(items),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "output": str(args.output),
    }
    meta_path = args.output.with_suffix(".json")
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved composite to {args.output} ({len(items)} scenes)")


if __name__ == "__main__":
    main()

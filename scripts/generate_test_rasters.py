"""Generate synthetic sample GeoTIFFs for development and testing."""

from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_bounds

BAND_NAMES = ["B02", "B03", "B04", "B08", "B11"]
WGS84_BBOX = (58.35, 23.50, 58.65, 23.65)  # west, south, east, north
WIDTH, HEIGHT = 200, 200
CRS = "EPSG:32640"


def _utm_bounds() -> tuple[float, float, float, float]:
    west, south, east, north = WGS84_BBOX
    transformer = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    xs, ys = transformer.transform([west, east, west, east], [south, south, north, north])
    return min(xs), min(ys), max(xs), max(ys)


def _create_bands(seed: int, change_patch: bool = False) -> np.ndarray:
    rng = np.random.default_rng(seed)
    bands = []
    for _ in range(5):
        base = rng.uniform(0.1, 0.6, (HEIGHT, WIDTH)).astype(np.float32)
        bands.append(base)

    # Simulate vegetation (high NIR, moderate red)
    bands[3] = bands[3] * 0.5 + 0.4  # NIR
    bands[2] = bands[2] * 0.3 + 0.1  # Red

    # Simulate built-up in SWIR
    bands[4] = bands[4] * 0.2 + 0.3

    if change_patch:
        # Urban expansion patch: lower NDVI, higher NDBI
        bands[2][80:120, 80:120] = 0.25
        bands[3][80:120, 80:120] = 0.15
        bands[4][80:120, 80:120] = 0.65

    return np.stack(bands, axis=0)


def write_geotiff(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bounds = _utm_bounds()
    transform = from_bounds(*bounds, WIDTH, HEIGHT)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=HEIGHT,
        width=WIDTH,
        count=array.shape[0],
        dtype=array.dtype,
        crs=CRS,
        transform=transform,
        compress="deflate",
    ) as dst:
        dst.write(array)
        for i, name in enumerate(BAND_NAMES):
            dst.set_band_description(i + 1, name)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    samples_dir = root / "data" / "samples"
    t1 = _create_bands(seed=42, change_patch=False)
    t2 = _create_bands(seed=42, change_patch=True)
    write_geotiff(samples_dir / "sample_t1.tif", t1)
    write_geotiff(samples_dir / "sample_t2.tif", t2)
    print(f"Created sample rasters in {samples_dir}")


if __name__ == "__main__":
    main()

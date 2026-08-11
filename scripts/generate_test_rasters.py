"""Generate synthetic sample GeoTIFFs for development and testing.

Produces a spatially coherent Muscat-like scene (not random TV static)
so RGB map overlays look intentional in the dashboard.
"""

from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_bounds

BAND_NAMES = ["B02", "B03", "B04", "B08", "B11"]
WGS84_BBOX = (58.35, 23.50, 58.65, 23.65)  # west, south, east, north
WIDTH, HEIGHT = 512, 256  # ~2:1 matches lon/lat span of the bbox; higher res = less map pixelation
CRS = "EPSG:32640"

# Urban-change patches (row0, row1, col0, col1) in array coordinates
CHANGE_PATCHES = [
    (36, 84, 60, 140),
    (40, 96, 340, 420),
    (100, 156, 200, 300),
    (170, 220, 80, 170),
    (180, 236, 350, 460),
    (110, 150, 60, 110),
    (70, 110, 240, 310),
]


def _utm_bounds() -> tuple[float, float, float, float]:
    west, south, east, north = WGS84_BBOX
    transformer = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    xs, ys = transformer.transform([west, east, west, east], [south, south, north, north])
    return min(xs), min(ys), max(xs), max(ys)


def _smooth_noise(rng: np.random.Generator, shape: tuple[int, int], scale: int) -> np.ndarray:
    """Low-frequency noise via upsample of a coarse grid (terrain-like)."""
    h, w = shape
    coarse = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    yy = np.linspace(0, coarse.shape[0] - 1, h)
    xx = np.linspace(0, coarse.shape[1] - 1, w)
    y0 = np.floor(yy).astype(int)
    x0 = np.floor(xx).astype(int)
    y1 = np.clip(y0 + 1, 0, coarse.shape[0] - 1)
    x1 = np.clip(x0 + 1, 0, coarse.shape[1] - 1)
    wy = (yy - y0)[:, None]
    wx = (xx - x0)[None, :]
    top = coarse[y0][:, x0] * (1 - wx) + coarse[y0][:, x1] * wx
    bot = coarse[y1][:, x0] * (1 - wx) + coarse[y1][:, x1] * wx
    return top * (1 - wy) + bot * wy


def _apply_urban_patch(bands: list[np.ndarray], r0: int, r1: int, c0: int, c1: int) -> None:
    bands[2][r0:r1, c0:c1] = np.clip(bands[2][r0:r1, c0:c1] * 0.4 + 0.32, 0, 1)  # Red up
    bands[3][r0:r1, c0:c1] = np.clip(bands[3][r0:r1, c0:c1] * 0.35 + 0.10, 0, 1)  # NIR down
    bands[4][r0:r1, c0:c1] = np.clip(bands[4][r0:r1, c0:c1] * 0.3 + 0.62, 0, 1)  # SWIR up
    # Blue/green slightly brighter (built-up)
    bands[0][r0:r1, c0:c1] = np.clip(bands[0][r0:r1, c0:c1] * 0.5 + 0.22, 0, 1)
    bands[1][r0:r1, c0:c1] = np.clip(bands[1][r0:r1, c0:c1] * 0.5 + 0.20, 0, 1)


def _create_bands(seed: int, change_patch: bool = False) -> np.ndarray:
    rng = np.random.default_rng(seed)
    h, w = HEIGHT, WIDTH

    land = _smooth_noise(rng, (h, w), scale=24)
    hills = _smooth_noise(rng, (h, w), scale=12)
    detail = _smooth_noise(rng, (h, w), scale=6) * 0.15

    # North = higher elevation / rockier; south-east coastal wash
    row = np.linspace(0.15, 0.85, h, dtype=np.float32)[:, None]
    col = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    desert = np.clip(0.35 + 0.35 * land + 0.2 * hills + detail - 0.15 * col, 0.05, 0.95)

    # Vegetation corridors (wadis / parks) — higher NIR, lower red
    veg_mask = (_smooth_noise(rng, (h, w), scale=18) > 0.62) & (np.broadcast_to(row > 0.25, (h, w)))
    # Water / coastal band along south edge
    water = np.broadcast_to(row > 0.88, (h, w)).copy()

    # Base reflectance (arid Oman palette)
    blue = np.clip(0.12 + 0.18 * desert + 0.05 * detail, 0, 1).astype(np.float32)
    green = np.clip(0.14 + 0.22 * desert + 0.04 * hills, 0, 1).astype(np.float32)
    red = np.clip(0.18 + 0.28 * desert + 0.06 * detail, 0, 1).astype(np.float32)
    nir = np.clip(0.22 + 0.20 * desert + 0.08 * hills, 0, 1).astype(np.float32)
    swir = np.clip(0.25 + 0.30 * desert, 0, 1).astype(np.float32)

    # Existing urban texture (Muscat-like grid clusters) present in both years
    urban0 = (_smooth_noise(rng, (h, w), scale=10) > 0.72) & (~water) & (col > 0.2) & (col < 0.85)
    for arr, add in ((blue, 0.08), (green, 0.06), (red, 0.10), (nir, -0.05), (swir, 0.12)):
        arr[urban0] = np.clip(arr[urban0] + add, 0, 1)

    blue[veg_mask] = np.clip(blue[veg_mask] * 0.7, 0, 1)
    green[veg_mask] = np.clip(green[veg_mask] * 0.85 + 0.08, 0, 1)
    red[veg_mask] = np.clip(red[veg_mask] * 0.55, 0, 1)
    nir[veg_mask] = np.clip(nir[veg_mask] * 0.5 + 0.45, 0, 1)
    swir[veg_mask] = np.clip(swir[veg_mask] * 0.6, 0, 1)

    blue[water] = 0.05
    green[water] = 0.08
    red[water] = 0.04
    nir[water] = 0.02
    swir[water] = 0.02

    bands = [blue, green, red, nir, swir]

    if change_patch:
        for r0, r1, c0, c1 in CHANGE_PATCHES:
            _apply_urban_patch(bands, r0, r1, c0, c1)

    # Tiny sensor noise (subtle, not TV static)
    for i in range(5):
        bands[i] = np.clip(bands[i] + rng.normal(0, 0.008, (h, w)).astype(np.float32), 0, 1).astype(
            np.float32
        )

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
    print(f"Created coherent sample rasters ({WIDTH}x{HEIGHT}) with {len(CHANGE_PATCHES)} change patches in {samples_dir}")


if __name__ == "__main__":
    main()

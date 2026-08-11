"""Shared raster I/O and metadata utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform, reproject


@dataclass
class RasterData:
    """In-memory raster with geospatial metadata."""

    array: np.ndarray
    transform: Affine
    crs: str
    nodata: float | None = None
    band_names: list[str] | None = None

    @property
    def shape(self) -> tuple[int, ...]:
        return self.array.shape

    @property
    def height(self) -> int:
        return self.array.shape[-2]

    @property
    def width(self) -> int:
        return self.array.shape[-1]

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return rasterio.transform.array_bounds(self.height, self.width, self.transform)

    def band(self, index: int) -> np.ndarray:
        if self.array.ndim == 2:
            return self.array
        return self.array[index]

    def to_dict(self) -> dict[str, Any]:
        return {
            "shape": self.shape,
            "crs": self.crs,
            "transform": list(self.transform),
            "bounds": self.bounds,
            "band_names": self.band_names,
        }


class RasterLoader:
    """Load GeoTIFF rasters and expose metadata."""

    @staticmethod
    def load(path: str | Path) -> RasterData:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Raster not found: {path}")

        with rasterio.open(path) as src:
            array = src.read().astype(np.float32)
            band_names = [src.descriptions[i] or f"band_{i+1}" for i in range(src.count)]
            return RasterData(
                array=array,
                transform=src.transform,
                crs=str(src.crs) if src.crs else "EPSG:4326",
                nodata=src.nodata,
                band_names=band_names,
            )

    @staticmethod
    def save(raster: RasterData, path: str | Path, compress: str = "deflate") -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        count = 1 if raster.array.ndim == 2 else raster.array.shape[0]
        dtype = raster.array.dtype

        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=raster.height,
            width=raster.width,
            count=count,
            dtype=dtype,
            crs=raster.crs,
            transform=raster.transform,
            nodata=raster.nodata,
            compress=compress,
        ) as dst:
            if raster.array.ndim == 2:
                dst.write(raster.array, 1)
            else:
                dst.write(raster.array)
            if raster.band_names:
                for i, name in enumerate(raster.band_names[:count]):
                    dst.set_band_description(i + 1, name)
        return path


def reproject_array(
    array: np.ndarray,
    src_transform: Affine,
    src_crs: str,
    dst_crs: str,
    dst_transform: Affine | None = None,
    dst_width: int | None = None,
    dst_height: int | None = None,
    resampling: Resampling = Resampling.bilinear,
) -> tuple[np.ndarray, Affine]:
    """Reproject a single-band or multi-band array to a target CRS."""
    if array.ndim == 2:
        arrays = [array]
    else:
        arrays = [array[i] for i in range(array.shape[0])]

    if dst_transform is None or dst_width is None or dst_height is None:
        dst_transform, dst_width, dst_height = calculate_default_transform(
            src_crs,
            dst_crs,
            arrays[0].shape[1],
            arrays[0].shape[0],
            *rasterio.transform.array_bounds(arrays[0].shape[0], arrays[0].shape[1], src_transform),
        )

    out_arrays = []
    for band in arrays:
        dest = np.zeros((dst_height, dst_width), dtype=band.dtype)
        reproject(
            source=band,
            destination=dest,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=resampling,
        )
        out_arrays.append(dest)

    result = out_arrays[0] if len(out_arrays) == 1 else np.stack(out_arrays, axis=0)
    return result, dst_transform


def pixel_area_m2(transform: Affine) -> float:
    return abs(transform.a * transform.e)


def pixel_area_km2(transform: Affine) -> float:
    return pixel_area_m2(transform) / 1_000_000.0

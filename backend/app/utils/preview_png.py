"""Export analysis arrays as Leaflet-friendly PNG overlays."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def _to_uint8_stretch(arr: np.ndarray, p_low: float = 2.0, p_high: float = 98.0) -> np.ndarray:
    data = np.asarray(arr, dtype=np.float32)
    valid = np.isfinite(data)
    if not valid.any():
        return np.zeros(data.shape, dtype=np.uint8)
    lo, hi = np.percentile(data[valid], [p_low, p_high])
    if hi <= lo:
        hi = lo + 1e-6
    scaled = (np.clip(data, lo, hi) - lo) / (hi - lo)
    scaled = np.where(valid, scaled, 0.0)
    return (scaled * 255.0).astype(np.uint8)


def save_rgb_png(rgb: np.ndarray, path: Path, soft: bool = True) -> Path:
    """rgb shape (3, H, W) or (H, W, 3). Uses linked stretch for natural color."""
    path = Path(path)
    arr = np.asarray(rgb, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[0] in (3, 4):
        arr = np.moveaxis(arr[:3], 0, -1)
    h, w = arr.shape[:2]
    valid = np.isfinite(arr).all(axis=-1)
    # Linked percentile stretch keeps RGB relationships (avoids TV-static look)
    flat = arr[valid]
    if flat.size == 0:
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", optimize=True)
        return path
    lo = float(np.percentile(flat, 2))
    hi = float(np.percentile(flat, 98))
    if hi <= lo:
        hi = lo + 1e-6
    scaled = np.clip((arr - lo) / (hi - lo), 0, 1)
    rgb8 = (scaled * 255.0).astype(np.uint8)
    rgb8[~valid] = 0
    if soft and min(h, w) >= 32:
        pad = np.pad(rgb8, ((1, 1), (1, 1), (0, 0)), mode="edge").astype(np.float32)
        rgb8 = (
            (
                pad[0:-2, 0:-2]
                + pad[0:-2, 1:-1]
                + pad[0:-2, 2:]
                + pad[1:-1, 0:-2]
                + pad[1:-1, 1:-1]
                + pad[1:-1, 2:]
                + pad[2:, 0:-2]
                + pad[2:, 1:-1]
                + pad[2:, 2:]
            )
            / 9.0
        ).astype(np.uint8)
    rgba = np.dstack([rgb8, np.full((h, w), 235, dtype=np.uint8)])
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", optimize=True)
    return path


def save_change_mask_png(mask: np.ndarray, path: Path) -> Path:
    """Binary change mask → amber overlay with transparency."""
    path = Path(path)
    m = np.asarray(mask)
    if m.ndim == 3:
        m = m[0]
    changed = m.astype(bool)
    h, w = changed.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[changed, 0] = 224  # amber/coral
    rgba[changed, 1] = 100
    rgba[changed, 2] = 52
    rgba[changed, 3] = 200
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", optimize=True)
    return path


def save_ndvi_diff_png(diff: np.ndarray, path: Path) -> Path:
    """Diverging teal↔coral colormap for NDVI difference."""
    path = Path(path)
    d = np.asarray(diff, dtype=np.float32)
    if d.ndim == 3:
        d = d[0]
    valid = np.isfinite(d)
    lim = float(np.nanpercentile(np.abs(d[valid]), 98)) if valid.any() else 1.0
    lim = max(lim, 1e-6)
    norm = np.clip(d / lim, -1.0, 1.0)
    h, w = d.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    # loss (negative) → coral, gain (positive) → teal
    loss = np.clip(-norm, 0, 1)
    gain = np.clip(norm, 0, 1)
    rgba[..., 0] = (224 * loss + 47 * gain).astype(np.uint8)
    rgba[..., 1] = (100 * loss + 158 * gain).astype(np.uint8)
    rgba[..., 2] = (82 * loss + 138 * gain).astype(np.uint8)
    rgba[..., 3] = (np.where(valid, (40 + 180 * np.abs(norm)), 0)).astype(np.uint8)
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", optimize=True)
    return path


def save_intensity_png(intensity: np.ndarray, path: Path) -> Path:
    path = Path(path)
    arr = np.asarray(intensity, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[0]
    gray = _to_uint8_stretch(arr)
    h, w = gray.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., 0] = gray
    rgba[..., 1] = (gray * 0.55).astype(np.uint8)
    rgba[..., 2] = 20
    rgba[..., 3] = np.where(gray > 5, np.clip(gray + 40, 0, 220), 0).astype(np.uint8)
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", optimize=True)
    return path

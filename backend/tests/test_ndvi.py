"""NDVI calculation tests."""

import numpy as np

from app.services.ndvi.ndvi_service import compute_ndvi


def test_compute_ndvi_vegetation():
    red = np.array([[0.1, 0.2], [0.1, 0.2]])
    nir = np.array([[0.5, 0.6], [0.5, 0.6]])
    ndvi = compute_ndvi(red, nir)
    assert ndvi.min() > 0
    assert ndvi.max() < 1


def test_compute_ndvi_bare_soil():
    red = np.array([[0.4, 0.4]])
    nir = np.array([[0.42, 0.42]])
    ndvi = compute_ndvi(red, nir)
    assert np.all(np.abs(ndvi) < 0.1)

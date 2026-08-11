"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_paths():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    samples = root / "data" / "samples"
    t1 = samples / "sample_t1.tif"
    t2 = samples / "sample_t2.tif"
    if not t1.exists() or not t2.exists():
        import sys

        sys.path.insert(0, str(root))
        from scripts.generate_test_rasters import main as generate_samples

        generate_samples()
    return t1, t2

"""Spatial analysis tests."""

from app.services.analysis_service import AnalysisService


def test_polygonize_produces_geojson(sample_paths):
    t1, t2 = sample_paths
    service = AnalysisService()
    result = service.run_analysis(t1, t2)

    assert result.geojson["type"] == "FeatureCollection"
    if result.num_change_regions > 0:
        feature = result.geojson["features"][0]
        assert "area_km2" in feature["properties"]
        assert feature["properties"]["area_km2"] > 0

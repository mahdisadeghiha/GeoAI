"""Change detection tests."""

from app.services.analysis_service import AnalysisService


def test_detects_known_change_patch(sample_paths):
    t1, t2 = sample_paths
    service = AnalysisService()
    result = service.run_analysis(t1, t2, method="baseline")

    assert result.changed_area_km2 > 0
    assert result.change_percentage > 0
    assert result.num_change_regions >= 1


def test_cva_method_runs(sample_paths):
    t1, t2 = sample_paths
    service = AnalysisService()
    result = service.run_analysis(t1, t2, method="cva")
    assert result.changed_area_km2 >= 0

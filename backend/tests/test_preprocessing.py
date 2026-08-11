"""Preprocessing pipeline tests."""

from app.services.preprocessing.pipeline import PreprocessingPipeline


def test_preprocessing_aligns_sample_pair(sample_paths):
    t1, t2 = sample_paths
    pipeline = PreprocessingPipeline()
    result = pipeline.run(t1, t2)

    assert result.raster_t1.shape == result.raster_t2.shape
    assert result.raster_t1.crs == result.raster_t2.crs
    assert result.valid_mask.sum() > 0

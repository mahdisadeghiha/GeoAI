"""CRS comparison utilities."""


def check_crs(crs_a: str, crs_b: str, target_crs: str | None = None) -> dict:
    """Compare CRS of two rasters and determine reprojection needs."""
    needs_reproject_a = target_crs is not None and crs_a != target_crs
    needs_reproject_b = target_crs is not None and crs_b != target_crs
    return {
        "crs_a": crs_a,
        "crs_b": crs_b,
        "target_crs": target_crs,
        "needs_reproject_a": needs_reproject_a,
        "needs_reproject_b": needs_reproject_b,
        "crs_match": crs_a == crs_b,
    }

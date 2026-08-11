"""API endpoint tests."""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data


def test_study_area_endpoint(client: TestClient):
    response = client.get("/api/study-area")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Muscat, Oman"
    assert len(data["bbox"]) == 4


def test_study_areas_list(client: TestClient):
    response = client.get("/api/study-areas")
    assert response.status_code == 200
    data = response.json()
    assert len(data["areas"]) >= 1
    assert 2020 in data["available_years"]


def test_analyze_with_samples(client: TestClient, sample_paths):
    response = client.post(
        "/api/analyze",
        data={
            "use_samples": "true",
            "method": "baseline",
            "study_area_id": "muscat",
            "year_t1": "2020",
            "year_t2": "2025",
            "bbox_west": "58.40",
            "bbox_south": "23.55",
            "bbox_east": "58.55",
            "bbox_north": "23.62",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["study_area_km2"] > 0
    assert data["aoi_bbox"] is not None
    assert data["study_area_name"] == "Muscat, Oman"
    assert data["year_t1"] == 2020
    assert data["year_t2"] == 2025
    assert "change_percentage" in data
    assert data["num_change_regions"] >= 0

    stats = client.get("/api/statistics", params={"run_id": data["run_id"]})
    assert stats.status_code == 200

    changes = client.get("/api/changes", params={"run_id": data["run_id"]})
    assert changes.status_code == 200
    assert changes.json()["type"] == "FeatureCollection"

    ndvi = client.get("/api/ndvi", params={"run_id": data["run_id"]})
    assert ndvi.status_code == 200

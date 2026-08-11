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


def test_analyze_with_samples(client: TestClient, sample_paths):
    response = client.post("/api/analyze", data={"use_samples": "true", "method": "baseline"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["study_area_km2"] > 0
    assert "change_percentage" in data
    assert data["num_change_regions"] >= 0

    stats = client.get("/api/statistics", params={"run_id": data["run_id"]})
    assert stats.status_code == 200

    changes = client.get("/api/changes", params={"run_id": data["run_id"]})
    assert changes.status_code == 200
    assert changes.json()["type"] == "FeatureCollection"

    ndvi = client.get("/api/ndvi", params={"run_id": data["run_id"]})
    assert ndvi.status_code == 200

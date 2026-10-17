"""
Automated unit & integration tests for DermaSense Public Health Surveillance,
Privacy Guarantees, Admin Authentication, and Epidemiological Spike Detection.
"""

import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import ADMIN_PASSWORD, SURVEILLANCE_DB_PATH
from backend.services.surveillance import surveillance_service

client = TestClient(app)


def test_telemetry_opt_in_success():
    """Validates that opt-in telemetry succeeds only with explicit user consent."""
    payload = {
        "consent": True,
        "condition_id": "melanocytic_nevus",
        "condition_name": "Melanocytic Nevus (Benign Mole)",
        "region": "Sundargarh, Odisha",
    }
    response = client.post("/api/telemetry/opt-in", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["condition_id"] == "melanocytic_nevus"
    assert data["region"] == "Sundargarh, Odisha"
    assert "record_id" in data


def test_telemetry_rejected_without_consent():
    """Asserts that telemetry is strictly rejected with HTTP 400 if user consent is False."""
    payload = {
        "consent": False,
        "condition_id": "melanoma",
        "condition_name": "Melanoma (Skin Cancer)",
        "region": "Khordha, Odisha",
    }
    response = client.post("/api/telemetry/opt-in", json=payload)
    assert response.status_code == 400
    assert "User consent is required" in response.json()["detail"]


def test_privacy_guarantee_no_ip_no_image_in_database():
    """
    Verifies that the SQLite surveillance schema has ZERO columns for IP addresses,
    personal identifiers, device headers, or image binaries.
    """
    conn = sqlite3.connect(str(SURVEILLANCE_DB_PATH))
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(opt_in_telemetry);")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()

    # Assert permitted columns only
    assert set(columns) == {"id", "condition_id", "condition_name", "region", "timestamp", "date_day"}
    assert "ip" not in columns
    assert "ip_address" not in columns
    assert "image" not in columns
    assert "user_id" not in columns
    assert "name" not in columns


def test_admin_metrics_unauthorized_without_password():
    """Asserts that GET /api/admin/metrics returns HTTP 401 when no valid password is provided."""
    response = client.get("/api/admin/metrics")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

    response_bad_pwd = client.get("/api/admin/metrics", headers={"X-Admin-Password": "wrong_password_123"})
    assert response_bad_pwd.status_code == 401


def test_admin_metrics_authorized_with_header():
    """Asserts that GET /api/admin/metrics succeeds with X-Admin-Password header."""
    response = client.get("/api/admin/metrics", headers={"X-Admin-Password": ADMIN_PASSWORD})
    assert response.status_code == 200
    data = response.json()

    assert "total_records" in data
    assert data["total_records"] > 0
    assert "by_condition" in data
    assert "by_region" in data
    assert "timeline" in data
    assert "spikes" in data
    assert "feedback_summary" in data


def test_admin_verify_password_endpoint():
    """Asserts that POST /api/admin/verify validates administrative passwords correctly."""
    res_valid = client.post("/api/admin/verify", json={"password": ADMIN_PASSWORD})
    assert res_valid.status_code == 200
    assert res_valid.json()["valid"] is True

    res_invalid = client.post("/api/admin/verify", json={"password": "bad_password"})
    assert res_invalid.status_code == 200
    assert res_invalid.json()["valid"] is False


def test_spike_detector_statistical_trigger():
    """
    Asserts that the statistical outbreak detection logic properly triggers is_spike=True
    when a condition/region weekly count exceeds mean + 2*sigma.
    """
    metrics = surveillance_service.get_metrics()
    spikes = metrics["spikes"]
    assert len(spikes) > 0

    # Locate seeded spike for Tinea in Khurda
    tinea_spike = next(
        (s for s in spikes if s["condition_id"] == "tinea_ringworm" and "Khurda" in s["region"]),
        None,
    )
    assert tinea_spike is not None
    assert tinea_spike["is_spike"] is True
    assert tinea_spike["current_week_count"] > tinea_spike["threshold"]
    assert tinea_spike["z_score"] >= 2.0
    assert tinea_spike["alert_level"] in ("WARNING", "CRITICAL")


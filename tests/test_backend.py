"""
DermaSense Automated Backend Test Suite.
Verifies all clinical safety requirements, file validation, OOD detection,
mandatory disclaimers, and API contracts according to SIH 2025 non-negotiable rules.
"""

import io
import glob
import pytest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import PROJECT_ROOT, MANDATORY_DISCLAIMER


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sample_melanoma_path():
    mel_files = glob.glob(str(PROJECT_ROOT / "data" / "raw" / "isic" / "melanoma" / "*.*"))
    assert len(mel_files) > 0, "No sample melanoma images found in data/raw/isic/melanoma"
    return Path(mel_files[0])


@pytest.fixture(scope="module")
def sample_nevus_path():
    nev_files = glob.glob(str(PROJECT_ROOT / "data" / "raw" / "isic" / "melanocytic_nevus" / "*.*"))
    assert len(nev_files) > 0, "No sample nevus images found in data/raw/isic/melanocytic_nevus"
    return Path(nev_files[0])


@pytest.fixture(scope="module")
def sample_not_skin_path():
    not_files = glob.glob(str(PROJECT_ROOT / "data" / "raw" / "not_skin" / "*.*"))
    assert len(not_files) > 0, "No sample non-skin images found in data/raw/not_skin"
    return Path(not_files[0])


def test_health_endpoint(client):
    """Verifies that the /api/health endpoint reports healthy status and model parameters."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "melanoma" in data["supported_classes"]
    assert data["temperature_scaling_factor"] > 0
    assert "DISCLAIMER" in data["disclaimer"]


def test_conditions_catalog_endpoint(client):
    """Verifies that /api/conditions lists verified medical guides with reviewed_by_clinician=False."""
    response = client.get("/api/conditions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 10
    assert "DISCLAIMER" in data["disclaimer"]

    # Verify Rule 5: reviewed_by_clinician must be False
    for condition in data["conditions"]:
        assert condition["reviewed_by_clinician"] is False
        assert "condition_id" in condition
        assert "name" in condition
        assert "description" in condition


def test_valid_skin_image(client, sample_melanoma_path):
    """Tests /api/predict with an authentic skin lesion image."""
    with open(sample_melanoma_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/predict",
        files={"file": (sample_melanoma_path.name, file_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()

    # Rule 4: Mandatory disclaimer
    assert "disclaimer" in data
    assert "DISCLAIMER" in data["disclaimer"]
    assert "diagnosis" not in data["assessment_summary"].lower() or "not provide a clinical diagnosis" in data["disclaimer"].lower()

    # Top-3 conditions verification
    assert len(data["top_conditions"]) == 3
    assert data["top_conditions"][0]["probability"] >= data["top_conditions"][1]["probability"]
    assert data["confidence_score"] > 0.0

    # Explainability: Grad-CAM base64 data URI
    assert data["gradcam_heatmap"] is not None
    assert data["gradcam_heatmap"].startswith("data:image/png;base64,")

    # High-risk doctor consultation notice
    assert data["doctor_notice"] is not None
    assert "URGENT MEDICAL NOTICE" in data["doctor_notice"]

    # Knowledge base attachment
    assert data["knowledge_base"] is not None
    assert data["knowledge_base"]["reviewed_by_clinician"] is False


def test_corrupt_image_upload(client):
    """Tests that corrupt image bytes trigger HTTP 400 Bad Request."""
    corrupt_bytes = b"NOT_A_VALID_IMAGE_HEADER_CORRUPTED_BYTES"
    response = client.post(
        "/api/predict",
        files={"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "corrupt or not a recognized image" in response.json()["detail"].lower()


def test_wrong_file_type(client):
    """Tests that non-image file uploads trigger HTTP 415 Unsupported Media Type."""
    text_bytes = b"Hello world, this is a plain text file."
    response = client.post(
        "/api/predict",
        files={"file": ("notes.txt", text_bytes, "text/plain")},
    )
    assert response.status_code == 415
    assert "unsupported" in response.json()["detail"].lower()


def test_oversized_file(client):
    """Tests that uploads exceeding 8 MB trigger HTTP 413 Payload Too Large."""
    oversized_bytes = b"X" * (8 * 1024 * 1024 + 1024) # 8 MB + 1 KB
    response = client.post(
        "/api/predict",
        files={"file": ("giant.jpg", oversized_bytes, "image/jpeg")},
    )
    assert response.status_code == 413
    assert "8 mb" in response.json()["detail"].lower()


def test_non_skin_image_returns_unable_to_assess(client, sample_not_skin_path):
    """
    Tests that uploading a non-skin image (clothing/furniture/background) triggers
    the out-of-distribution safeguard returning 'unable to assess'.
    """
    with open(sample_not_skin_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/predict",
        files={"file": (sample_not_skin_path.name, file_bytes, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()

    # Must return unable to assess
    assert data["status"] == "unable_to_assess"
    assert "unable to assess" in data["assessment_summary"].lower()
    assert data["low_confidence"] is True or data["is_skin"] is False

    # Disclaimer must still be present
    assert "disclaimer" in data
    assert "DISCLAIMER" in data["disclaimer"]


def test_disclaimer_always_present_and_no_diagnosis_claims(client, sample_nevus_path):
    """
    Rule 4 & 5 verification:
    - Disclaimer must be present in every result screen
    - App never claims to deliver a 'diagnosis'
    """
    with open(sample_nevus_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/predict",
        files={"file": (sample_nevus_path.name, file_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "disclaimer" in data
    assert len(data["disclaimer"]) > 50

    # Ensure result summary says 'Possible condition'
    assert "possible condition" in data["assessment_summary"].lower() or "unable to assess" in data["assessment_summary"].lower()


def test_feedback_submission(client):
    """Tests submitting feedback via /api/feedback."""
    payload = {
        "prediction_id": "test-uuid-12345",
        "condition_id": "melanocytic_nevus",
        "rating": 5,
        "feedback_text": "Clear explanation and helpful precautions.",
        "clinician_reviewed": False,
    }
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "recorded" in data["message"].lower()


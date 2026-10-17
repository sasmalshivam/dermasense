"""
DermaSense Phase 5 Automated Test Suite: RAG Chatbot, Multilingual & Grounding.
Verifies grounded extraction, follow-up context resolution, out-of-scope rejection,
and Indic translations (Hindi, Odia, etc.) according to SIH 2025 non-negotiable rules.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_grounded_melanoma_symptoms(client):
    """Q1: Verifies retrieval of melanoma symptoms with authoritative citations."""
    response = client.post(
        "/api/chat",
        json={"message": "What are the common symptoms of melanoma?", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert len(data["sources"]) > 0
    assert "mole" in data["answer"].lower() or "changing" in data["answer"].lower()
    assert "disclaimer" in data


def test_contextual_followup_contagious(client):
    """Q2: Verifies context resolution for follow-up question 'is it contagious?' for melanoma."""
    response = client.post(
        "/api/chat",
        json={"message": "is it contagious?", "detected_condition": "melanoma", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "not contagious" in data["answer"].lower()
    assert len(data["sources"]) > 0


def test_contextual_followup_donot(client):
    """Q3: Verifies context resolution for harmful practices to strictly avoid for melanoma."""
    response = client.post(
        "/api/chat",
        json={"message": "what should I avoid doing?", "detected_condition": "melanoma", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "do not" in data["answer"].lower() or "scrape" in data["answer"].lower() or "cut" in data["answer"].lower()
    assert len(data["sources"]) > 0


def test_tinea_first_aid(client):
    """Q4: Verifies retrieval of first aid guidance for ringworm / fungal infection."""
    response = client.post(
        "/api/chat",
        json={"message": "What is the first aid for ringworm or fungal infection?", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "wash" in data["answer"].lower() or "dry" in data["answer"].lower() or "clean" in data["answer"].lower()
    assert len(data["sources"]) > 0


def test_out_of_scope_english(client):
    """Q5: Verifies strict out-of-scope rejection for non-dermatological queries."""
    response = client.post(
        "/api/chat",
        json={"message": "What is the capital of Australia?", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is False
    assert data["answer"] == "I don't know, please see a doctor."
    assert len(data["sources"]) == 0


def test_hindi_grounded_contagious(client):
    """Q6: Verifies Hindi language grounded response for melanoma contagion."""
    response = client.post(
        "/api/chat",
        json={"message": "क्या मेलानोमा संक्रामक है?", "detected_condition": "melanoma", "language": "hi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "संक्रामक" in data["answer"]
    assert len(data["sources"]) > 0
    assert "translation_note" in data


def test_odia_grounded_donot(client):
    """Q7: Verifies Odia language grounded response for melanoma care."""
    response = client.post(
        "/api/chat",
        json={"message": "ମେଲାନୋମା ହେଲେ କଣ କରିବା ଉଚିତ ନୁହେଁ?", "detected_condition": "melanoma", "language": "or"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert len(data["sources"]) > 0


def test_hindi_out_of_scope(client):
    """Q8: Verifies Hindi language out-of-scope rejection for non-dermatological queries."""
    response = client.post(
        "/api/chat",
        json={"message": "क्रिकेट मैच कौन जीता?", "language": "hi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is False
    assert "मुझे नहीं पता, कृपया डॉक्टर को दिखाएं।" in data["answer"]
    assert len(data["sources"]) == 0


def test_translations_endpoint(client):
    """Verifies that /api/translations provides all 7 required languages and the disclaimer notice."""
    response = client.get("/api/translations")
    assert response.status_code == 200
    data = response.json()
    assert "notice" in data
    assert "Translations are machine-generated and need human review." in data["notice"]
    assert "languages" in data
    for lang in ["en", "hi", "or", "bn", "ta", "te", "mr"]:
        assert lang in data["languages"]
        assert lang in data["translations"]


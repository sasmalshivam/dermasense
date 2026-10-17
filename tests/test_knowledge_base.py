"""
Phase 1 Clinical Knowledge Base Validation Tests.
Enforces non-negotiable medical constraints:
- WHO, MoHFW, AAD, NHS, CDC, DermNet NZ source citation
- reviewed_by_clinician: False
- Absence of definitive diagnosis claims
- Full structure: symptoms, first_aid, precautions, do_nots, red_flags, when_to_see_doctor
"""

import os
import sys
import json
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data.knowledge_base.schema import KnowledgeBase, APPROVED_AUTHORITY_DOMAINS


KB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base", "conditions.json")


def test_knowledge_base_file_exists():
    assert os.path.exists(KB_PATH), f"Knowledge base file missing at {KB_PATH}"


def test_knowledge_base_schema_validation():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Validate with Pydantic model
    kb = KnowledgeBase.model_validate(raw_data)
    assert len(kb.conditions) >= 7, f"Expected at least 7 dermatological conditions, found {len(kb.conditions)}"
    assert "disclaimer" in raw_data and len(kb.disclaimer) > 20


def test_clinician_review_flag_is_strictly_false():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    for cond in raw_data["conditions"]:
        assert cond.get("reviewed_by_clinician") is False, (
            f"Rule 5 violation: condition {cond.get('condition_id')} has reviewed_by_clinician != False"
        )


def test_source_citations_and_domains():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    for cond in raw_data["conditions"]:
        sources = cond.get("sources", [])
        assert len(sources) >= 1, f"Condition {cond.get('condition_id')} missing source citations"
        for src in sources:
            url = src.get("url", "")
            has_approved_domain = any(domain in url for domain in APPROVED_AUTHORITY_DOMAINS)
            assert has_approved_domain, (
                f"Source URL {url} in condition {cond.get('condition_id')} does not match approved domains: {APPROVED_AUTHORITY_DOMAINS}"
            )


def test_structured_clinical_guidance_fields():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    required_fields = [
        "condition_id",
        "name",
        "category",
        "summary",
        "symptoms",
        "first_aid",
        "precautions",
        "do_nots",
        "red_flags",
        "when_to_see_doctor",
        "sources",
        "reviewed_by_clinician",
    ]

    for cond in raw_data["conditions"]:
        for field in required_fields:
            assert field in cond, f"Missing required field '{field}' in condition {cond.get('condition_id')}"
            val = cond[field]
            if isinstance(val, list):
                assert len(val) > 0, f"Field '{field}' cannot be empty list in {cond.get('condition_id')}"
            elif isinstance(val, str):
                assert len(val.strip()) > 0, f"Field '{field}' cannot be empty string in {cond.get('condition_id')}"


def test_prohibited_definitive_diagnosis_wording():
    """Ensure rule 4 adherence: no definitive diagnosis claims in advice text."""
    with open(KB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    forbidden_phrases = ["this diagnosis is definitive", "we diagnose you with", "diagnosed definitely"]
    for cond in raw_data["conditions"]:
        combined_text = f"{cond['summary']} {cond['when_to_see_doctor']}".lower()
        for phrase in forbidden_phrases:
            assert phrase not in combined_text, f"Found prohibited diagnosis claim in {cond['condition_id']}: '{phrase}'"

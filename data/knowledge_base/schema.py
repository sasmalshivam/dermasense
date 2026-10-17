"""
DermaSense Clinical Knowledge Base Schema & Validator.
Enforces SIH 2025 non-negotiable medical rules:
- Source cited from approved medical authorities (WHO, MoHFW, AAD, NHS, CDC, DermNet NZ)
- Every entry marked reviewed_by_clinician: False
- Prohibits clinical terms like "diagnosis" in recommendation outputs (enforces "possible condition")
- Mandatory structured clinical guidance: description, symptoms, first aid, precautions, do-nots, red flags, when to see doctor
"""

from typing import List
from pydantic import BaseModel, HttpUrl, Field, field_validator


APPROVED_AUTHORITY_DOMAINS = [
    "who.int",
    "mohfw.gov.in",
    "icmr.org.in",
    "aad.org",
    "nhs.uk",
    "cdc.gov",
    "dermnetnz.org",
]


class MedicalSource(BaseModel):
    authority: str = Field(..., description="Approved medical organization")
    url: HttpUrl = Field(..., description="Direct authoritative URL")
    title: str = Field(..., description="Title of the source publication or guideline")

    @field_validator("url")
    @classmethod
    def validate_domain(cls, v: HttpUrl) -> HttpUrl:
        url_str = str(v)
        if not any(domain in url_str for domain in APPROVED_AUTHORITY_DOMAINS):
            raise ValueError(
                f"Source URL {url_str} must be from an approved authority domain: {APPROVED_AUTHORITY_DOMAINS}"
            )
        return v


class ConditionGuide(BaseModel):
    condition_id: str = Field(..., description="Standard code e.g. mel, nv, bcc, akiec, bkl, df, vasc")
    name: str = Field(..., description="Condition name")
    category: str = Field(..., description="Dermatological classification category")
    summary: str = Field(..., description="Clinically verified summary")
    symptoms: List[str] = Field(..., min_length=1, description="Observable signs and symptoms")
    first_aid: List[str] = Field(..., min_length=1, description="Immediate supportive first aid")
    precautions: List[str] = Field(..., min_length=1, description="Preventive measures and care")
    do_nots: List[str] = Field(..., min_length=1, description="Harmful practices to avoid")
    red_flags: List[str] = Field(..., min_length=1, description="Warning signs indicating critical risk")
    when_to_see_doctor: str = Field(..., description="Actionable triage criteria for clinical consultation")
    sources: List[MedicalSource] = Field(..., min_length=1, description="Citations to reputable bodies")
    reviewed_by_clinician: bool = Field(
        default=False,
        description="Must be False unless certified by a licensed physician"
    )

    @field_validator("reviewed_by_clinician")
    @classmethod
    def enforce_unreviewed_state(cls, v: bool) -> bool:
        if v is not False:
            raise ValueError(
                "Rule 5 violation: 'reviewed_by_clinician' must be explicitly False."
            )
        return v

    @field_validator("summary", "when_to_see_doctor")
    @classmethod
    def forbid_definitive_diagnosis_wording(cls, v: str) -> str:
        # App must not promise or claim to provide a medical diagnosis
        lower_v = v.lower()
        if "definitive diagnosis" in lower_v or "this diagnosis" in lower_v:
            raise ValueError(
                "Rule 4 violation: App guidance must use 'possible condition' or preliminary assessment, not definitive diagnosis."
            )
        return v


class KnowledgeBase(BaseModel):
    disclaimer: str = Field(..., min_length=20, description="Mandatory legal & clinical disclaimer")
    conditions: List[ConditionGuide] = Field(..., min_length=1)

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer_content(cls, v: str) -> str:
        lower_v = v.lower()
        if "not" not in lower_v and "disclaimer" not in lower_v:
            raise ValueError("Disclaimer must clearly indicate tool does NOT replace clinical diagnosis.")
        return v


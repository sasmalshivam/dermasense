"""
DermaSense Pydantic Data Models and Validation Schemas.
Enforces typed request/response contracts for FastAPI endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MedicalSourceSchema(BaseModel):
    title: str = Field(..., description="Title of authoritative clinical source")
    url: str = Field(..., description="Web link to medical guideline (WHO, NHS, AAD, CDC, DermNet NZ)")


class KnowledgeBaseSchema(BaseModel):
    condition_id: str
    name: str
    local_names: List[str] = Field(default_factory=list)
    description: str
    common_symptoms: List[str] = Field(default_factory=list)
    causes: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    first_aid: List[str] = Field(default_factory=list)
    precautions: List[str] = Field(default_factory=list)
    home_care: List[str] = Field(default_factory=list)
    do_not: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    when_to_see_doctor: str
    contagious: bool
    severity_level: str # low, medium, high
    prevention: List[str] = Field(default_factory=list)
    sources: List[MedicalSourceSchema] = Field(default_factory=list)
    reviewed_by_clinician: bool = False


class ConditionProbability(BaseModel):
    condition_id: str = Field(..., description="Machine-readable condition identifier")
    name: str = Field(..., description="Clinical display name")
    probability: float = Field(..., ge=0.0, le=1.0, description="Calibrated softmax probability")
    percentage: str = Field(..., description="Formatted percentage string e.g. '88.0%'")


class PredictResponse(BaseModel):
    status: str = Field(..., description="'assessed' or 'unable_to_assess'")
    assessment_summary: str = Field(..., description="Human-readable result summary")
    top_conditions: List[ConditionProbability] = Field(..., description="Top predicted conditions ranked by calibrated probability")
    top_condition_id: str = Field(..., description="Identifier of the primary candidate condition")
    top_condition_name: str = Field(..., description="Display name of the primary candidate condition")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence of the primary prediction")
    is_skin: bool = Field(..., description="True if human skin lesion detected; False if non-skin / out-of-distribution")
    low_confidence: bool = Field(..., description="True if prediction falls below calibrated certainty thresholds")
    doctor_notice: Optional[str] = Field(None, description="Urgent medical consultation notice for high-risk conditions")
    gradcam_heatmap: Optional[str] = Field(None, description="Base64 Data URI of Grad-CAM explainability heatmap overlay")
    knowledge_base: Optional[KnowledgeBaseSchema] = Field(None, description="Comprehensive clinical guidance from knowledge base")
    severity_level: str = Field(..., description="'low', 'medium', or 'high'")
    disclaimer: str = Field(..., description="Mandatory clinical disclaimer")


class ConditionSummary(BaseModel):
    condition_id: str
    name: str
    local_names: List[str]
    description: str
    severity_level: str
    contagious: bool
    reviewed_by_clinician: bool


class ConditionsListResponse(BaseModel):
    conditions: List[ConditionSummary]
    total: int
    disclaimer: str


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    model_loaded: bool
    onnx_runtime_version: str
    supported_classes: List[str]
    temperature_scaling_factor: float
    disclaimer: str


class FeedbackRequest(BaseModel):
    prediction_id: Optional[str] = None
    condition_id: str = Field(..., description="Evaluated condition")
    rating: int = Field(..., ge=1, le=5, description="1 to 5 star rating")
    feedback_text: Optional[str] = Field(default="", max_length=1000)
    clinician_reviewed: bool = False


class FeedbackResponse(BaseModel):
    status: str
    message: str


class ChatSource(BaseModel):
    title: str
    url: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User question")
    detected_condition: Optional[str] = Field(None, description="Current condition context (e.g. melanoma, eczema)")
    language: Optional[str] = Field("en", description="Language code: en, hi, or, bn, ta, te, mr")


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource] = Field(default_factory=list)
    grounded: bool
    confidence: float
    matched_condition: Optional[str] = None
    condition_id: Optional[str] = None
    section: Optional[str] = None
    disclaimer: str
    translation_note: Optional[str] = "Translations are machine-generated and need human review."


class TelemetryOptInRequest(BaseModel):
    consent: bool = Field(..., description="Explicit user opt-in consent for public health telemetry")
    condition_id: str = Field(..., description="Predicted condition identifier")
    condition_name: str = Field(..., description="Human-readable condition title")
    region: str = Field(..., description="Coarse district/state (e.g. 'Khurda, Odisha')")


class TelemetryOptInResponse(BaseModel):
    status: str
    message: str
    record_id: Optional[int] = None
    condition_id: Optional[str] = None
    region: Optional[str] = None
    date: Optional[str] = None


class SpikeAlertSchema(BaseModel):
    condition_id: str
    condition_name: str
    region: str
    current_week_count: int
    baseline_mean: float
    baseline_std: float
    threshold: float
    z_score: float
    is_spike: bool
    alert_level: str


class AdminVerifyRequest(BaseModel):
    password: str = Field(..., description="Admin dashboard access password")


class AdminVerifyResponse(BaseModel):
    valid: bool
    message: str


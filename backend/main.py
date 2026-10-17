"""
DermaSense FastAPI Clinical Awareness Backend.
SIH 2025 (Team Healthnautix, PS 25049, Public Health Chatbot).

Non-Negotiable Medical & Architecture Rules Enforced:
1. Pure local execution with zero paid or external cloud APIs.
2. 100% in-memory processing: zero disk writes of user uploaded images.
3. Complete stripping of EXIF, GPS, and metadata before inference.
4. Mandatory legal/clinical disclaimer included on every response.
5. Strict terminology: outputs 'possible condition', strictly avoids 'diagnosis'.
6. Urgent doctor consultation notices for high-risk lesions (Melanoma, BCC, Actinic Keratosis).
"""

import json
import os
from pathlib import Path
from typing import List, Optional

import onnxruntime as ort
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import (
    CORS_ORIGINS,
    MAX_UPLOAD_SIZE_BYTES,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_EXTENSIONS,
    MANDATORY_DISCLAIMER,
    FEEDBACK_STORAGE_PATH,
    ADMIN_PASSWORD,
)
from backend.schemas import (
    PredictResponse,
    ConditionsListResponse,
    HealthResponse,
    FeedbackRequest,
    FeedbackResponse,
    ChatRequest,
    ChatResponse,
    TelemetryOptInRequest,
    TelemetryOptInResponse,
    AdminVerifyRequest,
    AdminVerifyResponse,
)
from backend.middleware import RateLimitMiddleware
from backend.services.inference_service import inference_service, strip_exif_and_validate
from backend.services.gradcam_service import gradcam_service
from backend.services.kb_service import kb_service
from backend.services.chat import rag_service, UI_TRANSLATIONS_PATH
from backend.services.surveillance import surveillance_service

# Initialize FastAPI application
app = FastAPI(
    title="DermaSense Skin Condition Awareness API",
    description="Explainable AI & Clinical Knowledge Base for Smart India Hackathon 2025",
    version="1.0.0",
)

# Register CORS Middleware from Environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Security & Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Returns runtime health status, model readiness, and calibration parameters."""
    return HealthResponse(
        status="healthy",
        model_loaded=inference_service.is_loaded,
        onnx_runtime_version=ort.__version__,
        supported_classes=list(inference_service.label_to_idx.keys()),
        temperature_scaling_factor=inference_service.temperature,
        disclaimer=MANDATORY_DISCLAIMER,
    )


@app.get("/api/conditions", response_model=ConditionsListResponse)
async def list_conditions():
    """Lists all clinically verified skin condition guides available in the knowledge base."""
    summaries = kb_service.get_summaries()
    return ConditionsListResponse(
        conditions=summaries,
        total=len(summaries),
        disclaimer=MANDATORY_DISCLAIMER,
    )


@app.post("/api/predict", response_model=PredictResponse)
async def predict_skin_condition(file: UploadFile = File(...)):
    """
    Evaluates an uploaded skin photo strictly in-memory.
    - Strips EXIF/GPS tags immediately
    - Validates file type, size (<8 MB), and image integrity
    - Generates temperature-calibrated probabilities for top-3 possible conditions
    - Detects non-skin and out-of-distribution (OOD) low-confidence photos
    - Attaches explainable Grad-CAM heatmap overlay (base64 PNG)
    - Provides verified clinical knowledge base guidance and urgent doctor notices
    """
    # 1. Validate file extension
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions are: {ALLOWED_EXTENSIONS}",
        )

    # 2. Validate MIME content type (if provided)
    if file.content_type and file.content_type.lower() not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported MIME type '{file.content_type}'. Allowed types are: {ALLOWED_IMAGE_TYPES}",
        )

    # 3. Read image bytes strictly into memory
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Uploaded image exceeds maximum allowable limit of 8 MB (received {len(file_bytes)} bytes).",
        )

    # 4. Verify image structure and strip all EXIF / GPS metadata entirely in memory
    try:
        clean_image = strip_exif_and_validate(file_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 5. Run ONNX Inference & Temperature-Calibrated OOD Assessment
    try:
        prediction = inference_service.predict(clean_image)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution error: {str(e)}",
        )

    # 6. Generate Grad-CAM explainability heatmap overlay (if model available)
    heatmap_b64 = None
    try:
        top_idx = prediction.get("top_idx", 0)
        heatmap_b64 = gradcam_service.generate_base64_heatmap(
            pil_image=clean_image,
            target_class_idx=top_idx,
            alpha=0.45
        )
    except Exception as e:
        print(f"[WARN] Grad-CAM generation encountered an issue: {e}")

    # Remove internal index before serialization
    prediction.pop("top_idx", None)
    prediction["gradcam_heatmap"] = heatmap_b64

    return PredictResponse(**prediction)


@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(payload: FeedbackRequest):
    """
    Collects community and clinician feedback for active model monitoring.
    Stored securely in local append-only JSONL format.
    """
    record = {
        "prediction_id": payload.prediction_id,
        "condition_id": payload.condition_id,
        "rating": payload.rating,
        "feedback_text": payload.feedback_text,
        "clinician_reviewed": payload.clinician_reviewed,
    }

    try:
        FEEDBACK_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_STORAGE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print(f"[ERROR] Failed to save feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback.",
        )

    return FeedbackResponse(
        status="success",
        message="Thank you! Your feedback has been recorded.",
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_knowledge_base(payload: ChatRequest):
    """
    RAG Chatbot: Answers skin condition questions strictly from verified knowledge base text.
    - Employs multilingual Sentence-Transformers + FAISS dense retrieval
    - Uses detected condition as conversational context
    - Returns 'I don't know, please see a doctor.' if out-of-scope or unverified
    - Includes source citations for every grounded answer
    """
    result = rag_service.query(
        question=payload.message,
        detected_condition=payload.detected_condition,
        language=payload.language or "en",
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        grounded=result.get("grounded", False),
        confidence=result.get("confidence", 0.0),
        matched_condition=result.get("matched_condition"),
        condition_id=result.get("condition_id"),
        section=result.get("section"),
        disclaimer=MANDATORY_DISCLAIMER,
        translation_note="Translations are machine-generated and need human review.",
    )


@app.get("/api/translations")
async def get_translations():
    """Returns multilingual UI translation strings for 7 Indian languages."""
    if UI_TRANSLATIONS_PATH.exists():
        with open(UI_TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"notice": "Translations are machine-generated and need human review.", "languages": {}, "translations": {}}


@app.post("/api/telemetry/opt-in", response_model=TelemetryOptInResponse)
async def record_public_health_telemetry(payload: TelemetryOptInRequest):
    """
    Records an anonymized disease occurrence record strictly with explicit citizen consent.
    Zero image data, zero IP addresses, and zero device identifiers are ever accepted or stored.
    """
    if not payload.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User consent is required. Telemetry rejected.",
        )

    try:
        res = surveillance_service.record_telemetry(
            consent=payload.consent,
            condition_id=payload.condition_id,
            condition_name=payload.condition_name,
            region=payload.region,
        )
        return TelemetryOptInResponse(
            status="success",
            message=res["message"],
            record_id=res["record_id"],
            condition_id=res["condition_id"],
            region=res["region"],
            date=res["date"],
        )
    except Exception as e:
        print(f"[ERROR] Failed to record telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record anonymized telemetry.",
        )


@app.post("/api/admin/verify", response_model=AdminVerifyResponse)
async def verify_admin_password(payload: AdminVerifyRequest):
    """Verifies administrator credentials for dashboard access."""
    if payload.password == ADMIN_PASSWORD:
        return AdminVerifyResponse(valid=True, message="Admin credentials verified.")
    return AdminVerifyResponse(valid=False, message="Invalid administrator password.")


@app.get("/api/admin/metrics")
async def get_admin_metrics(
    x_admin_password: Optional[str] = Header(None, alias="X-Admin-Password"),
    password: Optional[str] = Query(None),
):
    """
    Returns public health epidemiological trends, condition distributions,
    active disease cluster spikes (> mean + 2*sigma), and citizen feedback metrics.
    Protected by admin password.
    """
    provided_pwd = x_admin_password or password
    if provided_pwd != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid X-Admin-Password header or password query parameter required.",
        )

    return surveillance_service.get_metrics()


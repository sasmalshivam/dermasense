"""
DermaSense Backend Configuration.
Handles environment variables, CORS settings, security limits, and clinical constants.
"""

import os
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# CORS Configuration
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

env_cors = os.getenv("DERMASENSE_CORS_ORIGINS")
if env_cors:
    CORS_ORIGINS: List[str] = [origin.strip() for origin in env_cors.split(",") if origin.strip()]
else:
    CORS_ORIGINS: List[str] = DEFAULT_CORS_ORIGINS

# File Upload Security Limits
MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(8 * 1024 * 1024))) # 8 MB max
ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
ALLOWED_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

# Rate Limiting (per-IP token/sliding window)
RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECS", "60"))

# Model & Artifact Storage Paths
ONNX_MODEL_PATH: Path = PROJECT_ROOT / "ml" / "weights" / "model.onnx"
TEMPERATURE_CONFIG_PATH: Path = PROJECT_ROOT / "ml" / "weights" / "temperature.json"
LABELS_CONFIG_PATH: Path = PROJECT_ROOT / "ml" / "weights" / "labels.json"
PYTORCH_CHECKPOINT_PATH: Path = PROJECT_ROOT / "ml" / "weights" / "best_model.pt"
KNOWLEDGE_BASE_DIR: Path = PROJECT_ROOT / "data" / "knowledge_base"
FEEDBACK_STORAGE_PATH: Path = PROJECT_ROOT / "data" / "feedback.jsonl"
SURVEILLANCE_DB_PATH: Path = PROJECT_ROOT / "data" / "surveillance.db"

# Admin Authentication
ADMIN_PASSWORD: str = os.getenv("DERMASENSE_ADMIN_PASSWORD", "derma_admin_2025")

# Input Image Preprocessing Parameters
TARGET_IMAGE_SIZE: int = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Mandatory SIH 2025 Clinical Disclaimers
MANDATORY_DISCLAIMER: str = (
    "DISCLAIMER: DermaSense is an educational and skin health awareness tool developed for "
    "the Smart India Hackathon 2025 (Team Healthnautix, PS 25049). It does NOT provide a clinical diagnosis, "
    "prognosis, or formal medical advice. All predictions represent statistical 'possible conditions'. "
    "Always consult a qualified healthcare professional or dermatologist for proper clinical examination. "
    "If you experience rapid lesion growth, persistent bleeding, or severe pain, seek emergency medical care immediately."
)

URGENT_DOCTOR_NOTICE: str = (
    "URGENT MEDICAL NOTICE: This visual assessment detected characteristics commonly associated with a high-priority "
    "skin condition (e.g., Melanoma, Basal Cell Carcinoma, or Actinic Keratosis). Please schedule a clinical examination "
    "with a qualified dermatologist or physician promptly. Do not attempt home excision or self-treatment."
)

HIGH_PRIORITY_CONDITIONS = {
    "melanoma",
    "basal_cell_carcinoma",
    "actinic_keratosis",
}


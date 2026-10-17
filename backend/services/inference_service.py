"""
DermaSense ONNX Runtime Inference & Calibration Engine.
Processes in-memory images, computes calibrated probabilities via temperature scaling,
evaluates out-of-distribution (OOD) energy thresholds, and structures top-3 candidate conditions.
"""

import io
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List

import numpy as np
import onnxruntime as ort
import scipy.special
from PIL import Image

from backend.config import (
    ONNX_MODEL_PATH,
    TEMPERATURE_CONFIG_PATH,
    LABELS_CONFIG_PATH,
    TARGET_IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    MANDATORY_DISCLAIMER,
    URGENT_DOCTOR_NOTICE,
    HIGH_PRIORITY_CONDITIONS,
)
from backend.services.kb_service import kb_service


def strip_exif_and_validate(file_bytes: bytes) -> Image.Image:
    """
    Validates image integrity and strips all EXIF/GPS metadata entirely in memory.
    Returns a clean RGB PIL Image.
    """
    try:
        raw = Image.open(io.BytesIO(file_bytes))
        raw.verify()
    except Exception as e:
        raise ValueError(f"Uploaded file is corrupt or not a recognized image format: {e}")

    # Re-open after verify() closes the stream
    raw = Image.open(io.BytesIO(file_bytes))
    rgb_img = raw.convert("RGB")

    # Creating a new Image object discards all EXIF, GPS, and metadata tags
    clean_img = Image.new("RGB", rgb_img.size)
    clean_img.paste(rgb_img)
    return clean_img


class InferenceService:
    def __init__(
        self,
        onnx_path: Path = ONNX_MODEL_PATH,
        temp_path: Path = TEMPERATURE_CONFIG_PATH,
        labels_path: Path = LABELS_CONFIG_PATH,
    ):
        self.onnx_path = onnx_path
        self.temp_path = temp_path
        self.labels_path = labels_path

        self.session: ort.InferenceSession = None
        self.input_name: str = "input"
        self.temperature: float = 1.0
        self.max_softmax_threshold: float = 0.5
        self.energy_threshold: float = -10.0
        self.idx_to_label: Dict[str, str] = {}
        self.label_to_idx: Dict[str, int] = {}
        self.is_loaded: bool = False

        self._load_artifacts()

    def _load_artifacts(self):
        """Loads ONNX inference session and calibration parameters."""
        if not self.onnx_path.exists():
            raise FileNotFoundError(f"ONNX model file not found at {self.onnx_path}")
        if not self.temp_path.exists():
            raise FileNotFoundError(f"Temperature config not found at {self.temp_path}")
        if not self.labels_path.exists():
            raise FileNotFoundError(f"Labels config not found at {self.labels_path}")

        # Initialize ONNX Runtime session
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(self.onnx_path), sess_options=options)
        self.input_name = self.session.get_inputs()[0].name

        # Load temperature scaling & OOD thresholds
        with open(self.temp_path, "r", encoding="utf-8") as f:
            t_cfg = json.load(f)
            self.temperature = float(t_cfg.get("temperature", 1.0))
            self.max_softmax_threshold = float(t_cfg.get("max_softmax_threshold", 0.5))
            self.energy_threshold = float(t_cfg.get("energy_threshold", -10.0))

        # Load label mapping
        with open(self.labels_path, "r", encoding="utf-8") as f:
            l_cfg = json.load(f)
            self.idx_to_label = l_cfg.get("idx_to_label", {})
            self.label_to_idx = l_cfg.get("label_to_idx", {})

        self.is_loaded = True
        print(f"[OK] InferenceService loaded ONNX model with {len(self.idx_to_label)} classes.")

    def preprocess(self, pil_image: Image.Image) -> np.ndarray:
        """
        Preprocesses a clean PIL Image for model input:
        1. Resizes to (224, 224)
        2. Normalizes using ImageNet mean & standard deviation
        3. Formats to CHW float32 tensor array (1, 3, 224, 224)
        """
        resized = pil_image.resize((TARGET_IMAGE_SIZE, TARGET_IMAGE_SIZE), resample=Image.Resampling.BILINEAR)
        img_arr = np.array(resized, dtype=np.float32) / 255.0
        
        # Normalize
        mean = np.array(IMAGENET_MEAN, dtype=np.float32)
        std = np.array(IMAGENET_STD, dtype=np.float32)
        norm_arr = (img_arr - mean) / std

        # Transpose HWC -> CHW and add batch dimension
        tensor = np.transpose(norm_arr, (2, 0, 1))[np.newaxis, ...].astype(np.float32)
        return tensor

    def predict(self, clean_image: Image.Image) -> Dict[str, Any]:
        """
        Runs in-memory inference, calibrates logits, tests for OOD/non-skin,
        and constructs clinical response payload.
        """
        input_tensor = self.preprocess(clean_image)

        # Execute ONNX session
        raw_outputs = self.session.run(None, {self.input_name: input_tensor})
        logits = raw_outputs[0][0] # 1D array of shape (num_classes,)

        # Temperature scaling calibration
        scaled_logits = logits / self.temperature
        probs = scipy.special.softmax(scaled_logits)
        
        # Energy score for OOD: E = -T * logsumexp(logits / T)
        energy_score = float(-scipy.special.logsumexp(scaled_logits))

        # Rank all classes by probability
        ranked_indices = np.argsort(probs)[::-1]
        top_idx = int(ranked_indices[0])
        top_prob = float(probs[top_idx])
        top_cid = self.idx_to_label.get(str(top_idx), "unknown")

        # Construct top-3 predictions
        top_conditions: List[Dict[str, Any]] = []
        for rank, idx in enumerate(ranked_indices[:3]):
            cid = self.idx_to_label.get(str(idx), f"class_{idx}")
            prob = float(probs[idx])
            kb_entry = kb_service.get(cid)
            name = kb_entry.get("name", cid.replace("_", " ").title()) if kb_entry else cid.replace("_", " ").title()
            top_conditions.append({
                "condition_id": cid,
                "name": name,
                "probability": round(prob, 4),
                "percentage": f"{prob * 100:.1f}%",
            })

        # Fetch knowledge base entry for top candidate
        top_kb = kb_service.get(top_cid)
        top_name = top_kb.get("name", top_cid.replace("_", " ").title()) if top_kb else top_cid.replace("_", " ").title()
        severity = top_kb.get("severity_level", "low") if top_kb else "low"

        # Out-of-Distribution & Non-Skin Assessment
        is_skin = (top_cid != "not_skin")
        low_confidence = False

        if not is_skin:
            low_confidence = True
        elif top_prob < self.max_softmax_threshold:
            low_confidence = True
        elif energy_score < self.energy_threshold:
            low_confidence = True

        if not is_skin or low_confidence:
            status = "unable_to_assess"
            assessment_summary = (
                "Unable to assess: The image does not clearly depict human skin or confidence is too low "
                "to provide a reliable assessment. Please upload a well-focused, well-lit close-up photograph of the skin lesion."
            )
        else:
            status = "assessed"
            assessment_summary = f"Possible condition: {top_name} ({top_prob * 100:.1f}% preliminary statistical match)"

        # High-risk doctor consultation notice check
        doctor_notice = None
        has_high_risk = any(
            c["condition_id"] in HIGH_PRIORITY_CONDITIONS for c in top_conditions
        ) or (top_cid in HIGH_PRIORITY_CONDITIONS)
        
        if has_high_risk:
            doctor_notice = URGENT_DOCTOR_NOTICE

        return {
            "status": status,
            "assessment_summary": assessment_summary,
            "top_conditions": top_conditions,
            "top_condition_id": top_cid,
            "top_condition_name": top_name,
            "confidence_score": round(top_prob, 4),
            "is_skin": is_skin,
            "low_confidence": low_confidence,
            "doctor_notice": doctor_notice,
            "knowledge_base": top_kb,
            "severity_level": severity,
            "disclaimer": MANDATORY_DISCLAIMER,
            "top_idx": top_idx,
        }


# Singleton instance
inference_service = InferenceService()


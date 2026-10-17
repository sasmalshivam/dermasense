"""
DermaSense Explainable AI (Grad-CAM) Service.
Loads PyTorch model checkpoint in memory and generates base64-encoded Grad-CAM
heatmap overlays highlighting localized dermatological regions of interest.
"""

import io
import base64
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torchvision.transforms as transforms
import timm
from PIL import Image

from backend.config import (
    PYTORCH_CHECKPOINT_PATH,
    TARGET_IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
)
from ml.gradcam import GradCAM, apply_gradcam_overlay


class GradCAMService:
    def __init__(self, checkpoint_path: Path = PYTORCH_CHECKPOINT_PATH):
        self.checkpoint_path = checkpoint_path
        self.model: Optional[torch.nn.Module] = None
        self.gradcam: Optional[GradCAM] = None
        self.device = torch.device("cpu")
        self.transform = transforms.Compose([
            transforms.Resize((TARGET_IMAGE_SIZE, TARGET_IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])
        self._load_model()

    def _load_model(self):
        """Loads PyTorch model checkpoint and initializes Grad-CAM hooks."""
        if not self.checkpoint_path.exists():
            print(f"[WARN] PyTorch checkpoint not found at {self.checkpoint_path}. Grad-CAM disabled.")
            return

        try:
            checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
            backbone_name = checkpoint.get("backbone", "efficientnet_b0")
            num_classes = checkpoint.get("num_classes", 3)

            self.model = timm.create_model(
                backbone_name,
                pretrained=False,
                num_classes=num_classes
            )
            self.model.load_state_dict(checkpoint["state_dict"])
            self.model.to(self.device)
            self.model.eval()

            self.gradcam = GradCAM(self.model)
            print("[OK] GradCAMService initialized with PyTorch backbone.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize GradCAMService: {e}")
            self.model = None
            self.gradcam = None

    def generate_base64_heatmap(
        self,
        pil_image: Image.Image,
        target_class_idx: int,
        alpha: float = 0.45,
    ) -> Optional[str]:
        """
        Generates Grad-CAM activation map for the given PIL image and target class,
        blends it as an overlay, and encodes to a base64 PNG data URL in memory.
        """
        if self.gradcam is None or self.model is None:
            return None

        try:
            # Transform image to normalized tensor (1, 3, 224, 224)
            input_tensor = self.transform(pil_image).unsqueeze(0).to(self.device)

            # Generate raw activation map
            heatmap, _ = self.gradcam.generate_heatmap(
                input_tensor,
                target_class_idx=target_class_idx
            )

            # Apply overlay blend on original PIL image
            overlay_pil = apply_gradcam_overlay(
                image=pil_image,
                heatmap=heatmap,
                alpha=alpha,
                colormap_name="jet"
            )

            # Encode PIL image to Base64 PNG entirely in-memory
            buffered = io.BytesIO()
            overlay_pil.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            b64_str = base64.b64encode(img_bytes).decode("utf-8")
            return f"data:image/png;base64,{b64_str}"

        except Exception as e:
            print(f"[WARN] Grad-CAM generation failed: {e}")
            return None


# Singleton instance
gradcam_service = GradCAMService()


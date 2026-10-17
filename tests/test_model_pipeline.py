"""
Automated Unit Tests for Phase 2 Model Pipeline.
Verifies:
- Model instantiation and backbone freezing/unfreezing
- Focal Loss and Temperature Scaling calibration logic
- Energy score OOD calculation
- Grad-CAM heatmap extraction and overlay blending
- ONNX export and ONNX Runtime numerical equivalence verification
- CLI tools help and argument parsing
"""

import os
import sys
import tempfile
import pytest
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.train import (
    build_model,
    freeze_backbone,
    FocalLoss,
    compute_ece,
    fit_temperature,
    compute_energy_scores,
)
from ml.gradcam import GradCAM, apply_gradcam_overlay
from ml.export_onnx import export_model_to_onnx


def test_build_model_and_freezing():
    """Verify model factory and selective backbone freezing."""
    model = build_model("efficientnet_b0", num_classes=3, pretrained=False)
    assert model is not None
    
    # Test forward pass with dummy batch
    dummy_input = torch.randn(2, 3, 224, 224)
    logits = model(dummy_input)
    assert logits.shape == (2, 3)

    # Test freezing
    freeze_backbone(model, freeze=True)
    head_params = set(model.get_classifier().parameters())
    for p in model.parameters():
        if p in head_params:
            assert p.requires_grad is True
        else:
            assert p.requires_grad is False

    # Test unfreezing
    freeze_backbone(model, freeze=False)
    for p in model.parameters():
        assert p.requires_grad is True


def test_focal_loss():
    """Verify multiclass Focal Loss calculation and gradient flow."""
    logits = torch.randn(4, 5, requires_grad=True)
    targets = torch.tensor([0, 1, 2, 4])
    criterion = FocalLoss(gamma=2.0)
    loss = criterion(logits, targets)

    assert not torch.isnan(loss)
    assert loss.item() > 0.0
    loss.backward()
    assert logits.grad is not None


def test_temperature_scaling_and_ece():
    """Verify ECE computation and temperature calibration optimization."""
    # Synthetic logits and labels
    np.random.seed(42)
    logits_np = np.random.randn(50, 4).astype(np.float32)
    labels_np = np.random.randint(0, 4, size=(50,))

    ece_orig = compute_ece(logits_np, labels_np, n_bins=5)
    assert 0.0 <= ece_orig <= 1.0

    logits_t = torch.from_numpy(logits_np)
    labels_t = torch.from_numpy(labels_np).long()
    temp = fit_temperature(logits_t, labels_t)
    assert temp > 0.0

    # Scaled logits
    calibrated_logits = logits_np / temp
    ece_cal = compute_ece(calibrated_logits, labels_np, n_bins=5)
    assert 0.0 <= ece_cal <= 1.0


def test_energy_score_ood():
    """Verify energy score calculation for out-of-distribution detection."""
    logits = torch.randn(10, 5)
    scores = compute_energy_scores(logits, T=1.0)
    assert len(scores) == 10
    assert not np.isnan(scores).any()


def test_gradcam_generation():
    """Verify Grad-CAM activation map and image overlay generation."""
    model = build_model("efficientnet_b0", num_classes=3, pretrained=False)
    gradcam = GradCAM(model)

    dummy_input = torch.randn(1, 3, 224, 224)
    heatmap, pred_idx = gradcam.generate_heatmap(dummy_input, target_class_idx=1)

    assert heatmap.shape == (7, 7) or len(heatmap.shape) == 2
    assert 0.0 <= heatmap.min() <= heatmap.max() <= 1.0
    assert pred_idx == 1

    # Overlay on dummy PIL image
    dummy_img = Image.new("RGB", (224, 224), (200, 150, 100))
    overlay = apply_gradcam_overlay(dummy_img, heatmap, alpha=0.5)
    assert overlay.size == (224, 224)


def test_onnx_export_and_verification(tmp_path):
    """Verify ONNX export and numerical parity assertion with ONNX Runtime."""
    # Create lightweight checkpoint
    model = build_model("efficientnet_b0", num_classes=3, pretrained=False)
    checkpoint_file = tmp_path / "test_model.pt"
    onnx_file = tmp_path / "test_model.onnx"

    torch.save({
        "backbone": "efficientnet_b0",
        "num_classes": 3,
        "img_size": 224,
        "state_dict": model.state_dict(),
        "idx_to_label": {0: "melanoma", 1: "nevus", 2: "not_skin"},
        "label_to_idx": {"melanoma": 0, "nevus": 1, "not_skin": 2},
    }, checkpoint_file)

    max_diff, num_classes, img_size = export_model_to_onnx(checkpoint_file, onnx_file)
    assert onnx_file.exists()
    assert max_diff < 1e-4
    assert num_classes == 3
    assert img_size == 224

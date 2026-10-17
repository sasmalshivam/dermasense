"""
Phase 1 Environment & Library Verification Tests.
Ensures genuine local installations with NO mocked dependencies.
"""

import sys
import os
import pytest
import torch
import torchvision
import timm
import fastapi
import PIL


def test_python_version():
    """Verify Python version is 3.10 or higher."""
    major, minor = sys.version_info.major, sys.version_info.minor
    print(f"Executing with Python {major}.{minor}.{sys.version_info.micro}")
    assert (major, minor) >= (3, 10), f"Expected Python 3.10+, got {major}.{minor}"


def test_pytorch_tensor_operations():
    """Verify genuine PyTorch installation and tensor computations."""
    assert torch.__version__ is not None
    # Perform genuine CPU matrix multiplication
    x = torch.randn(10, 10)
    y = torch.randn(10, 10)
    z = torch.matmul(x, y)
    assert z.shape == (10, 10)
    assert not torch.isnan(z).any()


def test_timm_architecture_instantiation():
    """Verify genuine timm installation and capability to construct vision backbones."""
    assert timm.__version__ is not None
    # Instantiate lightweight backbone architecture without internet download
    model = timm.create_model("efficientnet_b0", pretrained=False, num_classes=7)
    assert model is not None
    dummy_input = torch.randn(2, 3, 224, 224)
    output = model(dummy_input)
    assert output.shape == (2, 7)


def test_fastapi_and_pil():
    """Verify FastAPI and Pillow versions."""
    assert fastapi.__version__ is not None
    assert PIL.__version__ is not None
    # Create simple PIL image
    img = PIL.Image.new("RGB", (64, 64), color="red")
    assert img.size == (64, 64)


def test_frontend_build_artifacts():
    """Verify React + Vite frontend was built successfully."""
    frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "index.html")
    assert os.path.exists(frontend_dist), f"Expected built frontend at {frontend_dist}"


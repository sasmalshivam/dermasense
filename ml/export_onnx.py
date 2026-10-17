"""
DermaSense ONNX Export & Verification Engine.
Exports PyTorch vision model to ONNX runtime format and verifies numerical equivalence
by calculating the maximum absolute difference between PyTorch and ONNX Runtime.
"""

import sys
import io
import argparse
from pathlib import Path
from typing import Tuple

# Ensure utf-8 encoding on Windows console for unicode status characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import torch
import torch.nn as nn
import onnx
import onnxruntime as ort
import timm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = PROJECT_ROOT / "ml" / "weights" / "best_model.pt"
DEFAULT_ONNX_OUTPUT = PROJECT_ROOT / "ml" / "weights" / "model.onnx"


def export_model_to_onnx(
    checkpoint_path: Path,
    onnx_output_path: Path,
    opset_version: int = 18
) -> Tuple[float, int, int]:
    """
    Exports a PyTorch model checkpoint to ONNX and validates the exported graph.
    Returns:
        (max_abs_difference, num_classes, img_size)
    """
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

    # Load checkpoint
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    backbone_name = checkpoint["backbone"]
    num_classes = checkpoint["num_classes"]
    img_size = checkpoint.get("img_size", 224)

    print("=" * 80)
    print("DERMASENSE ONNX EXPORT & NUMERICAL VERIFICATION")
    print("=" * 80)
    print(f"[*] Backbone: {backbone_name}")
    print(f"[*] Number of classes: {num_classes}")
    print(f"[*] Input resolution: {img_size}x{img_size}")
    print(f"[*] Target ONNX path: {onnx_output_path}")

    # Instantiate model
    model = timm.create_model(
        backbone_name,
        pretrained=False,
        num_classes=num_classes
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    # Create dummy input tensor
    dummy_input = torch.randn(1, 3, img_size, img_size, dtype=torch.float32)

    # 1. PyTorch Baseline Inference
    with torch.no_grad():
        torch_output = model(dummy_input).numpy()

    # 2. Export to ONNX
    onnx_output_path.parent.mkdir(parents=True, exist_ok=True)
    print("[*] Exporting model to ONNX...")
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_output_path),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "logits": {0: "batch_size"}
        }
    )
    print(f"[OK] ONNX file exported successfully -> {onnx_output_path}")

    # 3. Validate ONNX Graph
    print("[*] Validating ONNX model structure...")
    onnx_model = onnx.load(str(onnx_output_path))
    onnx.checker.check_model(onnx_model)
    print("[OK] ONNX model graph structure is valid.")

    # 4. ONNX Runtime Inference & Verification
    print("[*] Initializing ONNX Runtime session for numerical verification...")
    ort_session = ort.InferenceSession(
        str(onnx_output_path),
        providers=["CPUExecutionProvider"]
    )
    ort_inputs = {"input": dummy_input.numpy()}
    ort_outputs = ort_session.run(None, ort_inputs)
    ort_logits = ort_outputs[0]

    # 5. Compute Maximum Absolute Difference
    diff = np.abs(torch_output - ort_logits)
    max_abs_diff = float(np.max(diff))
    mean_abs_diff = float(np.mean(diff))

    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print(f"  PyTorch Output Shape:    {torch_output.shape}")
    print(f"  ONNX Runtime Shape:      {ort_logits.shape}")
    print(f"  Mean Absolute Difference: {mean_abs_diff:.6e}")
    print(f"  Max Absolute Difference:  {max_abs_diff:.6e}")

    # Numerical tolerance check (relative and absolute tolerance)
    is_close = np.allclose(torch_output, ort_logits, rtol=1e-2, atol=0.25)
    assert is_close, (
        f"[ERROR] Numerical discrepancy between PyTorch and ONNX (max_abs={max_abs_diff:.6e}, mean_abs={mean_abs_diff:.6e}) exceeds tolerance."
    )
    print(f"[ASSERTION PASSED] PyTorch and ONNX Runtime outputs match within tolerance (max abs diff: {max_abs_diff:.6e}).")
    print("=" * 80 + "\n")

    return max_abs_diff, num_classes, img_size


def main():
    parser = argparse.ArgumentParser(description="Export PyTorch model to ONNX and verify numerical parity")
    parser.add_argument("--checkpoint", type=str, default=str(DEFAULT_CHECKPOINT), help="Input PyTorch checkpoint (.pt)")
    parser.add_argument("--output", type=str, default=str(DEFAULT_ONNX_OUTPUT), help="Output ONNX path (.onnx)")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    output_path = Path(args.output)

    try:
        export_model_to_onnx(checkpoint_path, output_path)
    except Exception as e:
        print(f"[ERROR] ONNX export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


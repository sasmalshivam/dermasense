"""
DermaSense Grad-CAM Interpretability Engine.
Generates explainable AI Gradient-weighted Class Activation Maps (Grad-CAM)
highlighting regions of clinical interest for dermatological awareness.
Returns overlay heatmap blended with the input image as a PNG.
"""

import sys
import argparse
from pathlib import Path
from typing import Tuple, Optional, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image
import matplotlib.cm as cm


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class GradCAM:
    """
    Gradient-weighted Class Activation Mapping (Grad-CAM) generator
    for timm convolutional backbones (e.g., EfficientNet, ConvNeXt, ResNet).
    """
    def __init__(self, model: nn.Module, target_layer: Optional[nn.Module] = None):
        self.model = model
        self.model.eval()
        self.target_layer = target_layer or self._find_target_layer()

        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None

        self._register_hooks()

    def _find_target_layer(self) -> nn.Module:
        """Automatically identifies the final convolutional layer of the backbone."""
        # For timm EfficientNet models: conv_head or last block
        if hasattr(self.model, "conv_head") and isinstance(self.model.conv_head, nn.Conv2d):
            return self.model.conv_head
        
        # Traverse named modules in reverse to locate last Conv2d
        for name, module in reversed(list(self.model.named_modules())):
            if isinstance(module, nn.Conv2d):
                return module

        raise ValueError("Could not automatically locate a Conv2d layer for Grad-CAM.")

    def _register_hooks(self):
        """Registers forward and backward hooks on target convolutional layer."""
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate_heatmap(
        self,
        input_tensor: torch.Tensor,
        target_class_idx: Optional[int] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Computes Grad-CAM activation heatmap for specified class (or predicted class).
        Returns:
            heatmap (np.ndarray): 2D float array in [0, 1]
            predicted_class (int): Index of the analyzed class
        """
        self.model.zero_grad()
        output = self.model(input_tensor)

        if target_class_idx is None:
            target_class_idx = int(output.argmax(dim=1).item())

        score = output[0, target_class_idx]
        score.backward(retain_graph=True)

        # Global average pooling of gradients
        # gradients shape: [1, C, H, W]
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)
        # Weighted combination of forward activation maps
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)

        # Apply ReLU to focus on features having a positive contribution
        cam = F.relu(cam)
        cam = cam.squeeze().cpu().numpy()

        # Normalize to [0, 1]
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max - cam_min > 1e-8:
            heatmap = (cam - cam_min) / (cam_max - cam_min)
        else:
            heatmap = np.zeros_like(cam)

        return heatmap, target_class_idx


def apply_gradcam_overlay(
    image: Image.Image,
    heatmap: np.ndarray,
    alpha: float = 0.45,
    colormap_name: str = "jet"
) -> Image.Image:
    """
    Overlays a Grad-CAM heatmap on top of a PIL image.
    Args:
        image: Original RGB PIL image
        heatmap: 2D float numpy array in [0, 1]
        alpha: Blending weight for heatmap (0.0 to 1.0)
        colormap_name: Colormap name from matplotlib (default: 'jet')
    Returns:
        blended_image: PIL RGB image with heatmap overlay
    """
    # Resize heatmap to match original image dimensions
    heatmap_pil = Image.fromarray((heatmap * 255).astype(np.uint8)).resize(
        image.size,
        resample=Image.Resampling.BILINEAR
    )
    heatmap_norm = np.array(heatmap_pil, dtype=np.float32) / 255.0

    # Apply colormap
    try:
        import matplotlib
        colormap = matplotlib.colormaps[colormap_name]
    except Exception:
        colormap = cm.get_cmap(colormap_name)
    colored_heatmap = colormap(heatmap_norm)[:, :, :3] # Discard alpha
    colored_heatmap = (colored_heatmap * 255).astype(np.uint8)
    colored_heatmap_pil = Image.fromarray(colored_heatmap)

    # Alpha-blend original image with colored heatmap
    blended = Image.blend(image.convert("RGB"), colored_heatmap_pil, alpha=alpha)
    return blended


def generate_gradcam_for_image(
    model: nn.Module,
    image_path: Union[str, Path],
    img_size: int = 224,
    device: torch.device = torch.device("cpu"),
    target_class_idx: Optional[int] = None,
    alpha: float = 0.45
) -> Tuple[Image.Image, np.ndarray, int]:
    """
    Convenience function: loads an image, performs inference, computes Grad-CAM,
    and returns (overlay_image, raw_heatmap, predicted_class).
    """
    orig_image = Image.open(image_path).convert("RGB")

    # Transform matching training normalization
    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = transform(orig_image).unsqueeze(0).to(device)

    gradcam = GradCAM(model)
    heatmap, pred_idx = gradcam.generate_heatmap(input_tensor, target_class_idx=target_class_idx)
    overlay = apply_gradcam_overlay(orig_image, heatmap, alpha=alpha)

    return overlay, heatmap, pred_idx


def main():
    parser = argparse.ArgumentParser(description="DermaSense Grad-CAM Overlay Generator")
    parser.add_argument("--image", type=str, required=True, help="Path to input skin image")
    parser.add_argument("--checkpoint", type=str, default="ml/weights/best_model.pt", help="Path to model weights")
    parser.add_argument("--output", type=str, default="ml/gradcam_output.png", help="Path to save overlay PNG")
    parser.add_argument("--class-idx", type=int, default=None, help="Target class index (optional)")
    args = parser.parse_args()

    image_path = PROJECT_ROOT / args.image
    checkpoint_path = PROJECT_ROOT / args.checkpoint
    output_path = PROJECT_ROOT / args.output

    if not image_path.exists():
        print(f"[ERROR] Image not found at {image_path}")
        sys.exit(1)
    if not checkpoint_path.exists():
        print(f"[ERROR] Model checkpoint not found at {checkpoint_path}")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    import timm
    model = timm.create_model(
        checkpoint["backbone"],
        pretrained=False,
        num_classes=checkpoint["num_classes"]
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device)

    overlay, _, pred_idx = generate_gradcam_for_image(
        model=model,
        image_path=image_path,
        img_size=checkpoint.get("img_size", 224),
        device=device,
        target_class_idx=args.class_idx
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(output_path)
    print(f"[OK] Saved Grad-CAM overlay for class {pred_idx} to: {output_path}")


if __name__ == "__main__":
    main()

"""
DermaSense Model Training Pipeline.
Implements:
- timm vision backbones (efficientnet_b3 default, efficientnet_b0 CPU fallback)
- ImageNet pretraining
- Two-stage training: Head-only warmup, then full backbone unfreezing with Cosine Annealing
- Class imbalance handling: Weighted Random Sampler & Multiclass Focal Loss
- Comprehensive data augmentations (flip, rotate, color jitter, blur, resize-crop)
- Mixed precision (AMP) when CUDA is available
- Early stopping on validation macro-F1
- Validation temperature scaling calibration (ECE before/after)
- OOD / low-confidence tuning via Max-Softmax & Energy Score thresholds
- Checkpointing, label map export (labels.json), and temperature export (temperature.json)
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import yaml
import pandas as pd
import numpy as np
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import torchvision.transforms as transforms
import timm
from sklearn.metrics import f1_score, accuracy_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_DIR = PROJECT_ROOT / "ml" / "weights"
LOGS_DIR = PROJECT_ROOT / "ml" / "logs"


# -----------------------------------------------------------------------------
# 1. Dataset & Transforms
# -----------------------------------------------------------------------------

class SkinDataset(Dataset):
    """PyTorch Dataset loading images from splits CSV."""
    def __init__(self, df: pd.DataFrame, label_to_idx: Dict[str, int], transform=None):
        self.df = df.reset_index(drop=True)
        self.label_to_idx = label_to_idx
        self.transform = transform

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str]:
        row = self.df.iloc[idx]
        rel_path = str(row["path"]).replace("\\", "/")
        full_path = PROJECT_ROOT / rel_path
        
        try:
            image = Image.open(full_path).convert("RGB")
        except Exception:
            # Fallback to pure RGB black if read fails
            image = Image.new("RGB", (224, 224), (0, 0, 0))

        if self.transform:
            image = self.transform(image)

        label_str = row["label"]
        label_idx = self.label_to_idx[label_str]
        return image, label_idx, rel_path


def get_transforms(img_size: int, is_train: bool = True) -> transforms.Compose:
    """Returns data augmentation pipeline for clinical & mobile photography."""
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )

    if is_train:
        return transforms.Compose([
            transforms.RandomResizedCrop(img_size, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.RandomRotation(degrees=180),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
            transforms.ToTensor(),
            normalize,
        ])
    else:
        return transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            normalize,
        ])


# -----------------------------------------------------------------------------
# 2. Loss Functions (Focal Loss)
# -----------------------------------------------------------------------------

class FocalLoss(nn.Module):
    """Multiclass Focal Loss addressing severe dermatological class imbalance."""
    def __init__(self, gamma: float = 2.0, alpha: Optional[torch.Tensor] = None):
        super().__init__()
        self.gamma = gamma
        self.alpha = alpha

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = F.cross_entropy(logits, targets, reduction="none", weight=self.alpha)
        pt = torch.exp(-ce_loss)
        focal_loss = ((1.0 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()


# -----------------------------------------------------------------------------
# 3. Model Architecture Factory
# -----------------------------------------------------------------------------

def build_model(backbone_name: str, num_classes: int, pretrained: bool = True, dropout: float = 0.3) -> nn.Module:
    """Instantiates a timm vision model with customized classification head."""
    print(f"[*] Constructing vision backbone: {backbone_name} (num_classes={num_classes}, pretrained={pretrained})")
    model = timm.create_model(
        backbone_name,
        pretrained=pretrained,
        num_classes=num_classes,
        drop_rate=dropout
    )
    return model


def freeze_backbone(model: nn.Module, freeze: bool = True):
    """Freezes or unfreezes backbone parameters, keeping classification head trainable."""
    # timm models expose get_classifier()
    head_params = set(model.get_classifier().parameters())
    for param in model.parameters():
        if param in head_params:
            param.requires_grad = True
        else:
            param.requires_grad = not freeze


# -----------------------------------------------------------------------------
# 4. Calibration: Temperature Scaling & Expected Calibration Error (ECE)
# -----------------------------------------------------------------------------

class ModelWithTemperature(nn.Module):
    """A wrapper for learned temperature scaling calibration."""
    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.model(x)
        return self.temperature_scale(logits)

    def temperature_scale(self, logits: torch.Tensor) -> torch.Tensor:
        temp = self.temperature.unsqueeze(1).expand(logits.size(0), logits.size(1))
        return logits / temp


def compute_ece(logits: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """Computes Expected Calibration Error (ECE)."""
    softmax_probs = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
    confidences = np.max(softmax_probs, axis=1)
    predictions = np.argmax(softmax_probs, axis=1)
    accuracies = (predictions == labels)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(labels)

    for i in range(n_bins):
        bin_lower, bin_upper = bin_boundaries[i], bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            avg_acc = np.mean(accuracies[in_bin])
            avg_conf = np.mean(confidences[in_bin])
            ece += np.abs(avg_acc - avg_conf) * prop_in_bin

    return float(ece)


def fit_temperature(logits_val: torch.Tensor, labels_val: torch.Tensor) -> float:
    """Fits optimal temperature scalar on validation set via NLL optimization."""
    temperature = nn.Parameter(torch.ones(1) * 1.5)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.LBFGS([temperature], lr=0.01, max_iter=100)

    def eval_loss():
        optimizer.zero_grad()
        loss = criterion(logits_val / temperature, labels_val)
        loss.backward()
        return loss

    optimizer.step(eval_loss)
    return float(temperature.item())


# -----------------------------------------------------------------------------
# 5. Out-of-Distribution (OOD) / Low-Confidence Energy Score
# -----------------------------------------------------------------------------

def compute_energy_scores(logits: torch.Tensor, T: float = 1.0) -> np.ndarray:
    """
    Computes negative free energy score:
    E(x) = -T * log(sum(exp(logits / T)))
    Higher energy score indicates in-distribution; lower indicates anomalous/OOD.
    """
    # -logsumexp
    energy = -(T * torch.logsumexp(logits / T, dim=1)).cpu().numpy()
    return energy


# -----------------------------------------------------------------------------
# 6. Training Routine
# -----------------------------------------------------------------------------

def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    use_amp: bool = False
) -> Tuple[float, float, float]:
    """Executes a single training epoch."""
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    all_preds, all_targets = [], []

    scaler = torch.amp.GradScaler('cuda') if use_amp and device.type == 'cuda' else None

    for images, targets, _ in loader:
        images, targets = images.to(device), targets.to(device)
        optimizer.zero_grad()

        if scaler:
            with torch.amp.autocast('cuda'):
                outputs = model(images)
                loss = criterion(outputs, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(images)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

        total_loss += loss.item() * len(targets)
        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += len(targets)

        all_preds.extend(preds.cpu().numpy())
        all_targets.extend(targets.cpu().numpy())

    avg_loss = total_loss / total
    acc = correct / total
    macro_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    return avg_loss, acc, macro_f1


@torch.no_grad()
def evaluate_loader(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, float, float, torch.Tensor, torch.Tensor]:
    """Evaluates validation or test dataloader returning metrics and raw logits."""
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    all_logits, all_targets = [], []

    for images, targets, _ in loader:
        images, targets = images.to(device), targets.to(device)
        outputs = model(images)
        loss = criterion(outputs, targets)

        total_loss += loss.item() * len(targets)
        all_logits.append(outputs.cpu())
        all_targets.append(targets.cpu())

    all_logits_t = torch.cat(all_logits, dim=0)
    all_targets_t = torch.cat(all_targets, dim=0)

    preds = all_logits_t.argmax(dim=1).numpy()
    targets_np = all_targets_t.numpy()

    avg_loss = total_loss / len(targets_np)
    acc = accuracy_score(targets_np, preds)
    macro_f1 = f1_score(targets_np, preds, average="macro", zero_division=0)

    return avg_loss, acc, macro_f1, all_logits_t, all_targets_t


# -----------------------------------------------------------------------------
# 7. Main Entrypoint
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DermaSense Model Training")
    parser.add_argument("--config", type=str, default="ml/config.yaml", help="Path to YAML config")
    parser.add_argument("--epochs-stage1", type=int, default=None, help="Override Stage 1 epochs")
    parser.add_argument("--epochs-stage2", type=int, default=None, help="Override Stage 2 epochs")
    parser.add_argument("--backbone", type=str, default=None, help="Override vision backbone")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    args = parser.parse_args()

    # Load configuration
    config_path = PROJECT_ROOT / args.config
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Hardware & Device Selection
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 80)
    print("DERMASENSE TRAINING PIPELINE")
    print("=" * 80)
    print(f"[*] Compute Device: {device}")
    
    use_amp = False
    if device.type == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        print(f"[OK] GPU Detected: {gpu_name} (CUDA Enabled, Mixed Precision Active)")
        use_amp = cfg["training"]["mixed_precision"]
        backbone_name = args.backbone or cfg["model"]["backbone"]
        img_size = cfg["model"]["img_size"]
        batch_size = args.batch_size or cfg["training"]["batch_size"]
    else:
        print("[!] WARNING: No CUDA GPU detected. Running on CPU.")
        print("    For full-scale training across 30,000+ clinical images, execute")
        print("    ml/train_kaggle.ipynb on Kaggle or Google Colab (free GPU available).")
        backbone_name = args.backbone or cfg["model"]["cpu_fallback_backbone"]
        img_size = cfg["model"]["cpu_img_size"]
        batch_size = args.batch_size or cfg["training"]["cpu_batch_size"]
        print(f"[*] CPU fallback mode active: backbone={backbone_name}, img_size={img_size}, batch_size={batch_size}")

    # 2. Load Dataset Splits
    splits_csv = PROJECT_ROOT / cfg["paths"]["splits_csv"]
    if not splits_csv.exists():
        print(f"[ERROR] Splits CSV not found at {splits_csv}. Run ml/data/prepare.py first.")
        sys.exit(1)

    df_splits = pd.read_csv(splits_csv)
    df_train = df_splits[df_splits["split"] == "train"].reset_index(drop=True)
    df_val = df_splits[df_splits["split"] == "val"].reset_index(drop=True)
    df_test = df_splits[df_splits["split"] == "test"].reset_index(drop=True)

    # Build unique label vocabulary
    unique_labels = sorted(df_splits["label"].unique().tolist())
    num_classes = len(unique_labels)
    label_to_idx = {lbl: i for i, lbl in enumerate(unique_labels)}
    idx_to_label = {i: lbl for i, lbl in enumerate(unique_labels)}

    print(f"[*] Unique Classes ({num_classes}): {unique_labels}")
    print(f"[*] Samples - Train: {len(df_train)} | Val: {len(df_val)} | Test: {len(df_test)}")

    # Check minimum classes requirement
    if num_classes < 2:
        print("\n" + "=" * 80)
        print("[STOPPED] INSUFFICIENT NUMBER OF CLASSES FOR TRAINING")
        print("=" * 80)
        print(f"Current splits.csv only has {num_classes} active class: {unique_labels}")
        print("A multi-class classifier requires at least 2 distinct classes to train.")
        print("\nWhat you need to do:")
        print("  1. Download HAM10000 or DermNet using your Kaggle credentials:")
        print("     Place 'kaggle.json' in ~/.kaggle/ and run 'python ml/data/download.py'")
        print("  2. Re-run 'python ml/data/prepare.py' to generate multi-class splits.")
        print("  3. Then re-run this training script.")
        print("=" * 80)
        sys.exit(0)

    # Save labels.json
    labels_path = PROJECT_ROOT / cfg["paths"]["labels_file"]
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump({"idx_to_label": idx_to_label, "label_to_idx": label_to_idx}, f, indent=2)
    print(f"[OK] Saved label mapping to: {labels_path}")

    # Compute class weights for imbalanced sampling/loss
    class_counts = df_train["label"].value_counts()
    total_train = len(df_train)
    weights_per_class = {
        lbl: total_train / (num_classes * class_counts.get(lbl, 1))
        for lbl in unique_labels
    }
    sample_weights = [weights_per_class[row["label"]] for _, row in df_train.iterrows()]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)

    # 3. DataLoaders
    train_dataset = SkinDataset(df_train, label_to_idx, transform=get_transforms(img_size, is_train=True))
    val_dataset = SkinDataset(df_val, label_to_idx, transform=get_transforms(img_size, is_train=False))
    test_dataset = SkinDataset(df_test, label_to_idx, transform=get_transforms(img_size, is_train=False))

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        sampler=sampler if cfg["training"]["imbalance"]["use_weighted_sampler"] else None,
        shuffle=False if cfg["training"]["imbalance"]["use_weighted_sampler"] else True,
        num_workers=cfg["training"]["num_workers"],
        pin_memory=(device.type == "cuda")
    )
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=cfg["training"]["num_workers"])
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=cfg["training"]["num_workers"])

    # 4. Instantiate Model
    model = build_model(
        backbone_name=backbone_name,
        num_classes=num_classes,
        pretrained=cfg["model"]["pretrained"],
        dropout=cfg["model"]["dropout"]
    ).to(device)

    # Loss function
    focal_gamma = cfg["training"]["imbalance"]["focal_gamma"]
    alpha_tensor = torch.tensor([weights_per_class[idx_to_label[i]] for i in range(num_classes)], dtype=torch.float32).to(device)
    criterion = FocalLoss(gamma=focal_gamma, alpha=alpha_tensor)

    # Checkpoint tracker
    best_macro_f1 = -1.0
    best_checkpoint_path = PROJECT_ROOT / cfg["paths"]["best_checkpoint"]
    patience = cfg["training"]["early_stopping"]["patience"]
    patience_counter = 0

    log_records = []

    # -------------------------------------------------------------------------
    # Stage 1: Warmup Classifier Head (Frozen Backbone)
    # -------------------------------------------------------------------------
    s1_epochs = args.epochs_stage1 or cfg["training"]["stage1"]["epochs"]
    s1_lr = cfg["training"]["stage1"]["lr"]
    print(f"\n--- STAGE 1: Head Warmup ({s1_epochs} epochs, lr={s1_lr}) ---")
    freeze_backbone(model, freeze=True)

    optimizer_s1 = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=s1_lr,
        weight_decay=cfg["training"]["stage1"]["weight_decay"]
    )

    for epoch in range(1, s1_epochs + 1):
        t0 = time.time()
        tr_loss, tr_acc, tr_f1 = train_epoch(model, train_loader, optimizer_s1, criterion, device, use_amp)
        va_loss, va_acc, va_f1, _, _ = evaluate_loader(model, val_loader, criterion, device)
        elapsed = time.time() - t0

        print(f"Stage 1 [Epoch {epoch:02d}/{s1_epochs:02d}] Tr Loss: {tr_loss:.4f} Acc: {tr_acc:.4f} F1: {tr_f1:.4f} | "
              f"Val Loss: {va_loss:.4f} Acc: {va_acc:.4f} F1: {va_f1:.4f} ({elapsed:.1f}s)")

        log_records.append({
            "stage": 1, "epoch": epoch,
            "train_loss": tr_loss, "train_acc": tr_acc, "train_f1": tr_f1,
            "val_loss": va_loss, "val_acc": va_acc, "val_f1": va_f1
        })

    # -------------------------------------------------------------------------
    # Stage 2: Full Fine-Tuning with Cosine Annealing LR Decay
    # -------------------------------------------------------------------------
    s2_epochs = args.epochs_stage2 or cfg["training"]["stage2"]["epochs"]
    s2_lr = cfg["training"]["stage2"]["lr"]
    print(f"\n--- STAGE 2: Full Backbone Fine-Tuning ({s2_epochs} epochs, lr={s2_lr} with Cosine Decay) ---")
    freeze_backbone(model, freeze=False)

    optimizer_s2 = torch.optim.AdamW(
        model.parameters(),
        lr=s2_lr,
        weight_decay=cfg["training"]["stage2"]["weight_decay"]
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer_s2,
        T_max=s2_epochs,
        eta_min=cfg["training"]["stage2"]["min_lr"]
    )

    for epoch in range(1, s2_epochs + 1):
        t0 = time.time()
        tr_loss, tr_acc, tr_f1 = train_epoch(model, train_loader, optimizer_s2, criterion, device, use_amp)
        va_loss, va_acc, va_f1, _, _ = evaluate_loader(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        current_lr = scheduler.get_last_lr()[0]
        print(f"Stage 2 [Epoch {epoch:02d}/{s2_epochs:02d}] LR: {current_lr:.2e} | "
              f"Tr Loss: {tr_loss:.4f} F1: {tr_f1:.4f} | "
              f"Val Loss: {va_loss:.4f} Acc: {va_acc:.4f} F1: {va_f1:.4f} ({elapsed:.1f}s)")

        log_records.append({
            "stage": 2, "epoch": s1_epochs + epoch,
            "train_loss": tr_loss, "train_acc": tr_acc, "train_f1": tr_f1,
            "val_loss": va_loss, "val_acc": va_acc, "val_f1": va_f1
        })

        # Early stopping and checkpointing on val_macro_f1
        if va_f1 > best_macro_f1:
            best_macro_f1 = va_f1
            patience_counter = 0
            torch.save({
                "backbone": backbone_name,
                "num_classes": num_classes,
                "state_dict": model.state_dict(),
                "label_to_idx": label_to_idx,
                "idx_to_label": idx_to_label,
                "val_macro_f1": va_f1,
                "val_acc": va_acc,
                "img_size": img_size
            }, best_checkpoint_path)
            print(f"  [+] Saved new best model checkpoint -> {best_checkpoint_path} (val_macro_f1: {va_f1:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"[!] Early stopping triggered after {patience} epochs without improvement.")
                break

    # Save training log to CSV
    log_df = pd.DataFrame(log_records)
    log_csv = LOGS_DIR / "training_log.csv"
    log_df.to_csv(log_csv, index=False)
    print(f"[OK] Saved full training metrics log to: {log_csv}")

    # -------------------------------------------------------------------------
    # Post-Training Calibration & OOD Tuning
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("RUNNING POST-TRAINING CALIBRATION & OOD THRESHOLD TUNING")
    print("=" * 80)

    # Load best model weights
    checkpoint = torch.load(best_checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    # Extract raw logits and labels from validation set
    _, _, _, val_logits, val_labels = evaluate_loader(model, val_loader, criterion, device)
    val_logits_np = val_logits.numpy()
    val_labels_np = val_labels.numpy()

    # 1. ECE Before Calibration
    ece_before = compute_ece(val_logits_np, val_labels_np)
    print(f"[*] Expected Calibration Error (ECE) BEFORE Temperature Scaling: {ece_before:.4f}")

    # 2. Fit Optimal Temperature
    best_temp = fit_temperature(val_logits, val_labels)
    calibrated_val_logits_np = val_logits_np / best_temp
    ece_after = compute_ece(calibrated_val_logits_np, val_labels_np)
    print(f"[*] Learned Optimal Temperature: {best_temp:.4f}")
    print(f"[*] Expected Calibration Error (ECE) AFTER Temperature Scaling:  {ece_after:.4f}")

    # 3. OOD & Low Confidence Threshold Tuning
    # Max-softmax threshold
    val_probs = np.exp(calibrated_val_logits_np) / np.sum(np.exp(calibrated_val_logits_np), axis=1, keepdims=True)
    val_max_probs = np.max(val_probs, axis=1)
    max_softmax_threshold = float(np.percentile(val_max_probs, cfg["ood"]["max_softmax_percentile"]))

    # Energy score threshold
    val_energy = compute_energy_scores(torch.from_numpy(calibrated_val_logits_np), T=cfg["ood"]["energy_temperature"])
    energy_threshold = float(np.percentile(val_energy, cfg["ood"]["energy_percentile"]))

    print(f"[*] OOD / Low-Confidence Max-Softmax Threshold: {max_softmax_threshold:.4f}")
    print(f"[*] OOD / Low-Confidence Energy Score Threshold: {energy_threshold:.4f}")

    # Save temperature.json
    temp_json_path = PROJECT_ROOT / cfg["paths"]["temperature_file"]
    with open(temp_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "temperature": best_temp,
            "ece_before": ece_before,
            "ece_after": ece_after,
            "max_softmax_threshold": max_softmax_threshold,
            "energy_threshold": energy_threshold,
            "backbone": backbone_name,
            "num_classes": num_classes
        }, f, indent=2)
    print(f"[OK] Saved temperature and OOD calibration artifacts to: {temp_json_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()


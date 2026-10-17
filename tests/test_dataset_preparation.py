"""
Automated Tests for Dataset Preparation & Zero-Leakage Splitting.
Tests:
- GroupStratified splitting by lesion_id
- Leakage detection when lesion_id or hash overlap is simulated
- Verification of exported CSV splits (path, label, source_dataset, split)
- Verification of class distribution chart in docs/
"""

import os
import sys
import tempfile
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.data.prepare import perform_stratified_group_split, assert_zero_leakage, compute_file_hash


def test_splits_files_exist():
    """Verify that splits.csv, train.csv, val.csv, test.csv and class_distribution.png were generated."""
    base_dir = Path(__file__).resolve().parents[1]
    splits_csv = base_dir / "data" / "splits.csv"
    train_csv = base_dir / "data" / "train.csv"
    val_csv = base_dir / "data" / "val.csv"
    test_csv = base_dir / "data" / "test.csv"
    dist_plot = base_dir / "docs" / "class_distribution.png"

    assert splits_csv.exists(), f"Missing {splits_csv}"
    assert train_csv.exists(), f"Missing {train_csv}"
    assert val_csv.exists(), f"Missing {val_csv}"
    assert test_csv.exists(), f"Missing {test_csv}"
    assert dist_plot.exists(), f"Missing {dist_plot}"

    df = pd.read_csv(splits_csv)
    assert len(df) > 0, "splits.csv is empty"
    for col in ["path", "label", "source_dataset", "split", "lesion_id", "sha256"]:
        assert col in df.columns, f"Expected column {col} in splits.csv"


def test_splits_ratio_approximately_70_15_15():
    """Verify split ratios are roughly 70% train, 15% val, 15% test."""
    base_dir = Path(__file__).resolve().parents[1]
    splits_csv = base_dir / "data" / "splits.csv"
    df = pd.read_csv(splits_csv)
    total = len(df)
    n_train = len(df[df["split"] == "train"])
    n_val = len(df[df["split"] == "val"])
    n_test = len(df[df["split"] == "test"])

    assert n_train + n_val + n_test == total
    assert abs(n_train / total - 0.70) < 0.05
    assert abs(n_val / total - 0.15) < 0.05
    assert abs(n_test / total - 0.15) < 0.05


def test_ham10000_lesion_id_group_splitting_unit():
    """Unit test for HAM10000 lesion_id grouping logic: verifies that multiple images of the same lesion never cross splits."""
    dummy_records = []
    # Create 50 distinct lesions with 2 to 3 images each across 2 classes
    for i in range(50):
        lesion_id = f"LESION_{i:04d}"
        label = "melanoma" if i < 25 else "nevus"
        num_images = 2 if i % 2 == 0 else 3
        for img_idx in range(num_images):
            dummy_records.append({
                "path": f"fake_path_{i}_{img_idx}.jpg",
                "abs_path": f"/tmp/fake_{i}_{img_idx}.jpg",
                "label": label,
                "source_dataset": "HAM10000",
                "lesion_id": lesion_id,
            })

    dummy_df = pd.DataFrame(dummy_records)
    split_df = perform_stratified_group_split(dummy_df, train_frac=0.70, val_frac=0.15, test_frac=0.15, seed=42)

    # Check for lesion_id leakage
    train_lesions = set(split_df[split_df["split"] == "train"]["lesion_id"])
    val_lesions = set(split_df[split_df["split"] == "val"]["lesion_id"])
    test_lesions = set(split_df[split_df["split"] == "test"]["lesion_id"])

    assert len(train_lesions.intersection(val_lesions)) == 0, "Lesion ID leakage between train and val!"
    assert len(train_lesions.intersection(test_lesions)) == 0, "Lesion ID leakage between train and test!"
    assert len(val_lesions.intersection(test_lesions)) == 0, "Lesion ID leakage between val and test!"


def test_simulated_leakage_assertion_raises_error():
    """Verify that assert_zero_leakage raises AssertionError if leakage is intentionally introduced."""
    leaky_df = pd.DataFrame([
        {"abs_path": "a.png", "label": "melanoma", "source_dataset": "HAM10000", "lesion_id": "L1", "split": "train"},
        {"abs_path": "b.png", "label": "melanoma", "source_dataset": "HAM10000", "lesion_id": "L1", "split": "test"}, # LEAK
    ])
    with pytest.raises(AssertionError):
        assert_zero_leakage(leaky_df)


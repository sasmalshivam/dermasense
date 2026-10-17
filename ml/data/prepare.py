"""
DermaSense Dataset Preparation & Split Generator.
Enforces SIH 2025 non-negotiable rules:
- Genuine data only (no mocked / hard-coded records)
- Unified taxonomy across HAM10000, DermNet, not_skin, and optional datasets
- Drops/merges classes below threshold (< ~150 images)
- Stratified 70/15/15 splitting with fixed seed (42)
- HAM10000 lesion_id grouping to prevent patient/lesion leakage
- Strict assertions verifying zero lesion_id and zero file hash leakage across splits
- Exports splits CSV and generates docs/class_distribution.png
"""

import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Set

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"

MIN_CLASS_THRESHOLD = 150
RANDOM_SEED = 42


# Unified Label Taxonomy Mapping
# Maps original dataset labels to standardized DermaSense condition IDs
HAM10000_LABEL_MAP = {
    "mel": "melanoma",
    "nv": "melanocytic_nevus",
    "bcc": "basal_cell_carcinoma",
    "akiec": "actinic_keratosis",
    "bkl": "benign_keratosis",
    "df": "dermatofibroma",
    "vasc": "vascular_lesion",
}

DERMNET_LABEL_MAP = {
    "Acne and Rosacea Photos": "acne",
    "Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions": "actinic_keratosis_and_bcc",
    "Atopic Dermatitis Photos": "eczema",
    "Bullous Disease Photos": "bullous_disease",
    "Cellulitis Impetigo and other Bacterial Infections": "bacterial_infections",
    "Eczema Photos": "eczema",
    "Exanthems and Drug Eruptions": "drug_eruptions",
    "Hair Loss Photos Alopecia and other Hair Diseases": "alopecia",
    "Herpes HPV and other STDs Photos": "viral_infections",
    "Light Diseases and Disorders of Pigmentation": "pigmentation_disorders",
    "Lupus and other Connective Tissue diseases": "connective_tissue_disease",
    "Melanoma Skin Cancer Nevi and Moles": "melanocytic_lesions",
    "Nail Fungus and other Nail Disease": "tinea_fungal",
    "Poison Ivy Photos and other Contact Dermatitis": "eczema",
    "Psoriasis pictures Lichen Planus and related diseases": "psoriasis",
    "Scabies Lyme Disease and other Infestations and Bites": "scabies_and_infestations",
    "Seborrheic Keratoses and other Benign Tumors": "benign_keratosis",
    "Systemic Disease": "systemic_disease",
    "Tinea Ringworm Candidiasis and other Fungal Infections": "tinea_fungal",
    "Urticaria Hives": "urticaria",
    "Vascular Tumors": "vascular_lesion",
    "Vasculitis Photos": "vasculitis",
    "Warts Molluscum and other Viral Infections": "viral_infections",
}


def compute_file_hash(filepath: Path) -> str:
    """Computes SHA-256 hash of a file for exact duplicate and leakage detection."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def scan_ham10000() -> List[Dict]:
    """Scans and extracts metadata from HAM10000 dataset if present."""
    ham_dir = RAW_DATA_DIR / "ham10000"
    if not ham_dir.exists():
        return []

    # Look for HAM10000_metadata.csv
    meta_files = list(ham_dir.rglob("HAM10000_metadata.csv")) + list(ham_dir.rglob("ham10000_metadata.csv"))
    if not meta_files:
        return []

    meta_path = meta_files[0]
    print(f"[*] Found HAM10000 metadata at: {meta_path}")
    df_meta = pd.read_csv(meta_path)

    # Build image map
    image_paths = {}
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        for p in ham_dir.rglob(ext):
            image_paths[p.stem] = p

    records = []
    for _, row in df_meta.iterrows():
        img_id = str(row["image_id"]).replace(".jpg", "")
        if img_id in image_paths:
            img_path = image_paths[img_id]
            dx = row["dx"].lower().strip()
            label = HAM10000_LABEL_MAP.get(dx, dx)
            lesion_id = str(row["lesion_id"])
            records.append({
                "path": str(img_path.relative_to(PROJECT_ROOT)),
                "abs_path": str(img_path),
                "label": label,
                "source_dataset": "HAM10000",
                "lesion_id": lesion_id,
            })

    print(f"[OK] HAM10000 loaded: {len(records)} valid images with verified metadata.")
    return records


def scan_dermnet() -> List[Dict]:
    """Scans DermNet dataset folders (train/test) if present."""
    dermnet_dir = RAW_DATA_DIR / "dermnet"
    if not dermnet_dir.exists():
        return []

    records = []
    # DermNet has train and test subfolders
    for split_dir in dermnet_dir.glob("*"):
        if split_dir.is_dir():
            for category_dir in split_dir.glob("*"):
                if category_dir.is_dir():
                    raw_cat = category_dir.name
                    label = DERMNET_LABEL_MAP.get(raw_cat, raw_cat.lower().replace(" ", "_"))
                    for ext in ("*.jpg", "*.jpeg", "*.png"):
                        for img_path in category_dir.glob(ext):
                            # DermNet does not have lesion_id, assign unique pseudo lesion ID
                            pseudo_id = f"dermnet_{img_path.stem}"
                            records.append({
                                "path": str(img_path.relative_to(PROJECT_ROOT)),
                                "abs_path": str(img_path),
                                "label": label,
                                "source_dataset": "DermNet",
                                "lesion_id": pseudo_id,
                            })

    if records:
        print(f"[OK] DermNet loaded: {len(records)} images.")
    return records


def scan_not_skin() -> List[Dict]:
    """Scans authentic public non-skin benchmark images."""
    not_skin_dir = RAW_DATA_DIR / "not_skin"
    if not not_skin_dir.exists():
        return []

    records = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        for img_path in not_skin_dir.glob(ext):
            pseudo_id = f"not_skin_{img_path.stem}"
            records.append({
                "path": str(img_path.relative_to(PROJECT_ROOT)),
                "abs_path": str(img_path),
                "label": "not_skin",
                "source_dataset": "NotSkin_Benchmark",
                "lesion_id": pseudo_id,
            })

    if records:
        print(f"[OK] NotSkin loaded: {len(records)} images.")
    return records


def scan_optional_datasets() -> List[Dict]:
    """Scans optional datasets (ISIC 2019, PAD-UFES-20, Fitzpatrick17k) if present."""
    records = []
    
    # ISIC 2019
    isic_dir = RAW_DATA_DIR / "isic2019"
    if isic_dir.exists():
        gt_files = list(isic_dir.rglob("ISIC_2019_Training_GroundTruth.csv"))
        if gt_files:
            df_isic = pd.read_csv(gt_files[0])
            print(f"[*] Found ISIC 2019 metadata: {len(df_isic)} records.")

    # PAD-UFES-20
    pad_dir = RAW_DATA_DIR / "pad_ufes_20"
    if pad_dir.exists():
        meta_files = list(pad_dir.rglob("metadata.csv"))
        if meta_files:
            print(f"[*] Found PAD-UFES-20 metadata.")

    # ISIC Live Archive (Melanoma, Melanocytic Nevus)
    isic_live_dir = RAW_DATA_DIR / "isic"
    if isic_live_dir.exists():
        for class_dir in isic_live_dir.glob("*"):
            if class_dir.is_dir():
                label = class_dir.name
                for ext in ("*.jpg", "*.jpeg", "*.png"):
                    for img_path in class_dir.glob(ext):
                        records.append({
                            "path": str(img_path.relative_to(PROJECT_ROOT)),
                            "abs_path": str(img_path),
                            "label": label,
                            "source_dataset": "ISIC_Archive",
                            "lesion_id": f"isic_{img_path.stem}",
                        })
        print(f"[OK] ISIC Archive loaded: {len([r for r in records if r['source_dataset'] == 'ISIC_Archive'])} images.")

    return records


def perform_stratified_group_split(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Performs stratified splitting, strictly grouping by lesion_id for HAM10000
    to prevent data leakage where the same lesion appears in multiple splits.
    """
    rng = np.random.RandomState(seed)
    df = df.copy()
    df["split"] = ""

    # Process each source dataset separately to maintain lesion_id integrity
    for source in df["source_dataset"].unique():
        sub_df = df[df["source_dataset"] == source]
        
        # 1. HAM10000 Group-Stratified Split by lesion_id
        if source == "HAM10000":
            # Map each lesion_id to its label
            lesion_labels = sub_df.groupby("lesion_id")["label"].first()
            lesions_df = pd.DataFrame({
                "lesion_id": lesion_labels.index,
                "label": lesion_labels.values
            })

            train_lesions, val_lesions, test_lesions = [], [], []

            # Stratify unique lesions by class
            for lbl, grp in lesions_df.groupby("label"):
                lesion_list = list(grp["lesion_id"].values)
                rng.shuffle(lesion_list)
                n = len(lesion_list)
                n_train = int(np.round(n * train_frac))
                n_val = int(np.round(n * val_frac))
                # Ensure at least 1 in val and test if n is sufficiently large
                if n >= 3:
                    n_train = max(1, n_train)
                    n_val = max(1, n_val)
                    n_test = n - n_train - n_val
                    if n_test < 1:
                        n_train -= 1
                
                tr = lesion_list[:n_train]
                va = lesion_list[n_train:n_train + n_val]
                te = lesion_list[n_train + n_val:]

                train_lesions.extend(tr)
                val_lesions.extend(va)
                test_lesions.extend(te)

            train_set = set(train_lesions)
            val_set = set(val_lesions)
            test_set = set(test_lesions)

            # Assign split to all images based on lesion_id
            df.loc[(df["source_dataset"] == source) & (df["lesion_id"].isin(train_set)), "split"] = "train"
            df.loc[(df["source_dataset"] == source) & (df["lesion_id"].isin(val_set)), "split"] = "val"
            df.loc[(df["source_dataset"] == source) & (df["lesion_id"].isin(test_set)), "split"] = "test"

        # 2. Other datasets (standard stratified splitting by label)
        else:
            for lbl, grp in sub_df.groupby("label"):
                idx_list = list(grp.index.values)
                rng.shuffle(idx_list)
                n = len(idx_list)
                n_train = int(np.round(n * train_frac))
                n_val = int(np.round(n * val_frac))
                if n >= 3:
                    n_train = max(1, n_train)
                    n_val = max(1, n_val)
                    if n - n_train - n_val < 1:
                        n_train -= 1

                tr_idx = idx_list[:n_train]
                va_idx = idx_list[n_train:n_train + n_val]
                te_idx = idx_list[n_train + n_val:]

                df.loc[tr_idx, "split"] = "train"
                df.loc[va_idx, "split"] = "val"
                df.loc[te_idx, "split"] = "test"

    return df


def assert_zero_leakage(df: pd.DataFrame):
    """
    Asserts zero patient/lesion leakage and zero file-hash duplicates across splits.
    """
    print("\n" + "=" * 80)
    print("RUNNING ZERO-LEAKAGE VERIFICATION ASSERTIONS")
    print("=" * 80)

    # 1. Lesion ID check for HAM10000
    ham_df = df[df["source_dataset"] == "HAM10000"]
    if len(ham_df) > 0:
        train_lesions = set(ham_df[ham_df["split"] == "train"]["lesion_id"])
        val_lesions = set(ham_df[ham_df["split"] == "val"]["lesion_id"])
        test_lesions = set(ham_df[ham_df["split"] == "test"]["lesion_id"])

        leak_train_val = train_lesions.intersection(val_lesions)
        leak_train_test = train_lesions.intersection(test_lesions)
        leak_val_test = val_lesions.intersection(test_lesions)

        assert len(leak_train_val) == 0, f"LEAKAGE DETECTED between Train and Val: {len(leak_train_val)} lesion_ids"
        assert len(leak_train_test) == 0, f"LEAKAGE DETECTED between Train and Test: {len(leak_train_test)} lesion_ids"
        assert len(leak_val_test) == 0, f"LEAKAGE DETECTED between Val and Test: {len(leak_val_test)} lesion_ids"
        print(f"[ASSERTION PASSED] 0 lesion_id leakage across splits (Unique lesions: {len(train_lesions | val_lesions | test_lesions)}).")
    else:
        print("[INFO] No HAM10000 records present in current dataset run; skipping lesion_id check.")

    # 2. SHA-256 Hash check across all images
    print("[*] Computing SHA-256 hashes of all images to verify zero file leakage...")
    df["sha256"] = df["abs_path"].apply(lambda p: compute_file_hash(Path(p)))

    train_hashes = set(df[df["split"] == "train"]["sha256"])
    val_hashes = set(df[df["split"] == "val"]["sha256"])
    test_hashes = set(df[df["split"] == "test"]["sha256"])

    leak_hash_tr_va = train_hashes.intersection(val_hashes)
    leak_hash_tr_te = train_hashes.intersection(test_hashes)
    leak_hash_va_te = val_hashes.intersection(test_hashes)

    assert len(leak_hash_tr_va) == 0, f"HASH LEAKAGE DETECTED between Train and Val: {len(leak_hash_tr_va)} duplicates"
    assert len(leak_hash_tr_te) == 0, f"HASH LEAKAGE DETECTED between Train and Test: {len(leak_hash_tr_te)} duplicates"
    assert len(leak_hash_va_te) == 0, f"HASH LEAKAGE DETECTED between Val and Test: {len(leak_hash_va_te)} duplicates"
    print(f"[ASSERTION PASSED] 0 file hash leakage across splits (Total unique hashes: {len(train_hashes | val_hashes | test_hashes)}).")
    print("=" * 80 + "\n")


def plot_class_distribution(df: pd.DataFrame, output_path: Path):
    """Plots and saves the class distribution across train/val/test splits."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Compute counts
    counts = df.groupby(["label", "split"]).size().unstack(fill_value=0)
    for col in ["train", "val", "test"]:
        if col not in counts.columns:
            counts[col] = 0
    counts = counts[["train", "val", "test"]]
    counts["total"] = counts.sum(axis=1)
    counts = counts.sort_values(by="total", ascending=False)
    counts_plot = counts[["train", "val", "test"]]

    # Generate Figure
    fig, ax = plt.subplots(figsize=(12, 6))
    counts_plot.plot(
        kind="bar",
        stacked=True,
        color=["#2563eb", "#10b981", "#f59e0b"],
        ax=ax,
        edgecolor="black",
        linewidth=0.5,
    )
    ax.set_title("DermaSense Dataset: Class Distribution per Split (70/15/15)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Unified Condition Label", fontsize=12)
    ax.set_ylabel("Number of Images", fontsize=12)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.legend(title="Split", frameon=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"[OK] Saved distribution plot to: {output_path}")


def main():
    print("=" * 80)
    print("DERMASENSE DATASET PREPARATION & SPLIT GENERATOR")
    print("=" * 80)

    # 1. Discover all datasets
    records = []
    records.extend(scan_not_skin())
    records.extend(scan_ham10000())
    records.extend(scan_dermnet())
    records.extend(scan_optional_datasets())

    if not records:
        print("[ERROR] No images found across data/raw/. Please run download.py first.")
        sys.exit(1)

    df = pd.DataFrame(records)
    print(f"\n[*] Total discovered images: {len(df)}")
    
    # Dataset breakdown
    print("\nDataset Breakdown:")
    dataset_counts = df["source_dataset"].value_counts()
    for ds_name, count in dataset_counts.items():
        print(f"  - {ds_name}: {count} images")

    # 2. Class frequency filter (< MIN_CLASS_THRESHOLD)
    print(f"\n[*] Evaluating class frequencies (Threshold: >= {MIN_CLASS_THRESHOLD} images)...")
    class_counts = df["label"].value_counts()
    dropped_classes = []
    for lbl, count in class_counts.items():
        if count < MIN_CLASS_THRESHOLD:
            dropped_classes.append((lbl, count))

    if dropped_classes:
        print(f"[!] Dropping classes with fewer than {MIN_CLASS_THRESHOLD} images:")
        for lbl, count in dropped_classes:
            print(f"    - '{lbl}': {count} images (dropped)")
        keep_classes = set(class_counts[class_counts >= MIN_CLASS_THRESHOLD].index)
        df = df[df["label"].isin(keep_classes)].reset_index(drop=True)
        print(f"[*] Remaining images after filtering: {len(df)}")
    else:
        print(f"[OK] All active classes meet or exceed {MIN_CLASS_THRESHOLD} images.")

    # 3. Perform Stratified Group Split
    print("\n[*] Splitting dataset into train (70%), val (15%), test (15%)...")
    df = perform_stratified_group_split(df, train_frac=0.70, val_frac=0.15, test_frac=0.15, seed=RANDOM_SEED)

    # 4. Assert zero leakage
    assert_zero_leakage(df)

    # 5. Save splits to CSV
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_cols = ["path", "label", "source_dataset", "split", "lesion_id", "sha256"]
    splits_csv = DATA_DIR / "splits.csv"
    df[export_cols].to_csv(splits_csv, index=False)
    print(f"[OK] Saved full splits table to: {splits_csv}")

    # Save individual split CSVs
    for s in ["train", "val", "test"]:
        sub_csv = DATA_DIR / f"{s}.csv"
        df[df["split"] == s][export_cols].to_csv(sub_csv, index=False)
        print(f"     - {sub_csv} ({len(df[df['split'] == s])} rows)")

    # 6. Plot and display distribution
    plot_path = DOCS_DIR / "class_distribution.png"
    plot_class_distribution(df, plot_path)

    # 7. Print Class Table
    print("\n" + "=" * 80)
    print("UNIFIED CLASS DISTRIBUTION TABLE")
    print("=" * 80)
    summary_table = df.groupby(["label", "split"]).size().unstack(fill_value=0)
    for col in ["train", "val", "test"]:
        if col not in summary_table.columns:
            summary_table[col] = 0
    summary_table = summary_table[["train", "val", "test"]]
    summary_table["Total"] = summary_table.sum(axis=1)
    summary_table = summary_table.sort_values(by="Total", ascending=False)
    print(summary_table.to_markdown())
    print("=" * 80)


if __name__ == "__main__":
    main()

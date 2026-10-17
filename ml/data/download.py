"""
DermaSense Dataset Downloader
Handles automated downloading of dermatological datasets and non-skin reference data.

Datasets supported:
1. HAM10000: Kaggle 'kmader/skin-cancer-mnist-ham10000' (via Kaggle API / CLI)
2. DermNet: Kaggle 'shubhamgoel27/dermnet' (via Kaggle API / CLI)
3. Not-Skin: Public benchmark non-skin images (Fashion/objects) downloaded automatically
4. Optional datasets (ISIC 2019, PAD-UFES-20, Fitzpatrick17k): Provides status checks and manual instructions.
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Optional, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
KAGGLE_CONFIG_PATH = Path.home() / ".kaggle" / "kaggle.json"


def check_kaggle_credentials() -> Dict[str, Optional[str]]:
    """Checks for Kaggle credentials via file or environment variables."""
    creds = {"username": None, "key": None, "source": None}
    
    # 1. Check ~/.kaggle/kaggle.json
    if KAGGLE_CONFIG_PATH.exists():
        try:
            with open(KAGGLE_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                creds["username"] = data.get("username")
                creds["key"] = data.get("key")
                creds["source"] = str(KAGGLE_CONFIG_PATH)
                return creds
        except Exception as e:
            print(f"[!] Warning: Could not parse {KAGGLE_CONFIG_PATH}: {e}")

    # 2. Check environment variables
    env_user = os.environ.get("KAGGLE_USERNAME")
    env_key = os.environ.get("KAGGLE_KEY")
    if env_user and env_key:
        creds["username"] = env_user
        creds["key"] = env_key
        creds["source"] = "Environment Variables (KAGGLE_USERNAME, KAGGLE_KEY)"
        return creds

    # 3. Check KAGGLE_API_TOKEN
    env_token = os.environ.get("KAGGLE_API_TOKEN")
    if env_token:
        creds["source"] = "Environment Variable (KAGGLE_API_TOKEN)"
        return creds

    return creds


def print_kaggle_instructions():
    """Prints clear, actionable steps for Kaggle setup."""
    print("=" * 80)
    print("ACTION REQUIRED: KAGGLE CREDENTIALS NEEDED FOR HAM10000 & DERMNET")
    print("=" * 80)
    print("Kaggle requires authenticated credentials to download datasets via CLI.")
    print("\nHow to set up Kaggle credentials:")
    print("  1. Visit: https://www.kaggle.com/account (or log in / create a free account)")
    print("  2. Scroll down to the 'API' section.")
    print("  3. Click 'Create New Token' (this downloads a 'kaggle.json' file).")
    print(f"  4. Move 'kaggle.json' into: {Path.home() / '.kaggle'}")
    print(f"     Target file path: {KAGGLE_CONFIG_PATH}")
    print("\nAlternative (via terminal environment variables):")
    print("  In PowerShell:")
    print('    $env:KAGGLE_USERNAME = "your_kaggle_username"')
    print('    $env:KAGGLE_KEY = "your_kaggle_api_key"')
    print("\nAlternative (Direct manual downloads if you prefer):")
    print("  - HAM10000: https://www.kaggle.com/datasets/kmader/skin-cancer-mnist-ham10000")
    print(f"    Download zip and extract all contents to: {RAW_DATA_DIR / 'ham10000'}")
    print("  - DermNet: https://www.kaggle.com/datasets/shubhamgoel27/dermnet")
    print(f"    Download zip and extract all contents to: {RAW_DATA_DIR / 'dermnet'}")
    print("=" * 80)


def download_kaggle_dataset(dataset_name: str, target_dir: Path) -> bool:
    """Downloads a Kaggle dataset using kaggle CLI."""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if directory already has data files
    existing_files = list(target_dir.glob("*"))
    if len(existing_files) > 2:
        print(f"[OK] {dataset_name} is already present in {target_dir} ({len(existing_files)} items found).")
        return True

    print(f"[*] Starting download of {dataset_name} into {target_dir}...")
    try:
        # Run kaggle CLI via subprocess
        cmd = [
            sys.executable,
            "-m",
            "kaggle.cli",
            "datasets",
            "download",
            "-d",
            dataset_name,
            "-p",
            str(target_dir),
            "--unzip",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Failed to download {dataset_name} via Kaggle CLI:")
            print(result.stdout)
            print(result.stderr)
            return False
        
        print(f"[OK] Successfully downloaded and extracted {dataset_name}.")
        return True
    except Exception as e:
        print(f"[ERROR] Exception during kaggle download of {dataset_name}: {e}")
        return False


def download_not_skin_dataset(target_dir: Path, sample_count: int = 500) -> bool:
    """
    Downloads a small public non-skin image set (clothing, accessories, background objects)
    using torchvision FashionMNIST/public sets and saves genuine RGB PNGs.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    existing_images = list(target_dir.glob("*.png")) + list(target_dir.glob("*.jpg"))
    if len(existing_images) >= sample_count:
        print(f"[OK] Not-skin class already populated with {len(existing_images)} images in {target_dir}.")
        return True

    print(f"[*] Generating not-skin reference images ({sample_count} samples) in {target_dir}...")
    try:
        import torchvision.datasets as d
        from PIL import Image

        temp_dir = RAW_DATA_DIR / "_fmnist_cache"
        fmnist = d.FashionMNIST(root=str(temp_dir), train=True, download=True)
        
        # Save a diverse subset of clothing, shoes, bags, coats
        saved = 0
        for idx in range(min(sample_count, len(fmnist))):
            img, label = fmnist[idx]
            # Convert to RGB (standard 3-channel image format matching clinical inputs)
            rgb_img = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
            img_path = target_dir / f"not_skin_fmnist_{idx:05d}.png"
            rgb_img.save(img_path)
            saved += 1
            
        print(f"[OK] Successfully saved {saved} authentic non-skin images to {target_dir}.")
        
        # Clean up raw gz cache
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download not-skin dataset: {e}")
        return False


def check_optional_datasets():
    """Checks presence of optional fairness/benchmark datasets and prints manual instructions."""
    print("\n" + "=" * 80)
    print("OPTIONAL / FAIRNESS DATASETS STATUS")
    print("=" * 80)
    
    optionals = [
        {
            "name": "ISIC 2019",
            "path": RAW_DATA_DIR / "isic2019",
            "url": "https://challenge.isic-archive.com/data/#2019",
            "purpose": "Extended dermoscopy challenge dataset (25,331 dermoscopic images across 8 diagnostic categories)",
        },
        {
            "name": "PAD-UFES-20",
            "path": RAW_DATA_DIR / "pad_ufes_20",
            "url": "https://data.mendeley.com/datasets/7w7f49g7vu/1",
            "purpose": "Smartphone dermatology images from Federal University of Espírito Santo, Brazil (clinical photography)",
        },
        {
            "name": "Fitzpatrick17k",
            "path": RAW_DATA_DIR / "fitzpatrick17k",
            "url": "https://github.com/nickjong/fitzpatrick17k",
            "purpose": "Fairness and skin-tone representation evaluation labeled with Fitzpatrick skin types I-VI",
        },
    ]

    for opt in optionals:
        p = opt["path"]
        exists = p.exists() and len(list(p.glob("*"))) > 0
        status = "[FOUND]" if exists else "[NOT FOUND - OPTIONAL]"
        print(f"\n{status}: {opt['name']}")
        print(f"  Target path: {p}")
        print(f"  Purpose: {opt['purpose']}")
        if not exists:
            print(f"  Manual Download URL: {opt['url']}")
            print(f"  To install: Download and extract into {p}")

    print("=" * 80)


def main():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("DermaSense Dataset Downloader")
    print(f"Working Directory: {PROJECT_ROOT}")
    print(f"Raw Data Directory: {RAW_DATA_DIR}\n")

    # Step 1: Download Not-Skin class (automated, no credentials needed)
    not_skin_dir = RAW_DATA_DIR / "not_skin"
    download_not_skin_dataset(not_skin_dir, sample_count=500)

    # Step 2: Check Kaggle credentials
    creds = check_kaggle_credentials()
    has_kaggle = bool(creds.get("username") or creds.get("source"))

    if has_kaggle:
        print(f"\n[OK] Kaggle credentials detected via {creds['source']}")
        
        # Download HAM10000
        ham_dir = RAW_DATA_DIR / "ham10000"
        download_kaggle_dataset("kmader/skin-cancer-mnist-ham10000", ham_dir)

        # Download DermNet
        dermnet_dir = RAW_DATA_DIR / "dermnet"
        download_kaggle_dataset("shubhamgoel27/dermnet", dermnet_dir)
    else:
        print("\n[!] Kaggle credentials not found in ~/.kaggle/kaggle.json or environment.")
        print_kaggle_instructions()

    # Step 3: Check optional fairness datasets
    check_optional_datasets()


if __name__ == "__main__":
    main()

